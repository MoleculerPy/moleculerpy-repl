"""Events command — List available events."""

from __future__ import annotations

from typing import Any

from ..output import OutputFormatter
from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class EventsCommand(BaseCommand):
    """List registered events in the cluster.

    Shows event information including:
    - Event name
    - Group
    - State (OK/FAILED)
    - Node count with local marker (*)

    Usage:
        events [-a] [-l] [--skipInternal]

    Flags:
        -a: Show all events (including internal)
        -l: Show local events only
        --skipInternal: Skip $-prefixed internal events (default: True)
    """

    name = "events"
    description = "List registered events"
    usage = "events [-a] [-l] [--skipInternal]"
    aliases = ["ev"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the events command."""
        show_all = args.flags.get("a", False)
        show_local = args.flags.get("l", False)
        skip_internal = args.flags.get("skipInternal", True)

        try:
            events = []
            # MoleculerPy 0.14.35+ uses nodeID as primary attribute
            local_node_id = (
                getattr(broker, "nodeID", None)
                or getattr(broker, "node_id", None)
                or getattr(broker, "id", None)
            )

            # Get events from registry
            if hasattr(broker, "registry") and hasattr(broker.registry, "get_event_list"):
                events = broker.registry.get_event_list()
            elif hasattr(broker, "get_local_event_list"):
                events = broker.get_local_event_list()
            else:
                # Fallback: get from broker.services
                if hasattr(broker, "services"):
                    for service in broker.services.values():
                        if hasattr(service, "events"):
                            for event_name in service.events:
                                events.append(
                                    {
                                        "name": event_name,
                                        "group": service.name,
                                        "service": service.name,
                                        "nodeIds": [local_node_id] if local_node_id else [],
                                        "local": True,
                                        "available": True,
                                    }
                                )

            # Filter internal events (starting with $)
            if skip_internal and not show_all:
                events = [e for e in events if not e.get("name", "").startswith("$")]

            # Filter local only
            if show_local:
                events = [e for e in events if e.get("local", False)]

            if not events:
                return CommandResult(success=True, output="No events registered.")

            # Use OutputFormatter for beautiful output
            formatter = OutputFormatter(use_colors=True, capture=True)
            formatter.events_table(events, local_node_id=local_node_id)

            return CommandResult(
                success=True,
                output=formatter.get_output(),
                data=events if show_all else None,
            )

        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get completions for flags."""
        flags = ["-a", "-l", "--skipInternal"]
        return [f for f in flags if f.startswith(text)]
