"""Services command — List registered services."""

from __future__ import annotations

from typing import Any

from ..output import OutputFormatter
from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class ServicesCommand(BaseCommand):
    """List registered services in the cluster.

    Shows service information including:
    - Service name
    - Version
    - State (OK/FAILED)
    - Action count
    - Event count
    - Node count with local marker (*)

    Usage:
        services [-a] [-l] [--skipInternal]

    Flags:
        -a: Show all services (including internal)
        -l: Show local services only
        --skipInternal: Skip $-prefixed internal services (default: True)
    """

    name = "services"
    description = "List registered services"
    usage = "services [-a] [-l] [--skipInternal]"
    aliases = ["s"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the services command."""
        show_all = args.flags.get("a", False)
        show_local = args.flags.get("l", False)
        skip_internal = args.flags.get("skipInternal", True)

        try:
            services = []
            # MoleculerPy 0.14.35+ uses nodeID as primary attribute
            local_node_id = (
                getattr(broker, "nodeID", None)
                or getattr(broker, "node_id", None)
                or getattr(broker, "id", None)
            )

            # MoleculerPy pattern: broker.registry.__services__
            if hasattr(broker, "registry") and hasattr(broker.registry, "__services__"):
                for name, service in broker.registry.__services__.items():
                    services.append(
                        {
                            "name": name,
                            "version": getattr(service, "version", None) or "-",
                            "fullName": getattr(service, "full_name", name),
                            "nodeIds": [local_node_id] if local_node_id else [],
                            "local": True,
                            "available": True,
                            "actions": getattr(service, "actions", {}),
                            "events": getattr(service, "events", {}),
                        }
                    )
            # Moleculer.js pattern: registry.get_service_list()
            elif hasattr(broker, "registry") and hasattr(broker.registry, "get_service_list"):
                services = broker.registry.get_service_list()
            # Fallback: get from broker.services dict (mock broker)
            else:
                if hasattr(broker, "services"):
                    for name, service in broker.services.items():
                        services.append(
                            {
                                "name": name,
                                "version": getattr(service, "version", None) or "-",
                                "fullName": getattr(service, "full_name", name),
                                "nodeIds": [local_node_id] if local_node_id else [],
                                "local": True,
                                "available": True,
                                "actions": getattr(service, "actions", {}),
                                "events": getattr(service, "events", {}),
                            }
                        )

            # Filter internal services (starting with $)
            if skip_internal and not show_all:
                services = [s for s in services if not s.get("name", "").startswith("$")]

            # Filter local only
            if show_local:
                services = [s for s in services if s.get("local", False)]

            if not services:
                return CommandResult(success=True, output="No services registered.")

            # Use OutputFormatter for beautiful output
            formatter = OutputFormatter(use_colors=True, capture=True)
            formatter.services_table(services, local_node_id=local_node_id)

            return CommandResult(
                success=True,
                output=formatter.get_output(),
                data=services if show_all else None,
            )

        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get completions for flags."""
        flags = ["-a", "-l", "--skipInternal"]
        return [f for f in flags if f.startswith(text)]
