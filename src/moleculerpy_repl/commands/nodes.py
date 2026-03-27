"""Nodes command — List cluster nodes."""

from __future__ import annotations

import os
import psutil
from typing import Any

from .base import BaseCommand, CommandResult
from ..parser import ParsedArgs
from ..output import OutputFormatter


class NodesCommand(BaseCommand):
    """List nodes in the cluster.

    Shows node information including:
    - Node ID with local marker (*)
    - Service count
    - State (ONLINE/OFFLINE/LOCAL)
    - CPU usage with visual bar

    Usage:
        nodes [-a] [-d]

    Flags:
        -a: Show all nodes (including unavailable)
        -d: Show detailed view (IP, version, hostname)
    """

    name = "nodes"
    description = "List cluster nodes"
    usage = "nodes [-a] [-d]"
    aliases = ["n"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the nodes command."""
        show_all = args.flags.get("a", False)
        show_details = args.flags.get("d", False)

        try:
            nodes = []
            # MoleculerPy 0.14.35+ uses nodeID as primary attribute
            local_node_id = getattr(broker, "nodeID", None) or getattr(broker, "node_id", None) or getattr(broker, "id", None)

            # Get current CPU usage
            current_cpu = psutil.cpu_percent(interval=0.1)

            # MoleculerPy pattern: broker.node_catalog.nodes
            if hasattr(broker, "node_catalog") and hasattr(broker.node_catalog, "nodes"):
                for node_id, node in broker.node_catalog.nodes.items():
                    is_local = node_id == local_node_id
                    nodes.append({
                        "id": node_id,
                        "available": getattr(node, "available", True),
                        "local": is_local,
                        "cpu": current_cpu if is_local else getattr(node, "cpu", None),
                        "ipList": getattr(node, "ipList", []),
                        "hostname": getattr(node, "hostname", None),
                        "client": getattr(node, "client", {}),
                        "services": getattr(node, "services", []),
                        "serviceCount": len(getattr(node, "services", [])),
                    })
            # Moleculer.js pattern: registry.get_node_list()
            elif hasattr(broker, "registry") and hasattr(broker.registry, "get_node_list"):
                registry_nodes = broker.registry.get_node_list()
                for node in registry_nodes:
                    is_local = node.get("id") == local_node_id
                    if is_local:
                        node["cpu"] = current_cpu
                    nodes.append(node)
            # Fallback: just show local node
            else:
                hostname = os.uname().nodename if hasattr(os, "uname") else "localhost"
                nodes = [{
                    "id": local_node_id or "local",
                    "available": True,
                    "local": True,
                    "hostname": hostname,
                    "cpu": current_cpu,
                    "serviceCount": len(getattr(broker, "services", {})),
                    "ipList": self._get_local_ips(),
                    "client": {"version": getattr(broker, "__version__", "0.1.0")},
                }]

            # Filter unavailable nodes
            if not show_all:
                nodes = [n for n in nodes if n.get("available", True)]

            if not nodes:
                return CommandResult(
                    success=True,
                    output="No nodes available."
                )

            # Use OutputFormatter for beautiful output
            formatter = OutputFormatter(use_colors=True, capture=True)
            formatter.nodes_table(nodes, show_details=show_details, local_node_id=local_node_id)

            return CommandResult(
                success=True,
                output=formatter.get_output(),
                data=nodes if show_all else None,
            )

        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def _get_local_ips(self) -> list[str]:
        """Get local IP addresses."""
        try:
            ips = []
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == 2:  # AF_INET (IPv4)
                        if not addr.address.startswith("127."):
                            ips.append(addr.address)
            return ips[:3]  # Limit to 3
        except Exception:
            return []

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get completions for flags."""
        flags = ["-a", "-d"]
        return [f for f in flags if f.startswith(text)]
