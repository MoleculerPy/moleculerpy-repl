"""Tests for moleculerpy-runner."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest

from moleculerpy_repl.runner import (
    Runner,
    RunnerConfig,
    WorkerManager,
    run_cli,
    _load_env_file,
    _is_service_class,
)


class TestRunnerConfig:
    """Tests for RunnerConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RunnerConfig()

        assert config.service_paths == []
        assert config.instances == 1
        assert config.repl is False
        assert config.repl_delimiter == "$ "
        assert config.config_file is None
        assert config.env_file is None
        assert config.hot_reload is False
        assert config.log_level == "INFO"
        assert config.transporter is None
        assert config.node_id is None

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = RunnerConfig(
            service_paths=["./services", "./other"],
            instances=4,
            repl=True,
            repl_delimiter=">>> ",
            transporter="redis://localhost",
            node_id="my-node",
            log_level="DEBUG",
        )

        assert config.service_paths == ["./services", "./other"]
        assert config.instances == 4
        assert config.repl is True
        assert config.repl_delimiter == ">>> "
        assert config.transporter == "redis://localhost"
        assert config.node_id == "my-node"
        assert config.log_level == "DEBUG"


class TestRunner:
    """Tests for Runner class."""

    def test_init(self) -> None:
        """Test Runner initialization."""
        config = RunnerConfig(instances=2, repl=True)
        runner = Runner(config)

        assert runner.config == config
        assert runner.broker is None
        assert runner.worker_id is None

    def test_build_broker_config_with_node_id(self) -> None:
        """Test broker config generation with custom node ID."""
        config = RunnerConfig(
            node_id="test-node",
            transporter="redis://localhost",
            log_level="DEBUG",
        )
        runner = Runner(config)
        runner.worker_id = 1

        broker_config = runner._build_broker_config()

        assert broker_config["node_id"] == "test-node"
        assert broker_config["transporter"] == "redis://localhost"
        assert broker_config["log_level"] == "DEBUG"

    def test_build_broker_config_with_worker_suffix(self) -> None:
        """Test broker config adds worker suffix for worker > 1."""
        config = RunnerConfig(node_id="test-node")
        runner = Runner(config)
        runner.worker_id = 3  # Worker 3 should get suffix

        broker_config = runner._build_broker_config()

        assert broker_config["node_id"] == "test-node-3"

    def test_build_broker_config_auto_node_id(self) -> None:
        """Test broker config auto-generates node ID from hostname."""
        config = RunnerConfig()  # No node_id
        runner = Runner(config)
        runner.worker_id = 1

        with patch("socket.gethostname", return_value="my-host"):
            broker_config = runner._build_broker_config()

        assert broker_config["node_id"] == "my-host"

    @pytest.mark.asyncio
    async def test_run_broker_registers_loaded_services(self) -> None:
        """Test _run_broker registers discovered services."""
        config = RunnerConfig(service_paths=["./services"])
        runner = Runner(config)
        runner.worker_id = 1

        class DemoService:
            name = "demo"
            actions = {"ping": lambda: None}

        mock_broker = Mock()
        mock_broker.register = AsyncMock()
        mock_broker.start = AsyncMock()
        mock_broker.stop = AsyncMock()

        with patch.object(runner, "_create_broker", AsyncMock(return_value=mock_broker)):
            with patch.object(runner, "_load_services_from_path", return_value=[DemoService]):
                with patch.object(runner, "_wait_for_shutdown", AsyncMock()):
                    await runner._run_broker()

        mock_broker.register.assert_awaited_once()
        registered_service = mock_broker.register.await_args.args[0]
        assert isinstance(registered_service, DemoService)
        mock_broker.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_broker_from_python_config(self) -> None:
        """Test Python config file can provide a custom broker factory."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                "class DummyBroker:\n"
                "    async def start(self):\n"
                "        return None\n"
                "    async def stop(self):\n"
                "        return None\n"
                "\n"
                "def create_broker(config, worker_id):\n"
                "    broker = DummyBroker()\n"
                "    broker.config = config\n"
                "    broker.worker_id = worker_id\n"
                "    return broker\n"
            )
            f.flush()
            config_path = f.name

        try:
            config = RunnerConfig(config_file=config_path)
            runner = Runner(config)
            runner.worker_id = 7

            broker = await runner._create_broker()

            assert broker.worker_id == 7
            assert broker.config is config
        finally:
            Path(config_path).unlink()


class TestWorkerManager:
    """Tests for WorkerManager class."""

    def test_init(self) -> None:
        """Test WorkerManager initialization."""
        config = RunnerConfig()
        mock_fn = Mock()

        manager = WorkerManager(4, mock_fn, config)

        assert manager.num_workers == 4
        assert manager.worker_fn == mock_fn
        assert manager.config == config
        assert manager.workers == {}
        assert manager.stopping is False


class TestLoadEnvFile:
    """Tests for _load_env_file function."""

    def test_load_env_file(self) -> None:
        """Test loading environment variables from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("FOO=bar\n")
            f.write("BAZ=123\n")
            f.write("# Comment\n")
            f.write('QUOTED="value with spaces"\n')
            f.flush()
            filepath = f.name

        try:
            _load_env_file(filepath)

            assert os.environ.get("FOO") == "bar"
            assert os.environ.get("BAZ") == "123"
            assert os.environ.get("QUOTED") == "value with spaces"
        finally:
            Path(filepath).unlink()
            # Cleanup env
            os.environ.pop("FOO", None)
            os.environ.pop("BAZ", None)
            os.environ.pop("QUOTED", None)

    def test_load_nonexistent_env_file(self, capsys) -> None:
        """Test loading non-existent env file shows warning."""
        _load_env_file("/nonexistent/file.env")

        captured = capsys.readouterr()
        assert "Warning" in captured.out


