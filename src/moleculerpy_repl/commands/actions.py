"""Actions command — List available actions."""

from __future__ import annotations

from typing import Any

from ..output import OutputFormatter
from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class ActionsCommand(BaseCommand):
    """List available actions in the cluster.

    Shows action information including:
    - Action name (service.action)
    - Node count with local marker (*)
    - State (OK/FAILED)
    - Cached status (Yes/No)
    - Parameters

    Usage:
        actions [-a] [--skipInternal]

    Flags:
        -a: Show all actions (including internal)
        --skipInternal: Skip $-prefixed internal actions (default: True)
    """

    name = "actions"
    description = "List available actions"
    usage = "actions [-a] [--skipInternal]"
    aliases = ["a"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the actions command."""
        show_all = args.flags.get("a", False)
        skip_internal = args.flags.get("skipInternal", True)

        try:
            actions = []
            # MoleculerPy 0.14.35+ uses nodeID as primary attribute
            local_node_id = (
                getattr(broker, "nodeID", None)
                or getattr(broker, "node_id", None)
                or getattr(broker, "id", None)
            )

            # MoleculerPy pattern: broker.registry.__actions__
            if hasattr(broker, "registry") and hasattr(broker.registry, "__actions__"):
                for action in broker.registry.__actions__:
                    actions.append(
                        {
                            "name": getattr(action, "name", "unknown"),
                            "nodeIds": [local_node_id] if local_node_id else [],
                            "available": True,
                            "cache": getattr(action, "cache", False),
                            "params": getattr(action, "params", {}),
                        }
                    )
            # Moleculer.js pattern: registry.get_action_list()
            elif hasattr(broker, "registry") and hasattr(broker.registry, "get_action_list"):
                actions = broker.registry.get_action_list()
            # Fallback: try to get from registered services (mock broker)
            else:
                if hasattr(broker, "services"):
                    for service in broker.services.values():
                        if hasattr(service, "actions"):
                            for action_name, action in service.actions.items():
                                # Extract params from lambda/function if possible
                                params = {}
                                if callable(action):
                                    import inspect

                                    try:
                                        sig = inspect.signature(action)
                                        params = {
                                            p.name: {"type": "any"}
                                            for p in sig.parameters.values()
                                            if p.name != "self" and p.name != "params"
                                        }
                                    except (ValueError, TypeError):
                                        pass

                                actions.append(
                                    {
                                        "name": f"{service.name}.{action_name}",
                                        "service": service.name,
                                        "nodeIds": [local_node_id] if local_node_id else [],
                                        "available": True,
                                        "cache": False,
                                        "params": params,
                                    }
                                )

            # Filter internal actions
            if skip_internal and not show_all:
                actions = [
                    action
                    for action in actions
                    if not (
                        isinstance(action_name := action.get("name"), str)
                        and action_name.startswith("$")
                    )
                ]

            if not actions:
                return CommandResult(success=True, output="No actions available.")

            # Use OutputFormatter for beautiful output
            formatter = OutputFormatter(use_colors=True, capture=True)
            formatter.actions_table(actions, local_node_id=local_node_id)

            return CommandResult(
                success=True,
                output=formatter.get_output(),
                data=actions if show_all else None,
            )

        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get completions for flags."""
        flags = ["-a", "--skipInternal"]
        return [f for f in flags if f.startswith(text)]
