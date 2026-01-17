"""Version management - keeps all version entries in sync.

TIER 1: May import from core only.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import tomllib


def get_version(root: Path | None = None) -> str:
    """Get current version from project files.

    Checks in order of priority:
    1. pyproject.toml (Python projects)
    2. package.json (Node.js projects)
    3. .claude-plugin/plugin.json (Claude plugins)

    Args:
        root: Project root directory. Defaults to current directory.

    Returns:
        Version string or "0.0.0" if not found in any source.
    """
    if root is None:
        root = Path.cwd()

    # 1. Try pyproject.toml (Python projects)
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
            version = data.get("project", {}).get("version")
            if version:
                return version
        except (tomllib.TOMLDecodeError, OSError):
            pass

    # 2. Try package.json (Node.js projects)
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            version = data.get("version")
            if version:
                return version
        except (json.JSONDecodeError, OSError):
            pass

    # 3. Try plugin.json (Claude plugins)
    plugin_json = root / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        try:
            data = json.loads(plugin_json.read_text())
            version = data.get("version", "").split("-")[0]  # Strip commit suffix
            if version:
                return version
        except (json.JSONDecodeError, OSError):
            pass

    return "0.0.0"


def sync_versions(
    root: Path | None = None, version: str | None = None
) -> list[tuple[str, bool, str]]:
    """Sync version across all project files.

    Updates version in:
    - .claude/.devkit/config.jsonc (project.version)
    - package.json (version)
    - .claude-plugin/plugin.json (version)

    Args:
        root: Project root directory. Defaults to current directory.
        version: Version to set. If None, reads from pyproject.toml.

    Returns:
        List of (file_path, success, message) tuples.
    """
    if root is None:
        root = Path.cwd()

    if version is None:
        version = get_version(root)

    results: list[tuple[str, bool, str]] = []

    # Files to update with their JSON paths
    version_files = [
        (root / ".claude" / ".devkit" / "config.jsonc", ["project", "version"]),
        (root / "package.json", ["version"]),
        (root / ".claude-plugin" / "plugin.json", ["version"]),
    ]

    for file_path, json_path in version_files:
        rel_path = str(file_path.relative_to(root))

        if not file_path.exists():
            results.append((rel_path, True, "skipped (not found)"))
            continue

        try:
            result = _update_json_version(file_path, json_path, version)
            results.append((rel_path, True, result))
        except (json.JSONDecodeError, OSError) as e:
            results.append((rel_path, False, f"failed: {e}"))

    return results


def _update_json_version(file_path: Path, json_path: list[str], version: str) -> str:
    """Update version in a JSON/JSONC file.

    Args:
        file_path: Path to JSON file.
        json_path: Path to version field (e.g., ["project", "version"]).
        version: New version string.

    Returns:
        Result message.
    """
    content = file_path.read_text()

    # For JSONC files, we need to preserve comments
    # Use regex replacement instead of JSON parsing
    if file_path.suffix == ".jsonc" or "config.jsonc" in file_path.name:
        return _update_jsonc_version(file_path, content, json_path, version)

    # For regular JSON, parse and update
    data = json.loads(content)
    old_version = _get_nested(data, json_path)

    if old_version == version:
        return f"already {version}"

    _set_nested(data, json_path, version)

    # Preserve formatting (2-space indent)
    file_path.write_text(json.dumps(data, indent=2) + "\n")
    return f"{old_version} -> {version}"


def _update_jsonc_version(file_path: Path, content: str, json_path: list[str], version: str) -> str:
    """Update version in a JSONC file preserving comments.

    Args:
        file_path: Path to JSONC file.
        content: File content.
        json_path: Path to version field.
        version: New version string.

    Returns:
        Result message.
    """
    # Build regex pattern for the specific JSON path
    if json_path == ["project", "version"]:
        # Match: "version": "x.y.z" within "project" block
        pattern = r'("project"\s*:\s*\{[^}]*"version"\s*:\s*")([^"]+)(")'
    elif json_path == ["version"]:
        # Match top-level "version": "x.y.z"
        pattern = r'^(\s*"version"\s*:\s*")([^"]+)(")'
    else:
        # Generic pattern for other paths
        key = json_path[-1]
        pattern = rf'("{key}"\s*:\s*")([^"]+)(")'

    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if not match:
        return f"version field not found at {'.'.join(json_path)}"

    old_version = match.group(2)
    if old_version == version:
        return f"already {version}"

    # Replace version
    new_content = content[: match.start(2)] + version + content[match.end(2) :]
    file_path.write_text(new_content)

    return f"{old_version} -> {version}"


def _get_nested(data: dict, path: list[str]) -> str | None:
    """Get nested value from dict."""
    for key in path:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data if isinstance(data, str) else None


def _set_nested(data: dict, path: list[str], value: str) -> None:
    """Set nested value in dict."""
    for key in path[:-1]:
        if key not in data:
            data[key] = {}
        data = data[key]
    data[path[-1]] = value


# Plugin cache management
PLUGIN_REPO = "vndredev/devkit-plugin"
DEFAULT_MARKETPLACE = "claude-marketplace"


def get_cache_base(
    marketplace_name: str = DEFAULT_MARKETPLACE, plugin_name: str = "devkit-plugin"
) -> Path:
    """Get plugin cache base directory.

    Args:
        marketplace_name: Marketplace directory name (default: claude-marketplace).
        plugin_name: Plugin name.

    Returns:
        Path to cache directory.
    """
    return Path.home() / ".claude" / "plugins" / "cache" / marketplace_name / plugin_name


# Default cache path (backwards compatible)
CACHE_BASE = get_cache_base()


def get_latest_github_version(repo: str = PLUGIN_REPO) -> str | None:
    """Get the latest release version from GitHub.

    Args:
        repo: GitHub repo in format owner/repo.

    Returns:
        Version string (e.g., "0.24.0") or None if not available.
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"/repos/{repo}/releases/latest", "--jq", ".tag_name"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        tag = result.stdout.strip()
        # Remove 'v' prefix if present
        return tag.lstrip("v") if tag else None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None


