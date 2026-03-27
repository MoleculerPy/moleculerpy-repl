"""Info command — Show broker information."""

from __future__ import annotations

import platform
import sys
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class InfoCommand(BaseCommand):
    """Show broker and system information."""

    name = "info"
    description = "Show broker information"
    usage = "info"
    aliases = ["i"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the info command."""
        try:
            # Gather broker info
            # MoleculerPy 0.14.35+ uses nodeID as primary attribute
            node_id = (
                getattr(broker, "nodeID", None)
                or getattr(broker, "node_id", None)
                or getattr(broker, "id", "unknown")
            )
            namespace = getattr(broker, "namespace", "")

            # Get version info
            broker_version = getattr(broker, "__version__", None) or getattr(
                broker, "version", "unknown"
            )
            if hasattr(broker, "PROTOCOL_VERSION"):
                protocol_version = broker.PROTOCOL_VERSION
            else:
                protocol_version = "unknown"

            # Get transporter info
            transporter = "None"
            if hasattr(broker, "transit") and broker.transit:
                transit = broker.transit
                if hasattr(transit, "transporter"):
                    tp = transit.transporter
                    transporter = getattr(tp, "name", type(tp).__name__)
                elif hasattr(transit, "type"):
                    transporter = transit.type

            # Get serializer info
            serializer = "JSON"
            if hasattr(broker, "serializer"):
                ser = broker.serializer
                serializer = getattr(ser, "name", type(ser).__name__)

            # Count services and actions
            service_count = 0
            action_count = 0
            event_count = 0

            if hasattr(broker, "registry") and hasattr(broker.registry, "__services__"):
                services = list(broker.registry.__services__.values())
                actions = getattr(broker.registry, "__actions__", [])
                service_count = len(services)
                action_count = len(actions)
                for service in services:
                    service_events = getattr(service, "events", None)
                    if isinstance(service_events, dict):
                        event_count += len(service_events)
            elif hasattr(broker, "services"):
                service_count = len(broker.services)
                for service in broker.services.values():
                    service_actions = getattr(service, "actions", None)
                    if isinstance(service_actions, dict):
                        action_count += len(service_actions)
                    service_events = getattr(service, "events", None)
                    if isinstance(service_events, dict):
                        event_count += len(service_events)

            # System info
            python_version = (
                f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            )
            os_info = f"{platform.system()} {platform.release()}"
            hostname = platform.node()

            # Format output
            lines = [
                "Broker Information:",
                "-" * 40,
                f"  Node ID:         {node_id}",
                f"  Namespace:       {namespace or '(none)'}",
                f"  Version:         {broker_version}",
                f"  Protocol:        {protocol_version}",
                "",
                "Transport:",
                "-" * 40,
                f"  Transporter:     {transporter}",
                f"  Serializer:      {serializer}",
                "",
                "Statistics:",
                "-" * 40,
                f"  Services:        {service_count}",
                f"  Actions:         {action_count}",
                f"  Events:          {event_count}",
                "",
                "System:",
                "-" * 40,
                f"  Python:          {python_version}",
                f"  Platform:        {os_info}",
                f"  Hostname:        {hostname}",
                f"  PID:             {_get_pid()}",
            ]

            # Add uptime if available
            if hasattr(broker, "started_at") and broker.started_at is not None:
                import time

                uptime = time.time() - broker.started_at
                lines.append(f"  Uptime:          {_format_uptime(uptime)}")

            return CommandResult(
                success=True,
                output="\n".join(lines),
            )

        except Exception as e:
            return CommandResult(success=False, error=str(e))


def _get_pid() -> int:
    """Get current process ID."""
    import os

    return os.getpid()


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"
