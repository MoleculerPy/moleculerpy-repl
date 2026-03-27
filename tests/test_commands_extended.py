"""Extended tests for commands to improve coverage."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock
from moleculerpy_repl.parser import ParsedArgs
from moleculerpy_repl.commands.call import CallCommand
from moleculerpy_repl.commands.emit import EmitCommand, BroadcastCommand
from moleculerpy_repl.commands.actions import ActionsCommand
from moleculerpy_repl.commands.services import ServicesCommand
from moleculerpy_repl.commands.nodes import NodesCommand
from moleculerpy_repl.commands.events import EventsCommand
from moleculerpy_repl.commands.info import InfoCommand


class TestCallCommandExtended:
    """Extended tests for CallCommand."""

    @pytest.mark.asyncio
    async def test_call_with_retries_option(self, mock_broker) -> None:
        """Test call with $retries option."""
        cmd = CallCommand()
        args = ParsedArgs(positional=["math.add"], payload={"a": 1, "b": 2}, options={"retries": 3})
        result = await cmd.execute(mock_broker, args)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_call_exception_with_message_attr(self, mock_broker) -> None:
        """Test call exception with message attribute."""
        cmd = CallCommand()
        args = ParsedArgs(positional=["failing.action"], payload={})

        # Create exception with message attribute
        class CustomError(Exception):
            message = "Custom error message"

        mock_broker.call = AsyncMock(side_effect=CustomError())
        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Custom error message" in result.error

    @pytest.mark.asyncio
    async def test_call_exception_with_args(self, mock_broker) -> None:
        """Test call exception with args."""
        cmd = CallCommand()
        args = ParsedArgs(positional=["failing.action"], payload={})

        mock_broker.call = AsyncMock(side_effect=ValueError("Value error"))
        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Value error" in result.error

    def test_call_completions_from_registry(self) -> None:
        """Test action completions from registry."""
        cmd = CallCommand()
        broker = Mock()
        broker.registry = Mock()
        broker.registry.get_action_list = Mock(
            return_value=[{"name": "math.add"}, {"name": "math.sub"}, {"name": "user.get"}]
        )

        completions = cmd.get_completions(broker, "math", "call math")
        assert "math.add" in completions
        assert "math.sub" in completions

    def test_call_completions_exception(self) -> None:
        """Test completions handle exceptions."""
        cmd = CallCommand()
        broker = Mock()
        broker.registry = Mock()
        broker.registry.get_action_list = Mock(side_effect=RuntimeError())

        completions = cmd.get_completions(broker, "math", "call math")
        assert completions == []


class TestEmitCommandExtended:
    """Extended tests for EmitCommand."""

    @pytest.mark.asyncio
    async def test_emit_exception(self, mock_broker) -> None:
        """Test emit handles exceptions."""
        cmd = EmitCommand()
        args = ParsedArgs(positional=["fail.event"], payload={})

        mock_broker.emit = AsyncMock(side_effect=RuntimeError("Emit failed"))
        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Emit failed" in result.error

    def test_emit_completions_from_registry(self) -> None:
        """Test event completions from registry."""
        cmd = EmitCommand()
        broker = Mock()
        broker.registry = Mock()
        broker.registry.get_event_list = Mock(
            return_value=[{"name": "user.created"}, {"name": "order.placed"}]
        )

        completions = cmd.get_completions(broker, "user", "emit user")
        assert "user.created" in completions

    def test_emit_completions_from_services(self) -> None:
        """Test event completions from services."""
        cmd = EmitCommand()
        broker = Mock(spec=[])
        broker.services = {"user": Mock(events={"created": None, "deleted": None})}

        completions = cmd.get_completions(broker, "cr", "emit cr")
        assert "created" in completions

    def test_emit_completions_exception(self) -> None:
        """Test completions handle exceptions."""
        cmd = EmitCommand()
        broker = Mock()
        broker.registry = Mock()
        broker.registry.get_event_list = Mock(side_effect=RuntimeError())

        completions = cmd.get_completions(broker, "test", "emit test")
        assert completions == []


class TestBroadcastCommandExtended:
    """Extended tests for BroadcastCommand."""

    @pytest.mark.asyncio
    async def test_broadcast_fallback_to_emit(self) -> None:
        """Test broadcast falls back to emit if no broadcast method."""
        cmd = BroadcastCommand()
        broker = Mock(spec=["emit"])
        broker.emit = AsyncMock()

        args = ParsedArgs(positional=["cache.clear"], payload={"all": True})
        result = await cmd.execute(broker, args)

        assert result.success is True
        broker.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_exception(self, mock_broker) -> None:
        """Test broadcast handles exceptions."""
        cmd = BroadcastCommand()
        args = ParsedArgs(positional=["fail.event"], payload={})

        mock_broker.broadcast = AsyncMock(side_effect=RuntimeError("Broadcast failed"))
        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Broadcast failed" in result.error


class TestActionsCommandExtended:
    """Extended tests for ActionsCommand."""

    @pytest.mark.asyncio
    async def test_actions_from_moleculerpy_registry(self) -> None:
        """Test actions from MoleculerPy registry pattern."""
        cmd = ActionsCommand()
        broker = Mock()

        action1 = Mock()
        action1.name = "math.add"
        action1.node_id = "node-1"
        action1.is_local = True

        action2 = Mock()
        action2.name = "$internal.action"
        action2.node_id = "node-1"
        action2.is_local = True

        broker.registry = Mock()
        broker.registry.__actions__ = [action1, action2]

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        # Should skip internal actions by default
        assert "$internal" not in result.output

    @pytest.mark.asyncio
    async def test_actions_show_all_flag(self) -> None:
        """Test actions with -a flag shows internal."""
        cmd = ActionsCommand()
        broker = Mock()

        action1 = Mock()
        action1.name = "$internal.action"
        action1.node_id = "node-1"
        action1.is_local = True

        broker.registry = Mock()
        broker.registry.__actions__ = [action1]

        args = ParsedArgs(flags={"a": True})
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_actions_empty(self) -> None:
        """Test actions when none available."""
        cmd = ActionsCommand()
        broker = Mock(spec=[])

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "No actions" in result.output

    @pytest.mark.asyncio
    async def test_actions_exception(self) -> None:
        """Test actions handles exceptions."""
        cmd = ActionsCommand()
        broker = Mock()
        broker.registry = Mock()
        type(broker.registry).__actions__ = property(
            lambda s: (_ for _ in ()).throw(RuntimeError())
        )

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is False


class TestServicesCommandExtended:
    """Extended tests for ServicesCommand."""

    @pytest.mark.asyncio
    async def test_services_from_moleculerpy_registry(self) -> None:
        """Test services from MoleculerPy registry pattern."""
        cmd = ServicesCommand()
        broker = Mock()
        broker.id = "node-1"

        service = Mock()
        service.version = "1"
        service.full_name = "v1.math"

        broker.registry = Mock()
        broker.registry.__services__ = {"math": service}

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "math" in result.output

    @pytest.mark.asyncio
    async def test_services_local_flag(self) -> None:
        """Test services with -l flag shows only local."""
        cmd = ServicesCommand()
        broker = Mock(spec=["services"])
        broker.services = {"local": Mock(name="local", version=None, full_name="local")}
        broker.node_id = "node-1"

        args = ParsedArgs(flags={"l": True})
        result = await cmd.execute(broker, args)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_services_empty(self) -> None:
        """Test services when none available."""
        cmd = ServicesCommand()
        broker = Mock(spec=[])

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "No services" in result.output

    @pytest.mark.asyncio
    async def test_services_exception(self) -> None:
        """Test services handles exceptions."""
        cmd = ServicesCommand()
        broker = Mock()
        broker.registry = Mock()
        type(broker.registry).__services__ = property(
            lambda s: (_ for _ in ()).throw(RuntimeError())
        )

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is False


class TestNodesCommandExtended:
    """Extended tests for NodesCommand."""

    @pytest.mark.asyncio
    async def test_nodes_from_node_catalog(self) -> None:
        """Test nodes from node_catalog pattern."""
        cmd = NodesCommand()
        broker = Mock()

        node = Mock()
        node.available = True
        node.local = True
        node.cpu = 45
        node.ipList = ["127.0.0.1"]
        node.hostname = "localhost"
        node.client = {"type": "moleculerpy"}
        node.services = []

        broker.node_catalog = Mock()
        broker.node_catalog.nodes = {"node-1": node}

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "node-1" in result.output

    @pytest.mark.asyncio
    async def test_nodes_show_all_includes_offline(self) -> None:
        """Test nodes -a includes offline nodes."""
        cmd = NodesCommand()
        broker = Mock()

        online = Mock()
        online.available = True
        online.local = False
        online.cpu = None
        online.ipList = []
        online.hostname = None
        online.client = {}
        online.services = []

        offline = Mock()
        offline.available = False
        offline.local = False
        offline.cpu = None
        offline.ipList = []
        offline.hostname = None
        offline.client = {}
        offline.services = []

        broker.node_catalog = Mock()
        broker.node_catalog.nodes = {"online": online, "offline": offline}

        args = ParsedArgs(flags={"a": True})
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "offline" in result.output
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_nodes_details_flag(self) -> None:
        """Test nodes -d shows detailed output."""
        cmd = NodesCommand()
        broker = Mock()

        node = Mock()
        node.available = True
        node.local = True
        node.cpu = 50
        node.ipList = ["192.168.1.1"]
        node.hostname = "myhost"
        node.client = {}
        node.services = []

        broker.node_catalog = Mock()
        broker.node_catalog.nodes = {"node-1": node}

        args = ParsedArgs(flags={"d": True})
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "IP" in result.output  # Column renamed from Hostname
        assert "CPU" in result.output

    @pytest.mark.asyncio
    async def test_nodes_empty(self) -> None:
        """Test nodes when none available."""
        cmd = NodesCommand()
        broker = Mock()
        broker.node_catalog = Mock()
        broker.node_catalog.nodes = {}

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "No nodes" in result.output

    @pytest.mark.asyncio
    async def test_nodes_exception(self) -> None:
        """Test nodes handles exceptions."""
        cmd = NodesCommand()
        broker = Mock()
        broker.node_catalog = Mock()
        type(broker.node_catalog).nodes = property(lambda s: (_ for _ in ()).throw(RuntimeError()))

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is False


class TestEventsCommandExtended:
    """Extended tests for EventsCommand."""

    @pytest.mark.asyncio
    async def test_events_from_services(self, mock_broker) -> None:
        """Test events from services pattern."""
        cmd = EventsCommand()

        args = ParsedArgs()
        result = await cmd.execute(mock_broker, args)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_events_empty(self) -> None:
        """Test events when none available."""
        cmd = EventsCommand()
        broker = Mock(spec=[])

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "No events" in result.output

    @pytest.mark.asyncio
    async def test_events_exception(self) -> None:
        """Test events handles exceptions."""
        cmd = EventsCommand()
        broker = Mock()
        broker.registry = Mock()
        type(broker.registry).__events__ = property(lambda s: (_ for _ in ()).throw(RuntimeError()))

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is False


class TestInfoCommandExtended:
    """Extended tests for InfoCommand."""

    @pytest.mark.asyncio
    async def test_info_with_mock_broker(self, mock_broker) -> None:
        """Test info with mock broker."""
        cmd = InfoCommand()

        args = ParsedArgs()
        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert "test-node-001" in result.output

    @pytest.mark.asyncio
    async def test_info_output_format(self, mock_broker) -> None:
        """Test info output contains expected sections."""
        cmd = InfoCommand()

        args = ParsedArgs()
        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert "Broker Information" in result.output
        assert "Node ID" in result.output


class TestLogLevelCommand:
    """Tests for LogLevelCommand."""

    @pytest.mark.asyncio
    async def test_loglevel_show_current(self, mock_broker) -> None:
        """Test showing current log level."""
        from moleculerpy_repl.commands.loglevel import LogLevelCommand

        cmd = LogLevelCommand()
        args = ParsedArgs()
        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert "Current log level" in result.output
        assert "INFO" in result.output

    @pytest.mark.asyncio
    async def test_loglevel_set_debug(self, mock_broker) -> None:
        """Test setting log level to debug."""
        from moleculerpy_repl.commands.loglevel import LogLevelCommand
        from moleculerpy_repl.logger import LoggerFactory, LogLevel

        # Add logger factory to mock broker
        mock_broker.logger_factory = LoggerFactory(node_id="test")

        cmd = LogLevelCommand()
        args = ParsedArgs(positional=["debug"])
        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert "DEBUG" in result.output
        assert mock_broker.logger_factory.level == LogLevel.DEBUG

    @pytest.mark.asyncio
    async def test_loglevel_invalid_level(self, mock_broker) -> None:
        """Test setting invalid log level."""
        from moleculerpy_repl.commands.loglevel import LogLevelCommand

        cmd = LogLevelCommand()
        args = ParsedArgs(positional=["invalid"])
        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Invalid log level" in result.error

    def test_loglevel_completions(self) -> None:
        """Test log level completions."""
        from moleculerpy_repl.commands.loglevel import LogLevelCommand
        from unittest.mock import Mock

        cmd = LogLevelCommand()
        broker = Mock()

        completions = cmd.get_completions(broker, "d", "loglevel d")
        assert "debug" in completions

        completions = cmd.get_completions(broker, "e", "loglevel e")
        assert "error" in completions

    @pytest.mark.asyncio
    async def test_loglevel_all_levels(self, mock_broker) -> None:
        """Test all valid log levels."""
        from moleculerpy_repl.commands.loglevel import LogLevelCommand, VALID_LEVELS
        from moleculerpy_repl.logger import LoggerFactory

        mock_broker.logger_factory = LoggerFactory(node_id="test")
        cmd = LogLevelCommand()

        for level in VALID_LEVELS:
            args = ParsedArgs(positional=[level])
            result = await cmd.execute(mock_broker, args)
            assert result.success is True, f"Failed for level: {level}"
