"""Beautiful console logging for MoleculerPy Runner.

Inspired by Moleculer.js logging system with:
- Colorful log levels (INFO=green, DEBUG=magenta, WARN=yellow, ERROR=red)
- Module-based colors (deterministic based on name hash)
- Multiple formats (full, short, simple)
- Auto-padding for aligned output
- Unicode symbols (✔ ✗ → ⚡)
- Duration humanization (125ms, 5s, 1h)
- REPL-aware output (doesn't break readline prompt)
"""

from __future__ import annotations

import sys
import time
import readline
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TextIO, Callable

__all__ = [
    "Logger",
    "LoggerConfig",
    "LoggerFactory",
    "LogLevel",
    "LogFormat",
    "REPLAwareStream",
    "humanize_duration",
    "get_module_color",
]


class LogLevel(Enum):
    """Log levels with priorities."""

    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4
    FATAL = 5


class LogFormat(Enum):
    """Log output formats."""

    FULL = "full"  # [2024-01-29T10:15:22.450Z] INFO  node/BROKER: Message
    SHORT = "short"  # [10:15:22.450Z] INFO  BROKER: Message
    SIMPLE = "simple"  # INFO  - Message


# ANSI color codes
class Colors:
    """ANSI escape codes for colors."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Background
    BG_RED = "\033[41m"
    BG_WHITE = "\033[47m"


# Log level colors (like Moleculer)
LEVEL_COLORS = {
    LogLevel.TRACE: Colors.GRAY,
    LogLevel.DEBUG: Colors.MAGENTA,
    LogLevel.INFO: Colors.GREEN,
    LogLevel.WARN: Colors.YELLOW,
    LogLevel.ERROR: Colors.RED,
    LogLevel.FATAL: Colors.BG_RED + Colors.WHITE,
}

# Module colors for deterministic coloring
MODULE_COLORS = [
    Colors.YELLOW,
    Colors.BOLD + Colors.YELLOW,
    Colors.CYAN,
    Colors.BOLD + Colors.CYAN,
    Colors.GREEN,
    Colors.BOLD + Colors.GREEN,
    Colors.MAGENTA,
    Colors.BOLD + Colors.MAGENTA,
    Colors.BLUE,
    Colors.BOLD + Colors.BLUE,
]

# Symbols
SYMBOLS = {
    "success": "✔",
    "error": "✗",
    "warning": "⚠",
    "arrow": "→",
    "bullet": "•",
    "lightning": "⚡",
    "rocket": "🚀",
    "check": "✓",
}


class REPLAwareStream:
    """Stream wrapper that handles output while readline is active.

    When readline is active (user is typing), this stream:
    1. Clears the current line
    2. Prints the message
    3. Redraws the prompt and any partial input

    This allows background logs to appear without breaking the REPL.
    """

    # ANSI escape codes
    CLEAR_LINE = "\033[2K"  # Clear entire line
    CURSOR_START = "\r"  # Move cursor to start of line

    # Global state
    _prompt: str = ""
    _lock = threading.Lock()
    _enabled: bool = False

    @classmethod
    def set_prompt(cls, prompt: str) -> None:
        """Set the current REPL prompt."""
        cls._prompt = prompt

    @classmethod
    def enable(cls) -> None:
        """Enable REPL-aware output."""
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable REPL-aware output."""
        cls._enabled = False

    @classmethod
    def write(cls, stream: TextIO, message: str) -> None:
        """Write message to stream, handling readline if active."""
        with cls._lock:
            if cls._enabled:
                # Get current line buffer (what user has typed)
                try:
                    line_buffer = readline.get_line_buffer()
                except Exception:
                    line_buffer = ""

                # Clear line, print message, restore prompt and buffer
                stream.write(cls.CURSOR_START + cls.CLEAR_LINE)
                stream.write(message + "\n")

                # Redraw prompt and current input
                if cls._prompt:
                    stream.write(cls._prompt + line_buffer)

                stream.flush()

                # Force readline to redisplay (if in readline mode)
                try:
                    readline.redisplay()
                except Exception:
                    pass
            else:
                # Normal output
                stream.write(message + "\n")
                stream.flush()


def get_module_color(module_name: str) -> str:
    """Get deterministic color for module name based on hash.

    This ensures the same module always gets the same color,
    making logs easier to scan visually.
    """
    # Calculate hash of module name
    hash_val = 0
    for char in module_name:
        hash_val = ((hash_val << 5) - hash_val + ord(char)) & 0xFFFFFFFF

    return MODULE_COLORS[hash_val % len(MODULE_COLORS)]