def get_cached_plugin_version() -> str | None:
    """Get the currently cached plugin version.

    Returns:
        Version string or None if no cache exists.
    """
    if not CACHE_BASE.exists():
        return None

    # Find version directories (e.g., "0.23.2")
    versions = [
        d.name for d in CACHE_BASE.iterdir() if d.is_dir() and re.match(r"^\d+\.\d+\.\d+", d.name)
    ]
    if not versions:
        return None

    # Return highest version (semver sort)
    versions.sort(key=lambda v: [int(x) for x in v.split(".")[:3]])
    return versions[-1]


def clear_plugin_cache() -> tuple[bool, str]:
    """Clear the plugin cache to force re-download.

    Returns:
        Tuple of (success, message).
    """
    if not CACHE_BASE.exists():
        return True, "No cache to clear"

    try:
        shutil.rmtree(CACHE_BASE)
        return True, "Cache cleared"
    except OSError as e:
        return False, f"Failed to clear cache: {e}"


def check_plugin_update() -> tuple[bool, str | None, str | None]:
    """Check if a plugin update is available.

    Returns:
        Tuple of (update_available, current_version, latest_version).
    """
    current = get_cached_plugin_version()
    latest = get_latest_github_version()

    if not latest:
        return False, current, None

    if not current:
        return True, None, latest

    # Compare versions (semver)
    try:
        current_parts = [int(x) for x in current.split(".")[:3]]
        latest_parts = [int(x) for x in latest.split(".")[:3]]
        return latest_parts > current_parts, current, latest
    except ValueError:
        return False, current, latest


def auto_update_plugin() -> list[tuple[str, bool, str]]:
    """Check for updates and clear cache if new version available.

    Returns:
        List of (step, success, message) tuples.
    """
    results: list[tuple[str, bool, str]] = []

    update_available, current, latest = check_plugin_update()

    if not latest:
        results.append(("version check", True, "Could not check GitHub (offline?)"))
        return results

    if not update_available:
        results.append(("plugin version", True, f"{current} (up to date)"))
        return results

    # Update available - clear cache
    current_display = current or "not cached"
    results.append(("plugin update", True, f"{current_display} → {latest}"))

    success, msg = clear_plugin_cache()
    if success:
        results.append(("cache cleared", True, "Restart session to load new version"))
    else:
        results.append(("cache clear", False, msg))

    return results


# Dev mode - for plugin developers working on the plugin itself
PLUGIN_NAME = "devkit-plugin"


