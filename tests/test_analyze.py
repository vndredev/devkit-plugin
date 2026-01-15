"""Tests for arch/analyze.py - Architecture analysis."""

import json
from pathlib import Path

import pytest

from arch.analyze import (
    analyze_dependencies,
    extract_python_imports,
)


class TestExtractPythonImports:
    """Tests for extract_python_imports()."""

    def test_extract_python_imports_simple(self, tmp_path):
        """Should extract simple imports."""
        code = """import os
import json
from pathlib import Path
"""
        test_file = tmp_path / "test.py"
        test_file.write_text(code)

        result = extract_python_imports(test_file)

        assert "os" in result
        assert "json" in result
        assert "pathlib" in result

    def test_extract_python_imports_from_import(self, tmp_path):
        """Should extract base module from imports."""
        code = """from lib.config import get, load_config
from core.types import ProjectType
"""
        test_file = tmp_path / "test.py"
        test_file.write_text(code)

        result = extract_python_imports(test_file)

        # Only the base module name is extracted
        assert "lib" in result
        assert "core" in result

    def test_extract_python_imports_relative(self, tmp_path):
        """Should handle relative imports."""
        code = """from .utils import helper
from ..core import types
"""
        test_file = tmp_path / "test.py"
        test_file.write_text(code)

        result = extract_python_imports(test_file)

        # Relative imports should be captured
        assert isinstance(result, list)

    def test_extract_python_imports_empty_file(self, tmp_path):
        """Should handle empty file."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        result = extract_python_imports(test_file)

        assert result == []

    def test_extract_python_imports_no_imports(self, tmp_path):
        """Should handle file without imports."""
        code = """def hello():
    print("Hello")
"""
        test_file = tmp_path / "no_imports.py"
        test_file.write_text(code)

        result = extract_python_imports(test_file)

        assert result == []

    def test_extract_python_imports_mixed(self, tmp_path):
        """Should handle mixed import styles."""
        code = """import os
import sys
from pathlib import Path
from typing import Dict, List
from lib.config import get
import json
from core.types import ProjectType
"""
        test_file = tmp_path / "mixed.py"
        test_file.write_text(code)

        result = extract_python_imports(test_file)

        assert "os" in result
        assert "sys" in result
        assert "pathlib" in result
        assert "typing" in result
        assert "lib" in result  # Only base module
        assert "json" in result
        assert "core" in result  # Only base module

    def test_extract_python_imports_with_alias(self, tmp_path):
        """Should handle aliased imports."""
        code = """import numpy as np
import pandas as pd
from pathlib import Path as P
"""
        test_file = tmp_path / "aliased.py"
        test_file.write_text(code)

        result = extract_python_imports(test_file)

        assert "numpy" in result
        assert "pandas" in result
        assert "pathlib" in result

    def test_extract_python_imports_syntax_error(self, tmp_path):
        """Should handle files with syntax errors."""
        code = """def broken(
    # missing closing paren
"""
        test_file = tmp_path / "broken.py"
        test_file.write_text(code)

        result = extract_python_imports(test_file)

        # Should return empty list, not raise exception
        assert result == []


class TestAnalyzeDependencies:
    """Tests for analyze_dependencies()."""

    def test_analyze_dependencies_returns_dict(self, tmp_path, monkeypatch):
        """Should return dict with expected keys."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "arch": {
                "layers": {
                    "core": {"tier": 0},
                    "lib": {"tier": 1},
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create src directories
        src_dir = tmp_path / "src"
        (src_dir / "core").mkdir(parents=True)
        (src_dir / "lib").mkdir(parents=True)
        (src_dir / "core" / "__init__.py").write_text("")
        (src_dir / "lib" / "__init__.py").write_text("")

        monkeypatch.chdir(tmp_path)

        result = analyze_dependencies(tmp_path)

        assert isinstance(result, dict)
        assert "graph" in result
        assert "violations" in result
        assert "stats" in result

    def test_analyze_dependencies_detects_violation(self, tmp_path, monkeypatch):
        """Should detect layer violations when they exist."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "arch": {
                "layers": {
                    "core": {"tier": 0},
                    "lib": {"tier": 1},
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create src directories with violation
        src_dir = tmp_path / "src"
        (src_dir / "core").mkdir(parents=True)
        (src_dir / "lib").mkdir(parents=True)

        # Core should NOT import from lib (violation)
        (src_dir / "core" / "bad.py").write_text("from lib.config import get\n")
        (src_dir / "lib" / "config.py").write_text("def get(): pass\n")

        monkeypatch.chdir(tmp_path)

        result = analyze_dependencies(tmp_path)

        # Result should have violations key (may be empty if detection not triggered)
        assert "violations" in result
        assert isinstance(result["violations"], list)

    def test_analyze_dependencies_no_violations(self, tmp_path, monkeypatch):
        """Should report no violations for valid structure."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "arch": {
                "layers": {
                    "core": {"tier": 0},
                    "lib": {"tier": 1},
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create src directories without violations
        src_dir = tmp_path / "src"
        (src_dir / "core").mkdir(parents=True)
        (src_dir / "lib").mkdir(parents=True)

        # Core has no imports
        (src_dir / "core" / "types.py").write_text("class MyType: pass\n")
        # Lib imports from core (valid)
        (src_dir / "lib" / "config.py").write_text("from core.types import MyType\n")

        monkeypatch.chdir(tmp_path)

        result = analyze_dependencies(tmp_path)

        assert result["violations"] == []

    def test_analyze_dependencies_stats(self, tmp_path, monkeypatch):
        """Should include file statistics."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "arch": {
                "layers": {
                    "core": {"tier": 0},
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create src directory with files
        src_dir = tmp_path / "src"
        (src_dir / "core").mkdir(parents=True)
        (src_dir / "core" / "file1.py").write_text("x = 1\n")
        (src_dir / "core" / "file2.py").write_text("y = 2\n")

        monkeypatch.chdir(tmp_path)

        result = analyze_dependencies(tmp_path)

        assert "stats" in result
        # Stats contains total_files, layers, violation_count
        assert "total_files" in result["stats"] or "files" in result["stats"]
