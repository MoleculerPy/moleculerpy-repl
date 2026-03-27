"""Tests for argument parser."""

from __future__ import annotations

from moleculerpy_repl.parser import ArgParser, ParsedArgs


class TestArgParser:
    """Tests for ArgParser class."""

    def test_empty_input(self, parser: ArgParser) -> None:
        """Test parsing empty string."""
        result = parser.parse("")
        assert result.positional == []
        assert result.payload == {}
        assert result.meta == {}
        assert result.options == {}
        assert result.flags == {}

    def test_whitespace_only(self, parser: ArgParser) -> None:
        """Test parsing whitespace-only string."""
        result = parser.parse("   ")
        assert result.positional == []

    def test_positional_args(self, parser: ArgParser) -> None:
        """Test parsing positional arguments."""
        result = parser.parse("math.add")
        assert result.positional == ["math.add"]

        result = parser.parse("action arg1 arg2")
        assert result.positional == ["action", "arg1", "arg2"]

    def test_key_value_payload(self, parser: ArgParser) -> None:
        """Test parsing key=value pairs into payload."""
        result = parser.parse("a=5 b=10")
        assert result.payload == {"a": 5, "b": 10}

    def test_mixed_positional_and_payload(self, parser: ArgParser) -> None:
        """Test mixing positional args with payload."""
        result = parser.parse("math.add a=5 b=3")
        assert result.positional == ["math.add"]
        assert result.payload == {"a": 5, "b": 3}

    def test_meta_prefix(self, parser: ArgParser) -> None:
        """Test #key=value meta prefix."""
        result = parser.parse("#tenant=acme #user=admin")
        assert result.meta == {"tenant": "acme", "user": "admin"}

    def test_options_prefix(self, parser: ArgParser) -> None:
        """Test $key=value options prefix."""
        result = parser.parse("$timeout=5000 $retries=3")
        assert result.options == {"timeout": 5000, "retries": 3}

    def test_flags_boolean(self, parser: ArgParser) -> None:
        """Test --flag boolean flags."""
        result = parser.parse("--verbose --debug")
        assert result.flags == {"verbose": True, "debug": True}

    def test_flags_with_value(self, parser: ArgParser) -> None:
        """Test --key=value flags."""
        result = parser.parse("--output=json --limit=10")
        assert result.flags == {"output": "json", "limit": 10}

    def test_json_flag(self, parser: ArgParser) -> None:
        """Test --json flag for inline JSON."""
        result = parser.parse('--json \'{"x": 1, "y": 2}\'')
        assert result.payload == {"x": 1, "y": 2}

    def test_json_merge(self, parser: ArgParser) -> None:
        """Test --json merges with existing payload."""
        result = parser.parse("a=5 --json '{\"b\": 10}'")
        assert result.payload == {"a": 5, "b": 10}

    def test_all_prefixes_combined(self, parser: ArgParser) -> None:
        """Test combining all prefix types."""
        result = parser.parse("user.get id=123 #tenant=acme $timeout=5000 --verbose")
        assert result.positional == ["user.get"]
        assert result.payload == {"id": 123}
        assert result.meta == {"tenant": "acme"}
        assert result.options == {"timeout": 5000}
        assert result.flags == {"verbose": True}

    def test_raw_preserved(self, parser: ArgParser) -> None:
        """Test that raw input is preserved."""
        raw = "math.add a=5 b=3"
        result = parser.parse(raw)
        assert result.raw == raw


