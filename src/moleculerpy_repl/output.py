"""Output formatting for MoleculerPy REPL.

Moleculer-style formatting with:
- Colored status badges (OK=green, FAILED=red, OFFLINE=red)
- CPU visualization with progress bars
- Beautiful tables with box-drawing characters
- Local node markers (*)

Supports both ANSI colors (default) and rich (if installed).
"""

from __future__ import annotations

__all__ = ["OutputFormatter", "RICH_AVAILABLE"]

import json
from io import StringIO
from collections.abc import Mapping, Sequence
from typing import Any

OutputRecord = Mapping[str, Any]

# Try to import rich for pretty output
try:
    from rich.console import Console
    from rich.json import JSON
    from rich.table import Table
    from rich.style import Style
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ANSI Color codes (fallback when rich is not available)
class Colors:
    """ANSI escape codes for terminal colors."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    # Background
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def _cpu_bar(cpu: float | None, width: int = 20) -> str:
    """Create CPU usage visualization bar.

    Args:
        cpu: CPU percentage (0-100) or None
        width: Width of the bar in characters

    Returns:
        Formatted CPU bar like "[■■■■■.......] 27%"
    """
    if cpu is None:
        return "?"

    filled = round(cpu / (100 / width))
    filled = max(0, min(filled, width))
    empty = width - filled

    bar = "[" + "■" * filled + "." * empty + "]"
    return f"{bar} {cpu:>3.0f}%"


def _cpu_bar_colored(cpu: float | None, width: int = 20) -> str:
    """Create colored CPU usage visualization bar.

    Args:
        cpu: CPU percentage (0-100) or None
        width: Width of the bar in characters

    Returns:
        Formatted CPU bar with ANSI colors
    """
    if cpu is None:
        return f"{Colors.GRAY}?{Colors.RESET}"

    filled = round(cpu / (100 / width))
    filled = max(0, min(filled, width))
    empty = width - filled

    # Color based on usage
    if cpu >= 80:
        color = Colors.RED
    elif cpu >= 50:
        color = Colors.YELLOW
    else:
        color = Colors.GREEN

    bar = f"[{color}{'■' * filled}{Colors.GRAY}{'.' * empty}{Colors.RESET}]"
    return f"{bar} {cpu:>3.0f}%"


class OutputFormatter:
    """Format command output for terminal display.

    Moleculer-style formatting with:
    - Colored status badges (OK, FAILED, OFFLINE, ONLINE)
    - CPU visualization bars
    - Beautiful tables with box-drawing
    - Local node markers (*)

    Uses 'rich' library if available, falls back to ANSI colors.
    """

    def __init__(self, use_colors: bool = True, capture: bool = False) -> None:
        """Initialize formatter.

        Args:
            use_colors: Whether to use colors
            capture: If True, capture output instead of printing (for testing)
        """
        self.use_colors = use_colors
        self.use_rich = use_colors and RICH_AVAILABLE
        self._capture = capture
        self._captured: list[str] = []
        self._console: Console | None = None
        self._string_io: StringIO | None = None

        if self.use_rich and not capture:
            self._console = Console()
        elif self.use_rich and capture:
            self._string_io = StringIO()
            # No colors in capture mode with rich (for testing)
            # Wide width to prevent column truncation in tests
            self._console = Console(
                file=self._string_io, force_terminal=False, no_color=True, width=200
            )

    def get_output(self) -> str:
        """Get captured output (when capture=True)."""
        if self._capture and self._string_io is not None:
            return self._string_io.getvalue()
        return "\n".join(self._captured)

    def print(self, text: str) -> None:
        """Print text to console."""
        if self._capture and not self._console:
            self._captured.append(text)
        elif self._console:
            self._console.print(text)
        else:
            print(text)

    def success(self, message: str) -> None:
        """Print success message."""
        if self._console:
            self._console.print(f"[green]✓[/green] {message}")
        elif self.use_colors:
            print(f"{Colors.GREEN}✓{Colors.RESET} {message}")
        else:
            print(f"✓ {message}")

    def error(self, message: str) -> None:
        """Print error message."""
        if self._console:
            self._console.print(f"[red]✗[/red] {message}")
        elif self.use_colors:
            print(f"{Colors.RED}✗{Colors.RESET} {message}")
        else:
            print(f"✗ Error: {message}")

    def warning(self, message: str) -> None:
        """Print warning message."""
        if self._console:
            self._console.print(f"[yellow]⚠[/yellow] {message}")
        elif self.use_colors:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")
        else:
            print(f"⚠ Warning: {message}")

    def info(self, message: str) -> None:
        """Print info message."""
        if self._console:
            self._console.print(f"[blue]ℹ[/blue] {message}")
        elif self.use_colors:
            print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")
        else:
            print(f"ℹ {message}")

    def json(self, data: Any, indent: int = 2) -> None:
        """Print JSON data."""
        if self._console:
            self._console.print(JSON.from_data(data))
        else:
            print(json.dumps(data, indent=indent, default=str))

    def result(self, data: Any) -> None:
        """Print command result."""
        if data is None:
            return

        if isinstance(data, (dict, list)):
            self.json(data)
        else:
            self.print(f"Result: {data}")

    # ─────────────────────────────────────────────────────────────
    # Status Badges (Moleculer style)
    # ─────────────────────────────────────────────────────────────

    def status_badge(self, status: str) -> str:
        """Create a colored status badge.

        Args:
            status: Status string (OK, FAILED, OFFLINE, ONLINE, LOCAL, etc.)

        Returns:
            Colored status badge string
        """
        status_upper = status.upper()

        if self.use_rich:
            if status_upper in ("OK", "ONLINE"):
                return f"[black on green] {status_upper:^8} [/]"
            elif status_upper in ("FAILED", "OFFLINE", "ERROR"):
                return f"[white on red] {status_upper:^8} [/]"
            elif status_upper in ("TRYING", "PENDING"):
                return f"[black on yellow] {status_upper:^8} [/]"
            elif status_upper == "LOCAL":
                return f"[black on cyan] {status_upper:^8} [/]"
            else:
                return f"[white on bright_black] {status_upper:^8} [/]"
        elif self.use_colors:
            if status_upper in ("OK", "ONLINE"):
                return f"{Colors.BG_GREEN}{Colors.BLACK} {status_upper:^8} {Colors.RESET}"
            elif status_upper in ("FAILED", "OFFLINE", "ERROR"):
                return (
                    f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} {status_upper:^8} {Colors.RESET}"
                )
            elif status_upper in ("TRYING", "PENDING"):
                return f"{Colors.BG_YELLOW}{Colors.BLACK} {status_upper:^8} {Colors.RESET}"
            elif status_upper == "LOCAL":
                return f"{Colors.BG_BLUE}{Colors.WHITE} {status_upper:^8} {Colors.RESET}"
            else:
                return f" {status_upper:^8} "
        else:
            return f" {status_upper:^8} "

    def cpu_bar(self, cpu: float | None, width: int = 20) -> str:
        """Create CPU usage visualization.

        Args:
            cpu: CPU percentage (0-100) or None
            width: Bar width in characters

        Returns:
            Formatted CPU bar
        """
        if self.use_colors and not self.use_rich:
            return _cpu_bar_colored(cpu, width)
        return _cpu_bar(cpu, width)

    def local_marker(self, is_local: bool) -> str:
        """Create local node marker.

        Args:
            is_local: Whether this is the local node

        Returns:
            Marker string " (*)" or ""
        """
        if not is_local:
            return ""

        if self.use_rich:
            return " [dim](*)[/]"
        elif self.use_colors:
            return f" {Colors.GRAY}(*){Colors.RESET}"
        else:
            return " (*)"

    # ─────────────────────────────────────────────────────────────
    # Tables (Moleculer style)
    # ─────────────────────────────────────────────────────────────

    def table(
        self,
        headers: list[str],
        rows: list[list[Any]],
        title: str | None = None,
    ) -> None:
        """Print a table.

        Args:
            headers: Column headers
            rows: Table rows (list of lists)
            title: Optional table title
        """
        self._table_with_widths(headers, rows, None, title)

    def _table_with_widths(
        self,
        headers: list[str],
        rows: list[list[Any]],
        col_widths: list[int] | None = None,
        title: str | None = None,
    ) -> None:
        """Print a table with specified column widths.

        Args:
            headers: Column headers
            rows: Table rows (list of lists)
            col_widths: Optional min widths for each column
            title: Optional table title
        """
        if self.use_rich:
            from rich.text import Text

            table = Table(
                title=title,
                border_style="dim",
                header_style="bold cyan",
                row_styles=["", "dim"],
            )

            for i, header in enumerate(headers):
                min_w = col_widths[i] if col_widths and i < len(col_widths) else None
                table.add_column(header, min_width=min_w)

            for row in rows:
                # Convert cells - keep rich markup strings as-is
                cells = []
                for cell in row:
                    cell_str = str(cell)
                    # Parse rich markup in strings
                    cells.append(
                        Text.from_markup(cell_str)
                        if "[" in cell_str and "]" in cell_str
                        else cell_str
                    )
                table.add_row(*cells)

            if self._console is not None:
                self._console.print(table)
        else:
            self._print_ansi_table(headers, rows, title, col_widths)

    @staticmethod
    def _as_str(value: Any, default: str = "") -> str:
        """Safely convert an arbitrary value to string for display."""
        if value is None:
            return default
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _as_bool(value: Any, default: bool = False) -> bool:
        """Safely normalize a value to bool."""
        if isinstance(value, bool):
            return value
        return default

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        """Normalize a potentially iterable value to list."""
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return []

    @staticmethod
    def _as_mapping(value: Any) -> Mapping[str, Any]:
        """Normalize a value to mapping for nested lookups."""
        if isinstance(value, Mapping):
            return value
        return {}

    @staticmethod
    def _as_float(value: Any) -> float | None:
        """Normalize a numeric value for CPU formatting."""
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def _output(self, text: str) -> None:
        """Output text (print or capture)."""
        if self._capture:
            self._captured.append(text)
        else:
            print(text)

    def _print_ansi_table(
        self,
        headers: list[str],
        rows: list[list[Any]],
        title: str | None = None,
        col_widths: list[int] | None = None,
    ) -> None:
        """Print table with ANSI box-drawing characters."""
        if title:
            if self.use_colors:
                self._output(f"\n{Colors.CYAN}{Colors.BOLD}{title}{Colors.RESET}")
            else:
                self._output(f"\n{title}")

        # Calculate column widths (handle ANSI escape sequences)
        def visible_len(s: str) -> int:
            """Get visible length ignoring ANSI codes."""
            import re

            return len(re.sub(r"\033\[[0-9;]*m", "", str(s)))

        str_rows = [[str(cell) for cell in row] for row in rows]

        # Start with min widths from col_widths or header lengths
        widths = []
        for i, h in enumerate(headers):
            min_w = col_widths[i] if col_widths and i < len(col_widths) else 0
            widths.append(max(visible_len(h), min_w))

        # Expand to fit content
        for row in str_rows:
            for i, cell in enumerate(row):
                w = visible_len(cell)
                if w > widths[i]:
                    widths[i] = w

        # Box-drawing characters
        TL, TR, BL, BR = "┌", "┐", "└", "┘"
        H, V = "─", "│"
        TJ, BJ, LJ, RJ = "┬", "┴", "├", "┤"
        X = "┼"

        def gray(s: str) -> str:
            return f"{Colors.GRAY}{s}{Colors.RESET}" if self.use_colors else s

        def bold(s: str) -> str:
            return f"{Colors.BOLD}{s}{Colors.RESET}" if self.use_colors else s

        def pad(s: str, width: int) -> str:
            """Pad string considering ANSI codes."""
            vis_len = visible_len(s)
            return s + " " * (width - vis_len)

        # Top border
        top = TL + TJ.join(H * (w + 2) for w in widths) + TR
        self._output(gray(top))

        # Header
        header_row = V + V.join(f" {bold(pad(h, widths[i]))} " for i, h in enumerate(headers)) + V
        self._output(gray(V) + header_row[1:-1] + gray(V))

        # Header separator
        sep = LJ + X.join(H * (w + 2) for w in widths) + RJ
        self._output(gray(sep))

        # Data rows
        for row in str_rows:
            row_str = V + V.join(f" {pad(cell, widths[i])} " for i, cell in enumerate(row)) + V
            self._output(gray(V) + row_str[1:-1] + gray(V))

        # Bottom border
        bottom = BL + BJ.join(H * (w + 2) for w in widths) + BR
        self._output(gray(bottom))
        self._output("")

    def nodes_table(
        self,
        nodes: Sequence[OutputRecord],
        show_details: bool = False,
        local_node_id: str | None = None,
    ) -> None:
        """Print nodes table in Moleculer style.

        Args:
            nodes: List of node dictionaries
            show_details: Show detailed view with CPU, IP, etc.
            local_node_id: ID of the local node for marking
        """
        if show_details:
            headers = ["Node ID", "Services", "Version", "IP", "State", "CPU"]
            col_widths = [30, 8, 10, 15, 10, 28]  # Min widths
            rows = []

            for node in sorted(nodes, key=lambda item: self._as_str(item.get("id"))):
                node_id = self._as_str(node.get("id"), "unknown")
                is_local = node_id == local_node_id or self._as_bool(node.get("local"))

                display_id = node_id + self.local_marker(is_local)
                services = str(node.get("serviceCount", len(self._as_list(node.get("services")))))
                version = self._as_str(self._as_mapping(node.get("client")).get("version"), "-")

                # IP address
                ip_list = self._as_list(node.get("ipList"))
                if ip_list:
                    ip = self._as_str(ip_list[0], "-")
                    if len(ip_list) > 1:
                        ip += f" (+{len(ip_list) - 1})"
                else:
                    ip = self._as_str(node.get("hostname"), "-") or "-"

                # State
                available = self._as_bool(node.get("available"), True)
                if is_local:
                    state = self.status_badge("LOCAL")
                elif available:
                    state = self.status_badge("ONLINE")
                else:
                    state = self.status_badge("OFFLINE")

                # CPU
                cpu = self._as_float(node.get("cpu"))
                cpu_str = self.cpu_bar(cpu)

                rows.append([display_id, services, version, ip, state, cpu_str])

            self._table_with_widths(headers, rows, col_widths, "Nodes")
        else:
            headers = ["Node ID", "Services", "State", "CPU"]
            col_widths = [30, 8, 10, 28]  # Min widths
            rows = []

            for node in sorted(nodes, key=lambda item: self._as_str(item.get("id"))):
                node_id = self._as_str(node.get("id"), "unknown")
                is_local = node_id == local_node_id or self._as_bool(node.get("local"))

                display_id = node_id + self.local_marker(is_local)
                services = str(node.get("serviceCount", len(self._as_list(node.get("services")))))

                available = self._as_bool(node.get("available"), True)
                if is_local:
                    state = self.status_badge("LOCAL")
                elif available:
                    state = self.status_badge("ONLINE")
                else:
                    state = self.status_badge("OFFLINE")

                cpu = self._as_float(node.get("cpu"))
                cpu_str = self.cpu_bar(cpu)

                rows.append([display_id, services, state, cpu_str])

            self._table_with_widths(headers, rows, col_widths, "Nodes")

    def services_table(
        self,
        services: Sequence[OutputRecord],
        local_node_id: str | None = None,
    ) -> None:
        """Print services table in Moleculer style.

        Args:
            services: List of service dictionaries
            local_node_id: ID of the local node for marking
        """
        headers = ["Service", "Version", "State", "Actions", "Events", "Nodes"]
        col_widths = [25, 8, 10, 7, 6, 6]  # Min widths
        rows = []

        for svc in sorted(services, key=lambda item: self._as_str(item.get("name"))):
            name = self._as_str(svc.get("name"), "unknown")
            version = self._as_str(svc.get("version"), "-")

            # State
            available = self._as_bool(svc.get("available"), True)
            state = self.status_badge("OK" if available else "FAILED")

            # Counts - handle non-iterable mocks
            actions_val = svc.get("actions", {})
            events_val = svc.get("events", {})
            try:
                actions = str(len(actions_val))
            except TypeError:
                actions = "-"
            try:
                events = str(len(events_val))
            except TypeError:
                events = "-"

            # Nodes
            node_ids = self._as_list(svc.get("nodeIds"))
            has_local = local_node_id in node_ids if local_node_id else False
            nodes_str = str(len(node_ids))
            if has_local:
                nodes_str = f"(*) {nodes_str}"

            rows.append([name, version, state, actions, events, nodes_str])

        self._table_with_widths(headers, rows, col_widths, "Services")

    def actions_table(
        self,
        actions: Sequence[OutputRecord],
        local_node_id: str | None = None,
    ) -> None:
        """Print actions table in Moleculer style.

        Args:
            actions: List of action dictionaries
            local_node_id: ID of the local node for marking
        """
        headers = ["Action", "Nodes", "State", "Cached", "Params"]
        col_widths = [35, 6, 10, 6, 25]  # Min widths
        rows = []

        for action in sorted(actions, key=lambda item: self._as_str(item.get("name"))):
            name = self._as_str(action.get("name"), "unknown")

            # Nodes
            node_ids = self._as_list(action.get("nodeIds"))
            has_local = local_node_id in node_ids if local_node_id else False
            nodes_str = str(len(node_ids))
            if has_local:
                nodes_str = f"(*) {nodes_str}"

            # State (based on availability)
            available = self._as_bool(action.get("available"), True)
            state = self.status_badge("OK" if available else "FAILED")

            # Cached - use rich markup when rich is available
            cache = self._as_bool(action.get("cache"))
            if self.use_rich:
                cached = "[green]Yes[/]" if cache else "[dim]No[/]"
            elif self.use_colors:
                cached = (
                    f"{Colors.GREEN}Yes{Colors.RESET}"
                    if cache
                    else f"{Colors.GRAY}No{Colors.RESET}"
                )
            else:
                cached = "Yes" if cache else "No"

            # Params - limit to 25 chars width
            params = action.get("params", {})
            if isinstance(params, Mapping):
                param_names = list(params.keys())[:5]  # Limit to 5
                params_str = ", ".join(param_names)
                if len(params) > 5:
                    params_str += f" (+{len(params) - 5})"
                # Truncate if too long
                if len(params_str) > 25:
                    params_str = params_str[:22] + "..."
            else:
                params_str = "-"

            rows.append([name, nodes_str, state, cached, params_str])

        self._table_with_widths(headers, rows, col_widths, "Actions")

    def events_table(
        self,
        events: Sequence[OutputRecord],
        local_node_id: str | None = None,
    ) -> None:
        """Print events table in Moleculer style.

        Args:
            events: List of event dictionaries
            local_node_id: ID of the local node for marking
        """
        headers = ["Event", "Group", "State", "Nodes"]
        col_widths = [30, 15, 10, 6]  # Min widths
        rows = []

        for event in sorted(events, key=lambda item: self._as_str(item.get("name"))):
            name = self._as_str(event.get("name"), "unknown")
            group = self._as_str(event.get("group"), "-")

            # Nodes
            node_ids = self._as_list(event.get("nodeIds"))
            has_local = local_node_id in node_ids if local_node_id else False
            nodes_str = str(len(node_ids))
            if has_local:
                nodes_str = f"(*) {nodes_str}"

            # State
            available = self._as_bool(event.get("available"), True)
            state = self.status_badge("OK" if available else "FAILED")

            rows.append([name, group, state, nodes_str])

        self._table_with_widths(headers, rows, col_widths, "Events")

    # ─────────────────────────────────────────────────────────────
    # Info / Banner
    # ─────────────────────────────────────────────────────────────

    def section_header(self, title: str) -> None:
        """Print a section header (Moleculer style).

        Args:
            title: Section title
        """
        line = "=" * (len(title) + 4)
        if self.use_rich:
            if self._console is not None:
                self._console.print(f"\n[bold yellow]{line}[/]")
                self._console.print(f"[bold yellow]  {title}  [/]")
                self._console.print(f"[bold yellow]{line}[/]\n")
        elif self.use_colors:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}{line}{Colors.RESET}")
            print(f"{Colors.YELLOW}{Colors.BOLD}  {title}  {Colors.RESET}")
            print(f"{Colors.YELLOW}{Colors.BOLD}{line}{Colors.RESET}\n")
        else:
            print(f"\n{line}")
            print(f"  {title}  ")
            print(f"{line}\n")

    def info_line(self, label: str, value: Any, label_width: int = 20) -> None:
        """Print an info line (label: value).

        Args:
            label: Label text
            value: Value to display
            label_width: Width for label column
        """
        # Color value based on type
        if self.use_rich:
            if isinstance(value, bool):
                val_str = f"[magenta]{value}[/]"
            elif isinstance(value, (int, float)):
                val_str = f"[cyan]{value}[/]"
            elif isinstance(value, str):
                val_str = f'[green]"{value}"[/]'
            else:
                val_str = str(value)
            if self._console is not None:
                self._console.print(f"    {label:<{label_width}} : {val_str}")
        elif self.use_colors:
            if isinstance(value, bool):
                val_str = f"{Colors.MAGENTA}{value}{Colors.RESET}"
            elif isinstance(value, (int, float)):
                val_str = f"{Colors.CYAN}{value}{Colors.RESET}"
            elif isinstance(value, str):
                val_str = f'{Colors.GREEN}"{value}"{Colors.RESET}'
            else:
                val_str = str(value)
            print(f"    {label:<{label_width}} : {val_str}")
        else:
            print(f"    {label:<{label_width}} : {value}")

    def banner(self, text: str) -> None:
        """Print a banner/header."""
        if self._console:
            self._console.print(f"[bold cyan]{text}[/bold cyan]")
        elif self.use_colors:
            print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
            print(f"  {Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")
        else:
            print(f"\n{'=' * 60}")
            print(f"  {text}")
            print(f"{'=' * 60}\n")

    def divider(self) -> None:
        """Print a divider line."""
        if self._console:
            self._console.print("[dim]" + "─" * 60 + "[/dim]")
        elif self.use_colors:
            print(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        else:
            print("-" * 60)

    def clear(self) -> None:
        """Clear the terminal screen."""
        if self._console:
            self._console.clear()
        else:
            print("\033[2J\033[H", end="")