def is_plugin_dev_mode(project_dir: Path | None = None) -> bool:
    """Check if current project is the plugin itself (dev mode).

    Detects dev mode by checking:
    1. Project name is "devkit-plugin"
    2. Has .claude-plugin/plugin.json with matching name

    Args:
        project_dir: Project directory to check. Defaults to cwd.

    Returns:
        True if in plugin dev mode.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    # Check plugin.json
    plugin_json = project_dir / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        return False

    try:
        import json

        data = json.loads(plugin_json.read_text())
        return data.get("name") == PLUGIN_NAME
    except (json.JSONDecodeError, OSError):
        return False


def get_dev_mode_cache_path(version: str) -> Path:
    """Get the cache path where symlink should point.

    Args:
        version: Plugin version.

    Returns:
        Path to version directory in cache.
    """
    return CACHE_BASE / version


def is_dev_mode_active(project_dir: Path | None = None) -> bool:
    """Check if dev mode symlink is already active.

    Args:
        project_dir: Project directory. Defaults to cwd.

    Returns:
        True if cache points to project directory via symlink.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    version = get_version(project_dir)
    cache_path = get_dev_mode_cache_path(version)

    # Check if it's a symlink pointing to project dir
    if cache_path.is_symlink():
        try:
            target = cache_path.resolve()
            return target == project_dir.resolve()
        except OSError:
            return False

    return False


def setup_dev_mode(project_dir: Path | None = None) -> tuple[bool, str]:
    """Setup dev mode by creating symlink from cache to project.

    This allows changes to the plugin code to take effect immediately
    after restarting the Claude Code session.

    Args:
        project_dir: Project directory. Defaults to cwd.

    Returns:
        Tuple of (success, message).
    """
    if project_dir is None:
        project_dir = Path.cwd()

    # Verify we're in the plugin directory
    if not is_plugin_dev_mode(project_dir):
        return False, "Not in plugin directory"

    version = get_version(project_dir)
    cache_path = get_dev_mode_cache_path(version)

    # Already setup?
    if is_dev_mode_active(project_dir):
        return True, f"Dev mode active ({version})"

    # Ensure parent directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing cache (file or directory)
    if cache_path.exists() or cache_path.is_symlink():
        try:
            if cache_path.is_symlink() or cache_path.is_file():
                cache_path.unlink()
            else:
                shutil.rmtree(cache_path)
        except OSError as e:
            return False, f"Failed to remove existing cache: {e}"

    # Create symlink
    try:
        cache_path.symlink_to(project_dir.resolve())
        return True, f"Dev mode enabled ({version})"
    except OSError as e:
        return False, f"Failed to create symlink: {e}"


def ensure_dev_mode(project_dir: Path | None = None) -> tuple[bool, str] | None:
    """Ensure dev mode indicator is shown if in plugin directory.

    Called automatically during SessionStart. Returns dev mode indicator
    if the current project is the plugin itself (regardless of how it's loaded).

    Args:
        project_dir: Project directory. Defaults to cwd.

    Returns:
        Tuple of (success, message) if in plugin directory, None otherwise.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    # Show dev indicator if we're in the plugin directory
    if is_plugin_dev_mode(project_dir):
        return True, "dev"

    return None


def is_project_a_plugin(project_dir: Path | None = None) -> bool:
    """Check if the project is a Claude Code plugin.

    Args:
        project_dir: Project directory. Defaults to cwd.

    Returns:
        True if project has .claude-plugin/plugin.json.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    return (project_dir / ".claude-plugin" / "plugin.json").exists()


def is_plugin_loaded_via_plugin_dir(project_dir: Path | None = None) -> bool:
    """Check if the current project is loaded via --plugin-dir.

    This checks if CLAUDE_PLUGIN_ROOT matches the project directory,
    which indicates the project is being tested as a plugin.

    Args:
        project_dir: Project directory. Defaults to cwd.

    Returns:
        True if project is loaded via --plugin-dir.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not plugin_root:
        return False

    try:
        return Path(plugin_root).resolve() == project_dir.resolve()
    except OSError:
        return False


def get_plugin_dev_recommendation(project_dir: Path | None = None) -> str | None:
    """Get recommendation for plugin development if applicable.

    Returns a recommendation message if:
    - Project is a Claude Code plugin
    - Project is NOT loaded via --plugin-dir

    Args:
        project_dir: Project directory. Defaults to cwd.

    Returns:
        Recommendation message or None if not applicable.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    # Not a plugin project
    if not is_project_a_plugin(project_dir):
        return None

    # Already loaded via --plugin-dir
    if is_plugin_loaded_via_plugin_dir(project_dir):
        return None

    # Recommend --plugin-dir for live testing
    return f"claude --plugin-dir {project_dir}"
