"""Configuration management.

TIER 1: May import from core only.

Supports JSONC (JSON with Comments) for config files.
"""

import json
import os
from pathlib import Path
from typing import Any

from core.errors import ConfigError
from core.jsonc import parse_jsonc

# Cache for loaded config (keyed by cwd to support multiple projects)
_config_cache: dict[Path, dict] = {}
_project_root_cache: dict[Path, Path] = {}

# Config file names (priority order)
CONFIG_FILES = ["config.jsonc", "config.json"]


def get_project_root() -> Path:
    """Get the project root directory.

    Looks for .claude/ directory or git root.
    Cache is keyed by cwd to support hooks running in different projects.

    Returns:
        Project root path.

    Raises:
        ConfigError: If project root cannot be found.
    """
    cwd = Path.cwd()

    # Check cache first (keyed by cwd)
    if cwd in _project_root_cache:
        return _project_root_cache[cwd]

    # Check environment variable
    if env_root := os.environ.get("PROJECT_ROOT"):
        result = Path(env_root)
        _project_root_cache[cwd] = result
        return result

    # Walk up from current directory
    current = cwd
    while current != current.parent:
        if (current / ".claude").exists():
            _project_root_cache[cwd] = current
            return current
        if (current / ".git").exists():
            _project_root_cache[cwd] = current
            return current
        current = current.parent

    raise ConfigError("Could not find project root (no .claude/ or .git/ found)")


def get_config_path() -> Path | None:
    """Find config file path.

    Looks for config.jsonc first, then config.json.

    Returns:
        Path to config file, or None if not found.
    """
    devkit_dir = get_project_root() / ".claude" / ".devkit"

    for filename in CONFIG_FILES:
        config_path = devkit_dir / filename
        if config_path.exists():
            return config_path

    return None


def load_config() -> dict:
    """Load config from .claude/.devkit/config.jsonc or config.json.

    Supports JSONC (JSON with Comments) format.
    Looks for config.jsonc first, falls back to config.json.
    Cache is keyed by cwd to support hooks running in different projects.

    Returns:
        Configuration dictionary.
    """
    cwd = Path.cwd()

    # Check cache first (keyed by cwd)
    if cwd in _config_cache:
        return _config_cache[cwd]

    config_path = get_config_path()

    if config_path is None:
        _config_cache[cwd] = {}
        return _config_cache[cwd]

    try:
        content = config_path.read_text()

        # Parse JSONC (strip comments and trailing commas)
        if config_path.suffix == ".jsonc":
            content = parse_jsonc(content)

        _config_cache[cwd] = json.loads(content)
        return _config_cache[cwd]
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid {config_path.name}: {e}") from e
    except UnicodeDecodeError as e:
        raise ConfigError(f"Cannot read {config_path.name}: encoding error - {e}") from e


def get(key: str, default: Any = None) -> Any:
    """Get config value by dot notation.

    Args:
        key: Dot-separated key path (e.g., "arch.layers").
        default: Default value if key not found.

    Returns:
        Config value or default.

    Example:
        get("project.name")  # Returns project name
        get("hooks.format.enabled", True)  # Returns True if not set
    """
    config = load_config()
    parts = key.split(".")

    value = config
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default

    return value


def clear_cache() -> None:
    """Clear config cache (for testing)."""
    global _config_cache, _project_root_cache
    _config_cache.clear()
    _project_root_cache.clear()


