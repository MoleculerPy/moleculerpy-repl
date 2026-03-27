"""Tests to boost coverage to 100%."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch
from moleculerpy_repl.parser import ParsedArgs
from moleculerpy_repl.commands.base import BaseCommand, CommandResult, CommandRegistry
from moleculerpy_repl.commands.dcall import DirectCallCommand
from moleculerpy_repl.commands.info import InfoCommand
from moleculerpy_repl.commands.nodes import NodesCommand
from moleculerpy_repl.commands.actions import ActionsCommand
from moleculerpy_repl.commands.services import ServicesCommand
from moleculerpy_repl.commands.events import EventsCommand
from moleculerpy_repl.commands import create_default_registry
from moleculerpy_repl.output import OutputFormatter, RICH_AVAILABLE


class TestCreateDefaultRegistry:
    """Test create_default_registry function."""

    def test_create_default_registry(self) -> None:
        """Test creating default registry."""
        registry = create_default_registry()
        assert registry.get("call") is not None
        assert registry.get("dcall") is not None
        assert registry.get("emit") is not None


class TestBaseCommandEdgeCases:
    """Edge cases for BaseCommand."""

    def test_command_with_explicit_aliases(self) -> None:
        """Test command class with explicit aliases defined."""

        class AliasCommand(BaseCommand):
            name = "aliasedcmd"
            description = "Has aliases"
            aliases = ["ac", "acmd"]

            async def execute(self, broker, args):
                return CommandResult(success=True)

        cmd = AliasCommand()
        assert cmd.aliases == ["ac", "acmd"]

    def test_command_get_completions_default(self) -> None:
        """Test default get_completions returns empty list."""

        class SimpleCommand(BaseCommand):
            name = "simple"
            description = "Simple"

            async def execute(self, broker, args):
                return CommandResult(success=True)

        cmd = SimpleCommand()
        completions = cmd.get_completions(Mock(), "text", "line")
        assert completions == []


class TestDirectCallEdgeCases:
    """Edge cases for DirectCallCommand."""

    @pytest.mark.asyncio
    async def test_dcall_node_validation_with_catalog(self) -> None:
        """Test dcall validates node from node_catalog."""
        cmd = DirectCallCommand()
        broker = Mock()
        broker.node_catalog = Mock()
        broker.node_catalog.nodes = {"node-1": Mock(), "node-2": Mock()}
        broker.call = AsyncMock(return_value=42)
        broker.registry = Mock(spec=[])

        args = ParsedArgs(
            positional=["node-1", "math.add"],
            payload={"a": 1, "b": 2}
        )
        result = await cmd.execute(broker, args)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dcall_node_not_found(self) -> None:
        """Test dcall with non-existent node."""
        cmd = DirectCallCommand()
        broker = Mock()
        broker.node_catalog = Mock()
        broker.node_catalog.nodes = {"node-1": Mock()}
        broker.registry = Mock(spec=[])

        args = ParsedArgs(
            positional=["unknown-node", "math.add"],
            payload={}
        )
        result = await cmd.execute(broker, args)
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_dcall_with_registry_get_node(self) -> None:
        """Test dcall uses registry.get_node."""
        cmd = DirectCallCommand()
        broker = Mock()
        broker.registry = Mock()
        broker.registry.get_node = Mock(return_value=Mock())
        broker.call = AsyncMock(return_value=100)

        args = ParsedArgs(
            positional=["node-x", "action"],
            payload={}
        )
        result = await cmd.execute(broker, args)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dcall_with_registry_nodes_dict(self) -> None:
        """Test dcall uses registry.nodes dict."""
        cmd = DirectCallCommand()
        broker = Mock()
        broker.registry = Mock(spec=['nodes'])
        broker.registry.nodes = {"node-y": Mock()}
        broker.call = AsyncMock(return_value=200)

        args = ParsedArgs(
            positional=["node-y", "action"],
            payload={}
        )
        result = await cmd.execute(broker, args)
        assert result.success is True

    def test_dcall_node_completions_from_catalog(self) -> None:
        """Test node completions from node_catalog."""
        cmd = DirectCallCommand()
        broker = Mock()
        broker.node_catalog = Mock()
        broker.node_catalog.nodes = {"node-1": Mock(), "node-2": Mock(), "other": Mock()}

        completions = cmd._get_node_completions(broker, "node")
        assert "node-1" in completions
        assert "node-2" in completions
        assert "other" not in completions

    def test_dcall_node_completions_from_registry_list(self) -> None:
        """Test node completions from registry.get_node_list."""
        cmd = DirectCallCommand()
        broker = Mock(spec=['registry'])
        broker.registry = Mock()
        broker.registry.get_node_list = Mock(return_value=[
            {"id": "n1"}, {"id": "n2"}, {"id": "n3"}
        ])

        completions = cmd._get_node_completions(broker, "n")
        assert "n1" in completions
        assert "n2" in completions

    def test_dcall_node_completions_from_registry_nodes(self) -> None:
        """Test node completions from registry.nodes dict."""
        cmd = DirectCallCommand()
        broker = Mock(spec=['registry'])
        broker.registry = Mock(spec=['nodes'])
        broker.registry.nodes = {"alpha": Mock(), "beta": Mock()}

        completions = cmd._get_node_completions(broker, "a")
        assert "alpha" in completions

    def test_dcall_action_completions_from_registry(self) -> None:
        """Test action completions from registry.__actions__."""
        cmd = DirectCallCommand()
        broker = Mock()

        action1 = Mock()
        action1.name = "user.get"
        action2 = Mock()
        action2.name = "user.list"

        broker.registry = Mock()
        broker.registry.__actions__ = [action1, action2]

        completions = cmd._get_action_completions(broker, "user")
        assert "user.get" in completions
        assert "user.list" in completions


class TestInfoCommandEdgeCases:
    """Edge cases for InfoCommand."""

    @pytest.mark.asyncio
    async def test_info_with_namespace(self) -> None:
        """Test info with namespace."""
        cmd = InfoCommand()
        broker = Mock()
        broker.id = "my-node"
        broker.namespace = "production"
        broker.started_at = None
        broker.services = {}

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "production" in result.output

    @pytest.mark.asyncio
    async def test_info_with_settings(self) -> None:
        """Test info with settings object."""
        cmd = InfoCommand()
        broker = Mock()
        broker.id = "node-1"
        broker.namespace = None
        broker.started_at = 1704067200.0
        # Use dict instead of Mock for services (len() called)
        broker.services = {"svc1": "service"}

        broker.settings = Mock()
        broker.settings.transporter = "redis://localhost"
        broker.settings.serializer = "MsgPack"

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True


class TestNodesCommandEdgeCases:
    """Edge cases for NodesCommand."""

    @pytest.mark.asyncio
    async def test_nodes_from_registry_get_node_list(self) -> None:
        """Test nodes from registry.get_node_list method."""
        cmd = NodesCommand()
        broker = Mock(spec=['registry'])
        broker.registry = Mock()
        broker.registry.get_node_list = Mock(return_value=[
            {"id": "n1", "available": True, "local": False},
            {"id": "n2", "available": False, "local": False}
        ])

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        # Only available nodes shown by default
        assert "n1" in result.output

    @pytest.mark.asyncio
    async def test_nodes_fallback_to_local(self) -> None:
        """Test nodes fallback when no node info available."""
        cmd = NodesCommand()
        broker = Mock(spec=['node_id'])
        broker.node_id = "local-node"

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "local-node" in result.output


class TestActionsCommandEdgeCases:
    """Edge cases for ActionsCommand."""

    @pytest.mark.asyncio
    async def test_actions_from_moleculer_registry(self) -> None:
        """Test actions from Moleculer-style registry."""
        cmd = ActionsCommand()
        broker = Mock(spec=['registry'])
        broker.registry = Mock()
        broker.registry.get_action_list = Mock(return_value=[
            {"name": "math.add", "nodeCount": 2, "available": True},
            {"name": "user.get", "nodeCount": 1, "available": True}
        ])

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "math.add" in result.output

    def test_actions_completions(self) -> None:
        """Test actions command completions."""
        cmd = ActionsCommand()
        completions = cmd.get_completions(Mock(), "-", "actions -")
        assert "-a" in completions


class TestServicesCommandEdgeCases:
    """Edge cases for ServicesCommand."""

    @pytest.mark.asyncio
    async def test_services_from_moleculer_registry(self) -> None:
        """Test services from Moleculer-style registry."""
        cmd = ServicesCommand()
        broker = Mock(spec=['registry'])
        broker.registry = Mock()
        broker.registry.get_service_list = Mock(return_value=[
            {"name": "math", "version": "1", "available": True, "nodeCount": 2},
            {"name": "user", "version": "2", "available": True, "nodeCount": 1}
        ])

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "math" in result.output

    def test_services_completions(self) -> None:
        """Test services command completions."""
        cmd = ServicesCommand()
        completions = cmd.get_completions(Mock(), "-", "services -")
        assert "-a" in completions
        assert "-l" in completions


class TestEventsCommandEdgeCases:
    """Edge cases for EventsCommand."""

    @pytest.mark.asyncio
    async def test_events_from_moleculer_registry(self) -> None:
        """Test events from Moleculer-style registry."""
        cmd = EventsCommand()
        broker = Mock(spec=['registry'])
        broker.registry = Mock()
        broker.registry.get_event_list = Mock(return_value=[
            {"name": "user.created", "group": "user", "nodeCount": 1},
            {"name": "order.placed", "group": "order", "nodeCount": 2}
        ])

        args = ParsedArgs()
        result = await cmd.execute(broker, args)

        assert result.success is True
        assert "user.created" in result.output

    def test_events_completions(self) -> None:
        """Test events command completions."""
        cmd = EventsCommand()
        completions = cmd.get_completions(Mock(), "-", "events -")
        assert "-a" in completions


class TestOutputFormatterRich:
    """Test OutputFormatter with rich library."""

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_print(self) -> None:
        """Test printing with rich console."""
        formatter = OutputFormatter(use_colors=True)
        formatter.print("test message")

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_success(self) -> None:
        """Test success message with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.success("Success!")

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_error(self) -> None:
        """Test error message with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.error("Error!")

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_warning(self) -> None:
        """Test warning message with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.warning("Warning!")

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_info(self) -> None:
        """Test info message with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.info("Info!")

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_banner(self) -> None:
        """Test banner with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.banner("Banner")

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_divider(self) -> None:
        """Test divider with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.divider()

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_clear(self) -> None:
        """Test clear with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.clear()
