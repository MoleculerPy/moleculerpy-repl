"""Bench command — Benchmark a service action.

Node.js equivalent: moleculer-repl/src/commands/bench.js
"""

from __future__ import annotations

import time
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult

_DEFAULT_NUM = 1000
# Node.js: if neither --num nor --time given, defaults to 5 seconds
_DEFAULT_TIME = 5.0


class BenchCommand(BaseCommand):
    """Benchmark a service action with timing statistics."""

    name = "bench"
    description = "Benchmark a service action"
    usage = "bench <action> [jsonParams] [--num N] [--time T] [--nodeID id]"

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the bench command."""
        if not args.positional:
            return CommandResult(
                success=False,
                error="Action name required. Usage: bench <action> [params] [--num N] [--time T]",
            )

        action_name = args.positional[0]

        # Parse flags
        has_num = "num" in args.flags
        has_time = "time" in args.flags
        num = int(args.flags.get("num", _DEFAULT_NUM))
        duration = float(args.flags.get("time", _DEFAULT_TIME))

        # Node.js: if --num given explicitly, use count-based mode
        # If --time given, use time-based mode
        # If neither, default to time-based (5s)
        use_time = not has_num or has_time

        # Build params
        params = dict(args.payload) if args.payload else {}
        if len(args.positional) > 1:
            import json  # noqa: PLC0415

            try:
                extra = json.loads(args.positional[1])
                if isinstance(extra, dict):
                    params.update(extra)
            except (json.JSONDecodeError, ValueError):
                pass

        try:
            output = await _run_benchmark(
                broker, action_name, params, num if not use_time else 0, duration if use_time else 0
            )
            return CommandResult(success=True, output=output)
        except Exception as e:
            return CommandResult(success=False, error=f"Benchmark failed: {e}")


async def _run_benchmark(
    broker: Any,
    action: str,
    params: dict[str, Any],
    num: int,
    duration: float,
) -> str:
    """Run the benchmark loop and return formatted statistics."""
    timings: list[float] = []
    errors = 0

    print(f"Benchmarking '{action}'...")

    # Track total wall-clock time for real RPS calculation
    wall_start = time.perf_counter()

    if duration > 0:
        # Time-based: run for `duration` seconds
        end_time = wall_start + duration
        while time.perf_counter() < end_time:
            t0 = time.perf_counter()
            try:
                await broker.call(action, params)
            except Exception:
                errors += 1
            # Record time for ALL calls including errors (audit fix H3/M3)
            timings.append((time.perf_counter() - t0) * 1000)
    else:
        # Count-based: run `num` iterations
        for _ in range(num):
            t0 = time.perf_counter()
            try:
                await broker.call(action, params)
            except Exception:
                errors += 1
            timings.append((time.perf_counter() - t0) * 1000)

    wall_total = time.perf_counter() - wall_start
    return _format_stats(action, timings, errors, wall_total)


def _format_stats(action: str, timings: list[float], errors: int, wall_seconds: float) -> str:
    """Format benchmark statistics."""
    total = len(timings)

    if not timings:
        return f"Benchmark '{action}': 0 calls, {errors} errors"

    total_time_ms = sum(timings)
    avg_ms = total_time_ms / total
    min_ms = min(timings)
    max_ms = max(timings)

    # Real throughput RPS (Node.js: resCount / duration * 1000)
    rps = total / wall_seconds if wall_seconds > 0 else 0.0

    lines = [
        f"Benchmark: {action}",
        "-" * 40,
        f"  Total calls:   {total}",
        f"  Successful:    {total - errors}",
        f"  Errors:        {errors}",
        f"  Duration:      {wall_seconds:.3f}s",
        f"  Req/sec:       {rps:.1f}",
        "",
        "Latency:",
        f"  min:           {min_ms:.3f}ms",
        f"  avg:           {avg_ms:.3f}ms",
        f"  max:           {max_ms:.3f}ms",
    ]

    return "\n".join(lines)
