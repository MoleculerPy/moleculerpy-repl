"""REPL commands for MoleculerPy.

This module provides all built-in commands and the registry.
"""

# Import all command classes
from .actions import ActionsCommand
from .base import BaseCommand, CommandRegistry, CommandResult
from .call import CallCommand
from .dcall import DirectCallCommand
from .emit import BroadcastCommand, EmitCommand
from .events import EventsCommand
from .info import InfoCommand
from .loglevel import LogLevelCommand
from .nodes import NodesCommand
from .services import ServicesCommand


def get_builtin_commands() -> list[type[BaseCommand]]:
    """Get all built-in command classes.

    Returns:
        List of command classes to register
    """
    return [
        ActionsCommand,
        BroadcastCommand,
        CallCommand,
        DirectCallCommand,
        EmitCommand,
        EventsCommand,
        InfoCommand,
        LogLevelCommand,
        NodesCommand,
        ServicesCommand,
    ]


def create_default_registry() -> CommandRegistry:
    """Create registry with all built-in commands.

    Returns:
        CommandRegistry with registered commands
    """
    registry = CommandRegistry()
    for cmd_class in get_builtin_commands():
        registry.register(cmd_class())
    return registry


__all__ = [
    "BaseCommand",
    "CommandRegistry",
    "CommandResult",
    "get_builtin_commands",
    "create_default_registry",
    # Individual commands
    "ActionsCommand",
    "BroadcastCommand",
    "CallCommand",
    "DirectCallCommand",
    "EmitCommand",
    "EventsCommand",
    "InfoCommand",
    "LogLevelCommand",
    "NodesCommand",
    "ServicesCommand",
]
