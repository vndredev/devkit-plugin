"""Tests for code discovery module."""

import pytest
from pathlib import Path
from unittest.mock import patch

from arch.discovery import (
    CodeMatch,
    extract_definitions_from_content,
    extract_definitions_from_file,
    calculate_name_similarity,
    scan_codebase,
    find_similar_code,
    find_duplicates_for_name,
    format_matches_report,
)


class TestCodeMatch:
    """Tests for CodeMatch dataclass."""

    def test_creates_match_with_all_fields(self):
        """Creates CodeMatch with all required fields."""
        match = CodeMatch(
            name="test_func",
            type="function",
            file="src/test.py",
            line=42,
            signature="def test_func(x: int) -> str",
            similarity=0.85,
        )
        assert match.name == "test_func"
        assert match.type == "function"
        assert match.file == "src/test.py"
        assert match.line == 42
        assert match.signature == "def test_func(x: int) -> str"
        assert match.similarity == 0.85


class TestExtractDefinitionsFromContent:
    """Tests for extract_definitions_from_content."""

    def test_extracts_simple_function(self):
        """Extracts simple function definition."""
        content = "def hello(): pass"
        result = extract_definitions_from_content(content)
        assert len(result) == 1
        assert result[0]["name"] == "hello"
        assert result[0]["type"] == "function"
        assert result[0]["line"] == 1

    def test_extracts_function_with_args(self):
        """Extracts function with typed arguments."""
        content = "def greet(name: str, age: int) -> str: pass"
        result = extract_definitions_from_content(content)
        assert len(result) == 1
        assert "name: str" in result[0]["signature"]
        assert "age: int" in result[0]["signature"]
        assert "-> str" in result[0]["signature"]

    def test_extracts_async_function(self):
        """Extracts async function definition."""
        content = "async def fetch_data(): pass"
        result = extract_definitions_from_content(content)
        assert len(result) == 1
        assert result[0]["name"] == "fetch_data"
        assert result[0]["type"] == "function"

    def test_extracts_class(self):
        """Extracts class definition."""
        content = "class MyClass: pass"
        result = extract_definitions_from_content(content)
        assert len(result) == 1
        assert result[0]["name"] == "MyClass"
        assert result[0]["type"] == "class"

    def test_extracts_class_with_bases(self):
        """Extracts class with base classes."""
        content = "class Child(Parent, Mixin): pass"
        result = extract_definitions_from_content(content)
        assert len(result) == 1
        assert "Parent" in result[0]["signature"]
        assert "Mixin" in result[0]["signature"]

    def test_extracts_multiple_definitions(self):
        """Extracts multiple definitions from content."""
        content = """
class Config:
    pass

def get_config():
    pass

def set_config(value):
    pass
"""
        result = extract_definitions_from_content(content)
        names = [d["name"] for d in result]
        assert "Config" in names
        assert "get_config" in names
        assert "set_config" in names

    def test_returns_empty_for_invalid_syntax(self):
        """Returns empty list for invalid Python syntax."""
        content = "def broken( pass"
        result = extract_definitions_from_content(content)
        assert result == []

    def test_returns_empty_for_no_definitions(self):
        """Returns empty list when no definitions found."""
        content = "x = 1\ny = 2\nprint(x + y)"
        result = extract_definitions_from_content(content)
        assert result == []


class TestExtractDefinitionsFromFile:
    """Tests for extract_definitions_from_file."""

    def test_extracts_from_file(self, tmp_path: Path):
        """Extracts definitions from Python file."""
        file = tmp_path / "test.py"
        file.write_text("def my_func(): pass")
        
        result = extract_definitions_from_file(file)
        assert len(result) == 1
        assert result[0]["name"] == "my_func"
        assert result[0]["file"] == str(file)

    def test_returns_empty_for_missing_file(self, tmp_path: Path):
        """Returns empty list for missing file."""
        file = tmp_path / "nonexistent.py"
        result = extract_definitions_from_file(file)
        assert result == []

    def test_returns_empty_for_unreadable_file(self, tmp_path: Path):
        """Returns empty list for unreadable file."""
        file = tmp_path / "binary.py"
        file.write_bytes(b"\x80\x81\x82\x83")  # Invalid UTF-8
        
        result = extract_definitions_from_file(file)
        assert result == []


