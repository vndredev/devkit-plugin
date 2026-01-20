"""Tests for lib/tools.py - External tools, linters, formatters."""

from pathlib import Path
from unittest.mock import patch

import pytest

from core.types import ProjectType
from lib.tools import (
    ESLINT_EXTENSIONS,
    FORMATTERS,
    _find_project_root,
    detect_project_type,
    detect_project_version,
    format_file,
    lint_file,
    run_linter,
)


class TestFormatters:
    """Tests for FORMATTERS mapping."""

    def test_python_formatter(self):
        """Should use ruff for Python files."""
        assert FORMATTERS[".py"] == ["ruff", "format"]

    def test_typescript_formatter(self):
        """Should use prettier for TypeScript files."""
        assert FORMATTERS[".ts"] == ["npx", "prettier", "--write"]
        assert FORMATTERS[".tsx"] == ["npx", "prettier", "--write"]

    def test_javascript_formatter(self):
        """Should use prettier for JavaScript files."""
        assert FORMATTERS[".js"] == ["npx", "prettier", "--write"]
        assert FORMATTERS[".jsx"] == ["npx", "prettier", "--write"]

    def test_json_formatter(self):
        """Should use prettier for JSON files."""
        assert FORMATTERS[".json"] == ["npx", "prettier", "--write"]

    def test_markdown_formatter(self):
        """Should use prettier for Markdown files."""
        assert FORMATTERS[".md"] == ["npx", "prettier", "--write"]


class TestFormatFile:
    """Tests for format_file()."""

    def test_returns_disabled_when_auto_false(self, tmp_path):
        """Should return success when auto=False."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x=1")

        success, msg = format_file(str(test_file), auto=False)

        assert success is True
        assert "disabled" in msg.lower()

    def test_returns_no_formatter_for_unknown_ext(self, tmp_path):
        """Should return success with no formatter message for unknown extension."""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("content")

        success, msg = format_file(str(test_file))

        assert success is True
        assert "no formatter" in msg.lower()

    @patch("lib.tools.subprocess.run")
    def test_formats_python_file(self, mock_run, tmp_path):
        """Should call ruff format for Python files."""
        mock_run.return_value.returncode = 0
        test_file = tmp_path / "test.py"
        test_file.write_text("x=1")

        success, msg = format_file(str(test_file))

        assert success is True
        assert "formatted" in msg.lower()
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ruff"
        assert call_args[1] == "format"

    @patch("lib.tools.subprocess.run")
    def test_handles_format_failure(self, mock_run, tmp_path):
        """Should return failure when formatter fails."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "ruff", stderr=b"error")
        test_file = tmp_path / "test.py"
        test_file.write_text("x=1")

        success, msg = format_file(str(test_file))

        assert success is False
        assert "failed" in msg.lower()

    @patch("lib.tools.subprocess.run")
    def test_handles_formatter_not_found(self, mock_run, tmp_path):
        """Should return failure when formatter not found."""
        mock_run.side_effect = FileNotFoundError()
        test_file = tmp_path / "test.py"
        test_file.write_text("x=1")

        success, msg = format_file(str(test_file))

        assert success is False
        assert "not found" in msg.lower()


