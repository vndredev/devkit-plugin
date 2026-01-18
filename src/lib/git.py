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
            timeout=30,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired as e:
        raise GitError(f"git {' '.join(args)} timed out after 30s") from e
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

        # First byte: index/staged status (MADRC = staged changes)
        if status[0] in "MADRC":
            result["staged"].append(filepath)
        # Second byte: working tree status (M=modified, D=deleted, T=type changed)
        if status[1] in "MDT":
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


def git_add(files: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    """Stage files for commit.

    Args:
        files: List of file paths to stage.
        cwd: Working directory (defaults to current).

    Returns:
        Tuple of (success, message).
    """
    if not files:
        return False, "No files to stage"

    try:
        run_git(["add", *files], cwd=cwd)
        return True, f"Staged {len(files)} file(s)"
    except GitError as e:
        return False, str(e)


def git_commit(
    message: str, co_author: str | None = None, cwd: Path | None = None
) -> tuple[bool, str]:
    """Create a commit.

    Args:
        message: Commit message.
        co_author: Optional co-author line.
        cwd: Working directory (defaults to current).

    Returns:
        Tuple of (success, message).
    """
    if co_author:
        message = f"{message}\n\nCo-Authored-By: {co_author}"

    try:
        run_git(["commit", "-m", message], cwd=cwd)
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


def get_remote_url(cwd: Path | None = None) -> str | None:
    """Get the origin remote URL.

    Args:
        cwd: Working directory (defaults to current).

    Returns:
        Remote URL or None if not found.
    """
    try:
        return run_git(["remote", "get-url", "origin"], cwd=cwd)
    except GitError:
        return None


def is_https_remote(cwd: Path | None = None) -> bool:
    """Check if origin remote uses HTTPS.

    Args:
        cwd: Working directory (defaults to current).

    Returns:
        True if remote uses HTTPS protocol.
    """
    url = get_remote_url(cwd)
    return url is not None and url.startswith("https://")


def has_workflow_files(cwd: Path | None = None) -> bool:
    """Check if repo has GitHub workflow files.

    Args:
        cwd: Working directory (defaults to current).

    Returns:
        True if .github/workflows/ contains .yml files.
    """
    workflows_dir = (cwd or Path.cwd()) / ".github" / "workflows"
    if not workflows_dir.exists():
        return False
    return any(workflows_dir.glob("*.yml")) or any(workflows_dir.glob("*.yaml"))


def check_https_with_workflows(cwd: Path | None = None) -> bool:
    """Check if HTTPS is used with workflow files.

    This combination causes issues when pushing workflow changes,
    as OAuth tokens don't have workflow scope.

    Args:
        cwd: Working directory (defaults to current).

    Returns:
        True if HTTPS remote AND workflow files exist (problematic).
    """
    return is_https_remote(cwd) and has_workflow_files(cwd)