# Recommended defaults for optional config sections
# These are added when running /dk plugin update on older configs
RECOMMENDED_DEFAULTS = {
    # === Session Hook ===
    "hooks.session.prompts": {
        "branch": "📍 {branch}",
        "staged": "⚡{count} staged",
        "modified": "✏️{count} modified",
        "untracked": "❓{count} untracked",
        "hint": "Use `/dk` for commands, `/dk dev` for workflow",
        "system_warning": "⚠️ Project has issues - check with /dk plugin check",
    },
    # === Validate Hook ===
    "hooks.validate.prompts": {
        "branch_invalid": "Branch '{branch}' should match: {pattern}",
        "commit_invalid": "Commit should match: type(scope): message (types: {types})",
        "scope_invalid": "Unknown scope '{scope}'. Allowed: {allowed}",
        "force_push_blocked": "Force push is blocked. Use --force-with-lease if needed.",
        "gh_blocked": "Blocked: '{cmd}' - too dangerous for automatic execution",
        "pr_missing_body": "gh pr create requires --body with PR template",
    },
    # === Format Hook ===
    "hooks.format.arch_check": True,
    "hooks.format.auto_sync_arch": True,
    "hooks.format.prompts": {
        "formatted": "✓ Formatted: {file}",
        "test_reminder": "💡 New file - consider adding: tests/{file}",
        "arch_violation": "⚠️ Arch violation: {message}",
        "arch_synced": "📄 Updated docs/ARCHITECTURE.md",
    },
    # === Plan Hook ===
    "hooks.plan.planning": {
        "requirements": [
            "Identify affected layers (check arch.layers)",
            "List files to modify vs. create",
            "Consider edge cases and error handling",
            "Check for breaking changes",
        ],
        "structure": [
            "## Overview - What and why",
            "## Affected Files - List with rationale",
            "## Implementation Steps - Ordered tasks",
            "## Testing Strategy - How to verify",
            "## Risks - What could go wrong",
        ],
    },
    "hooks.plan.implementation": {
        "header": "## Implementation Phase",
        "instructions": [
            "Complete one task at a time, mark done in todo list",
            "Run linters after code changes",
            "Run tests if available",
            "Use conventional commits: type(scope): message",
            "Ask if blocked or unclear",
        ],
    },
    "hooks.plan.hints": [
        "Respect layer boundaries if arch.layers is configured",
        "New modules should have corresponding tests",
        "Public API changes need CHANGELOG consideration",
    ],
    # === Git Conventions ===
    "git.conventions": {
        "types": ["feat", "fix", "chore", "refactor", "test", "docs", "perf", "ci"],
        "scopes": {
            "mode": "strict",
            "allowed": [],
            "internal": ["internal", "review", "ci", "deps"],
        },
        "branch_pattern": "{type}/{description}",
    },
}

# Standard managed entries that should exist in all projects
# These are added by upgrade_config() if missing
MANAGED_DEFAULTS = {
    "github": {
        ".github/workflows/claude.yml": {
            "template": "github/workflows/claude.yml.template",
            "enabled": True,
        },
        ".github/workflows/claude-code-review.yml": {
            "template": "github/workflows/claude-code-review.yml.template",
            "enabled": True,
        },
        ".github/ISSUE_TEMPLATE/bug_report.yml": {
            "template": "github/ISSUE_TEMPLATE/bug_report.yml.template",
            "enabled": True,
        },
        ".github/ISSUE_TEMPLATE/feature_request.yml": {
            "template": "github/ISSUE_TEMPLATE/feature_request.yml.template",
            "enabled": True,
        },
        ".github/ISSUE_TEMPLATE/config.yml": {
            "template": "github/ISSUE_TEMPLATE/config.yml.template",
            "enabled": True,
        },
        ".github/PULL_REQUEST_TEMPLATE.md": {
            "template": "github/PULL_REQUEST_TEMPLATE.md.template",
            "enabled": True,
        },
    },
    "linters": {
        ".markdownlint.json": {
            "template": "linters/common/markdownlint.json.template",
            "enabled": True,
        },
        ".markdownlintignore": {
            "template": "gitignore/markdownlint.ignore",
            "enabled": True,
        },
    },
    "docs": {
        "CLAUDE.md": {"type": "auto_sections", "enabled": True},
        "README.md": {"type": "auto_sections", "enabled": True},
    },
}


def get_missing_sections() -> list[str]:
    """Check which recommended config sections are missing.

    Returns:
        List of missing section paths (dot notation).
    """
    config = load_config()
    missing = []

    for key_path in RECOMMENDED_DEFAULTS:
        # Navigate to the parent and check if key exists
        parts = key_path.split(".")
        current = config

        found = True
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found = False
                break

        if not found:
            missing.append(key_path)

    return missing


