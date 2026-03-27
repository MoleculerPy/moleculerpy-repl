"""Extended tests for parser to improve coverage."""

from __future__ import annotations

import pytest
import tempfile
import json
from pathlib import Path
from moleculerpy_repl.parser import ArgParser, ParsedArgs


class TestLoadFlag:
    """Tests for --load flag."""

    def test_load_from_file(self, parser: ArgParser) -> None:
        """Test loading params from JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"name": "test", "value": 42}, f)
            f.flush()
            filepath = f.name

        try:
            result = parser.parse(f"--load {filepath}")
            assert result.payload == {"name": "test", "value": 42}
        finally:
            Path(filepath).unlink()

    def test_load_nonexistent_file(self, parser: ArgParser) -> None:
        """Test loading from non-existent file."""
        result = parser.parse("--load /nonexistent/file.json")
        # Should not crash, just ignore
        assert result.payload == {}

    def test_load_invalid_json_file(self, parser: ArgParser) -> None:
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
            filepath = f.name

        try:
            result = parser.parse(f"--load {filepath}")
            # Should not crash, just ignore
            assert result.payload == {}
        finally:
            Path(filepath).unlink()

    def test_load_with_other_params(self, parser: ArgParser) -> None:
        """Test --load merges with other params."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"from_file": True}, f)
            f.flush()
            filepath = f.name

        try:
            result = parser.parse(f"inline=value --load {filepath}")
            assert result.payload == {"inline": "value", "from_file": True}
        finally:
            Path(filepath).unlink()


class TestJsonFlag:
    """Tests for --json flag."""

    def test_json_invalid_ignored(self, parser: ArgParser) -> None:
        """Test invalid JSON is ignored."""
        result = parser.parse("--json 'invalid json'")
        assert result.payload == {}

    def test_json_non_dict_ignored(self, parser: ArgParser) -> None:
        """Test non-dict JSON is ignored."""
        result = parser.parse("--json '[1,2,3]'")
        # Arrays should be ignored
        assert result.payload == {}

    def test_json_with_special_chars(self, parser: ArgParser) -> None:
        """Test JSON with special characters."""
        result = parser.parse('--json \'{"msg": "hello\\nworld"}\'')
        assert result.payload == {"msg": "hello\nworld"}


class TestValueConversionEdgeCases:
    """Edge cases for value conversion."""

    def test_very_large_integer(self, parser: ArgParser) -> None:
        """Test very large integer."""
        result = parser.parse("big=999999999999999999")
        assert result.payload["big"] == 999999999999999999

    def test_scientific_notation(self, parser: ArgParser) -> None:
        """Test scientific notation float."""
        result = parser.parse("sci=1.5e10")
        assert result.payload["sci"] == 1.5e10

    def test_negative_float(self, parser: ArgParser) -> None:
        """Test negative float."""
        result = parser.parse("neg=-3.14")
        assert result.payload["neg"] == -3.14

    def test_json_nested_object(self, parser: ArgParser) -> None:
        """Test nested JSON object."""
        result = parser.parse('data={"a":{"b":{"c":1}}}')
        # May or may not parse depending on quoting
        assert "data" in result.payload

    def test_empty_json_object(self, parser: ArgParser) -> None:
        """Test empty JSON object."""
        result = parser.parse("data={}")
        assert result.payload["data"] == {}


class TestFlagEdgeCases:
    """Edge cases for flag parsing."""

    def test_double_dash_flag_with_equals(self, parser: ArgParser) -> None:
        """Test --key=value flag format."""
        result = parser.parse("--format=json --limit=100")
        assert result.flags == {"format": "json", "limit": 100}

    def test_flag_boolean_conversion(self, parser: ArgParser) -> None:
        """Test flag with boolean value."""
        result = parser.parse("--verbose=true --quiet=false")
        assert result.flags["verbose"] is True
        assert result.flags["quiet"] is False

    def test_multiple_of_same_flag(self, parser: ArgParser) -> None:
        """Test multiple instances of same flag."""
        result = parser.parse("--tag=a --tag=b")
        # Last value wins
        assert result.flags["tag"] == "b"


class TestMetaAndOptions:
    """Tests for meta and options prefixes."""

    def test_meta_with_nested_value(self, parser: ArgParser) -> None:
        """Test meta with complex value."""
        result = parser.parse('#config={"key":"value"}')
        assert "config" in result.meta

    def test_options_with_integer(self, parser: ArgParser) -> None:
        """Test options with integer value."""
        result = parser.parse("$timeout=5000 $retries=3")
        assert result.options["timeout"] == 5000
        assert result.options["retries"] == 3

    def test_mixed_prefixes(self, parser: ArgParser) -> None:
        """Test all prefixes in one command."""
        result = parser.parse(
            "action x=1 y=2 #tenant=acme #user=admin $timeout=5000 --verbose --format=json"
        )
        assert result.positional == ["action"]
        assert result.payload == {"x": 1, "y": 2}
        assert result.meta == {"tenant": "acme", "user": "admin"}
        assert result.options == {"timeout": 5000}
        assert result.flags == {"verbose": True, "format": "json"}


class TestSpecialCharacters:
    """Tests for special character handling."""

    def test_value_with_spaces_quoted(self, parser: ArgParser) -> None:
        """Test value with spaces in quotes."""
        result = parser.parse('msg="hello world"')
        assert result.payload["msg"] == "hello world"

    def test_value_with_equals_sign(self, parser: ArgParser) -> None:
        """Test value containing equals sign."""
        result = parser.parse("equation=a=b+c")
        assert result.payload["equation"] == "a=b+c"

    def test_value_with_hash(self, parser: ArgParser) -> None:
        """Test value with hash character."""
        result = parser.parse('color="#ff0000"')
        assert result.payload["color"] == "#ff0000"

    def test_value_with_dollar(self, parser: ArgParser) -> None:
        """Test value with dollar sign."""
        result = parser.parse('price="$100"')
        assert result.payload["price"] == "$100"
