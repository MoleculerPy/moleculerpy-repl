"""Tests for output formatter."""

from __future__ import annotations

import io
import sys
import pytest
from moleculerpy_repl.output import OutputFormatter, RICH_AVAILABLE


class TestOutputFormatterNoColors:
    """Tests for OutputFormatter without rich colors."""

    def test_print_text(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test printing plain text."""
        output_formatter.print("Hello, World!")
        captured = capsys.readouterr()
        assert "Hello, World!" in captured.out

    def test_success_message(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test success message."""
        output_formatter.success("Operation completed")
        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "Operation completed" in captured.out

    def test_error_message(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test error message."""
        output_formatter.error("Something failed")
        captured = capsys.readouterr()
        assert "✗" in captured.out
        assert "Something failed" in captured.out

    def test_warning_message(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test warning message."""
        output_formatter.warning("Be careful")
        captured = capsys.readouterr()
        assert "⚠" in captured.out
        assert "Be careful" in captured.out

    def test_info_message(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test info message."""
        output_formatter.info("Just FYI")
        captured = capsys.readouterr()
        assert "ℹ" in captured.out
        assert "Just FYI" in captured.out

    def test_json_dict(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test JSON dict output."""
        data = {"id": 1, "name": "Test"}
        output_formatter.json(data)
        captured = capsys.readouterr()
        assert '"id": 1' in captured.out or '"id":1' in captured.out
        assert '"name": "Test"' in captured.out or '"name":"Test"' in captured.out

    def test_json_list(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test JSON list output."""
        data = [1, 2, 3]
        output_formatter.json(data)
        captured = capsys.readouterr()
        assert "1" in captured.out
        assert "2" in captured.out
        assert "3" in captured.out

    def test_result_none(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test result with None data."""
        output_formatter.result(None)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_result_dict(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test result with dict data (outputs JSON)."""
        output_formatter.result({"key": "value"})
        captured = capsys.readouterr()
        assert "key" in captured.out

    def test_result_scalar(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test result with scalar data."""
        output_formatter.result(42)
        captured = capsys.readouterr()
        assert "Result:" in captured.out
        assert "42" in captured.out


class TestOutputFormatterTable:
    """Tests for table output."""

    def test_table_basic(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test basic table output."""
        headers = ["Name", "Value"]
        rows = [["foo", 1], ["bar", 2]]
        output_formatter.table(headers, rows)
        captured = capsys.readouterr()

        assert "Name" in captured.out
        assert "Value" in captured.out
        assert "foo" in captured.out
        assert "bar" in captured.out

    def test_table_with_title(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test table with title."""
        headers = ["ID", "Name"]
        rows = [["1", "Alice"]]
        output_formatter.table(headers, rows, title="Users")
        captured = capsys.readouterr()

        assert "Users" in captured.out

    def test_table_column_alignment(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test table columns are properly aligned."""
        headers = ["Short", "LongColumnName"]
        rows = [["a", "b"], ["longer value", "c"]]
        output_formatter.table(headers, rows)
        captured = capsys.readouterr()

        # Check headers and separator are present
        assert "Short" in captured.out
        assert "LongColumnName" in captured.out
        assert "─" in captured.out

    def test_table_empty_rows(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test table with empty rows."""
        headers = ["Col1", "Col2"]
        rows = []
        output_formatter.table(headers, rows)
        captured = capsys.readouterr()

        # Should still print headers
        assert "Col1" in captured.out
        assert "Col2" in captured.out


class TestOutputFormatterDecorative:
    """Tests for decorative output methods."""

    def test_banner(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test banner output."""
        output_formatter.banner("Welcome to REPL")
        captured = capsys.readouterr()

        assert "Welcome to REPL" in captured.out
        assert "=" in captured.out  # Separator line

    def test_divider(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test divider output."""
        output_formatter.divider()
        captured = capsys.readouterr()

        assert "-" in captured.out

    def test_clear(self, output_formatter: OutputFormatter, capsys) -> None:
        """Test clear screen."""
        # Just verify it doesn't raise
        output_formatter.clear()


class TestOutputFormatterWithColors:
    """Tests for OutputFormatter with colors enabled."""

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_available(self) -> None:
        """Test rich is available."""
        formatter = OutputFormatter(use_colors=True)
        assert formatter.use_colors is True
        assert formatter._console is not None

    def test_colors_disabled(self) -> None:
        """Test colors can be disabled."""
        formatter = OutputFormatter(use_colors=False)
        assert formatter.use_colors is False
        assert formatter._console is None

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_json_output(self, capsys) -> None:
        """Test JSON output with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.json({"test": "value"})
        # Just verify no errors

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
    def test_rich_table_output(self, capsys) -> None:
        """Test table output with rich."""
        formatter = OutputFormatter(use_colors=True)
        formatter.table(["A", "B"], [["1", "2"]])
        # Just verify no errors


class TestRichAvailableFlag:
    """Tests for RICH_AVAILABLE flag."""

    def test_rich_available_is_bool(self) -> None:
        """Test RICH_AVAILABLE is a boolean."""
        assert isinstance(RICH_AVAILABLE, bool)

    def test_formatter_respects_rich_availability(self) -> None:
        """Test formatter respects rich availability."""
        formatter = OutputFormatter(use_colors=True)

        # use_colors=True is respected (uses ANSI codes if rich unavailable)
        assert formatter.use_colors is True

        # use_rich depends on rich availability
        if RICH_AVAILABLE:
            assert formatter.use_rich is True
        else:
            assert formatter.use_rich is False