def _set_nested(config: dict, key_path: str, value: Any) -> None:
    """Set a nested value in config using dot notation."""
    parts = key_path.split(".")
    current = config

    # Navigate/create path to parent
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the value
    current[parts[-1]] = value


def get_missing_managed_entries() -> dict[str, list[str]]:
    """Check which standard managed entries are missing.

    Returns:
        Dict of {category: [missing_entry_paths]}.
    """
    config = load_config()
    managed = config.get("managed", {})
    missing: dict[str, list[str]] = {}

    for category, default_entries in MANAGED_DEFAULTS.items():
        current_entries = managed.get(category, {})
        for entry_path in default_entries:
            if entry_path not in current_entries:
                if category not in missing:
                    missing[category] = []
                missing[category].append(entry_path)

    return missing


def upgrade_config() -> tuple[bool, list[str]]:
    """Add missing recommended sections and managed entries to config.

    Modifies config.jsonc in place, preserving comments where possible.

    Returns:
        Tuple of (success, list of added items).
    """
    config_path = get_config_path()
    if config_path is None:
        return False, ["No config file found"]

    # Load current config
    config = load_config()
    added = []

    # Add missing sections
    missing_sections = get_missing_sections()
    for key_path in missing_sections:
        if key_path in RECOMMENDED_DEFAULTS:
            _set_nested(config, key_path, RECOMMENDED_DEFAULTS[key_path])
            added.append(key_path)

    # Add missing managed entries
    missing_managed = get_missing_managed_entries()
    if missing_managed:
        if "managed" not in config:
            config["managed"] = {}

        for category, entries in missing_managed.items():
            if category not in config["managed"]:
                config["managed"][category] = {}

            for entry_path in entries:
                config["managed"][category][entry_path] = MANAGED_DEFAULTS[category][entry_path]
                added.append(f"managed.{category}.{entry_path}")

    if not added:
        return True, []

    # Write back with comments
    try:
        _write_config_with_comments(config_path, config)
        clear_cache()  # Clear cache to reload
        return True, added
    except OSError as e:
        return False, [f"Failed to write config: {e}"]


# Section definitions with descriptions (for .jsonc files)
_SECTIONS = {
    "project": {
        "header": "IDENTITY - Project information",
        "desc": "name, type, version, slogan, description, principles",
    },
    "git": {
        "header": "DEVELOPMENT - Git configuration",
        "desc": "protected_branches, conventions (types, scopes, branch_pattern)",
    },
    "github": {
        "header": "DEVELOPMENT - GitHub configuration",
        "desc": "url, visibility, pr settings (auto_merge, delete_branch, merge_method)",
    },
    "linters": {
        "header": "QUALITY - Linters configuration",
        "desc": "preset (strict|relaxed|minimal), overrides",
    },
    "testing": {
        "header": "QUALITY - Testing configuration",
        "desc": "enabled, framework (pytest|vitest|jest), coverage, required_modules",
    },
    "hooks": {
        "header": "AUTOMATION - Claude Code hooks",
        "desc": "session, validate, format, plan - customize prompts and behavior",
    },
    "changelog": {
        "header": "AUTOMATION - Changelog generation",
        "desc": "audience (developer|user) - controls detail level",
    },
    "deployment": {
        "header": "DEPLOYMENT - Platform configuration",
        "desc": "platform (vercel|railway|etc), env_sync, production_domain",
    },
    "arch": {
        "header": "ARCHITECTURE - Clean Architecture layers",
        "desc": "layers with tier (0=innermost), patterns, description",
    },
    "logging": {
        "header": "OBSERVABILITY - Logging service configuration",
        "desc": "providers (axiom|sentry|logrocket|datadog|pino|winston)",
    },
    "managed": {
        "header": "MANAGED FILES - Auto-generated by /dk plugin update",
        "desc": "linters, github, docs, ignore - set enabled:false to skip",
    },
}

