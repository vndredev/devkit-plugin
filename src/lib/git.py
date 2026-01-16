"""Git operations.

TIER 1: May import from core only.
"""

import subprocess
from pathlib import Path

from core.errors import GitError


def run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command.

    Args:
        args: Git command arguments.
        cwd: Working directory (defaults to current).

    Returns:
        Command output.

    Raises:
        GitError: If command fails.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"git {' '.join(args)} failed: {e.stderr}") from e


def git_status(cwd: Path | None = None) -> dict[str, list[str]]:
    """Get git status.

    Args:
        cwd: Working directory (defaults to current).

    Returns:
        Dict with 'staged', 'modified', 'untracked' file lists.
    """
    output = run_git(["status", "--porcelain"], cwd=cwd)
    result: dict[str, list[str]] = {
        "staged": [],
        "modified": [],
        "untracked": [],
    }

    for line in output.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        filepath = line[3:].strip()

        if status[0] in "MADRC":
            result["staged"].append(filepath)
        if status[1] == "M":
            result["modified"].append(filepath)
        if status == "??":
            result["untracked"].append(filepath)

    return result


def git_branch(cwd: Path | None = None) -> str:
    """Get current branch name.

    Args:
        cwd: Working directory (defaults to current).

    Returns:
        Branch name.
    """
    return run_git(["branch", "--show-current"], cwd=cwd)


def git_commit(message: str, co_author: str | None = None) -> tuple[bool, str]:
    """Create a commit.

    Args:
        message: Commit message.
        co_author: Optional co-author line.

    Returns:
        Tuple of (success, message).
    """
    if co_author:
        message = f"{message}\n\nCo-Authored-By: {co_author}"

    try:
        run_git(["commit", "-m", message])
        return True, "Commit created"
    except GitError as e:
        return False, str(e)


def is_protected_branch(protected: list[str] | None = None) -> bool:
    """Check if current branch is protected.

    Args:
        protected: List of protected branch names.

    Returns:
        True if current branch is protected.
    """
    if protected is None:
        protected = ["main"]  # Matches schema default

    current = git_branch()
    return current in protected


def extract_git_args(cmd: str) -> tuple[str, list[str]]:
    """Extract git subcommand and args from command string.

    Args:
        cmd: Full command string.

    Returns:
        Tuple of (subcommand, args).
    """
    parts = cmd.split()
    if len(parts) < 2 or parts[0] != "git":
        return "", []

    return parts[1], parts[2:]
