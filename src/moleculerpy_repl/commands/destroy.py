"""Destroy command — Destroy a local service."""

from __future__ import annotations

from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class DestroyCommand(BaseCommand):
    """Destroy a local service by name."""

    name = "destroy"
    description = "Destroy a local service"
    usage = "destroy <serviceName>"

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the destroy command."""
        if not args.positional:
            return CommandResult(
                success=False,
                error="Service name required. Usage: destroy <serviceName>",
            )

        service_name = args.positional[0]

        try:
            if hasattr(broker, "destroyService"):
                # Find the service instance by name
                service = None
                if hasattr(broker, "services"):
                    service = broker.services.get(service_name)

                if service is None:
                    return CommandResult(success=False, error=f"Service '{service_name}' not found")

                await broker.destroyService(service)
                return CommandResult(
                    success=True,
                    output=f"Service '{service_name}' destroyed.",
                )
            else:
                return CommandResult(
                    success=False,
                    error="broker.destroyService is not supported in this version",
                )

        except Exception as e:
            return CommandResult(success=False, error=f"Destroy failed: {e}")

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get service name completions."""
        try:
            if hasattr(broker, "services"):
                return [name for name in broker.services if name.startswith(text)]
        except Exception:
            pass
        return []
