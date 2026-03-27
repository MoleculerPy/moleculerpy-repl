"""Base command class for MoleculerPy REPL commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from moleculerpy_repl.parser import ParsedArgs


@dataclass
class CommandResult:
    """Result of command execution."""

    success: bool
    data: Any = None
    error: str | None = None
    output: str | None = None  # Pre-formatted output for display


class BaseCommand(ABC):
    """Base class for all REPL commands.

    Each command must implement:
        - name: Command name (e.g., "call")
        - description: Short description for help
        - execute(): Main logic

    Optional:
        - usage: Usage string for help
        - aliases: Alternative command names
        - get_completions(): Tab completion suggestions

    Example:
        class CallCommand(BaseCommand):
            name = "call"
            description = "Call a service action"
            usage = "call <action> [params...]"

            async def execute(self, broker, args):
                action = args.positional[0]
                result = await broker.call(action, args.payload)
                return CommandResult(success=True, data=result)
    """

    name: str = ""
    description: str = ""
    usage: str = ""
    aliases: Sequence[str] = ()

    def __init__(self) -> None:
        """Initialize command."""
        if not hasattr(self, "aliases"):
            self.aliases = ()

    @abstractmethod
    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the command.

        Args:
            broker: MoleculerPy ServiceBroker instance
            args: Parsed command arguments

        Returns:
            CommandResult with success status and data/error
        """
        ...

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get tab completion suggestions.

        Override this method to provide command-specific completions.

        Args:
            broker: MoleculerPy ServiceBroker instance
            text: Current word being typed
            line: Full line buffer

        Returns:
            List of completion suggestions
        """
        return []

    def help_text(self) -> str:
        """Generate help text for this command."""
        parts = [f"{self.name} — {self.description}"]

        if self.usage:
            parts.append(f"\nUsage: {self.usage}")

        if self.aliases:
            parts.append(f"\nAliases: {', '.join(self.aliases)}")

        return "\n".join(parts)


@dataclass
class CommandRegistry:
    """Registry for REPL commands."""

    _commands: dict[str, BaseCommand] = field(default_factory=dict)
    _aliases: dict[str, str] = field(default_factory=dict)

    def register(self, command: BaseCommand) -> None:
        """Register a command.

        Args:
            command: Command instance to register
        """
        self._commands[command.name] = command

        for alias in command.aliases:
            self._aliases[alias] = command.name

    def get(self, name: str) -> BaseCommand | None:
        """Get command by name or alias.

        Args:
            name: Command name or alias

        Returns:
            Command instance or None if not found
        """
        # Check direct name
        if name in self._commands:
            return self._commands[name]

        # Check aliases
        if name in self._aliases:
            return self._commands[self._aliases[name]]

        return None

    def all(self) -> list[BaseCommand]:
        """Get all registered commands.

        Note: Returns values directly to avoid list allocation on each call.
        """
        return list(self._commands.values())

    def names(self) -> list[str]:
        """Get all command names (including aliases)."""
        return list(self._commands.keys()) + list(self._aliases.keys())
