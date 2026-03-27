"""Emit command — Publish an event."""

from __future__ import annotations

from typing import Any

from .base import BaseCommand, CommandResult
from ..parser import ParsedArgs


class EmitCommand(BaseCommand):
    """Emit an event to the cluster."""

    name = "emit"
    description = "Emit an event"
    usage = "emit <event> [params...] [#meta...]"
    aliases = ["e"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the emit command."""
        if not args.positional:
            return CommandResult(
                success=False, error="Event name required. Usage: emit <event> [params...]"
            )

        event_name = args.positional[0]

        try:
            # Emit the event
            await broker.emit(
                event_name,
                args.payload,
                meta=args.meta if args.meta else None,
            )

            return CommandResult(
                success=True,
                output=f"Event emitted: {event_name}",
            )

        except Exception as e:
            return CommandResult(success=False, error=f"Emit failed: {e}")

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get event name completions."""
        try:
            events = []

            # Try to get events from registry
            if hasattr(broker, "registry") and hasattr(broker.registry, "get_event_list"):
                event_list = broker.registry.get_event_list()
                events = [e.get("name", "") for e in event_list]
            elif hasattr(broker, "services"):
                for service in broker.services.values():
                    if hasattr(service, "events"):
                        for event_name in service.events:
                            events.append(event_name)

            return [e for e in events if e.startswith(text)]

        except Exception:
            return []


class BroadcastCommand(BaseCommand):
    """Broadcast an event to all nodes."""

    name = "broadcast"
    description = "Broadcast an event to all nodes"
    usage = "broadcast <event> [params...] [#meta...]"
    aliases = ["b"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the broadcast command."""
        if not args.positional:
            return CommandResult(
                success=False, error="Event name required. Usage: broadcast <event> [params...]"
            )

        event_name = args.positional[0]

        try:
            # Broadcast the event
            if hasattr(broker, "broadcast"):
                await broker.broadcast(
                    event_name,
                    args.payload,
                    meta=args.meta if args.meta else None,
                )
            else:
                # Fallback to emit
                await broker.emit(
                    event_name,
                    args.payload,
                    meta=args.meta if args.meta else None,
                )

            return CommandResult(
                success=True,
                output=f"Broadcast sent: {event_name}",
            )

        except Exception as e:
            return CommandResult(success=False, error=f"Broadcast failed: {e}")
