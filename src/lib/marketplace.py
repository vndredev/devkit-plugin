"""Marketplace operations for Claude Code plugins.

TIER 1: May import from core only.
"""

import json
import subprocess
from pathlib import Path


# Default marketplace configuration
DEFAULT_MARKETPLACE_REPO = "claude-marketplace"
DEFAULT_MARKETPLACE_DIR = "claude-marketplace"


def get_github_username() -> str | None:
    """Get GitHub username from git remote or gh CLI.

    Auto-detects username in order:
    1. From git remote origin URL
    2. From gh CLI (gh api user)

    Returns:
        GitHub username or None if not available.
    """
    # Try git remote first
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        url = result.stdout.strip()
        # Parse username from URL formats:
        # https://github.com/username/repo.git
        # git@github.com:username/repo.git
        if "github.com" in url:
            if url.startswith("git@"):
                # git@github.com:username/repo.git
                parts = url.split(":")[1].split("/")
            else:
                # https://github.com/username/repo.git
                parts = url.replace("https://github.com/", "").split("/")
            if parts:
                return parts[0]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        pass

    # Fallback to gh CLI
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        username = result.stdout.strip()
        if username:
            return username
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        pass

    return None


def check_marketplace_repo_exists(username: str, repo_name: str = DEFAULT_MARKETPLACE_REPO) -> bool:
    """Check if marketplace repository exists on GitHub.

    Args:
        username: GitHub username.
        repo_name: Repository name (default: claude-marketplace).

    Returns:
        True if repo exists, False otherwise.
    """
    try:
        result = subprocess.run(
            ["gh", "repo", "view", f"{username}/{repo_name}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def create_marketplace_repo(
    username: str,
    repo_name: str = DEFAULT_MARKETPLACE_REPO,
    description: str = "Claude Code Plugin Marketplace",
) -> tuple[bool, str]:
    """Create marketplace repository on GitHub.

    Args:
        username: GitHub username.
        repo_name: Repository name (default: claude-marketplace).
        description: Repository description.

    Returns:
        Tuple of (success, message).
    """
    repo = f"{username}/{repo_name}"

    # Check if repo already exists
    if check_marketplace_repo_exists(username, repo_name):
        return True, f"Repository {repo} already exists"

    try:
        subprocess.run(
            [
                "gh",
                "repo",
                "create",
                repo,
                "--public",
                "--description",
                description,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return True, f"Created repository {repo}"
    except subprocess.CalledProcessError as e:
        stderr = e.stderr if e.stderr else str(e)
        return False, f"Failed to create {repo}: {stderr}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout creating {repo}"
    except OSError as e:
        return False, f"gh CLI error: {e}"


def get_marketplace_local_dir(username: str | None = None) -> Path:
    """Get local marketplace directory path.

    Args:
        username: GitHub username (optional, for backwards compatibility).

    Returns:
        Path to local marketplace directory.
    """
    # Use standardized path: ~/dev/claude-marketplace
    return Path.home() / "dev" / DEFAULT_MARKETPLACE_DIR


def rename_local_marketplace(
    old_dir: Path | str,
    new_dir: Path | str | None = None,
) -> tuple[bool, str]:
    """Rename local marketplace directory.

    Args:
        old_dir: Current marketplace directory path.
        new_dir: New marketplace directory path (default: ~/dev/claude-marketplace).

    Returns:
        Tuple of (success, message).
    """
    old_path = Path(old_dir).expanduser()
    new_path = Path(new_dir).expanduser() if new_dir else get_marketplace_local_dir()

    if not old_path.exists():
        return False, f"Source directory not found: {old_path}"

    if new_path.exists():
        return True, f"Target already exists: {new_path}"

    try:
        old_path.rename(new_path)
        return True, f"Renamed {old_path} -> {new_path}"
    except OSError as e:
        return False, f"Failed to rename: {e}"


def setup_marketplace(
    username: str | None = None,
    create_repo: bool = True,
    rename_local: bool = True,
    old_local_dir: str | None = None,
) -> list[tuple[str, bool, str]]:
    """Setup marketplace for Claude Code plugins.

    Orchestrates:
    1. Auto-detect GitHub username if not provided
    2. Create GitHub repository if requested
    3. Rename local marketplace directory if requested

    Args:
        username: GitHub username (auto-detected if None).
        create_repo: Whether to create GitHub repo.
        rename_local: Whether to rename local directory.
        old_local_dir: Old local directory path (for rename).

    Returns:
        List of (step, success, message) tuples.
    """
    results: list[tuple[str, bool, str]] = []

    # 1. Get/detect username
    if not username:
        username = get_github_username()
        if not username:
            results.append(("username", False, "Could not detect GitHub username"))
            return results

    results.append(("username", True, username))

    # 2. Create GitHub repo if requested
    if create_repo:
        success, msg = create_marketplace_repo(username)
        results.append(("github repo", success, msg))

    # 3. Rename local directory if requested
    if rename_local and old_local_dir:
        success, msg = rename_local_marketplace(old_local_dir)
        results.append(("local rename", success, msg))

    return results


def get_marketplace_config(username: str | None = None) -> dict:
    """Get marketplace configuration for config.jsonc.

    Args:
        username: GitHub username (auto-detected if None).

    Returns:
        Marketplace configuration dict.
    """
    if not username:
        username = get_github_username() or "unknown"

    return {
        "username": username,
        "repo_name": DEFAULT_MARKETPLACE_REPO,
        "local_dir": str(get_marketplace_local_dir()),
    }


def publish_plugin_to_marketplace(
    plugin_dir: Path,
    marketplace_dir: Path | None = None,
) -> tuple[bool, str]:
    """Publish a plugin to the local marketplace.

    Copies plugin to marketplace plugins directory.

    Args:
        plugin_dir: Path to plugin directory.
        marketplace_dir: Path to marketplace (default: ~/dev/claude-marketplace).

    Returns:
        Tuple of (success, message).
    """
    if marketplace_dir is None:
        marketplace_dir = get_marketplace_local_dir()

    plugins_dir = marketplace_dir / "plugins"

    # Read plugin.json to get plugin name
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        return False, f"Not a plugin: {plugin_dir} (missing .claude-plugin/plugin.json)"

    try:
        plugin_data = json.loads(plugin_json.read_text())
        plugin_name = plugin_data.get("name", plugin_dir.name)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Failed to read plugin.json: {e}"

    target_dir = plugins_dir / plugin_name
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy plugin files (simplified - in practice would use shutil.copytree)
    try:
        import shutil

        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(plugin_dir, target_dir, dirs_exist_ok=True)
        return True, f"Published {plugin_name} to {target_dir}"
    except OSError as e:
        return False, f"Failed to copy plugin: {e}"
