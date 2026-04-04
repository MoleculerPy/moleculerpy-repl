"""Bench command — Benchmark a service action."""

from __future__ import annotations

import time
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult

_DEFAULT_NUM = 1000
_DEFAULT_TIME = 0  # 0 means use --num instead


class BenchCommand(BaseCommand):
    """Benchmark a service action with timing statistics."""

    name = "bench"
    description = "Benchmark a service action"
    usage = "bench <action> [jsonParams] [--num N] [--time T]"

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the bench command."""
        if not args.positional:
            return CommandResult(
                success=False,
                error="Action name required. Usage: bench <action> [params] [--num N] [--time T]",
            )

        action_name = args.positional[0]

        # Parse num and time from flags
        num = int(args.flags.get("num", _DEFAULT_NUM))
        duration = float(args.flags.get("time", _DEFAULT_TIME))

        # Build params from payload
        params = dict(args.payload) if args.payload else {}

        # Try to parse second positional as JSON params
        if len(args.positional) > 1:
            import json

            try:
                extra = json.loads(args.positional[1])
                if isinstance(extra, dict):
                    params.update(extra)
            except (json.JSONDecodeError, ValueError):
                pass

        try:
            output = await _run_benchmark(broker, action_name, params, num, duration)
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

    if duration > 0:
        # Time-based: run for `duration` seconds
        end_time = time.perf_counter() + duration
        while time.perf_counter() < end_time:
            t0 = time.perf_counter()
            try:
                await broker.call(action, params)
                timings.append((time.perf_counter() - t0) * 1000)
            except Exception:
                errors += 1
    else:
        # Count-based: run `num` iterations
        for _ in range(num):
            t0 = time.perf_counter()
            try:
                await broker.call(action, params)
                timings.append((time.perf_counter() - t0) * 1000)
            except Exception:
                errors += 1

    return _format_stats(action, timings, errors)


def _format_stats(action: str, timings: list[float], errors: int) -> str:
    """Format benchmark statistics."""
    total = len(timings) + errors

    if not timings:
        return f"Benchmark '{action}': 0 successful calls, {errors} errors"

    total_time_ms = sum(timings)
    avg_ms = total_time_ms / len(timings)
    min_ms = min(timings)
    max_ms = max(timings)

    # req/sec based on average latency
    rps = 1000.0 / avg_ms if avg_ms > 0 else 0.0

    lines = [
        f"Benchmark: {action}",
        "-" * 40,
        f"  Total calls:   {total}",
        f"  Successful:    {len(timings)}",
        f"  Errors:        {errors}",
        f"  Req/sec:       {rps:.1f}",
        "",
        "Latency:",
        f"  min:           {min_ms:.3f}ms",
        f"  avg:           {avg_ms:.3f}ms",
        f"  max:           {max_ms:.3f}ms",
    ]

    return "\n".join(lines)