class TestRunLinter:
    """Tests for run_linter()."""

    def test_returns_success_for_empty_files(self):
        """Should return success when no files to lint."""
        success, msg = run_linter("ruff", [])

        assert success is True
        assert "no files" in msg.lower()

    def test_returns_failure_for_unknown_linter(self):
        """Should return failure for unknown linter."""
        success, msg = run_linter("unknown_linter", ["file.py"])

        assert success is False
        assert "unknown linter" in msg.lower()

    @patch("lib.tools.subprocess.run")
    def test_runs_ruff_linter(self, mock_run):
        """Should call ruff check for Python files."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        success, msg = run_linter("ruff", ["file.py"])

        assert success is True
        call_args = mock_run.call_args[0][0]
        assert "ruff" in call_args
        assert "check" in call_args

    @patch("lib.tools.subprocess.run")
    def test_runs_ruff_with_fix(self, mock_run):
        """Should pass --fix flag when fix=True."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        run_linter("ruff", ["file.py"], fix=True)

        call_args = mock_run.call_args[0][0]
        assert "--fix" in call_args

    @patch("lib.tools.subprocess.run")
    def test_runs_eslint(self, mock_run):
        """Should call eslint for JavaScript files."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        success, msg = run_linter("eslint", ["file.js"])

        assert success is True
        call_args = mock_run.call_args[0][0]
        assert "eslint" in call_args

    @patch("lib.tools.subprocess.run")
    def test_runs_markdownlint(self, mock_run):
        """Should call markdownlint for Markdown files."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        success, msg = run_linter("markdownlint", ["file.md"])

        assert success is True
        call_args = mock_run.call_args[0][0]
        assert "markdownlint-cli" in call_args

    @patch("lib.tools.subprocess.run")
    def test_handles_linter_failure(self, mock_run):
        """Should return failure when linter finds issues."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "error: line 1"
        mock_run.return_value.stderr = ""

        success, msg = run_linter("ruff", ["file.py"])

        assert success is False
        assert "error" in msg.lower()

    @patch("lib.tools.subprocess.run")
    def test_handles_linter_not_found(self, mock_run):
        """Should return failure when linter not found."""
        mock_run.side_effect = FileNotFoundError()

        success, msg = run_linter("ruff", ["file.py"])

        assert success is False
        assert "not found" in msg.lower()


class TestDetectProjectType:
    """Tests for detect_project_type()."""

    def test_detects_claude_plugin(self, tmp_path):
        """Should detect Claude plugin project."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text("{}")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.CLAUDE_PLUGIN

    def test_detects_python_with_pyproject(self, tmp_path):
        """Should detect Python project with pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.PYTHON

    def test_detects_python_with_setup_py(self, tmp_path):
        """Should detect Python project with setup.py."""
        (tmp_path / "setup.py").write_text("from setuptools import setup")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.PYTHON

    def test_detects_nextjs_with_next_config_ts(self, tmp_path):
        """Should detect Next.js project with next.config.ts."""
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "next.config.ts").write_text("export default {}")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.NEXTJS

    def test_detects_nextjs_with_next_config_js(self, tmp_path):
        """Should detect Next.js project with next.config.js."""
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "next.config.js").write_text("module.exports = {}")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.NEXTJS

    def test_detects_typescript(self, tmp_path):
        """Should detect TypeScript project."""
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "tsconfig.json").write_text("{}")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.TYPESCRIPT

    def test_detects_javascript(self, tmp_path):
        """Should detect JavaScript project."""
        (tmp_path / "package.json").write_text("{}")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.JAVASCRIPT

    def test_returns_unknown_for_empty_dir(self, tmp_path):
        """Should return UNKNOWN for empty directory."""
        result = detect_project_type(tmp_path)

        assert result == ProjectType.UNKNOWN

    def test_claude_plugin_takes_precedence(self, tmp_path):
        """Should prioritize Claude plugin over other types."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text("{}")
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "package.json").write_text("{}")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.CLAUDE_PLUGIN

    def test_python_takes_precedence_over_node(self, tmp_path):
        """Should prioritize Python over Node.js."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "package.json").write_text("{}")

        result = detect_project_type(tmp_path)

        assert result == ProjectType.PYTHON


class TestDetectProjectVersion:
    """Tests for detect_project_version()."""

    def test_delegates_to_get_version(self, tmp_path):
        """Should delegate to lib.version.get_version."""
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.3"')

        result = detect_project_version(tmp_path)

        assert result == "1.2.3"

    def test_returns_default_if_not_found(self, tmp_path):
        """Should return 0.0.0 if version not found."""
        result = detect_project_version(tmp_path)

        assert result == "0.0.0"


class TestEslintExtensions:
    """Tests for ESLINT_EXTENSIONS constant."""

    def test_includes_typescript_extensions(self):
        """Should include TypeScript extensions."""
        assert ".ts" in ESLINT_EXTENSIONS
        assert ".tsx" in ESLINT_EXTENSIONS

    def test_includes_javascript_extensions(self):
        """Should include JavaScript extensions."""
        assert ".js" in ESLINT_EXTENSIONS
        assert ".jsx" in ESLINT_EXTENSIONS


class TestFindProjectRoot:
    """Tests for _find_project_root()."""

    def test_finds_git_root(self, tmp_path):
        """Should find project root by .git directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.ts"
        test_file.write_text("const x = 1;")

        result = _find_project_root(test_file)

        assert result == tmp_path

    def test_finds_package_json_root(self, tmp_path):
        """Should find project root by package.json if no .git."""
        (tmp_path / "package.json").write_text("{}")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.ts"
        test_file.write_text("const x = 1;")

        result = _find_project_root(test_file)

        assert result == tmp_path

    def test_returns_parent_if_no_markers(self, tmp_path):
        """Should return file's parent if no project markers found."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.ts"
        test_file.write_text("const x = 1;")

        result = _find_project_root(test_file)

        assert result == src_dir

    def test_prefers_git_over_package_json(self, tmp_path):
        """Should prefer .git over package.json when both exist."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (tmp_path / "package.json").write_text("{}")
        test_file = tmp_path / "test.ts"
        test_file.write_text("const x = 1;")

        result = _find_project_root(test_file)

        assert result == tmp_path


