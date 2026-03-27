"""MoleculerPy Runner — CLI for starting MoleculerPy microservices.

Similar to moleculer-runner, this module provides:
- CLI entry point for services
- Multi-worker support via multiprocessing
- Graceful shutdown handling
- REPL integration (on worker 1)

Usage:
    # Single worker
    moleculerpy-runner services/

    # Multiple workers (instances)
    moleculerpy-runner -i 4 services/

    # Auto-detect CPU count
    moleculerpy-runner -i 0 services/

    # With REPL (only on worker 1)
    moleculerpy-runner --repl services/
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import inspect
import json
import multiprocessing as mp
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

__all__ = ["Runner", "RunnerConfig", "run_cli", "main"]


@dataclass
class RunnerConfig:
    """Configuration for MoleculerPy Runner."""

    # Service paths to load
    service_paths: list[str] = field(default_factory=list)

    # Number of worker instances (0 = auto-detect CPU count)
    instances: int = 1

    # Enable REPL (only on worker 1)
    repl: bool = False

    # REPL delimiter
    repl_delimiter: str = "$ "

    # Config file path
    config_file: str | None = None

    # Environment file (.env)
    env_file: str | None = None

    # Hot reload services on file change
    hot_reload: bool = False

    # Log level
    log_level: str = "INFO"

    # Transporter URL (e.g., "redis://localhost")
    transporter: str | None = None

    # Node ID prefix
    node_id: str | None = None


class WorkerManager:
    """Manages worker processes for multi-instance mode.

    Based on Node.js cluster module pattern:
    - Master process spawns and monitors workers
    - Workers run the actual broker
    - Auto-restart on crash (production mode)
    - Graceful shutdown on signals
    """

    def __init__(
        self,
        num_workers: int,
        worker_fn: Callable[[int, "RunnerConfig"], None],
        config: RunnerConfig,
    ):
        self.num_workers = num_workers
        self.worker_fn = worker_fn
        self.config = config
        self.workers: dict[int, mp.Process] = {}
        self.stopping = False
        self._lock = mp.Lock()

    def start(self) -> None:
        """Start all workers."""
        print(f"[Master] Starting {self.num_workers} workers...")

        for worker_id in range(1, self.num_workers + 1):
            self._spawn_worker(worker_id)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        self._monitor_workers()

    def _spawn_worker(self, worker_id: int) -> None:
        """Spawn a single worker process."""
        process = mp.Process(
            target=self.worker_fn,
            args=(worker_id, self.config),
            name=f"worker-{worker_id}",
        )
        process.start()
        self.workers[worker_id] = process
        print(f"[Master] Worker #{worker_id} started (PID: {process.pid})")

    def _monitor_workers(self) -> None:
        """Monitor workers and restart on crash."""
        while not self.stopping:
            for worker_id, process in list(self.workers.items()):
                if not process.is_alive():
                    exit_code = process.exitcode

                    if not self.stopping and exit_code != 0:
                        # Restart crashed worker in production
                        is_production = os.environ.get("MOLECULERPY_ENV") == "production"

                        if is_production:
                            print(f"[Master] Worker #{worker_id} crashed (code={exit_code}), restarting...")
                            self._spawn_worker(worker_id)
                        else:
                            print(f"[Master] Worker #{worker_id} exited (code={exit_code})")

            time.sleep(0.5)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        if self.stopping:
            return

        sig_name = signal.Signals(signum).name
        print(f"\n[Master] Got {sig_name}, stopping workers...")
        self.stopping = True

        self._stop_all_workers()

    def _stop_all_workers(self, timeout: float = 10.0) -> None:
        """Stop all workers gracefully."""
        # Send SIGTERM to all workers
        for worker_id, process in self.workers.items():
            if process.is_alive():
                print(f"[Master] Stopping worker #{worker_id}...")
                process.terminate()

        # Wait for workers to finish
        deadline = time.time() + timeout
        for worker_id, process in self.workers.items():
            remaining = max(0, deadline - time.time())
            process.join(timeout=remaining)

            if process.is_alive():
                print(f"[Master] Force-killing worker #{worker_id}")
                process.kill()

        print("[Master] All workers stopped.")


class Runner:
    """MoleculerPy service runner.

    Loads services and starts the broker, with optional:
    - Multi-worker mode (multiprocessing)
    - REPL integration
    - Hot reload
    """

    def __init__(self, config: RunnerConfig):
        self.config = config
        self.broker: Any = None
        self.worker_id: int | None = None

    def run(self) -> None:
        """Run the services.

        - If instances > 1: spawn worker processes
        - If instances == 1: run directly
        """
        if self.config.instances > 1 or self.config.instances == 0:
            num_workers = (
                self.config.instances
                if self.config.instances > 0
                else mp.cpu_count()
            )
            manager = WorkerManager(num_workers, _worker_main, self.config)
            manager.start()
        else:
            # Single worker mode
            self.worker_id = 1
            asyncio.run(self._run_broker())

    async def _run_broker(self) -> None:
        """Run the broker with services."""
        # Load environment file if specified
        if self.config.env_file:
            _load_env_file(self.config.env_file)

        self.broker = await self._create_broker()

        # Load services
        service_classes: list[type[Any]] = []
        for path in self.config.service_paths:
            service_classes.extend(self._load_services_from_path(path))

        for service_class in service_classes:
            await self._register_service(service_class)

        # Start broker
        await self.broker.start()
        node_id = (
            getattr(self.broker, "nodeID", None)
            or getattr(self.broker, "node_id", None)
            or getattr(self.broker, "id", "unknown")
        )
        print(f"[Worker #{self.worker_id}] Broker started (nodeID: {node_id})")

        # Start REPL (only on worker 1)
        if self.config.repl and self.worker_id == 1:
            await self._start_repl()
        else:
            # Keep running until signal
            await self._wait_for_shutdown()

    async def _create_broker(self) -> Any:
        """Create a broker from config file or default runner settings."""
        if self.config.config_file:
            return await self._create_broker_from_config_file(self.config.config_file)
        return self._create_default_broker()

    def _create_default_broker(self) -> Any:
        """Create a standard ServiceBroker instance."""
        try:
            moleculerpy_module = importlib.import_module("moleculerpy")
            service_broker_cls = getattr(moleculerpy_module, "ServiceBroker")
            settings_cls = getattr(moleculerpy_module, "Settings")
        except ImportError:
            print("Error: MoleculerPy is not installed. Install with: pip install moleculerpy")
            sys.exit(1)

        broker_config = self._build_broker_config()
        broker_id = str(broker_config["node_id"])
        settings_kwargs = {
            "log_level": broker_config["log_level"],
        }
        transporter = broker_config.get("transporter")
        if transporter:
            settings_kwargs["transporter"] = transporter

        settings = settings_cls(**settings_kwargs)
        return service_broker_cls(id=broker_id, settings=settings)

    async def _create_broker_from_config_file(self, config_file: str) -> Any:
        """Create a broker using a config file.

        Supported formats:
        - `.py`: must export `create_broker` or `broker_factory`
        - `.json`, `.yaml`, `.yml`: basic broker settings mapping
        """
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        suffix = config_path.suffix.lower()
        if suffix == ".py":
            return await self._create_broker_from_python_config(config_path)
        if suffix in {".json", ".yaml", ".yml"}:
            config_data = self._load_structured_config(config_path)
            return self._create_broker_from_mapping(config_data)

        raise ValueError(
            f"Unsupported config file format: {config_file}. "
            "Use .py, .json, .yaml, or .yml"
        )

    async def _create_broker_from_python_config(self, config_path: Path) -> Any:
        """Create a broker from a Python config file."""
        spec = importlib.util.spec_from_file_location(config_path.stem, config_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load config module: {config_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        factory = getattr(module, "create_broker", None) or getattr(
            module, "broker_factory", None
        )
        if not callable(factory):
            raise ValueError(
                f"Python config {config_path} must define create_broker(...) "
                "or broker_factory(...)"
            )

        kwargs: dict[str, Any] = {}
        signature = inspect.signature(factory)
        if "config" in signature.parameters:
            kwargs["config"] = self.config
        if "worker_id" in signature.parameters:
            kwargs["worker_id"] = self.worker_id

        result = factory(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    def _load_structured_config(self, config_path: Path) -> dict[str, Any]:
        """Load JSON or YAML runner configuration."""
        if config_path.suffix.lower() == ".json":
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Config file must contain a JSON object: {config_path}")
            return data

        try:
            import yaml
        except ImportError as err:
            raise RuntimeError(
                "YAML config requires PyYAML. Install with: pip install pyyaml"
            ) from err

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain an object: {config_path}")
        return data

    def _create_broker_from_mapping(self, config_data: dict[str, Any]) -> Any:
        """Create a default broker from a JSON/YAML configuration mapping."""
        merged = dict(config_data)
        if self.config.node_id is not None:
            merged["node_id"] = self.config.node_id
        if self.config.transporter is not None:
            merged["transporter"] = self.config.transporter
        if self.config.log_level:
            merged["log_level"] = self.config.log_level

        try:
            moleculerpy_module = importlib.import_module("moleculerpy")
            service_broker_cls = getattr(moleculerpy_module, "ServiceBroker")
            settings_cls = getattr(moleculerpy_module, "Settings")
        except ImportError:
            print("Error: MoleculerPy is not installed. Install with: pip install moleculerpy")
            sys.exit(1)

        broker_id = str(
            merged.get("node_id")
            or self._build_broker_config()["node_id"]
        )
        settings_kwargs = {
            "log_level": str(merged.get("log_level", self.config.log_level)),
        }
        transporter = merged.get("transporter")
        if transporter:
            settings_kwargs["transporter"] = str(transporter)

        settings = settings_cls(**settings_kwargs)
        return service_broker_cls(id=broker_id, settings=settings)

    def _build_broker_config(self) -> dict[str, Any]:
        """Build broker configuration."""
        config: dict[str, Any] = {}

        # Node ID with worker suffix
        if self.config.node_id:
            base_id = self.config.node_id
        else:
            import socket
            base_id = socket.gethostname()

        if self.worker_id and self.worker_id > 1:
            config["node_id"] = f"{base_id}-{self.worker_id}"
        else:
            config["node_id"] = base_id

        # Transporter
        if self.config.transporter:
            config["transporter"] = self.config.transporter

        # Log level
        config["log_level"] = self.config.log_level

        return config

    async def _register_service(self, service_class: type[Any]) -> None:
        """Register one loaded service class on the active broker."""
        if hasattr(self.broker, "register"):
            await self.broker.register(service_class())
            print(f"[Worker #{self.worker_id}] Loaded service: {service_class.__name__}")
            return

        if hasattr(self.broker, "create_service"):
            self.broker.create_service(service_class)
            print(f"[Worker #{self.worker_id}] Loaded service: {service_class.__name__}")
            return

        raise RuntimeError("Broker does not support register() or create_service()")

    def _load_services_from_path(self, path: str) -> list[type[Any]]:
        """Load services from a path.

        Supports:
        - Directory with service files
        - Single Python file
        - Python module path
        """
        p = Path(path)

        if p.is_dir():
            # Load all .py files in directory
            service_classes: list[type[Any]] = []
            for file in p.glob("*.py"):
                if not file.name.startswith("_"):
                    service_classes.extend(self._load_service_file(file))
            return service_classes
        if p.is_file() and p.suffix == ".py":
            return self._load_service_file(p)
        # Try as module path
        return self._load_service_module(path)

    def _load_service_file(self, filepath: Path) -> list[type[Any]]:
        """Load service from a Python file."""
        parent_dir = str(filepath.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return _discover_service_classes(module)
        return []

    def _load_service_module(self, module_path: str) -> list[type[Any]]:
        """Load service from a Python module."""
        try:
            module = importlib.import_module(module_path)
            return _discover_service_classes(module)
        except ImportError as e:
            print(f"Warning: Could not load module {module_path}: {e}")
            return []

    async def _start_repl(self) -> None:
        """Start the REPL."""
        from .repl import REPL

        repl = REPL(
            broker=self.broker,
            delimiter=self.config.repl_delimiter,
        )
        await repl.run()

    async def _wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        shutdown_event = asyncio.Event()

        def handle_signal(signum: int, frame: Any) -> None:
            print(f"\n[Worker #{self.worker_id}] Shutdown signal received")
            shutdown_event.set()

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        await shutdown_event.wait()

        # Graceful shutdown
        if hasattr(self.broker, "stop"):
            await self.broker.stop()


def _worker_main(worker_id: int, config: RunnerConfig) -> None:
    """Main function for worker processes."""
    runner = Runner(config)
    runner.worker_id = worker_id
    asyncio.run(runner._run_broker())


def _load_env_file(filepath: str) -> None:
    """Load environment variables from a file."""
    p = Path(filepath)
    if not p.exists():
        print(f"Warning: Env file not found: {filepath}")
        return

    with open(p) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip().strip("\"'")


def _is_service_class(obj: Any) -> bool:
    """Check if object is a MoleculerPy service class."""
    if not isinstance(obj, type):
        return False

    try:
        service_cls = getattr(importlib.import_module("moleculerpy"), "Service")
    except (ImportError, AttributeError):
        service_cls = None

    if service_cls is not None:
        try:
            return issubclass(obj, service_cls) and obj is not service_cls
        except TypeError:
            return False

    # Fallback for tests or lightweight mock services.
    if not hasattr(obj, "name"):
        return False

    return hasattr(obj, "actions") or hasattr(obj, "events") or hasattr(obj, "mixins")


def _discover_service_classes(module: Any) -> list[type[Any]]:
    """Return all service classes defined directly in a module."""
    service_classes: list[type[Any]] = []
    for name in dir(module):
        obj = getattr(module, name)
        if _is_service_class(obj) and getattr(obj, "__module__", None) == module.__name__:
            service_classes.append(obj)
    return service_classes


def run_cli(args: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(
        description="MoleculerPy Service Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single worker
  moleculerpy-runner services/

  # Multiple workers (4 instances)
  moleculerpy-runner -i 4 services/

  # Auto-detect CPU count
  moleculerpy-runner -i 0 services/

  # With REPL
  moleculerpy-runner --repl services/

  # With Redis transporter
  moleculerpy-runner -T redis://localhost services/
""",
    )

    parser.add_argument(
        "services",
        nargs="*",
        help="Service paths to load (directories or files)",
    )

    parser.add_argument(
        "-i", "--instances",
        type=int,
        default=1,
        help="Number of worker instances (0 = auto-detect CPU count)",
    )

    parser.add_argument(
        "-r", "--repl",
        action="store_true",
        help="Start REPL (only on worker 1)",
    )

    parser.add_argument(
        "-e", "--env",
        type=str,
        help="Path to .env file",
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        help="Path to config file (JSON/YAML)",
    )

    parser.add_argument(
        "-T", "--transporter",
        type=str,
        help="Transporter URL (e.g., redis://localhost)",
    )

    parser.add_argument(
        "-n", "--node-id",
        type=str,
        help="Node ID prefix",
    )

    parser.add_argument(
        "-H", "--hot-reload",
        action="store_true",
        help="Enable hot reload on file changes",
    )

    parser.add_argument(
        "-l", "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level (default: INFO)",
    )

    parsed = parser.parse_args(args)

    config = RunnerConfig(
        service_paths=parsed.services or ["."],
        instances=parsed.instances,
        repl=parsed.repl,
        env_file=parsed.env,
        config_file=parsed.config,
        transporter=parsed.transporter,
        node_id=parsed.node_id,
        hot_reload=parsed.hot_reload,
        log_level=parsed.log_level,
    )

    runner = Runner(config)

    try:
        runner.run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Entry point for moleculerpy-runner command."""
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
