"""Version management - keeps all version entries in sync.

TIER 1: May import from core only.
"""

import json
import re
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


def get_commit_version(root: Path | None = None) -> str:
    """Get version with commit ID suffix for cache invalidation.

    Format: {base_version}-{short_commit_id}
    Example: 0.18.1-fb8ca3d

    Args:
        root: Project root directory. Defaults to current directory.

    Returns:
        Version string with commit suffix, or base version if git fails.
    """
    if root is None:
        root = Path.cwd()

    base_version = get_version(root)

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_id = result.stdout.strip()
        return f"{base_version}-{commit_id}"
    except (subprocess.SubprocessError, OSError):
        return base_version


def update_plugin_version(root: Path | None = None) -> tuple[bool, str]:
    """Update plugin.json version with commit ID for cache invalidation.

    Also updates the local marketplace.json if configured.

    Args:
        root: Plugin root directory. Defaults to current directory.

    Returns:
        Tuple of (success, message).
    """
    if root is None:
        root = Path.cwd()

    plugin_json = root / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        return False, "plugin.json not found"

    commit_version = get_commit_version(root)

    try:
        content = plugin_json.read_text()
        data = json.loads(content)
        plugin_name = data.get("name", "")
        old_version = data.get("version", "unknown")

        # Always sync marketplace, even if plugin.json unchanged
        _update_local_marketplace(plugin_name, commit_version)

        if old_version == commit_version:
            return True, f"already {commit_version}"

        data["version"] = commit_version
        plugin_json.write_text(json.dumps(data, indent=2) + "\n")

        return True, f"{old_version} -> {commit_version}"
    except (json.JSONDecodeError, OSError) as e:
        return False, f"failed: {e}"


def _update_local_marketplace(plugin_name: str, version: str) -> None:
    """Update version in local marketplace.json if found.

    Finds local directory-based marketplaces and updates the plugin version.

    Args:
        plugin_name: Name of the plugin to update.
        version: New version string.
    """
    known_marketplaces = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
    if not known_marketplaces.exists():
        return

    try:
        marketplaces = json.loads(known_marketplaces.read_text())

        for marketplace in marketplaces.values():
            source = marketplace.get("source", {})
            # Only process local directory marketplaces
            if source.get("source") != "directory":
                continue

            marketplace_path = Path(source.get("path", ""))
            marketplace_json = marketplace_path / ".claude-plugin" / "marketplace.json"

            if not marketplace_json.exists():
                continue

            # Update plugin version in marketplace
            mp_data = json.loads(marketplace_json.read_text())
            plugins = mp_data.get("plugins", [])

            for plugin in plugins:
                if plugin.get("name") == plugin_name:
                    plugin["version"] = version
                    marketplace_json.write_text(json.dumps(mp_data, indent=2) + "\n")
                    break
    except (json.JSONDecodeError, OSError):
        pass  # Silently ignore marketplace update errors