class TestLintFile:
    """Tests for lint_file()."""

    def test_skips_non_js_ts_files(self, tmp_path):
        """Should skip files that aren't JS/TS."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        success, errors, warnings, msg = lint_file(str(test_file))

        assert success is True
        assert errors == 0
        assert warnings == 0
        assert "no linter" in msg.lower()

    @patch("lib.tools.subprocess.run")
    def test_runs_eslint_on_ts_file(self, mock_run, tmp_path):
        """Should run ESLint on TypeScript files."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '[{"errorCount": 0, "warningCount": 0}]'
        mock_run.return_value.stderr = ""
        test_file = tmp_path / "test.ts"
        test_file.write_text("const x = 1;")

        success, errors, warnings, msg = lint_file(str(test_file))

        assert success is True
        assert errors == 0
        assert warnings == 0
        call_args = mock_run.call_args[0][0]
        assert "eslint" in call_args
        assert "--format" in call_args
        assert "json" in call_args

    @patch("lib.tools.subprocess.run")
    def test_runs_eslint_with_correct_cwd(self, mock_run, tmp_path):
        """Should run ESLint from project root directory (fixes #75)."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '[{"errorCount": 0, "warningCount": 0}]'
        mock_run.return_value.stderr = ""
        # Create project structure with .git marker
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "component.tsx"
        test_file.write_text("const x = 1;")

        lint_file(str(test_file))

        # Verify cwd is set to project root (where .git is)
        call_kwargs = mock_run.call_args[1]
        assert "cwd" in call_kwargs
        assert call_kwargs["cwd"] == tmp_path

    @patch("lib.tools.subprocess.run")
    def test_runs_eslint_with_fix(self, mock_run, tmp_path):
        """Should pass --fix flag when fix=True."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '[{"errorCount": 0, "warningCount": 0}]'
        mock_run.return_value.stderr = ""
        test_file = tmp_path / "test.tsx"
        test_file.write_text("const x = 1;")

        lint_file(str(test_file), fix=True)

        call_args = mock_run.call_args[0][0]
        assert "--fix" in call_args

    @patch("lib.tools.subprocess.run")
    def test_returns_errors_and_warnings(self, mock_run, tmp_path):
        """Should return error and warning counts."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = (
            '[{"errorCount": 2, "warningCount": 1, "messages": ['
            '{"severity": 2, "line": 1, "ruleId": "no-unused-vars", "message": "unused var"},'
            '{"severity": 1, "line": 2, "ruleId": "prefer-const", "message": "use const"}'
            "]}]"
        )
        mock_run.return_value.stderr = ""
        test_file = tmp_path / "test.js"
        test_file.write_text("let x = 1;")

        success, errors, warnings, msg = lint_file(str(test_file))

        assert success is False
        assert errors == 2
        assert warnings == 1
        assert "error" in msg.lower() or "L1:" in msg

    @patch("lib.tools.subprocess.run")
    def test_handles_eslint_not_found(self, mock_run, tmp_path):
        """Should return success when ESLint not installed."""
        mock_run.side_effect = FileNotFoundError()
        test_file = tmp_path / "test.jsx"
        test_file.write_text("const x = 1;")

        success, errors, warnings, msg = lint_file(str(test_file))

        assert success is True
        assert errors == 0
        assert warnings == 0
        assert "not installed" in msg.lower() or "skipped" in msg.lower()

    @patch("lib.tools.subprocess.run")
    def test_handles_timeout(self, mock_run, tmp_path):
        """Should handle timeout gracefully."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("eslint", 30)
        test_file = tmp_path / "test.ts"
        test_file.write_text("const x = 1;")

        success, errors, warnings, msg = lint_file(str(test_file))

        assert success is False
        assert "timed out" in msg.lower()