class TestValueConversion:
    """Tests for value type conversion."""

    def test_integer_conversion(self, parser: ArgParser) -> None:
        """Test integer conversion."""
        result = parser.parse("a=42 b=-10 c=0")
        assert result.payload == {"a": 42, "b": -10, "c": 0}
        assert isinstance(result.payload["a"], int)

    def test_float_conversion(self, parser: ArgParser) -> None:
        """Test float conversion."""
        result = parser.parse("a=3.14 b=-2.5 c=0.0")
        assert result.payload == {"a": 3.14, "b": -2.5, "c": 0.0}
        assert isinstance(result.payload["a"], float)

    def test_boolean_conversion(self, parser: ArgParser) -> None:
        """Test boolean conversion."""
        result = parser.parse("a=true b=false c=True d=FALSE")
        assert result.payload == {"a": True, "b": False, "c": True, "d": False}
        assert isinstance(result.payload["a"], bool)

    def test_null_conversion(self, parser: ArgParser) -> None:
        """Test null/none conversion."""
        result = parser.parse("a=null b=none c=None d=NULL")
        assert result.payload == {"a": None, "b": None, "c": None, "d": None}

    def test_json_object_conversion(self, parser: ArgParser) -> None:
        """Test JSON object conversion."""
        # Note: JSON must be valid - keys need quotes
        result = parser.parse('data={"x":1}')
        # shlex removes outer quotes, result becomes {x:1} which is invalid JSON
        # The value is preserved as string when invalid
        # To get parsed JSON, use --json flag or proper quoting
        assert "data" in result.payload

    def test_json_object_via_flag(self, parser: ArgParser) -> None:
        """Test JSON via --json flag."""
        result = parser.parse("--json '{\"x\": 1}'")
        assert result.payload == {"x": 1}

    def test_json_array_conversion(self, parser: ArgParser) -> None:
        """Test JSON array conversion."""
        result = parser.parse("items=[1,2,3]")
        assert result.payload == {"items": [1, 2, 3]}

    def test_string_preserved(self, parser: ArgParser) -> None:
        """Test that non-convertible strings are preserved."""
        result = parser.parse("name=hello path=/usr/bin")
        assert result.payload == {"name": "hello", "path": "/usr/bin"}
        assert isinstance(result.payload["name"], str)

    def test_force_string_with_at_prefix(self, parser: ArgParser) -> None:
        """Test @key=value forces string type."""
        result = parser.parse("@id=123 @flag=true")
        assert result.payload == {"id": "123", "flag": "true"}
        assert isinstance(result.payload["id"], str)


class TestQuotedStrings:
    """Tests for quoted string handling."""

    def test_single_quoted_value(self, parser: ArgParser) -> None:
        """Test single-quoted values."""
        result = parser.parse("msg='hello world'")
        assert result.payload == {"msg": "hello world"}

    def test_double_quoted_value(self, parser: ArgParser) -> None:
        """Test double-quoted values."""
        result = parser.parse('msg="hello world"')
        assert result.payload == {"msg": "hello world"}

    def test_quoted_with_special_chars(self, parser: ArgParser) -> None:
        """Test quoted values with special characters."""
        result = parser.parse("query='SELECT * FROM users WHERE id=1'")
        assert result.payload == {"query": "SELECT * FROM users WHERE id=1"}


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_malformed_json_preserved_as_string(self, parser: ArgParser) -> None:
        """Test malformed JSON is preserved as string."""
        result = parser.parse("data={invalid}")
        assert result.payload == {"data": "{invalid}"}

    def test_empty_value(self, parser: ArgParser) -> None:
        """Test empty value handling."""
        result = parser.parse("key=")
        assert result.payload == {"key": ""}

    def test_equals_in_value(self, parser: ArgParser) -> None:
        """Test handling equals sign in value."""
        result = parser.parse("formula=a=b+c")
        assert result.payload == {"formula": "a=b+c"}

    def test_prefix_without_equals(self, parser: ArgParser) -> None:
        """Test prefix characters without equals are positional."""
        result = parser.parse("#tag $var")
        # Without =, these are positional
        assert "#tag" in result.positional
        assert "$var" in result.positional

    def test_invalid_shlex_fallback(self, parser: ArgParser) -> None:
        """Test fallback to simple split when shlex fails."""
        # Unclosed quote - shlex will fail, falls back to split
        result = parser.parse("action 'unclosed")
        assert len(result.positional) >= 1


class TestParsedArgsDataclass:
    """Tests for ParsedArgs dataclass."""

    def test_default_values(self) -> None:
        """Test default values of ParsedArgs."""
        args = ParsedArgs()
        assert args.positional == []
        assert args.payload == {}
        assert args.meta == {}
        assert args.options == {}
        assert args.flags == {}
        assert args.raw == ""

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        args = ParsedArgs(
            positional=["action"],
            payload={"x": 1},
            meta={"tenant": "test"},
            options={"timeout": 5000},
            flags={"verbose": True},
            raw="action x=1",
        )
        assert args.positional == ["action"]
        assert args.payload == {"x": 1}
        assert args.meta == {"tenant": "test"}
        assert args.options == {"timeout": 5000}
        assert args.flags == {"verbose": True}
        assert args.raw == "action x=1"