# Hook sub-section comments
_HOOK_COMMENTS = {
    "session": "SessionStart - shows git status, project info",
    "validate": "PreToolUse:Bash - validates git/gh commands",
    "format": "PostToolUse:Write/Edit - auto-format, arch check",
    "plan": "PostToolUse:ExitPlanMode - planning and implementation guidance",
}

# Section order for config file
_SECTION_ORDER = [
    "project",
    "git",
    "github",
    "linters",
    "testing",
    "hooks",
    "changelog",
    "deployment",
    "arch",
    "logging",
    "managed",
]


def _format_section_header(key: str) -> list[str]:
    """Format section header with comment block.

    Args:
        key: Section key name.

    Returns:
        List of header lines.
    """
    info = _SECTIONS.get(key, {"header": key.upper(), "desc": ""})
    lines = [
        f"  // {'=' * 70}",
        f"  // {info['header']}",
    ]
    if info["desc"]:
        lines.append(f"  // {info['desc']}")
    lines.append(f"  // {'=' * 70}")
    return lines


def _format_hooks_section(hooks_data: dict[str, Any]) -> list[str]:
    """Format hooks section with sub-comments.

    Args:
        hooks_data: Hooks configuration dict.

    Returns:
        List of formatted lines.
    """
    lines = ['  "hooks": {']
    hook_items = list(hooks_data.items())

    for i, (hook_name, hook_value) in enumerate(hook_items):
        comment = _HOOK_COMMENTS.get(hook_name, "")
        if comment:
            lines.append(f"    // === {comment} ===")

        hook_json = json.dumps(hook_value, indent=2)
        hook_lines = hook_json.split("\n")
        lines.append(f'    "{hook_name}": {hook_lines[0]}')
        lines.extend(f"    {hl}" for hl in hook_lines[1:])

        if i < len(hook_items) - 1:
            lines[-1] = lines[-1].rstrip() + ","
        lines.append("")

    if lines[-1] == "":
        lines.pop()
    lines.append("  },")
    return lines


def _format_standard_section(key: str, value: Any) -> list[str]:
    """Format a standard (non-hooks) section.

    Args:
        key: Section key name.
        value: Section value.

    Returns:
        List of formatted lines.
    """
    section_json = json.dumps({key: value}, indent=2)
    lines = section_json.split("\n")[1:-1]
    if lines and lines[-1].rstrip().endswith("}"):
        lines[-1] = lines[-1].rstrip() + ","
    return lines


def _remove_trailing_comma(lines: list[str]) -> None:
    """Remove trailing comma from last non-empty line.

    Args:
        lines: List of lines to modify in place.
    """
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            lines[i] = lines[i].rstrip().rstrip(",")
            break


def _build_config_lines(config: dict[str, Any]) -> list[str]:
    """Build JSONC config lines with comments.

    Args:
        config: Configuration dict.

    Returns:
        List of formatted lines.
    """
    lines = ["{", '  "$schema": "./config.schema.json",', ""]
    written_keys = {"$schema"}

    for key in _SECTION_ORDER:
        if key not in config:
            continue

        lines.extend(_format_section_header(key))

        if key == "hooks" and isinstance(config[key], dict):
            lines.extend(_format_hooks_section(config[key]))
        else:
            lines.extend(_format_standard_section(key, config[key]))

        lines.append("")
        written_keys.add(key)

    # Write any remaining keys not in our order
    for key, value in config.items():
        if key in written_keys:
            continue
        lines.extend(_format_standard_section(key, value))
        lines.append("")

    _remove_trailing_comma(lines)
    lines.append("}")
    return lines


def _write_config_with_comments(config_path: Path, config: dict[str, Any]) -> None:
    """Write config back with section comments.

    For .json files, writes plain JSON without comments.
    For .jsonc files, writes with section comments.

    Args:
        config_path: Path to config file.
        config: Configuration dict to write.
    """
    if config_path.suffix == ".json":
        config_path.write_text(json.dumps(config, indent=2))
        return

    lines = _build_config_lines(config)
    config_path.write_text("\n".join(lines))
