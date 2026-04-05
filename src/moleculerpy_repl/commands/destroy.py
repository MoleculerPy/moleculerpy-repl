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
            # Try broker.destroyService first (Node.js pattern)
            if hasattr(broker, "destroyService"):
                service = None
                if hasattr(broker, "services"):
                    service = broker.services.get(service_name)
                if service is None and hasattr(broker, "registry"):
                    service = broker.registry.__services__.get(service_name)
                if service is None:
                    return CommandResult(success=False, error=f"Service '{service_name}' not found")
                await broker.destroyService(service)
            elif hasattr(broker, "registry"):
                # Fallback: remove from registry directly
                registry = broker.registry
                if service_name not in registry.__services__:
                    return CommandResult(success=False, error=f"Service '{service_name}' not found")
                del registry.__services__[service_name]
                # Remove associated actions
                registry.__actions__ = [a for a in registry.__actions__ if not a.name.startswith(f"{service_name}.")]
                registry._actions_by_name = {
                    k: v for k, v in registry._actions_by_name.items()
                    if not k.startswith(f"{service_name}.")
                }
            else:
                return CommandResult(success=False, error="Cannot destroy: no registry access")

            return CommandResult(success=True, output=f"Service '{service_name}' destroyed.")
        except Exception as e:
            return CommandResult(success=False, error=f"Destroy failed: {e}")

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get service name completions."""
        try:
            if hasattr(broker, "registry"):
                return [n for n in broker.registry.__services__ if n.startswith(text)]
        except Exception:
            pass
        return []
