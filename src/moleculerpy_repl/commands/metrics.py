"""Metrics command — Show broker metrics."""

from __future__ import annotations

from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class MetricsCommand(BaseCommand):
    """Show broker metrics."""

    name = "metrics"
    description = "Show broker metrics"
    usage = "metrics [-f pattern]"
    aliases = ["m"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the metrics command."""
        pattern = args.flags.get("f")

        # Try to find MetricsMiddleware in broker middlewares
        metrics_registry = _find_metrics_registry(broker)

        if metrics_registry is None:
            return CommandResult(success=False, error="Metrics not enabled")

        try:
            output = _format_metrics(metrics_registry, pattern)
            return CommandResult(success=True, output=output)
        except Exception as e:
            return CommandResult(success=False, error=f"Failed to get metrics: {e}")


def _find_metrics_registry(broker: Any) -> Any:
    """Find metrics registry from broker."""
    # Check direct metrics attribute
    if hasattr(broker, "metrics") and broker.metrics:
        return broker.metrics

    # Search in middlewares list
    middlewares = getattr(broker, "middlewares", None) or []
    if hasattr(middlewares, "middlewares"):
        middlewares = middlewares.middlewares

    for mw in middlewares:
        mw_name = type(mw).__name__.lower()
        if "metric" in mw_name:
            # Try common attribute names for the registry
            for attr in ("registry", "metrics", "store", "_registry", "_metrics"):
                registry = getattr(mw, attr, None)
                if registry:
                    return registry
            return mw

    return None


def _format_metrics(registry: Any, pattern: str | None) -> str:
    """Format metrics as text output."""
    lines: list[str] = []

    # Try Prometheus-style output
    if hasattr(registry, "to_prometheus"):
        try:
            prometheus_output = registry.to_prometheus()
            if pattern:
                filtered = [
                    line
                    for line in prometheus_output.splitlines()
                    if pattern.lower() in line.lower()
                ]
                lines.extend(filtered)
            else:
                lines.extend(prometheus_output.splitlines())
            return "\n".join(lines) if lines else "No metrics found"
        except Exception:
            pass

    # Try iterating metrics dict or list
    metrics_data: Any = None
    for attr in ("_metrics", "metrics", "_store", "store", "_registry"):
        candidate = getattr(registry, attr, None)
        if candidate and isinstance(candidate, dict):
            metrics_data = candidate
            break

    if metrics_data is None and isinstance(registry, dict):
        metrics_data = registry

    if metrics_data:
        header = f"Metrics ({len(metrics_data)}):"
        if pattern:
            header = f"Metrics matching '{pattern}':"
        lines.append(header)
        lines.append("-" * 40)

        for name, value in sorted(metrics_data.items()):
            if pattern and pattern.lower() not in name.lower():
                continue
            lines.append(f"  {name}: {value}")

        return "\n".join(lines) if len(lines) > 2 else "No metrics found"

    return "Metrics registry found but no metrics available"
