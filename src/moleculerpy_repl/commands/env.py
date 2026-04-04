"""Env command — Print environment variables."""

from __future__ import annotations

import os
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class EnvCommand(BaseCommand):
    """Print all environment variables."""

    name = "env"
    description = "Print environment variables"
    usage = "env"

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the env command."""
        lines = [f"{key}={value}" for key, value in sorted(os.environ.items())]
        output = "\n".join(lines)
        return CommandResult(success=True, output=output)
