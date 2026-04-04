"""Quit command — Stop broker and exit."""

from __future__ import annotations

import sys
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class QuitCommand(BaseCommand):
    """Stop the broker and exit the REPL."""

    name = "quit"
    description = "Stop broker and exit"
    usage = "quit"
    aliases = ["exit", "q"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the quit command."""
        try:
            if broker is not None and hasattr(broker, "stop"):
                await broker.stop()
        except Exception:
            pass

        sys.exit(0)
