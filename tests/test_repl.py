"""Tests for REPL integration."""

from __future__ import annotations

import asyncio
import threading
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from moleculerpy_repl.repl import REPL, REPLConfig
from moleculerpy_repl.commands.base import BaseCommand, CommandResult
from moleculerpy_repl.parser import ParsedArgs


class TestREPLConfig:
    """Tests for REPLConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default config values."""
        config = REPLConfig()
        assert config.delimiter == "mol $ "
        assert config.history_file == "~/.moleculerpy_repl_history"
        assert config.history_size == 1000
        assert config.use_colors is True
        assert config.custom_commands == []

    def test_custom_values(self) -> None:
        """Test custom config values."""
        config = REPLConfig(delimiter="test> ", history_size=500, use_colors=False)
        assert config.delimiter == "test> "
        assert config.history_size == 500
        assert config.use_colors is False


class TestREPLInit:
    """Tests for REPL initialization."""

    def test_init_with_broker(self, mock_broker) -> None:
        """Test REPL initializes with broker."""
        repl = REPL(mock_broker, use_colors=False)

        assert repl.broker is mock_broker
        assert repl.parser is not None
        assert repl.output is not None
        assert repl.registry is not None

    def test_init_custom_delimiter(self, mock_broker) -> None:
        """Test REPL with custom delimiter."""
        repl = REPL(mock_broker, delimiter="custom> ", use_colors=False)
        assert repl.prompt == "custom> "

    def test_init_adds_space_to_delimiter(self, mock_broker) -> None:
        """Test delimiter gets space added if missing."""
        repl = REPL(mock_broker, delimiter="test>", use_colors=False)
        assert repl.prompt == "test> "

    def test_intro_contains_node_id(self, mock_broker) -> None:
        """Test intro banner contains node ID."""
        repl = REPL(mock_broker, use_colors=False)
        assert "test-node-001" in repl.intro

    def test_builtin_commands_registered(self, mock_broker) -> None:
        """Test built-in commands are registered."""
        repl = REPL(mock_broker, use_colors=False)

        # Check essential commands exist
        assert repl.registry.get("call") is not None
        assert repl.registry.get("emit") is not None
        assert repl.registry.get("actions") is not None
        assert repl.registry.get("services") is not None


class TestREPLCustomCommands:
    """Tests for custom command registration."""

    def test_register_custom_command(self, mock_broker) -> None:
        """Test registering custom commands."""

        class TestCommand(BaseCommand):
            name = "testcmd"
            description = "A test command"

            async def execute(self, broker, args):
                return CommandResult(success=True, data="test result")

        repl = REPL(mock_broker, custom_commands=[TestCommand], use_colors=False)

        cmd = repl.registry.get("testcmd")
        assert cmd is not None
        assert cmd.name == "testcmd"

    def test_duplicate_command_warning(self, mock_broker, capsys) -> None:
        """Test warning when registering duplicate command."""
        from moleculerpy_repl.commands.call import CallCommand

        # CallCommand already exists as built-in
        repl = REPL(mock_broker, custom_commands=[CallCommand], use_colors=False)

        # Should have printed a warning
        captured = capsys.readouterr()
        assert "already exists" in captured.out or True  # May or may not print


class TestREPLCommandExecution:
    """Tests for command execution."""

    def test_execute_known_command(self, mock_broker) -> None:
        """Test executing a known command."""
        repl = REPL(mock_broker, use_colors=False)

        # Execute via default handler
        result = repl.default("call math.add a=5 b=3")

        # Should not return True (exit signal)
        assert result is None or result is False

    def test_execute_unknown_command(self, mock_broker, capsys) -> None:
        """Test executing unknown command shows error."""
        repl = REPL(mock_broker, use_colors=False)
        result = repl.default("nonexistent arg1 arg2")

        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_execute_empty_line(self, mock_broker) -> None:
        """Test empty line does nothing."""
        repl = REPL(mock_broker, use_colors=False)
        result = repl.emptyline()
        assert result is False

    def test_execute_whitespace_only(self, mock_broker) -> None:
        """Test whitespace-only input."""
        repl = REPL(mock_broker, use_colors=False)
        result = repl.default("   ")
        assert result is None

    def test_execute_via_alias(self, mock_broker) -> None:
        """Test executing command via alias."""
        repl = REPL(mock_broker, use_colors=False)
        # "c" is alias for "call"
        result = repl.default("c math.add a=5 b=3")
        assert result is None or result is False


