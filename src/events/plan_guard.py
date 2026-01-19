#!/usr/bin/env python3
"""PreToolUse hook - blocks edits on feat/refactor until plan approved.

TIER 3: events layer.
"""

import re
from pathlib import Path

from lib.config import get
from lib.git import git_branch
from lib.hooks import allow_response, deny_response, read_hook_input

PLAN_REQUIRED_PATTERNS = [r"^feat/", r"^refactor/"]

# Paths that are always allowed (plan files, etc.)
ALWAYS_ALLOWED_PATHS = [
    Path.home() / ".claude" / "plans",
]


def is_allowed_path(file_path: str | None) -> bool:
    """Check if file path is in always-allowed directories.

    Args:
        file_path: Path to the file being edited.

    Returns:
        True if path is in an always-allowed directory.
    """
    if not file_path:
        return False

    try:
        path = Path(file_path).resolve()
        for allowed in ALWAYS_ALLOWED_PATHS:
            allowed_resolved = allowed.resolve()
            if path == allowed_resolved or allowed_resolved in path.parents:
                return True
    except (OSError, ValueError):
        pass

    return False


def get_plan_marker_path(branch: str) -> Path:
    """Get marker file path for branch.

    Args:
        branch: Git branch name.

    Returns:
        Path to marker file.
    """
    project_dir = Path.cwd()
    sanitized = branch.replace("/", "-")
    return project_dir / ".claude" / f".plan-approved-{sanitized}"


def is_plan_required_branch(branch: str) -> bool:
    """Check if branch requires plan mode.

    Args:
        branch: Git branch name.

    Returns:
        True if branch matches feat/* or refactor/*.
    """
    return any(re.match(p, branch) for p in PLAN_REQUIRED_PATTERNS)


def is_plan_approved(branch: str) -> bool:
    """Check if plan marker exists.

    Args:
        branch: Git branch name.

    Returns:
        True if plan was approved (marker exists).
    """
    marker = get_plan_marker_path(branch)
    return marker.exists()


def main() -> None:
    """Handle PreToolUse hook for Edit/Write - Plan Guard."""
    hook_data = read_hook_input()
    if not hook_data or not get("hooks.plan_guard.enabled", True):
        allow_response()
        return

    # Allow writes to plan files (outside project)
    tool_input = hook_data.get("tool_input", {})
    file_path = tool_input.get("file_path")
    if is_allowed_path(file_path):
        allow_response()
        return

    try:
        branch = git_branch()
    except Exception:
        # Fail-open on git errors
        allow_response()
        return

    if not is_plan_required_branch(branch) or is_plan_approved(branch):
        allow_response()
        return

    msg = get(
        "hooks.plan_guard.prompts.blocked",
        "🚫 BLOCKED: On `{branch}` - complete planning first.\n\n"
        "Run `EnterPlanMode` → create plan → `ExitPlanMode` to approve.",
    ).format(branch=branch)

    deny_response(msg)


if __name__ == "__main__":
    import json
    import sys

    try:
        main()
    except Exception as e:
        # On error, allow but report
        print(json.dumps({"continue": True, "message": f"⚠️ Plan guard error: {e}"}))
        sys.exit(0)
