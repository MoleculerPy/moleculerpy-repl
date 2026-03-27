"""Main REPL class for MoleculerPy.

Interactive command-line interface for MoleculerPy microservices,
compatible with moleculer-repl patterns.
"""

from __future__ import annotations

import asyncio
import cmd
import readline
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .commands.base import BaseCommand, CommandRegistry, CommandResult
from .output import OutputFormatter
from .parser import ArgParser, ParsedArgs

if TYPE_CHECKING:
    pass  # MoleculerPy types would go here


@dataclass
class REPLConfig:
    """REPL configuration."""

    # Prompt
    delimiter: str = "mol $ "

    # History
    history_file: str = "~/.moleculerpy_repl_history"
    history_size: int = 1000

    # Output
    use_colors: bool = True

    # Custom commands
    custom_commands: list[type[BaseCommand]] = field(default_factory=list)


class REPL(cmd.Cmd):
    """Interactive REPL for MoleculerPy broker.

    Usage:
        repl = REPL(broker)
        await repl.run()

    Or via broker method:
        await broker.repl()

    Commands are defined in commands/ directory and auto-registered.
    """

    intro = ""  # Set in __init__
    doc_header = "Available commands (type 'help <command>' for details):"

    def __init__(
        self,
        broker: Any,
        delimiter: str = "mol $ ",
        custom_commands: list[type[BaseCommand]] | None = None,
        use_colors: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize REPL.

        Args:
            broker: MoleculerPy ServiceBroker instance
            delimiter: Command prompt string
            custom_commands: Additional command classes to register
            use_colors: Enable colored output (requires rich)
            **kwargs: Additional config options
        """
        super().__init__()

        self.broker = broker
        self.prompt = delimiter if delimiter.endswith(" ") else delimiter + " "

        # Config
        self.config = REPLConfig(
            delimiter=delimiter,
            use_colors=use_colors,
            custom_commands=custom_commands or [],
        )

        # Components
        self.parser = ArgParser()
        self.output = OutputFormatter(use_colors=use_colors)
        self.registry = CommandRegistry()
        self._loop: asyncio.AbstractEventLoop | None = None

        # Register commands
        self._register_builtin_commands()
        self._register_custom_commands(custom_commands or [])

        # Setup intro banner
        self._setup_intro()

    def _setup_intro(self) -> None:
        """Setup intro banner."""
        version = getattr(self.broker, "__version__", None) or getattr(
            self.broker, "version", "unknown"
        )
        node_id = (
            getattr(self.broker, "nodeID", None)
            or getattr(self.broker, "node_id", None)
            or getattr(self.broker, "id", "unknown")
        )

        self.intro = f"""
🚀 MoleculerPy REPL v0.1.0
   Node ID: {node_id}
   Type 'help' for available commands.
"""

    def _register_builtin_commands(self) -> None:
        """Register built-in commands."""
        # Import and register all built-in commands
        from .commands import get_builtin_commands

        for cmd_class in get_builtin_commands():
            self.registry.register(cmd_class())

    def _register_custom_commands(
        self, custom_commands: list[type[BaseCommand]]
    ) -> None:
        """Register custom commands."""
        for cmd_class in custom_commands:
            try:
                cmd_instance = cmd_class()
                if self.registry.get(cmd_instance.name):
                    self.output.warning(
                        f"Command '{cmd_instance.name}' already exists. Skipping."
                    )
                    continue
                self.registry.register(cmd_instance)
            except Exception as e:
                self.output.error(f"Failed to register command: {e}")

    # =========================================================================
    # Async bridge
    # =========================================================================

    def run_async(self, coro: Any) -> Any:
        """Run async coroutine from sync context.

        Since cmdloop() runs in an executor (separate thread), commands must
        be marshalled back onto the broker's original event loop. Running the
        coroutine in a brand new loop breaks transports and other loop-bound
        resources such as live NATS connections.

        Args:
            coro: Coroutine to run

        Returns:
            Result of coroutine
        """
        if self._loop is None:
            return asyncio.run(coro)

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    # =========================================================================
    # cmd.Cmd overrides
    # =========================================================================

    def default(self, line: str) -> None:
        """Handle unknown commands.

        Routes to registered command handlers.
        """
        if not line.strip():
            return

        parts = line.split(maxsplit=1)
        cmd_name = parts[0]
        args_str = parts[1] if len(parts) > 1 else ""

        # Check if command exists in registry
        command = self.registry.get(cmd_name)
        if command:
            return cast(None, self._execute_command(command, args_str))

        self.output.error(
            f"Unknown command: '{cmd_name}'. Type 'help' for available commands."
        )
        return

    def _execute_command(self, command: BaseCommand, args_str: str) -> bool | None:
        """Execute a registered command.

        Args:
            command: Command to execute
            args_str: Argument string

        Returns:
            True to exit REPL, None to continue
        """
        try:
            parsed = self.parser.parse(args_str)
            result = self.run_async(command.execute(self.broker, parsed))

            if result.error:
                self.output.error(result.error)
            else:
                # Show output first (e.g., "Response (0.5ms):")
                if result.output:
                    self.output.print(result.output)
                # Then show data if present
                if result.data is not None:
                    self.output.result(result.data)

            # Check if command wants to exit
            if result.data == "__EXIT__":
                return True

        except KeyboardInterrupt:
            self.output.print("\nInterrupted.")
        except Exception as e:
            self.output.error(f"Command failed: {e}")

        return None

    def emptyline(self) -> bool:
        """Handle empty line (just Enter)."""
        return False  # Don't repeat last command

    def completedefault(
        self, text: str, line: str, begidx: int, endidx: int
    ) -> list[str]:
        """Default tab completion."""
        parts = line[:begidx].split()

        if not parts:
            # Complete command names
            return [
                name for name in self.registry.names() if name.startswith(text)
            ]

        # Get command-specific completions
        cmd_name = parts[0]
        command = self.registry.get(cmd_name)
        if command:
            return command.get_completions(self.broker, text, line)

        return []

    def do_help(self, arg: str) -> None:
        """Show help for commands."""
        if arg:
            # Help for specific command
            command = self.registry.get(arg)
            if command:
                self.output.print(command.help_text())
            else:
                self.output.error(f"Unknown command: '{arg}'")
        else:
            # General help
            self.output.banner("MoleculerPy REPL Commands")

            headers = ["Command", "Description"]
            rows = [
                [cmd.name, cmd.description] for cmd in self.registry.all()
            ]
            self.output.table(headers, rows)

    def do_quit(self, arg: str) -> bool:
        """Exit the REPL."""
        self.output.print("Goodbye! 👋")
        return True

    def do_exit(self, arg: str) -> bool:
        """Exit the REPL (alias for quit)."""
        return self.do_quit(arg)

    def do_clear(self, arg: str) -> None:
        """Clear the terminal screen."""
        self.output.clear()

    def do_cls(self, arg: str) -> None:
        """Clear the terminal screen (alias)."""
        self.do_clear(arg)

    # =========================================================================
    # Entry point
    # =========================================================================

    async def run(self) -> None:
        """Start the REPL.

        This is the main entry point for running the REPL.
        It sets up readline history and runs the command loop
        in a separate thread to not block the event loop.
        """
        # Setup readline history
        histfile = Path(self.config.history_file).expanduser()
        try:
            # Ensure parent directory exists
            histfile.parent.mkdir(parents=True, exist_ok=True)
            if histfile.exists():
                readline.read_history_file(histfile)
        except (FileNotFoundError, OSError, PermissionError):
            pass  # Ignore history file errors

        readline.set_history_length(self.config.history_size)

        # Setup tab completion
        readline.set_completer_delims(" \t\n;")
        readline.parse_and_bind("tab: complete")

        # Enable REPL-aware logging output
        try:
            from .logger import REPLAwareStream
            REPLAwareStream.set_prompt(self.prompt)
            REPLAwareStream.enable()
        except ImportError:
            pass

        try:
            # Run cmd loop in executor to not block event loop
            loop = asyncio.get_running_loop()
            self._loop = loop
            await loop.run_in_executor(None, self.cmdloop)
        except KeyboardInterrupt:
            self.output.print("\nInterrupted.")
        finally:
            self._loop = None
            # Disable REPL-aware logging
            try:
                from .logger import REPLAwareStream
                REPLAwareStream.disable()
            except ImportError:
                pass

            # Save history
            try:
                readline.write_history_file(histfile)
            except OSError:
                pass

            # Stop broker on exit
            if hasattr(self.broker, "stop"):
                try:
                    await self.broker.stop()
                except Exception:
                    pass
