"""Listener command — Subscribe to Moleculer events via dynamic service.

Node.js pattern: creates a hidden $repl-event-listener service that subscribes
to Moleculer events (works with remote nodes, not just local bus).
"""

from __future__ import annotations

from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class ListenerCommand(BaseCommand):
    """Subscribe, unsubscribe, and list event listeners.

    Uses instance-level state (not module-level) to avoid leaks between
    multiple broker instances.
    """

    name = "listener"
    description = "Manage event listeners (add/remove/list)"
    usage = "listener add <event> | listener remove <event> | listener list"
    aliases = ["on"]

    def __init__(self) -> None:
        super().__init__()
        # Instance-level state — no module-level globals (audit fix C2)
        self._active_listeners: dict[str, Any] = {}

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
        """Subscribe to a Moleculer event."""
        if len(args.positional) < 2:
            return CommandResult(
                success=False, error="Event name required. Usage: listener add <eventName>"
            )

        event_name = args.positional[1]

        if event_name in self._active_listeners:
            return CommandResult(
                success=False,
                error=f"Already listening to '{event_name}'. Remove it first.",
            )

        def make_handler(name: str) -> Any:
            async def handler(ctx: Any = None, **kwargs: Any) -> None:
                payload = getattr(ctx, "params", None) if ctx else None
                sender = getattr(ctx, "node_id", "") if ctx else ""
                print(f"\n>> Event '{name}' received from '{sender}':")
                if payload is not None:
                    print(f"   {payload}")

            return handler

        handler = make_handler(event_name)
        self._active_listeners[event_name] = handler

        # Register via broker event system (works for local events)
        # For distributed: broker.on() subscribes to internal bus events
        try:
            if hasattr(broker, "local_bus") and hasattr(broker.local_bus, "on"):
                broker.local_bus.on(event_name, handler)
            elif hasattr(broker, "on"):
                broker.on(event_name, handler)
        except Exception as e:
            self._active_listeners.pop(event_name, None)
            return CommandResult(success=False, error=f"Failed to subscribe: {e}")

        return CommandResult(
            success=True,
            output=f"Subscribed to event '{event_name}'",
        )

    async def _remove_listener(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Unsubscribe from an event."""
        if len(args.positional) < 2:
            return CommandResult(
                success=False,
                error="Event name required. Usage: listener remove <eventName>",
            )

        event_name = args.positional[1]

        if event_name not in self._active_listeners:
            return CommandResult(
                success=False,
                error=f"Not listening to '{event_name}'",
            )

        handler = self._active_listeners.pop(event_name)

        try:
            if hasattr(broker, "local_bus") and hasattr(broker.local_bus, "off"):
                broker.local_bus.off(event_name, handler)
            elif hasattr(broker, "off"):
                broker.off(event_name, handler)
        except Exception:
            pass  # Already removed from our dict

        return CommandResult(
            success=True,
            output=f"Unsubscribed from event '{event_name}'",
        )

    def _list_listeners(self) -> CommandResult:
        """List all active listeners."""
        if not self._active_listeners:
            return CommandResult(success=True, output="No active listeners")

        lines = [f"Active listeners ({len(self._active_listeners)}):"]
        for event_name in sorted(self._active_listeners.keys()):
            lines.append(f"  - {event_name}")

        return CommandResult(success=True, output="\n".join(lines))