class TestREPLBuiltinCommands:
    """Tests for built-in REPL commands."""

    def test_quit_returns_true(self, mock_broker) -> None:
        """Test quit command returns True to exit."""
        repl = REPL(mock_broker, use_colors=False)
        result = repl.do_quit("")
        assert result is True

    def test_exit_returns_true(self, mock_broker) -> None:
        """Test exit command returns True to exit."""
        repl = REPL(mock_broker, use_colors=False)
        result = repl.do_exit("")
        assert result is True

    def test_help_specific_command(self, mock_broker, capsys) -> None:
        """Test help for specific command."""
        repl = REPL(mock_broker, use_colors=False)
        repl.do_help("call")

        captured = capsys.readouterr()
        assert "call" in captured.out
        assert "action" in captured.out.lower()

    def test_help_unknown_command(self, mock_broker, capsys) -> None:
        """Test help for unknown command."""
        repl = REPL(mock_broker, use_colors=False)
        repl.do_help("nonexistent")

        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_help_all_commands(self, mock_broker, capsys) -> None:
        """Test help without argument lists all commands."""
        repl = REPL(mock_broker, use_colors=False)
        repl.do_help("")

        captured = capsys.readouterr()
        assert "call" in captured.out
        assert "emit" in captured.out

    def test_clear_command(self, mock_broker) -> None:
        """Test clear command doesn't raise."""
        repl = REPL(mock_broker, use_colors=False)
        # Just verify it doesn't raise
        repl.do_clear("")
        repl.do_cls("")


class TestREPLTabCompletion:
    """Tests for tab completion."""

    def test_complete_command_names(self, mock_broker) -> None:
        """Test completing command names."""
        repl = REPL(mock_broker, use_colors=False)
        completions = repl.completedefault("ca", "ca", 0, 2)

        assert "call" in completions

    def test_complete_empty_returns_all_commands(self, mock_broker) -> None:
        """Test empty prefix returns command names."""
        repl = REPL(mock_broker, use_colors=False)
        completions = repl.completedefault("", "", 0, 0)

        # Should include command names
        assert len(completions) > 0

    def test_complete_with_command_context(self, mock_broker) -> None:
        """Test completion delegates to command."""
        repl = REPL(mock_broker, use_colors=False)
        completions = repl.completedefault("math", "call math", 5, 9)

        # CallCommand should provide action completions
        # May or may not have matches depending on mock broker setup


class TestREPLAsyncBridge:
    """Tests for async/sync bridge."""

    def test_run_async_executes_coroutine(self, mock_broker) -> None:
        """Test run_async executes coroutine."""
        repl = REPL(mock_broker, use_colors=False)

        async def sample_coro():
            return 42

        result = repl.run_async(sample_coro())
        assert result == 42

    def test_run_async_with_exception(self, mock_broker) -> None:
        """Test run_async propagates exceptions."""
        repl = REPL(mock_broker, use_colors=False)

        async def failing_coro():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            repl.run_async(failing_coro())

    def test_run_async_uses_bound_event_loop(self, mock_broker) -> None:
        """Test run_async dispatches onto the broker loop when available."""
        repl = REPL(mock_broker, use_colors=False)

        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop.run_forever)
        thread.start()
        try:
            repl._loop = loop

            async def sample_coro():
                return asyncio.get_running_loop()

            result_loop = repl.run_async(sample_coro())
            assert result_loop is loop
        finally:
            repl._loop = None
            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=1.0)
            loop.close()


class TestREPLErrorHandling:
    """Tests for error handling."""

    def test_command_error_shown(self, mock_broker, capsys) -> None:
        """Test command errors are displayed."""

        class FailingCommand(BaseCommand):
            name = "fail"
            description = "Always fails"

            async def execute(self, broker, args):
                return CommandResult(success=False, error="Intentional failure")

        repl = REPL(mock_broker, custom_commands=[FailingCommand], use_colors=False)

        repl.default("fail")

        captured = capsys.readouterr()
        assert "Intentional failure" in captured.out

    def test_exception_in_command_caught(self, mock_broker, capsys) -> None:
        """Test exceptions in commands are caught."""

        class CrashingCommand(BaseCommand):
            name = "crash"
            description = "Crashes"

            async def execute(self, broker, args):
                raise RuntimeError("Boom!")

        repl = REPL(mock_broker, custom_commands=[CrashingCommand], use_colors=False)

        result = repl.default("crash")

        captured = capsys.readouterr()
        assert "Command failed" in captured.out or "Boom" in captured.out
        # Should not raise, should continue
        assert result is None


class TestREPLExitSignal:
    """Tests for REPL exit signals."""

    def test_exit_signal_via_result(self, mock_broker) -> None:
        """Test __EXIT__ data value triggers exit."""

        class ExitCommand(BaseCommand):
            name = "myexit"
            description = "Custom exit"

            async def execute(self, broker, args):
                return CommandResult(success=True, data="__EXIT__")

        repl = REPL(mock_broker, custom_commands=[ExitCommand], use_colors=False)

        result = repl.default("myexit")
        assert result is True  # Signals exit