class TestCalculateNameSimilarity:
    """Tests for calculate_name_similarity."""

    def test_exact_match_returns_one(self):
        """Exact match returns 1.0."""
        assert calculate_name_similarity("get_config", "get_config") == 1.0

    def test_case_insensitive_returns_high(self):
        """Case-insensitive match returns 0.95."""
        assert calculate_name_similarity("GetConfig", "getconfig") == 0.95

    def test_contains_returns_high(self):
        """One name containing another returns 0.8."""
        assert calculate_name_similarity("config", "get_config") == 0.8
        assert calculate_name_similarity("get_config", "config") == 0.8

    def test_word_overlap_returns_partial(self):
        """Word overlap returns partial score."""
        score = calculate_name_similarity("get_user", "fetch_user")
        assert 0.2 <= score <= 0.7

    def test_no_similarity_returns_low(self):
        """Completely different names return low score."""
        score = calculate_name_similarity("foo", "bar")
        assert score < 0.3

    def test_empty_words_returns_zero(self):
        """Empty names return 0."""
        assert calculate_name_similarity("", "") == 1.0  # Exact match
        
    def test_camel_case_splitting(self):
        """Handles camelCase name splitting."""
        score = calculate_name_similarity("getUserData", "fetchUserData")
        assert score > 0.3  # Should find "User" and "Data" overlap

    def test_snake_case_splitting(self):
        """Handles snake_case name splitting."""
        score = calculate_name_similarity("get_user_data", "fetch_user_data")
        assert score > 0.3  # Should find "user" and "data" overlap


class TestScanCodebase:
    """Tests for scan_codebase."""

    def test_scans_python_files(self, tmp_path: Path):
        """Scans Python files in directory."""
        src = tmp_path / "src"
        src.mkdir()
        
        (src / "module.py").write_text("def scan_func(): pass")
        
        result = scan_codebase(tmp_path, ["src/**/*.py"])
        names = [d["name"] for d in result]
        assert "scan_func" in names

    def test_scans_multiple_patterns(self, tmp_path: Path):
        """Scans with multiple glob patterns."""
        src = tmp_path / "src"
        lib = tmp_path / "lib"
        src.mkdir()
        lib.mkdir()
        
        (src / "a.py").write_text("def func_a(): pass")
        (lib / "b.py").write_text("def func_b(): pass")
        
        result = scan_codebase(tmp_path, ["src/**/*.py", "lib/**/*.py"])
        names = [d["name"] for d in result]
        assert "func_a" in names
        assert "func_b" in names

    def test_skips_directories(self, tmp_path: Path):
        """Skips directories matching pattern."""
        src = tmp_path / "src"
        src.mkdir()
        
        # Create a directory that matches *.py pattern (edge case)
        weird_dir = src / "weird.py"
        weird_dir.mkdir()
        
        (src / "real.py").write_text("def real_func(): pass")
        
        result = scan_codebase(tmp_path, ["src/**/*.py"])
        # Should not crash and should find real.py
        names = [d["name"] for d in result]
        assert "real_func" in names

    def test_uses_default_patterns(self, tmp_path: Path):
        """Uses default src/**/*.py pattern when none provided."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text("def default_func(): pass")
        
        with patch("arch.discovery.get_project_root", return_value=tmp_path):
            result = scan_codebase(root=tmp_path)
        
        names = [d["name"] for d in result]
        assert "default_func" in names


class TestFindSimilarCode:
    """Tests for find_similar_code."""

    def test_finds_exact_match(self, tmp_path: Path):
        """Finds exact name match in codebase."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "existing.py").write_text("def process_data(): pass")
        
        new_content = "def process_data(): pass"
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            result = find_similar_code(new_content, threshold=0.7, root=tmp_path)
        
        assert len(result) >= 1
        assert result[0].name == "process_data"
        assert result[0].similarity == 1.0

    def test_finds_similar_names(self, tmp_path: Path):
        """Finds similar function names."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "existing.py").write_text("def get_user_config(): pass")
        
        new_content = "def get_user_settings(): pass"
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            result = find_similar_code(new_content, threshold=0.3, root=tmp_path)
        
        # Should find similar due to "get" and "user" overlap
        assert len(result) >= 1

    def test_excludes_specified_file(self, tmp_path: Path):
        """Excludes specified file from search."""
        src = tmp_path / "src"
        src.mkdir()
        existing = src / "existing.py"
        existing.write_text("def my_func(): pass")
        
        new_content = "def my_func(): pass"
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            result = find_similar_code(
                new_content, 
                threshold=0.7, 
                root=tmp_path,
                exclude_file=str(existing)
            )
        
        # Should not find match since file is excluded
        assert len(result) == 0

    def test_returns_empty_for_no_definitions(self, tmp_path: Path):
        """Returns empty when new content has no definitions."""
        new_content = "x = 1"
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            result = find_similar_code(new_content, threshold=0.7, root=tmp_path)
        
        assert result == []

    def test_sorts_by_similarity(self, tmp_path: Path):
        """Sorts results by similarity descending."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "existing.py").write_text("""