class TestIsServiceClass:
    """Tests for _is_service_class function."""

    def test_valid_service_class(self) -> None:
        """Test detection of valid service class."""
        try:
            from moleculerpy import Service

            class MyService(Service):
                name = "my-service"

                def __init__(self) -> None:
                    super().__init__(self.name)

            assert _is_service_class(MyService) is True
        except ImportError:
            # Fallback: when moleculerpy not installed
            class MyServiceFallback:  # type: ignore[no-redef]
                name = "my-service"
                actions = {"get": lambda: None}

            assert _is_service_class(MyServiceFallback) is True

    def test_valid_service_with_events(self) -> None:
        """Test detection of service with events."""
        try:
            from moleculerpy import Service

            class EventService(Service):
                name = "event-service"

                def __init__(self) -> None:
                    super().__init__(self.name)

            assert _is_service_class(EventService) is True
        except ImportError:

            class EventServiceFallback:  # type: ignore[no-redef]
                name = "event-service"
                events = {"user.created": lambda: None}

            assert _is_service_class(EventServiceFallback) is True

    def test_invalid_no_name(self) -> None:
        """Test rejection of class without name."""

        class NoName:
            actions = {}

        assert _is_service_class(NoName) is False

    def test_invalid_instance(self) -> None:
        """Test rejection of instance (not class)."""

        class Service:
            name = "svc"
            actions = {}

        instance = Service()
        assert _is_service_class(instance) is False

    def test_invalid_no_actions_or_events(self) -> None:
        """Test rejection of class without actions/events."""

        class NoActions:
            name = "no-actions"

        assert _is_service_class(NoActions) is False

    def test_real_moleculerpy_service_subclass(self) -> None:
        """Test real MoleculerPy Service subclasses are detected."""
        moleculerpy_root = Path(__file__).resolve().parents[2] / "moleculerpy"
        moleculerpy_root_str = str(moleculerpy_root)
        if moleculerpy_root_str not in sys.path:
            sys.path.insert(0, moleculerpy_root_str)

        from moleculerpy import Service, action

        class RealService(Service):
            name = "real-service"

            @action()
            async def ping(self, ctx):
                return {"ok": True}

        assert _is_service_class(RealService) is True


class TestRunCli:
    """Tests for run_cli function."""

    def test_parse_single_service_path(self) -> None:
        """Test parsing single service path."""
        # Mock Runner to not actually run
        with patch.object(Runner, "run") as mock_run:
            run_cli(["./services"])
            # run() was called
            mock_run.assert_called_once()

    def test_parse_instances_flag(self) -> None:
        """Test parsing -i/--instances flag."""
        with patch.object(Runner, "run"):
            with patch.object(Runner, "__init__", return_value=None) as mock_init:
                run_cli(["-i", "4", "./services"])

                # Check config was created with instances=4
                call_args = mock_init.call_args
                config = call_args[0][0]
                assert config.instances == 4

    def test_parse_repl_flag(self) -> None:
        """Test parsing --repl flag."""
        with patch.object(Runner, "run"):
            with patch.object(Runner, "__init__", return_value=None) as mock_init:
                run_cli(["--repl", "./services"])

                config = mock_init.call_args[0][0]
                assert config.repl is True

    def test_parse_transporter_flag(self) -> None:
        """Test parsing -T/--transporter flag."""
        with patch.object(Runner, "run"):
            with patch.object(Runner, "__init__", return_value=None) as mock_init:
                run_cli(["-T", "redis://localhost", "./services"])

                config = mock_init.call_args[0][0]
                assert config.transporter == "redis://localhost"

    def test_parse_all_flags(self) -> None:
        """Test parsing all flags together."""
        with patch.object(Runner, "run"):
            with patch.object(Runner, "__init__", return_value=None) as mock_init:
                run_cli(
                    [
                        "-i",
                        "0",
                        "--repl",
                        "-e",
                        ".env",
                        "-T",
                        "nats://localhost",
                        "-n",
                        "my-node",
                        "-H",
                        "-l",
                        "DEBUG",
                        "./services",
                        "./other",
                    ]
                )

                config = mock_init.call_args[0][0]
                assert config.instances == 0
                assert config.repl is True
                assert config.env_file == ".env"
                assert config.transporter == "nats://localhost"
                assert config.node_id == "my-node"
                assert config.hot_reload is True
                assert config.log_level == "DEBUG"
                assert config.service_paths == ["./services", "./other"]

    def test_keyboard_interrupt_returns_zero(self) -> None:
        """Test KeyboardInterrupt returns exit code 0."""
        with patch.object(Runner, "run", side_effect=KeyboardInterrupt):
            result = run_cli(["./services"])
            assert result == 0

    def test_exception_returns_one(self) -> None:
        """Test exception returns exit code 1."""
        with patch.object(Runner, "run", side_effect=RuntimeError("Test error")):
            result = run_cli(["./services"])
            assert result == 1
