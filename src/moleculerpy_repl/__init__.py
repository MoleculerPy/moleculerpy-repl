"""MoleculerPy REPL — Interactive CLI for MoleculerPy microservices.

Usage:
    from moleculerpy_repl import REPL

    repl = REPL(broker)
    await repl.run()

Or via broker method:
    await broker.repl()
"""

from importlib.metadata import PackageNotFoundError, version

from .commands.base import BaseCommand, CommandRegistry, CommandResult
from .output import OutputFormatter
from .parser import ArgParser, ParsedArgs
from .repl import REPL, REPLConfig
from .runner import Runner, RunnerConfig, run_cli

try:
    __version__ = version("moleculerpy-repl")
except PackageNotFoundError:
    __version__ = "0.14.2"

__all__ = [
    # Main classes
    "REPL",
    "REPLConfig",
    # Runner
    "Runner",
    "RunnerConfig",
    "run_cli",
    # Command system
    "BaseCommand",
    "CommandResult",
    "CommandRegistry",
    # Parsing
    "ArgParser",
    "ParsedArgs",
    # Output
    "OutputFormatter",
]
