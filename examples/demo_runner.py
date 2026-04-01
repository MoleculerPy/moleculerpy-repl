#!/usr/bin/env python3
"""Demo script to test moleculerpy-runner with mock broker.

This demonstrates the runner without requiring actual MoleculerPy installation.

Usage:
    # Single worker with REPL (recommended for testing)
    python demo_runner.py --repl

    # Multiple workers (4 instances) - requires actual MoleculerPy
    python demo_runner.py -i 4

    # For multi-worker mode, install MoleculerPy first:
    # pip install ../moleculerpy
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import sys
import time
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MockService:
    """Mock service for demo."""

    name = "math"
    version = "1"
    full_name = "v1.math"
    actions = {
        "add": lambda params: params.get("a", 0) + params.get("b", 0),
        "multiply": lambda params: params.get("a", 0) * params.get("b", 0),
    }
    events = {}


class GreeterService:
    """Mock greeter service."""

    name = "greeter"
    version = "1"
    full_name = "v1.greeter"
    actions = {
        "hello": lambda params: f"Hello, {params.get('name', 'World')}!",
    }
    events = {"user.created": True}


class MockBroker:
    """Mock broker for demo without actual MoleculerPy."""

    def __init__(self, node_id: str = "mock-node", heartbeat_interval: float = 0):
        self.id = node_id
        self.node_id = node_id
        self.services = {
            "math": MockService(),
            "greeter": GreeterService(),
        }
        self.started_at = None
        self.namespace = None
        self.__version__ = "0.1.0"
        self.PROTOCOL_VERSION = "4"

        # Heartbeat settings
        self.heartbeat_interval = heartbeat_interval  # 0 = disabled
        self._heartbeat_task = None

        # Initialize logger factory for Moleculer-style logging
        from moleculerpy_repl.logger import LogFormat, LoggerFactory, LogLevel

        self.logger_factory = LoggerFactory(
            node_id=node_id,
            level=LogLevel.INFO,
            format=LogFormat.FULL,
            colors=True,
        )
        self.logger = self.logger_factory.get_logger("BROKER")
        self._discovery_log = self.logger_factory.get_logger("DISCOVERY")

    async def start(self) -> None:
        """Start the broker."""
        self.started_at = time.time()
        self.logger.info("ServiceBroker is starting...")
        self.logger.info(f"Node ID: {self.id}")
        self.logger.debug("Initializing services...")
        for name in self.services:
            self.logger.debug(f"  Registering service: {name}")
        self.logger.success(f"ServiceBroker started with {len(self.services)} service(s)")

        # Start heartbeat task if enabled
        if self.heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._discovery_log.debug(f"Heartbeat started (interval: {self.heartbeat_interval}s)")

    async def _heartbeat_loop(self) -> None:
        """Background heartbeat loop."""
        import psutil

        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                cpu = psutil.cpu_percent(interval=0)
                self._discovery_log.trace(f"Heartbeat sent (CPU: {cpu:.1f}%)")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._discovery_log.warn(f"Heartbeat error: {e}")

    async def stop(self) -> None:
        """Stop the broker."""
        # Stop heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
            self._discovery_log.debug("Heartbeat stopped")

        self.logger.info("ServiceBroker is stopping...")
        self.logger.success("ServiceBroker stopped")

    async def call(self, action: str, params: dict = None, **kwargs) -> Any:
        """Call an action."""
        transit_log = self.logger_factory.get_logger("TRANSIT")
        transit_log.debug(f"=> Call '{action}'", params=params)

        service_name, action_name = action.split(".", 1)
        service = self.services.get(service_name)

        if not service:
            self.logger.error(f"Service '{service_name}' not found")
            raise Exception(f"Service '{service_name}' not found")

        action_fn = service.actions.get(action_name)
        if not action_fn:
            self.logger.error(f"Action '{action}' not found")
            raise Exception(f"Action '{action}' not found")

        result = action_fn(params or {})
        transit_log.debug(f"<= Response '{action}'", result=result)
        return result

    async def emit(self, event: str, params: dict = None, **kwargs) -> None:
        """Emit an event."""
        transit_log = self.logger_factory.get_logger("TRANSIT")
        transit_log.debug(f"=> Emit '{event}'", params=params)

    async def broadcast(self, event: str, params: dict = None, **kwargs) -> None:
        """Broadcast an event."""
        transit_log = self.logger_factory.get_logger("TRANSIT")
        transit_log.debug(f"=> Broadcast '{event}'", params=params)


async def run_single_worker_demo(node_id: str, with_repl: bool = True, heartbeat: float = 0):
    """Run a single worker demo with mock broker."""
    from moleculerpy_repl.repl import REPL

    print("=" * 60)
    print("MoleculerPy Runner Demo (Single Worker Mode)")
    print("=" * 60)
    print(f"Node ID: {node_id}")
    print(f"REPL: {with_repl}")
    print("=" * 60)
    print()

    # Create and start mock broker
    broker = MockBroker(node_id=node_id, heartbeat_interval=heartbeat)
    await broker.start()

    if with_repl:
        # Start REPL
        # Note: REPL.run() calls broker.stop() in finally block,
        # so we don't need to stop it here
        repl = REPL(
            broker=broker,
            delimiter=f"{node_id} $ ",
        )
        await repl.run()
    else:
        # Wait for shutdown signal
        shutdown_event = asyncio.Event()

        def handle_signal(signum, frame):
            print("\nShutdown signal received")
            shutdown_event.set()

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        print("Running... Press Ctrl+C to stop")
        await shutdown_event.wait()
        # Only stop broker manually when not using REPL
        await broker.stop()


def main():
    """Run the demo."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Demo moleculerpy-runner with mock broker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single worker with REPL (default)
  python demo_runner.py --repl

  # Specify node ID
  python demo_runner.py -n my-node --repl

  # Without REPL (just keeps running)
  python demo_runner.py -n worker-1

Note: Multi-worker mode (-i > 1) requires actual MoleculerPy installation.
For testing REPL and commands, use single worker mode.
""",
    )
    parser.add_argument(
        "-i",
        "--instances",
        type=int,
        default=1,
        help="Number of worker instances (requires MoleculerPy for >1)",
    )
    parser.add_argument("-r", "--repl", action="store_true", help="Start REPL")
    parser.add_argument("-n", "--node-id", type=str, default="demo-node", help="Node ID prefix")
    parser.add_argument(
        "--heartbeat", type=float, default=0, help="Heartbeat interval in seconds (0 = disabled)"
    )

    args = parser.parse_args()

    if args.instances > 1:
        # Multi-worker mode requires actual MoleculerPy
        print("Multi-worker mode requires actual MoleculerPy installation.")
        print("For demo purposes, use single worker mode:")
        print("  python demo_runner.py --repl")
        print()
        print("To use multi-worker mode:")
        print("  1. Install MoleculerPy: pip install ../moleculerpy")
        print("  2. Run: moleculerpy-runner -i 4 ./services/")
        sys.exit(1)

    # Single worker demo
    try:
        asyncio.run(run_single_worker_demo(args.node_id, args.repl, args.heartbeat))
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
