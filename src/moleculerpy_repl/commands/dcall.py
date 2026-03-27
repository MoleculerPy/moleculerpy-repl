"""Direct Call command — Call action on specific node."""

from __future__ import annotations

import time
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class DirectCallCommand(BaseCommand):
    """Direct call an action on a specific node."""

    name = "dcall"
    description = "Direct call an action on a specific node"
    usage = "dcall <nodeID> <action> [params...] [#meta...] [$options...]"
    aliases = ["dc"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the direct call command.

        Syntax: dcall <nodeID> <action> [params...]

        Example:
            dcall node-2-1 math.add a=5 b=3
            dcall node-1 user.get id=123 #tenant=acme
        """
        if len(args.positional) < 2:
            return CommandResult(
                success=False,
                error="Node ID and action name required. Usage: dcall <nodeID> <action> [params...]",
            )

        node_id = args.positional[0]
        action_name = args.positional[1]

        # Validate node exists (if registry available)
        if hasattr(broker, "registry"):
            node = None

            # Try different MoleculerPy patterns
            if hasattr(broker, "node_catalog") and hasattr(broker.node_catalog, "nodes"):
                node = broker.node_catalog.nodes.get(node_id)
            elif hasattr(broker.registry, "get_node"):
                node = broker.registry.get_node(node_id)
            elif hasattr(broker.registry, "nodes"):
                nodes = broker.registry.nodes
                if hasattr(nodes, "get"):
                    node = nodes.get(node_id)

            # Check if node is valid (optional - some brokers may not have this)
            if node is None and hasattr(broker, "node_catalog"):
                available_nodes = (
                    list(broker.node_catalog.nodes.keys())
                    if hasattr(broker.node_catalog, "nodes")
                    else []
                )
                if available_nodes:
                    return CommandResult(
                        success=False,
                        error=f"Node '{node_id}' not found. Available: {', '.join(available_nodes)}",
                    )

        # Build call options
        call_opts = {"node_id": node_id}

        # Handle $timeout option
        if "timeout" in args.options:
            call_opts["timeout"] = args.options.pop("timeout")

        # Handle $retries option
        if "retries" in args.options:
            call_opts["retries"] = args.options.pop("retries")

        # Merge remaining options
        call_opts.update(args.options)

        try:
            start_time = time.perf_counter()

            # Call the action with nodeID
            result = await broker.call(
                action_name, args.payload, meta=args.meta if args.meta else None, **call_opts
            )

            elapsed = (time.perf_counter() - start_time) * 1000  # ms

            return CommandResult(
                success=True,
                data=result,
                output=f">> Direct call to [{node_id}] ({elapsed:.2f}ms):",
            )

        except Exception as e:
            error_msg = str(e)

            # Try to extract meaningful error message
            if hasattr(e, "message"):
                error_msg = e.message
            elif hasattr(e, "args") and e.args:
                error_msg = str(e.args[0])

            return CommandResult(
                success=False, error=f"Direct call to [{node_id}] failed: {error_msg}"
            )

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get node ID and action name completions."""
        parts = line.split()

        # If typing nodeID (first argument after dcall)
        if len(parts) <= 2:
            return self._get_node_completions(broker, text)

        # If typing action name (second argument)
        if len(parts) <= 3:
            return self._get_action_completions(broker, text)

        return []

    def _get_node_completions(self, broker: Any, text: str) -> list[str]:
        """Get node ID completions."""
        try:
            nodes = []

            if hasattr(broker, "node_catalog") and hasattr(broker.node_catalog, "nodes"):
                nodes = list(broker.node_catalog.nodes.keys())
            elif hasattr(broker, "registry"):
                if hasattr(broker.registry, "get_node_list"):
                    node_list = broker.registry.get_node_list()
                    nodes = [n.get("id", "") for n in node_list]
                elif hasattr(broker.registry, "nodes"):
                    nodes = list(broker.registry.nodes.keys())

            return [n for n in nodes if n.startswith(text)]

        except Exception:
            return []

    def _get_action_completions(self, broker: Any, text: str) -> list[str]:
        """Get action name completions."""
        try:
            actions = []

            if hasattr(broker, "registry") and hasattr(broker.registry, "__actions__"):
                for action in broker.registry.__actions__:
                    name = getattr(action, "name", "")
                    if name:
                        actions.append(name)
            elif hasattr(broker, "services"):
                for service in broker.services.values():
                    if hasattr(service, "actions"):
                        for action_name in service.actions:
                            actions.append(f"{service.name}.{action_name}")

            return [a for a in actions if a.startswith(text)]

        except Exception:
            return []
