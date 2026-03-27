"""Tests for REPL commands."""

from __future__ import annotations

import pytest
from moleculerpy_repl.parser import ParsedArgs
from moleculerpy_repl.commands.base import BaseCommand, CommandResult, CommandRegistry
from moleculerpy_repl.commands.call import CallCommand
from moleculerpy_repl.commands.dcall import DirectCallCommand
from moleculerpy_repl.commands.emit import EmitCommand, BroadcastCommand
from moleculerpy_repl.commands.actions import ActionsCommand
from moleculerpy_repl.commands.services import ServicesCommand
from moleculerpy_repl.commands.nodes import NodesCommand
from moleculerpy_repl.commands.events import EventsCommand
from moleculerpy_repl.commands.info import InfoCommand


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating success result."""
        result = CommandResult(success=True, data={"id": 1})
        assert result.success is True
        assert result.data == {"id": 1}
        assert result.error is None

    def test_error_result(self) -> None:
        """Test creating error result."""
        result = CommandResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_with_output(self) -> None:
        """Test result with pre-formatted output."""
        result = CommandResult(success=True, output="Custom output", data=42)
        assert result.output == "Custom output"
        assert result.data == 42


class TestCommandRegistry:
    """Tests for CommandRegistry."""

    def test_register_command(self) -> None:
        """Test registering a command."""
        registry = CommandRegistry()
        cmd = CallCommand()
        registry.register(cmd)

        assert registry.get("call") is cmd

    def test_get_by_alias(self) -> None:
        """Test getting command by alias."""
        registry = CommandRegistry()
        cmd = CallCommand()
        registry.register(cmd)

        # CallCommand has alias "c"
        assert registry.get("c") is cmd

    def test_get_unknown_returns_none(self) -> None:
        """Test getting unknown command returns None."""
        registry = CommandRegistry()
        assert registry.get("unknown") is None

    def test_all_commands(self) -> None:
        """Test getting all commands."""
        registry = CommandRegistry()
        registry.register(CallCommand())
        registry.register(EmitCommand())

        all_cmds = list(registry.all())
        assert len(all_cmds) == 2

    def test_names_include_aliases(self) -> None:
        """Test names includes both names and aliases."""
        registry = CommandRegistry()
        registry.register(CallCommand())  # name="call", aliases=["c"]

        names = registry.names()
        assert "call" in names
        assert "c" in names


class TestCallCommand:
    """Tests for CallCommand."""

    @pytest.mark.asyncio
    async def test_call_success(self, mock_broker) -> None:
        """Test successful action call."""
        cmd = CallCommand()
        args = ParsedArgs(positional=["math.add"], payload={"a": 5, "b": 3})

        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert result.data == 8  # 5 + 3
        assert "Response" in result.output

    @pytest.mark.asyncio
    async def test_call_with_meta(self, mock_broker) -> None:
        """Test call with meta data."""
        cmd = CallCommand()
        args = ParsedArgs(
            positional=["user.get"],
            payload={"id": "u1"},
            meta={"tenant": "acme"}
        )

        result = await cmd.execute(mock_broker, args)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_call_missing_action(self, mock_broker) -> None:
        """Test call without action name."""
        cmd = CallCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Action name required" in result.error

    @pytest.mark.asyncio
    async def test_call_with_timeout_option(self, mock_broker) -> None:
        """Test call with $timeout option."""
        cmd = CallCommand()
        args = ParsedArgs(
            positional=["math.add"],
            payload={"a": 1, "b": 2},
            options={"timeout": 5000}
        )

        result = await cmd.execute(mock_broker, args)

        assert result.success is True

    def test_get_completions(self, mock_broker) -> None:
        """Test action name completions."""
        cmd = CallCommand()
        completions = cmd.get_completions(mock_broker, "math", "call math")

        assert any("math" in c for c in completions)


class TestDirectCallCommand:
    """Tests for DirectCallCommand."""

    @pytest.mark.asyncio
    async def test_dcall_success(self, mock_broker) -> None:
        """Test successful direct call."""
        cmd = DirectCallCommand()
        args = ParsedArgs(positional=["test-node-001", "math.add"], payload={"a": 5, "b": 3})

        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert result.data == 8  # 5 + 3
        assert "Direct call" in result.output
        assert "test-node-001" in result.output

    @pytest.mark.asyncio
    async def test_dcall_missing_args(self, mock_broker) -> None:
        """Test dcall without required arguments."""
        cmd = DirectCallCommand()
        args = ParsedArgs(positional=["node-only"])

        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Node ID and action name required" in result.error

    @pytest.mark.asyncio
    async def test_dcall_empty_args(self, mock_broker) -> None:
        """Test dcall with no arguments."""
        cmd = DirectCallCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Node ID and action name required" in result.error

    @pytest.mark.asyncio
    async def test_dcall_with_meta(self, mock_broker) -> None:
        """Test dcall with meta data."""
        cmd = DirectCallCommand()
        args = ParsedArgs(
            positional=["test-node-001", "user.get"],
            payload={"id": "u1"},
            meta={"tenant": "acme"}
        )

        result = await cmd.execute(mock_broker, args)

        assert result.success is True

    def test_dcall_help_text(self) -> None:
        """Test dcall help text."""
        cmd = DirectCallCommand()
        help_text = cmd.help_text()

        assert "dcall" in help_text
        assert "nodeID" in help_text.lower() or "node" in help_text.lower()

    @pytest.mark.asyncio
    async def test_dcall_with_options(self, mock_broker) -> None:
        """Test dcall with $timeout and $retries options."""
        cmd = DirectCallCommand()
        args = ParsedArgs(
            positional=["test-node-001", "math.add"],
            payload={"a": 1, "b": 2},
            options={"timeout": 5000, "retries": 3}
        )

        result = await cmd.execute(mock_broker, args)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dcall_exception(self, mock_broker) -> None:
        """Test dcall handles exceptions."""
        from unittest.mock import AsyncMock
        cmd = DirectCallCommand()
        args = ParsedArgs(positional=["test-node-001", "failing.action"], payload={})

        mock_broker.call = AsyncMock(side_effect=RuntimeError("Node unreachable"))
        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Node unreachable" in result.error or "failed" in result.error

    @pytest.mark.asyncio
    async def test_dcall_exception_with_message_attr(self, mock_broker) -> None:
        """Test dcall exception with message attribute."""
        from unittest.mock import AsyncMock
        cmd = DirectCallCommand()
        args = ParsedArgs(positional=["test-node-001", "failing.action"], payload={})

        class CustomError(Exception):
            message = "Custom error"

        mock_broker.call = AsyncMock(side_effect=CustomError())
        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Custom error" in result.error

    def test_dcall_node_completions(self, mock_broker) -> None:
        """Test node ID completions."""
        cmd = DirectCallCommand()
        completions = cmd.get_completions(mock_broker, "test", "dcall test")
        # Mock broker doesn't have node_catalog, so empty
        assert isinstance(completions, list)

    def test_dcall_action_completions(self, mock_broker) -> None:
        """Test action completions after node ID."""
        cmd = DirectCallCommand()
        completions = cmd.get_completions(mock_broker, "math", "dcall node-1 math")
        assert any("math" in c for c in completions)


class TestEmitCommand:
    """Tests for EmitCommand."""

    @pytest.mark.asyncio
    async def test_emit_success(self, mock_broker) -> None:
        """Test successful event emit."""
        cmd = EmitCommand()
        args = ParsedArgs(positional=["user.created"], payload={"id": "u1"})

        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert "Event emitted" in result.output
        assert len(mock_broker._emitted_events) == 1
        assert mock_broker._emitted_events[0]["event"] == "user.created"

    @pytest.mark.asyncio
    async def test_emit_with_meta(self, mock_broker) -> None:
        """Test emit with meta data."""
        cmd = EmitCommand()
        args = ParsedArgs(
            positional=["order.placed"],
            payload={"order_id": "o1"},
            meta={"source": "api"}
        )

        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        event = mock_broker._emitted_events[0]
        assert event["kwargs"].get("meta") == {"source": "api"}

    @pytest.mark.asyncio
    async def test_emit_missing_event(self, mock_broker) -> None:
        """Test emit without event name."""
        cmd = EmitCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Event name required" in result.error


class TestBroadcastCommand:
    """Tests for BroadcastCommand."""

    @pytest.mark.asyncio
    async def test_broadcast_success(self, mock_broker) -> None:
        """Test successful broadcast."""
        cmd = BroadcastCommand()
        args = ParsedArgs(positional=["cache.clear"], payload={"key": "*"})

        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert "Broadcast sent" in result.output
        assert len(mock_broker._broadcast_events) == 1

    @pytest.mark.asyncio
    async def test_broadcast_missing_event(self, mock_broker) -> None:
        """Test broadcast without event name."""
        cmd = BroadcastCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is False
        assert "Event name required" in result.error


class TestActionsCommand:
    """Tests for ActionsCommand."""

    @pytest.mark.asyncio
    async def test_list_actions(self, mock_broker) -> None:
        """Test listing actions."""
        cmd = ActionsCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert result.output is not None
        # Should list math.add, math.multiply, user.get, user.list
        assert "math.add" in result.output or "Actions" in result.output

    @pytest.mark.asyncio
    async def test_list_actions_with_all_flag(self, mock_broker) -> None:
        """Test listing actions with -a flag."""
        cmd = ActionsCommand()
        args = ParsedArgs(flags={"a": True})

        result = await cmd.execute(mock_broker, args)

        assert result.success is True


class TestServicesCommand:
    """Tests for ServicesCommand."""

    @pytest.mark.asyncio
    async def test_list_services(self, mock_broker) -> None:
        """Test listing services."""
        cmd = ServicesCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert result.output is not None


class TestNodesCommand:
    """Tests for NodesCommand."""

    @pytest.mark.asyncio
    async def test_list_nodes(self, mock_broker) -> None:
        """Test listing nodes."""
        cmd = NodesCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is True


class TestEventsCommand:
    """Tests for EventsCommand."""

    @pytest.mark.asyncio
    async def test_list_events(self, mock_broker) -> None:
        """Test listing events."""
        cmd = EventsCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is True


class TestInfoCommand:
    """Tests for InfoCommand."""

    @pytest.mark.asyncio
    async def test_broker_info(self, mock_broker) -> None:
        """Test getting broker info."""
        cmd = InfoCommand()
        args = ParsedArgs()

        result = await cmd.execute(mock_broker, args)

        assert result.success is True
        assert result.output is not None
        # Should contain node ID
        assert "test-node-001" in result.output or "Node" in result.output


class TestBaseCommandHelpText:
    """Tests for command help text generation."""

    def test_help_text_includes_name(self) -> None:
        """Test help text includes command name."""
        cmd = CallCommand()
        help_text = cmd.help_text()

        assert "call" in help_text

    def test_help_text_includes_description(self) -> None:
        """Test help text includes description."""
        cmd = CallCommand()
        help_text = cmd.help_text()

        assert cmd.description in help_text

    def test_help_text_includes_usage(self) -> None:
        """Test help text includes usage."""
        cmd = CallCommand()
        help_text = cmd.help_text()

        assert "Usage:" in help_text
        assert cmd.usage in help_text

    def test_help_text_includes_aliases(self) -> None:
        """Test help text includes aliases."""
        cmd = CallCommand()
        help_text = cmd.help_text()

        assert "Aliases:" in help_text
        assert "c" in help_text
