"""External tools - linters, formatters, notifications.

TIER 1: May import from core only.
"""

import subprocess
import sys
from pathlib import Path

from core.types import ProjectType

# File extension to formatter mapping
FORMATTERS: dict[str, list[str]] = {
    ".py": ["ruff", "format"],
    ".ts": ["npx", "prettier", "--write"],
    ".tsx": ["npx", "prettier", "--write"],
    ".js": ["npx", "prettier", "--write"],
    ".jsx": ["npx", "prettier", "--write"],
    ".json": ["npx", "prettier", "--write"],
    ".md": ["npx", "prettier", "--write"],
}


def format_file(path: str, auto: bool = True) -> tuple[bool, str]:
    """Format a file based on extension.

    Args:
        path: File path to format.
        auto: Whether to auto-format.

    Returns:
        Tuple of (success, message).
    """
    if not auto:
        return True, "Auto-format disabled"

    filepath = Path(path)
    ext = filepath.suffix.lower()

    formatter = FORMATTERS.get(ext)
    if not formatter:
        return True, f"No formatter for {ext}"

    try:
        subprocess.run(  # noqa: S603
            [*formatter, str(filepath)],
            capture_output=True,
            check=True,
            timeout=30,
        )
        return True, f"Formatted {filepath.name}"
    except subprocess.TimeoutExpired:
        return False, f"Format timed out after 30s: {filepath.name}"
    except subprocess.CalledProcessError as e:
        return False, f"Format failed: {e.stderr.decode(errors='replace') if e.stderr else str(e)}"
    except FileNotFoundError:
        return False, f"Formatter not found: {formatter[0]}"


def run_linter(
    name: str,
    files: list[str],
    fix: bool = False,
) -> tuple[bool, str]:
    """Run a linter on files.

    Args:
        name: Linter name (ruff, eslint, markdownlint).
        files: Files to lint.
        fix: Whether to auto-fix.

    Returns:
        Tuple of (success, output).
    """
    if not files:
        return True, "No files to lint"

    commands: dict[str, list[str]] = {
        "ruff": ["ruff", "check", *(["--fix"] if fix else []), *files],
        "eslint": ["npx", "eslint", *(["--fix"] if fix else []), *files],
        "markdownlint": ["npx", "markdownlint-cli", *(["--fix"] if fix else []), *files],
    }

    cmd = commands.get(name)
    if not cmd:
        return False, f"Unknown linter: {name}"

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)  # noqa: S603
        if result.returncode == 0:
            return True, f"{name}: All checks passed"
        return False, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"{name}: Timed out after 60s"
    except FileNotFoundError:
        return False, f"Linter not found: {name}"


# JS/TS extensions that should be linted with ESLint
ESLINT_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}


def _find_project_root(file_path: Path) -> Path:
    """Find project root by looking for common markers.

    Searches upward from file_path for git root or package.json.

    Args:
        file_path: Path to start searching from.

    Returns:
        Project root directory or file's parent if not found.
    """
    current = file_path.parent if file_path.is_file() else file_path
    for parent in [current, *current.parents]:
        # Check for git root first (most reliable)
        if (parent / ".git").exists():
            return parent
        # Fallback to package.json for Node projects
        if (parent / "package.json").exists():
            return parent
    return current


def lint_file(path: str, fix: bool = False) -> tuple[bool, int, int, str]:
    """Run ESLint on a single JS/TS file.

    Args:
        path: File path to lint.
        fix: Whether to auto-fix issues.

    Returns:
        Tuple of (success, error_count, warning_count, message).
    """
    filepath = Path(path)
    ext = filepath.suffix.lower()

    if ext not in ESLINT_EXTENSIONS:
        return True, 0, 0, f"No linter for {ext}"

    # Find project root to run ESLint from correct directory
    project_root = _find_project_root(filepath)

    try:
        # Run ESLint with JSON output for structured results
        cmd = [
            "npx",
            "eslint",
            "--format",
            "json",
            *(["--fix"] if fix else []),
            str(filepath),
        ]
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            cwd=project_root,  # Run from project root to find eslint.config
        )

        # Parse JSON output to get error/warning counts
        import json

        try:
            lint_results = json.loads(result.stdout)
            if lint_results:
                file_result = lint_results[0]
                errors = file_result.get("errorCount", 0)
                warnings = file_result.get("warningCount", 0)

                if errors > 0 or warnings > 0:
                    # Format messages for display
                    messages = file_result.get("messages", [])
                    msg_lines = []
                    for msg in messages[:5]:  # Limit to first 5
                        severity = "error" if msg.get("severity") == 2 else "warn"
                        line = msg.get("line", 0)
                        rule = msg.get("ruleId", "unknown")
                        text = msg.get("message", "")
                        msg_lines.append(f"  [{severity}] L{line}: {text} ({rule})")

                    if len(messages) > 5:
                        msg_lines.append(f"  ... and {len(messages) - 5} more issues")

                    return False, errors, warnings, "\n".join(msg_lines)

                return True, 0, 0, "ESLint: All checks passed"
            return True, 0, 0, "ESLint: All checks passed"
        except json.JSONDecodeError:
            # Fallback to simple check
            if result.returncode == 0:
                return True, 0, 0, "ESLint: All checks passed"
            return False, 1, 0, result.stderr or result.stdout

    except subprocess.TimeoutExpired:
        return False, 0, 0, "ESLint: Timed out after 30s"
    except FileNotFoundError:
        return True, 0, 0, "ESLint not installed (skipped)"


def notify(title: str, message: str) -> None:
    """Send a desktop notification.

    Args:
        title: Notification title.
        message: Notification message.
    """
    if sys.platform == "darwin":
        subprocess.run(  # noqa: S603
            ["osascript", "-e", f'display notification "{message}" with title "{title}"'],  # noqa: S607
            capture_output=True,
            check=False,
            timeout=5,
        )


def detect_project_type(root: Path) -> ProjectType:
    """Detect project type from files.

    Args:
        root: Project root directory.

    Returns:
        Detected ProjectType.
    """
    # Check Claude Code plugin first (highest priority)
    if (root / ".claude-plugin" / "plugin.json").exists():
        return ProjectType.CLAUDE_PLUGIN

    # Check Python (pyproject.toml takes precedence)
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        return ProjectType.PYTHON

    # Then check JavaScript/TypeScript
    if (root / "package.json").exists():
        if (root / "next.config.ts").exists() or (root / "next.config.js").exists():
            return ProjectType.NEXTJS
        if (root / "tsconfig.json").exists():
            return ProjectType.TYPESCRIPT
        return ProjectType.JAVASCRIPT

    return ProjectType.UNKNOWN


def detect_project_version(root: Path) -> str:
    """Detect project version from package.json or pyproject.toml.

    Args:
        root: Project root directory.

    Returns:
        Version string or "0.0.0" if not found.

    Note:
        This is an alias for lib.version.get_version() for backwards compatibility.
    """
    from lib.version import get_version

    return get_version(root)
