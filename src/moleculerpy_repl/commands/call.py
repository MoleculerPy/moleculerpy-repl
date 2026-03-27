"""Call command — Invoke a service action."""

from __future__ import annotations

import time
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class CallCommand(BaseCommand):
    """Call a service action."""

    name = "call"
    description = "Call a service action"
    usage = "call <action> [params...] [#meta...] [$options...]"
    aliases = ["c"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the call command."""
        if not args.positional:
            return CommandResult(
                success=False, error="Action name required. Usage: call <action> [params...]"
            )

        action_name = args.positional[0]

        # Build call options
        call_opts = {}

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

            # Call the action
            result = await broker.call(
                action_name, args.payload, meta=args.meta if args.meta else None, **call_opts
            )

            elapsed = (time.perf_counter() - start_time) * 1000  # ms

            return CommandResult(
                success=True,
                data=result,
                output=f">> Response ({elapsed:.2f}ms):",
            )

        except Exception as e:
            error_msg = str(e)

            # Try to extract meaningful error message
            if hasattr(e, "message"):
                error_msg = e.message
            elif hasattr(e, "args") and e.args:
                error_msg = str(e.args[0])

            return CommandResult(success=False, error=f"Call failed: {error_msg}")

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get action name completions."""
        try:
            actions = []

            # Try to get actions from registry
            if hasattr(broker, "registry") and hasattr(broker.registry, "get_action_list"):
                action_list = broker.registry.get_action_list()
                actions = [a.get("name", "") for a in action_list]
            elif hasattr(broker, "services"):
                for service in broker.services.values():
                    if hasattr(service, "actions"):
                        for action_name in service.actions:
                            actions.append(f"{service.name}.{action_name}")

            return [a for a in actions if a.startswith(text)]

        except Exception:
            return []
