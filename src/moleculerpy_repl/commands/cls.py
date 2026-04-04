"""Cls command — Clear terminal screen."""

from __future__ import annotations

import sys
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class ClsCommand(BaseCommand):
    """Clear the terminal screen."""

    name = "cls"
    description = "Clear terminal screen"
    usage = "cls"
    aliases = ["clear"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the cls command."""
        sys.stdout.write("\x1bc")
        sys.stdout.flush()
        return CommandResult(success=True)
