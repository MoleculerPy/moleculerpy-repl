"""Load command — Load a service from a file.

WARNING: This command executes arbitrary Python code from the specified file.
Only load files from trusted sources.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any

from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult


class LoadCommand(BaseCommand):
    """Load a service from a Python file."""

    name = "load"
    description = "Load a service from file"
    usage = "load <path>"

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the load command."""
        if not args.positional:
            return CommandResult(success=False, error="File path required. Usage: load <path>")

        file_path = Path(args.positional[0]).expanduser().resolve()

        if not file_path.exists():
            return CommandResult(success=False, error=f"File not found: {file_path}")

        if file_path.suffix != ".py":
            return CommandResult(
                success=False, error=f"Expected a .py file, got: {file_path.suffix}"
            )

        try:
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return CommandResult(success=False, error=f"Cannot load module from: {file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)  # type: ignore[union-attr]

            # Find Service subclasses in module
            service_class = None
            try:
                from moleculerpy import Service  # type: ignore[import-untyped]

                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Service) and obj is not Service:
                        service_class = obj
                        break
            except ImportError:
                # Fallback: look for class with 'name' attribute typical of services
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if hasattr(obj, "name") and hasattr(obj, "actions"):
                        service_class = obj
                        break

            if service_class is None:
                return CommandResult(
                    success=False,
                    error=f"No Service subclass found in {file_path.name}",
                )

            svc = service_class(broker)
            await broker.addLocalService(svc)

            return CommandResult(
                success=True,
                output=f"Service '{getattr(svc, 'name', service_class.__name__)}' loaded from {file_path.name}",
            )

        except SystemExit:
            raise
        except Exception as e:
            return CommandResult(success=False, error=f"Load failed: {e}")