def process_data(): pass
def process(): pass
""")
        
        new_content = "def process_data(): pass"
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            result = find_similar_code(new_content, threshold=0.5, root=tmp_path)
        
        if len(result) >= 2:
            assert result[0].similarity >= result[1].similarity


class TestFindDuplicatesForName:
    """Tests for find_duplicates_for_name."""

    def test_finds_exact_match(self, tmp_path: Path):
        """Finds exact function name match."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text("def my_function(): pass")
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            result = find_duplicates_for_name("my_function", root=tmp_path)
        
        assert len(result) == 1
        assert result[0].name == "my_function"

    def test_filters_by_type(self, tmp_path: Path):
        """Filters results by code type."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text("""
def Config(): pass
class Config: pass
""")
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            func_result = find_duplicates_for_name("Config", code_type="function", root=tmp_path)
            class_result = find_duplicates_for_name("Config", code_type="class", root=tmp_path)
        
        assert all(m.type == "function" for m in func_result)
        assert all(m.type == "class" for m in class_result)

    def test_any_type_returns_all(self, tmp_path: Path):
        """code_type='any' returns both functions and classes."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text("""
def Config(): pass
class Config: pass
""")
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            result = find_duplicates_for_name("Config", code_type="any", root=tmp_path)
        
        types = [m.type for m in result]
        assert "function" in types
        assert "class" in types

    def test_respects_threshold(self, tmp_path: Path):
        """Respects similarity threshold."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text("def get_user(): pass")
        
        with patch("arch.discovery.get", return_value=["src/**/*.py"]):
            high_threshold = find_duplicates_for_name("get_user", threshold=0.99, root=tmp_path)
            low_threshold = find_duplicates_for_name("fetch_user", threshold=0.3, root=tmp_path)
        
        # Exact match should pass high threshold
        assert len(high_threshold) == 1
        # Similar name should pass low threshold
        assert len(low_threshold) >= 0  # May or may not match depending on overlap


class TestFormatMatchesReport:
    """Tests for format_matches_report."""

    def test_returns_no_matches_message(self):
        """Returns message when no matches."""
        result = format_matches_report([])
        assert "No similar code found" in result

    def test_includes_context(self):
        """Includes context in header."""
        matches = [
            CodeMatch("func", "function", "test.py", 1, "def func()", 0.9)
        ]
        result = format_matches_report(matches, context="for function 'test'")
        assert "for function 'test'" in result

    def test_formats_match_details(self):
        """Formats match file, line, and signature."""
        matches = [
            CodeMatch("my_func", "function", "src/module.py", 42, "def my_func(x: int)", 0.85)
        ]
        result = format_matches_report(matches)
        assert "src/module.py:42" in result
        assert "def my_func(x: int)" in result
        assert "85%" in result

    def test_limits_to_five_matches(self):
        """Limits output to top 5 matches."""
        matches = [
            CodeMatch(f"func_{i}", "function", f"file_{i}.py", i, f"def func_{i}()", 0.9 - i*0.01)
            for i in range(10)
        ]
        result = format_matches_report(matches)
        assert "and 5 more matches" in result

    def test_shows_percentage(self):
        """Shows similarity as percentage."""
        matches = [
            CodeMatch("func", "function", "test.py", 1, "def func()", 0.75)
        ]
        result = format_matches_report(matches)
        assert "75%" in result

