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
        )
        return True, f"Formatted {filepath.name}"
    except subprocess.CalledProcessError as e:
        return False, f"Format failed: {e.stderr.decode() if e.stderr else str(e)}"
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
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
        if result.returncode == 0:
            return True, f"{name}: All checks passed"
        return False, result.stdout + result.stderr
    except FileNotFoundError:
        return False, f"Linter not found: {name}"


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
        )


def detect_project_type(root: Path) -> ProjectType:
    """Detect project type from files.

    Args:
        root: Project root directory.

    Returns:
        Detected ProjectType.
    """
    # Check Python first (pyproject.toml takes precedence)
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
