"""Tests for core/jsonc.py - JSONC parsing."""

import json

import pytest

from core.jsonc import strip_comments


class TestStripComments:
    """Tests for strip_comments()."""

    def test_strip_single_line_comment(self):
        """Should remove single-line comments."""
        content = '{"key": "value"} // comment'
        result = strip_comments(content)
        assert json.loads(result) == {"key": "value"}

    def test_strip_single_line_comment_on_own_line(self):
        """Should remove single-line comments on their own line."""
        content = """// comment at start
{
    "key": "value"
}"""
        result = strip_comments(content)
        assert json.loads(result) == {"key": "value"}

    def test_strip_multiple_single_line_comments(self):
        """Should remove multiple single-line comments."""
        content = """{
    // comment 1
    "key1": "value1", // comment 2
    // comment 3
    "key2": "value2"
}"""
        result = strip_comments(content)
        assert json.loads(result) == {"key1": "value1", "key2": "value2"}

    def test_strip_multi_line_comment(self):
        """Should remove multi-line comments."""
        content = '{"key": /* comment */ "value"}'
        result = strip_comments(content)
        assert json.loads(result) == {"key": "value"}

    def test_strip_multi_line_comment_spanning_lines(self):
        """Should remove multi-line comments spanning multiple lines."""
        content = """{
    "key1": "value1",
    /* This is a
       multi-line
       comment */
    "key2": "value2"
}"""
        result = strip_comments(content)
        assert json.loads(result) == {"key1": "value1", "key2": "value2"}

    def test_preserve_double_slash_in_string(self):
        """Should preserve // inside strings."""
        content = '{"url": "https://example.com"}'
        result = strip_comments(content)
        assert json.loads(result) == {"url": "https://example.com"}

    def test_preserve_slash_star_in_string(self):
        """Should preserve /* inside strings."""
        content = '{"pattern": "/* pattern */"}'
        result = strip_comments(content)
        assert json.loads(result) == {"pattern": "/* pattern */"}

    def test_preserve_escaped_quotes_in_string(self):
        """Should handle escaped quotes in strings."""
        content = r'{"key": "value with \" escaped quote"}'
        result = strip_comments(content)
        assert json.loads(result) == {"key": 'value with " escaped quote'}

    def test_preserve_backslash_in_string(self):
        """Should handle backslashes in strings."""
        content = r'{"path": "C:\\Users\\test"}'
        result = strip_comments(content)
        assert json.loads(result) == {"path": r"C:\Users\test"}

    def test_empty_content(self):
        """Should handle empty content."""
        result = strip_comments("")
        assert result == ""

    def test_no_comments(self):
        """Should return unchanged content without comments."""
        content = '{"key": "value"}'
        result = strip_comments(content)
        assert result == content

    def test_comment_at_end_of_file(self):
        """Should handle comment at end of file without newline."""
        content = '{"key": "value"} // comment'
        result = strip_comments(content)
        assert json.loads(result) == {"key": "value"}

    def test_unclosed_multi_line_comment(self):
        """Should handle unclosed multi-line comment at end of file."""
        content = '{"key": "value"} /* unclosed'
        result = strip_comments(content)
        # Should not crash, content after /* is stripped
        assert "value" in result

    def test_complex_jsonc(self):
        """Should handle complex JSONC with mixed comments."""
        content = """{
    // Project settings
    "project": {
        "name": "test", /* inline */
        "type": "python"
    },
    /* Multi-line
       comment block */
    "features": ["a", "b"] // trailing
}"""
        result = strip_comments(content)
        parsed = json.loads(result)
        assert parsed["project"]["name"] == "test"
        assert parsed["project"]["type"] == "python"
        assert parsed["features"] == ["a", "b"]