def humanize_duration(milliseconds: float | None) -> str:
    """Convert milliseconds to human-readable format.

    Examples:
        humanize_duration(125) -> "125ms"
        humanize_duration(5000) -> "5s"
        humanize_duration(65000) -> "1m"
        humanize_duration(3600000) -> "1h"
    """
    if milliseconds is None:
        return "?"

    if milliseconds < 0:
        return "0ms"

    units = [
        (3600000, "h"),  # hours
        (60000, "m"),  # minutes
        (1000, "s"),  # seconds
        (1, "ms"),  # milliseconds
        (0.001, "μs"),  # microseconds
    ]

    for divisor, unit in units:
        if milliseconds >= divisor:
            value = milliseconds / divisor
            if value >= 10:
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"

    return "now"


@dataclass
class LoggerConfig:
    """Logger configuration."""

    # Log level threshold
    level: LogLevel = LogLevel.INFO

    # Output format
    format: LogFormat = LogFormat.FULL

    # Enable colors
    colors: bool = True

    # Enable module colors
    module_colors: bool = True

    # Auto-pad module names for alignment
    auto_padding: bool = True

    # Node ID to include in logs
    node_id: str = ""

    # Output stream
    stream: TextIO = field(default_factory=lambda: sys.stdout)


class Logger:
    """Beautiful console logger for MoleculerPy.

    Usage:
        logger = Logger("BROKER", config)
        logger.info("Starting...")
        logger.debug("Loading service", service="math")
        logger.info(f"{SYMBOLS['success']} Started successfully in {humanize_duration(150)}")

    Output (full format):
        [2024-01-29T10:15:22.450Z] INFO  my-node/BROKER: Starting...
        [2024-01-29T10:15:22.451Z] DEBUG my-node/BROKER: Loading service service=math
        [2024-01-29T10:15:22.600Z] INFO  my-node/BROKER: ✔ Started successfully in 150ms
    """

    # Track max module length for auto-padding
    _max_module_length: int = 0

    def __init__(self, module: str, config: LoggerConfig | None = None):
        self.module = module.upper()
        self.config = config or LoggerConfig()

        # Update max length for padding
        Logger._max_module_length = max(Logger._max_module_length, len(self.module))

        # Pre-compute colored strings
        self._setup_colors()

    def _setup_colors(self) -> None:
        """Pre-compute colored level and module strings."""
        if not self.config.colors:
            self._level_strings = {level: level.name.ljust(5) for level in LogLevel}
            self._module_color = ""
            self._reset = ""
            self._gray = ""
            return

        self._reset = Colors.RESET
        self._gray = Colors.GRAY

        # Level strings with colors
        self._level_strings = {
            level: f"{LEVEL_COLORS[level]}{level.name.ljust(5)}{Colors.RESET}" for level in LogLevel
        }

        # Module color
        if self.config.module_colors:
            self._module_color = get_module_color(self.module)
        else:
            self._module_color = ""

    def _get_timestamp(self) -> str:
        """Get formatted timestamp."""
        now = datetime.utcnow()

        if self.config.format == LogFormat.FULL:
            return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
        elif self.config.format == LogFormat.SHORT:
            return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
        else:
            return ""

    def _get_prefix(self) -> str:
        """Get module prefix with optional node ID."""
        module = self.module

        # Apply padding
        if self.config.auto_padding:
            padding = " " * (Logger._max_module_length - len(module))
        else:
            padding = ""

        # Color the module name
        if self._module_color:
            colored_module = f"{self._module_color}{module}{self._reset}"
        else:
            colored_module = module

        # Add node ID if present
        if self.config.node_id and self.config.format == LogFormat.FULL:
            return f"{self.config.node_id}/{colored_module}{padding}"

        return f"{colored_module}{padding}"

    def _format_message(self, level: LogLevel, message: str, **kwargs: Any) -> str:
        """Format a log message."""
        # Add key-value pairs
        if kwargs:
            pairs = " ".join(f"{k}={v}" for k, v in kwargs.items())
            message = f"{message} {pairs}"

        timestamp = self._get_timestamp()
        level_str = self._level_strings[level]
        prefix = self._get_prefix()

        if self.config.format == LogFormat.SIMPLE:
            return f"{level_str} - {message}"
        elif self.config.format == LogFormat.SHORT:
            return f"{self._gray}[{timestamp}]{self._reset} {level_str} {prefix}{self._gray}:{self._reset} {message}"
        else:  # FULL
            return f"{self._gray}[{timestamp}]{self._reset} {level_str} {prefix}{self._gray}:{self._reset} {message}"

    def _log(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        """Internal log method."""
        if level.value < self.config.level.value:
            return

        formatted = self._format_message(level, message, **kwargs)

        # Route to stderr for errors, stdout for others (like Moleculer.js)
        if level in (LogLevel.FATAL, LogLevel.ERROR, LogLevel.WARN):
            stream = sys.stderr
        else:
            stream = self.config.stream

        # Use REPL-aware stream for proper handling during readline
        REPLAwareStream.write(stream, formatted)

    def trace(self, message: str, **kwargs: Any) -> None:
        """Log trace message."""
        self._log(LogLevel.TRACE, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)

    def warn(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(LogLevel.WARN, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, **kwargs)

    def fatal(self, message: str, **kwargs: Any) -> None:
        """Log fatal message."""
        self._log(LogLevel.FATAL, message, **kwargs)

    # Convenience methods with symbols
    def success(self, message: str, **kwargs: Any) -> None:
        """Log success message with checkmark."""
        self.info(f"{SYMBOLS['success']} {message}", **kwargs)

    def failure(self, message: str, **kwargs: Any) -> None:
        """Log failure message with X mark."""
        self.error(f"{SYMBOLS['error']} {message}", **kwargs)


class LoggerFactory:
    """Factory for creating loggers with shared config.

    Usage:
        factory = LoggerFactory(node_id="my-node", level=LogLevel.DEBUG)
        broker_log = factory.get_logger("BROKER")
        transit_log = factory.get_logger("TRANSIT")
        registry_log = factory.get_logger("REGISTRY")
    """

    def __init__(
        self,
        node_id: str = "",
        level: LogLevel = LogLevel.INFO,
        format: LogFormat = LogFormat.FULL,
        colors: bool = True,
    ):
        self.config = LoggerConfig(
            node_id=node_id,
            level=level,
            format=format,
            colors=colors,
        )
        self._loggers: dict[str, Logger] = {}

    def get_logger(self, module: str) -> Logger:
        """Get or create a logger for a module."""
        if module not in self._loggers:
            self._loggers[module] = Logger(module, self.config)
        return self._loggers[module]

    def set_level(self, level: LogLevel | str) -> None:
        """Change log level for all loggers dynamically.

        Args:
            level: LogLevel enum or string like "debug", "info", "warn"
        """
        if isinstance(level, str):
            level = LogLevel[level.upper()]

        self.config.level = level
        # Update all existing loggers
        for logger in self._loggers.values():
            logger.config.level = level

    @property
    def level(self) -> LogLevel:
        """Get current log level."""
        return self.config.level


def print_banner(version: str = "0.1.0", node_id: str = "") -> None:
    """Print startup banner.

    Output:
        ╔═══════════════════════════════════════╗
        ║   🚀 MoleculerPy Runner v0.1.0          ║
        ║   Node ID: my-node                    ║
        ╚═══════════════════════════════════════╝
    """
    width = 41

    print(f"{Colors.CYAN}╔{'═' * (width - 2)}╗{Colors.RESET}")
    print(
        f"{Colors.CYAN}║{Colors.RESET}   {SYMBOLS['rocket']} {Colors.BOLD}MoleculerPy Runner{Colors.RESET} v{version}".ljust(
            width + 15
        )
        + f"{Colors.CYAN}║{Colors.RESET}"
    )
    if node_id:
        print(
            f"{Colors.CYAN}║{Colors.RESET}   Node ID: {Colors.YELLOW}{node_id}{Colors.RESET}".ljust(
                width + 20
            )
            + f"{Colors.CYAN}║{Colors.RESET}"
        )
    print(f"{Colors.CYAN}╚{'═' * (width - 2)}╝{Colors.RESET}")
    print()


# Demo
if __name__ == "__main__":
    # Demo the logging system
    print_banner("0.1.0", "demo-node-001")

    factory = LoggerFactory(node_id="demo-node", level=LogLevel.DEBUG)

    broker = factory.get_logger("BROKER")
    transit = factory.get_logger("TRANSIT")
    registry = factory.get_logger("REGISTRY")

    # Simulate startup sequence
    start = time.time()

    broker.info("MoleculerPy v0.1.0 is starting...")
    broker.info("Namespace: production")
    broker.info("Node ID: demo-node-001")

    broker.debug("Initializing components...")
    broker.info("Serializer: JSON")
    broker.info("Validator: Typia")
    broker.info("Transporter: Redis")

    transit.info("Connecting to the transporter...")
    time.sleep(0.1)
    transit.debug("TCP connection established")
    transit.info("Connected successfully")

    registry.debug("Loading service: math")
    registry.debug("Loading service: user")
    registry.debug("Loading service: api")

    broker.info("Registered 3 middleware(s).")

    duration_ms = (time.time() - start) * 1000
    broker.success(
        f"ServiceBroker with 3 service(s) started successfully in {humanize_duration(duration_ms)}"
    )

    print()
    broker.warn("This is a warning message")
    broker.error("This is an error message")
