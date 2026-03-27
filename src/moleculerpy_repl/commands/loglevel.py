"""LogLevel command — Get or set broker log level."""

from __future__ import annotations

from typing import Any

from ..logger import LoggerFactory
from ..parser import ParsedArgs
from .base import BaseCommand, CommandResult

# Valid log levels
VALID_LEVELS = ["trace", "debug", "info", "warn", "error", "fatal"]


class LogLevelCommand(BaseCommand):
    """Get or set the broker log level.

    Without arguments, shows the current log level.
    With a level argument, sets the new log level.

    Usage:
        loglevel           # Show current level
        loglevel debug     # Set to debug
        loglevel info      # Set to info

    Levels (in order of verbosity):
        trace  - Most verbose, all messages
        debug  - Debug messages and above
        info   - Info messages and above (default)
        warn   - Warnings and errors only
        error  - Errors only
        fatal  - Fatal errors only
    """

    name = "loglevel"
    description = "Get or set log level"
    usage = "loglevel [level]"
    aliases = ["log", "ll"]

    async def execute(self, broker: Any, args: ParsedArgs) -> CommandResult:
        """Execute the loglevel command."""
        try:
            # Get logger factory from broker
            logger_factory = self._get_logger_factory(broker)

            # No arguments - show current level
            if not args.positional:
                current = self._get_current_level(broker, logger_factory)
                return CommandResult(
                    success=True,
                    output=self._format_level_info(current),
                )

            # Set new level
            new_level = args.positional[0].lower()

            if new_level not in VALID_LEVELS:
                return CommandResult(
                    success=False,
                    error=f"Invalid log level: '{new_level}'. Valid levels: {', '.join(VALID_LEVELS)}",
                )

            # Update logger factory
            if logger_factory:
                logger_factory.set_level(new_level)

            # Also update broker's logger if present
            if hasattr(broker, "logger") and broker.logger:
                if hasattr(broker.logger, "set_level"):
                    broker.logger.set_level(new_level)
                elif hasattr(broker.logger, "setLevel"):
                    # Python logging compatibility
                    import logging

                    level_map = {
                        "trace": 5,
                        "debug": logging.DEBUG,
                        "info": logging.INFO,
                        "warn": logging.WARNING,
                        "error": logging.ERROR,
                        "fatal": logging.CRITICAL,
                    }
                    broker.logger.setLevel(level_map.get(new_level, logging.INFO))

            return CommandResult(
                success=True,
                output=f"Log level changed to: {new_level.upper()}",
            )

        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def _get_logger_factory(self, broker: Any) -> LoggerFactory | None:
        """Get logger factory from broker."""
        for attr_name in ("logger_factory", "_logger_factory", "loggerFactory"):
            candidate = getattr(broker, attr_name, None)
            if isinstance(candidate, LoggerFactory):
                return candidate
        return None

    def _get_current_level(self, broker: Any, factory: LoggerFactory | None) -> str:
        """Get current log level."""
        # From factory
        if factory:
            return factory.level.name.lower()

        # From broker logger
        if hasattr(broker, "logger") and broker.logger:
            if hasattr(broker.logger, "level"):
                level = broker.logger.level
                if hasattr(level, "name"):
                    level_name = level.name
                    if isinstance(level_name, str):
                        return level_name.lower()
                return str(level).lower()

        # From settings
        if hasattr(broker, "settings"):
            settings = broker.settings
            log_level = getattr(settings, "log_level", None)
            if isinstance(log_level, str):
                return log_level
            legacy_log_level = getattr(settings, "logLevel", None)
            if isinstance(legacy_log_level, str):
                return legacy_log_level

        return "info"

    def _format_level_info(self, current: str) -> str:
        """Format level info with visual indicator."""
        lines = [
            f"Current log level: {current.upper()}",
            "",
            "Available levels:",
        ]

        for level in VALID_LEVELS:
            marker = "→ " if level == current else "  "
            lines.append(f"  {marker}{level.upper()}")

        return "\n".join(lines)

    def get_completions(self, broker: Any, text: str, line: str) -> list[str]:
        """Get completions for log levels."""
        return [level for level in VALID_LEVELS if level.startswith(text.lower())]
