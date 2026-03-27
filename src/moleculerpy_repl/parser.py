"""Argument parser for MoleculerPy REPL commands.

Supports prefix system like moleculer-repl:
    - key=value       → payload
    - #key=value      → meta
    - $key=value      → options
    - --flag          → flags[flag] = True
    - --key=value     → flags[key] = value
    - --json '{...}'  → merge into payload
"""

from __future__ import annotations

__all__ = ["ParsedArgs", "ArgParser"]

import json
import shlex
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedArgs:
    """Parsed command arguments."""

    positional: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    raw: str = ""


class ArgParser:
    """Parse command arguments with prefix support.

    Syntax:
        key=value           → payload
        #key=value          → meta
        $key=value          → options
        --flag              → flags[flag] = True
        --key=value         → flags[key] = value
        --json '{...}'      → merge into payload
        --load file.json    → load payload from file

    Examples:
        >>> parser = ArgParser()
        >>> result = parser.parse("math.add a=5 b=3")
        >>> result.positional
        ['math.add']
        >>> result.payload
        {'a': 5, 'b': 3}

        >>> result = parser.parse("user.get id=u1 #tenant=acme $timeout=5000")
        >>> result.meta
        {'tenant': 'acme'}
        >>> result.options
        {'timeout': 5000}
    """

    def parse(self, args: str) -> ParsedArgs:
        """Parse argument string into structured result.

        Args:
            args: Raw argument string from command line

        Returns:
            ParsedArgs with categorized arguments
        """
        result = ParsedArgs(raw=args)

        if not args.strip():
            return result

        try:
            tokens = shlex.split(args)
        except ValueError:
            # Fallback to simple split if shlex fails
            tokens = args.split()

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Handle --json flag
            if token == "--json" and i + 1 < len(tokens):
                i += 1
                try:
                    json_data = json.loads(tokens[i])
                    if isinstance(json_data, dict):
                        result.payload.update(json_data)
                except json.JSONDecodeError:
                    pass
                i += 1
                continue

            # Handle --load flag
            if token == "--load" and i + 1 < len(tokens):
                i += 1
                try:
                    with open(tokens[i]) as f:
                        json_data = json.load(f)
                        if isinstance(json_data, dict):
                            result.payload.update(json_data)
                except (OSError, json.JSONDecodeError):
                    pass
                i += 1
                continue

            # Handle -- flags
            if token.startswith("--"):
                key = token[2:]
                if "=" in key:
                    k, v = key.split("=", 1)
                    result.flags[k] = self._convert_value(v)
                else:
                    result.flags[key] = True
                i += 1
                continue

            # Handle # meta prefix
            if token.startswith("#") and "=" in token:
                key, value = token[1:].split("=", 1)
                result.meta[key] = self._convert_value(value)
                i += 1
                continue

            # Handle $ options prefix
            if token.startswith("$") and "=" in token:
                key, value = token[1:].split("=", 1)
                result.options[key] = self._convert_value(value)
                i += 1
                continue

            # Handle key=value payload
            if "=" in token and not token.startswith("-"):
                key, value = token.split("=", 1)
                # Handle @ prefix (force string)
                if key.startswith("@"):
                    result.payload[key[1:]] = value
                else:
                    result.payload[key] = self._convert_value(value)
                i += 1
                continue

            # Positional argument
            result.positional.append(token)
            i += 1

        return result

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type.

        Args:
            value: String value to convert

        Returns:
            Converted value (int, float, bool, or str)
        """
        # Boolean - cache lower() result to avoid repeated allocations
        lower_value = value.lower()
        if lower_value == "true":
            return True
        if lower_value == "false":
            return False
        if lower_value in ("null", "none"):
            return None

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # JSON object/array
        if value.startswith("{") or value.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # String (default)
        return value
