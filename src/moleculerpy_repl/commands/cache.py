"""Cache command — Manage broker cache."""

from __future__ import annotations

from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class CacheCommand(BaseCommand):
    """Manage broker cache keys and entries."""

    name = "cache"
    description = "Manage cache (keys/clear)"
    usage = "cache keys [-f pattern] | cache clear [pattern]"

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the cache command."""
        cacher = getattr(broker, "cacher", None)
        if not cacher:
            return CommandResult(success=False, error="Cacher is not configured")

        subcommand = args.positional[0] if args.positional else "keys"

        if subcommand == "keys":
            return await self._list_keys(cacher, args)
        elif subcommand == "clear":
            return await self._clear_keys(cacher, args)
        else:
            return CommandResult(
                success=False,
                error=f"Unknown subcommand '{subcommand}'. Use: keys, clear",
            )

    async def _list_keys(self, cacher: Any, args: ParsedArgs) -> CommandResult:
        """List cache keys, optionally filtered by pattern."""
        pattern = args.flags.get("f") or (args.positional[1] if len(args.positional) > 1 else None)

        try:
            if hasattr(cacher, "keys"):
                raw_keys = cacher.keys(pattern) if pattern else cacher.keys()
                # keys() may be sync or async depending on cacher impl
                import asyncio
                keys = (await raw_keys) if asyncio.iscoroutine(raw_keys) else raw_keys
            else:
                return CommandResult(
                    success=False,
                    error="Cacher does not support listing keys",
                )

            if not keys:
                output = "No cache keys found"
                if pattern:
                    output += f" matching '{pattern}'"
            else:
                lines = [f"Cache keys ({len(keys)}):"]
                lines.extend(f"  {key}" for key in sorted(keys))
                output = "\n".join(lines)

            return CommandResult(success=True, output=output)

        except Exception as e:
            return CommandResult(success=False, error=f"Failed to list keys: {e}")

    async def _clear_keys(self, cacher: Any, args: ParsedArgs) -> CommandResult:
        """Clear cache entries, optionally matching pattern."""
        pattern = args.positional[1] if len(args.positional) > 1 else None

        try:
            if hasattr(cacher, "clean"):
                await cacher.clean(pattern) if pattern else await cacher.clean()
            else:
                return CommandResult(
                    success=False,
                    error="Cacher does not support clean operation",
                )

            msg = f"Cache cleared (pattern: '{pattern}')" if pattern else "Cache cleared"
            return CommandResult(success=True, output=msg)

        except Exception as e:
            return CommandResult(success=False, error=f"Failed to clear cache: {e}")
