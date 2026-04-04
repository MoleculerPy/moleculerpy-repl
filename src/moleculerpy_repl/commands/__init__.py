"""REPL commands for MoleculerPy.

This module provides all built-in commands and the registry.
"""

# Import all command classes
from .actions import ActionsCommand
from .base import BaseCommand, CommandRegistry, CommandResult
from .bench import BenchCommand
from .cache import CacheCommand
from .call import CallCommand
from .cls import ClsCommand
from .dcall import DirectCallCommand
from .destroy import DestroyCommand
from .emit import BroadcastCommand, EmitCommand
from .env import EnvCommand
from .events import EventsCommand
from .info import InfoCommand
from .listener import ListenerCommand
from .load import LoadCommand
from .loglevel import LogLevelCommand
from .metrics import MetricsCommand
from .nodes import NodesCommand
from .quit import QuitCommand
from .services import ServicesCommand


def get_builtin_commands() -> list[type[BaseCommand]]:
    """Get all built-in command classes.

    Returns:
        List of command classes to register
    """
    return [
        ActionsCommand,
        BenchCommand,
        BroadcastCommand,
        CacheCommand,
        CallCommand,
        ClsCommand,
        DestroyCommand,
        DirectCallCommand,
        EmitCommand,
        EnvCommand,
        EventsCommand,
        InfoCommand,
        ListenerCommand,
        LoadCommand,
        LogLevelCommand,
        MetricsCommand,
        NodesCommand,
        QuitCommand,
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
    "BenchCommand",
    "BroadcastCommand",
    "CacheCommand",
    "CallCommand",
    "ClsCommand",
    "DestroyCommand",
    "DirectCallCommand",
    "EmitCommand",
    "EnvCommand",
    "EventsCommand",
    "InfoCommand",
    "ListenerCommand",
    "LoadCommand",
    "LogLevelCommand",
    "MetricsCommand",
    "NodesCommand",
    "QuitCommand",
    "ServicesCommand",
]
