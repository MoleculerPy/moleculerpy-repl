"""Listener command — Subscribe to broker events."""

from __future__ import annotations

from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult

# Module-level dict to store active listeners: {event_name: handler_callable}
_active_listeners: dict[str, Any] = {}


class ListenerCommand(BaseCommand):
    """Subscribe, unsubscribe, and list event listeners."""

    name = "listener"
    description = "Manage event listeners (add/remove/list)"
    usage = "listener add <event> | listener remove <event> | listener list"
    aliases = ["on"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the listener command."""
        subcommand = args.positional[0] if args.positional else "list"

        if subcommand == "add":
            return await self._add_listener(broker, args)
        elif subcommand == "remove":
            return await self._remove_listener(broker, args)
        elif subcommand == "list":
            return self._list_listeners()
        else:
            return CommandResult(
                success=False,
                error=f"Unknown subcommand '{subcommand}'. Use: add, remove, list",
            )

    async def _add_listener(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Subscribe to an event and print when received."""
        if len(args.positional) < 2:
            return CommandResult(
                success=False, error="Event name required. Usage: listener add <eventName>"
            )

        event_name = args.positional[1]

        if event_name in _active_listeners:
            return CommandResult(
                success=False,
                error=f"Already listening to '{event_name}'. Remove it first.",
            )

        def make_handler(name: str) -> Any:
            async def handler(payload: Any = None, sender: str = "", **kwargs: Any) -> None:
                print(f"\n>> Event '{name}' received from '{sender}':")
                if payload is not None:
                    print(f"   {payload}")

            return handler

        handler = make_handler(event_name)

        try:
            broker.on(event_name, handler)
            _active_listeners[event_name] = handler
            return CommandResult(
                success=True,
                output=f"Subscribed to event '{event_name}'",
            )
        except Exception as e:
            return CommandResult(success=False, error=f"Failed to subscribe: {e}")

    async def _remove_listener(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Unsubscribe from an event."""
        if len(args.positional) < 2:
            return CommandResult(
                success=False,
                error="Event name required. Usage: listener remove <eventName>",
            )

        event_name = args.positional[1]

        if event_name not in _active_listeners:
            return CommandResult(
                success=False,
                error=f"Not listening to '{event_name}'",
            )

        handler = _active_listeners.pop(event_name)

        try:
            broker.off(event_name, handler)
            return CommandResult(
                success=True,
                output=f"Unsubscribed from event '{event_name}'",
            )
        except Exception as e:
            # Already removed from our dict, just warn
            return CommandResult(
                success=True,
                output=f"Removed listener for '{event_name}' (broker.off error: {e})",
            )

    def _list_listeners(self) -> CommandResult:
        """List all active listeners."""
        if not _active_listeners:
            return CommandResult(success=True, output="No active listeners")

        lines = [f"Active listeners ({len(_active_listeners)}):"]
        for event_name in sorted(_active_listeners.keys()):
            lines.append(f"  - {event_name}")

        return CommandResult(success=True, output="\n".join(lines))
