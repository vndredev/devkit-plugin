"""Configuration management.

TIER 1: May import from core only.

Supports JSONC (JSON with Comments) for config files.
"""

import json
import os
from pathlib import Path
from typing import Any

from core.errors import ConfigError

# Cache for loaded config
_config_cache: dict | None = None
_project_root_cache: Path | None = None

# Config file names (priority order)
CONFIG_FILES = ["config.jsonc", "config.json"]


def strip_jsonc_comments(content: str) -> str:
    """Strip JSONC comments from content.

    Removes:
    - Single-line comments: // comment
    - Multi-line comments: /* comment */

    Preserves strings containing // or /* sequences.

    Args:
        content: JSONC content with comments.

    Returns:
        Valid JSON content without comments.
    """
    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(content):
        char = content[i]

        # Handle escape sequences in strings
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        # Track string boundaries
        if char == '"' and not escape_next:
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        # Handle escape character
        if char == "\\" and in_string:
            escape_next = True
            result.append(char)
            i += 1
            continue

        # Skip comments only outside strings
        if not in_string:
            # Single-line comment
            if content[i : i + 2] == "//":
                # Skip until end of line
                while i < len(content) and content[i] != "\n":
                    i += 1
                continue

            # Multi-line comment
            if content[i : i + 2] == "/*":
                # Skip until */
                i += 2
                while i < len(content) - 1:
                    if content[i : i + 2] == "*/":
                        i += 2
                        break
                    i += 1
                continue

        result.append(char)
        i += 1

    return "".join(result)


def get_project_root() -> Path:
    """Get the project root directory.

    Looks for .claude/ directory or git root.

    Returns:
        Project root path.

    Raises:
        ConfigError: If project root cannot be found.
    """
    global _project_root_cache

    if _project_root_cache is not None:
        return _project_root_cache

    # Check environment variable first
    if env_root := os.environ.get("PROJECT_ROOT"):
        _project_root_cache = Path(env_root)
        return _project_root_cache

    # Walk up from current directory
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude").exists():
            _project_root_cache = current
            return _project_root_cache
        if (current / ".git").exists():
            _project_root_cache = current
            return _project_root_cache
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

    Returns:
        Configuration dictionary.
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    config_path = get_config_path()

    if config_path is None:
        _config_cache = {}
        return _config_cache

    try:
        content = config_path.read_text()

        # Strip comments if JSONC
        if config_path.suffix == ".jsonc":
            content = strip_jsonc_comments(content)

        _config_cache = json.loads(content)
        return _config_cache
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid {config_path.name}: {e}") from e


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
    _config_cache = None
    _project_root_cache = None


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
    except Exception as e:
        return False, [f"Failed to write config: {e}"]


def _write_config_with_comments(config_path: Path, config: dict) -> None:
    """Write config back with section comments.

    For .json files, writes plain JSON without comments.
    For .jsonc files, writes with section comments.
    """
    # If .json file, write plain JSON (no comments allowed)
    if config_path.suffix == ".json":
        config_path.write_text(json.dumps(config, indent=2))
        return

    # Section definitions with descriptions (for .jsonc files)
    sections = {
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
        "managed": {
            "header": "MANAGED FILES - Auto-generated by /dk plugin update",
            "desc": "linters, github, docs, ignore - set enabled:false to skip",
        },
    }

    # Hook sub-section comments
    hook_comments = {
        "session": "SessionStart - shows git status, project info",
        "validate": "PreToolUse:Bash - validates git/gh commands",
        "format": "PostToolUse:Write/Edit - auto-format, arch check",
        "plan": "PostToolUse:ExitPlanMode - planning and implementation guidance",
    }

    lines = ["{"]
    lines.append('  "$schema": "./config.schema.json",')
    lines.append("")

    section_order = [
        "project",
        "git",
        "github",
        "linters",
        "testing",
        "hooks",
        "changelog",
        "deployment",
        "arch",
        "managed",
    ]
    written_keys = {"$schema"}

    for key in section_order:
        if key not in config:
            continue

        info = sections.get(key, {"header": key.upper(), "desc": ""})

        lines.append(f"  // {'=' * 70}")
        lines.append(f"  // {info['header']}")
        if info["desc"]:
            lines.append(f"  // {info['desc']}")
        lines.append(f"  // {'=' * 70}")

        if key == "hooks" and isinstance(config[key], dict):
            # Special handling for hooks - add sub-comments
            lines.append(f'  "{key}": {{')
            hook_items = list(config[key].items())
            for i, (hook_name, hook_value) in enumerate(hook_items):
                comment = hook_comments.get(hook_name, "")
                if comment:
                    lines.append(f"    // === {comment} ===")
                hook_json = json.dumps(hook_value, indent=2)
                hook_lines = hook_json.split("\n")
                # First line with key
                lines.append(f'    "{hook_name}": {hook_lines[0]}')
                # Remaining lines indented
                lines.extend(f"    {hl}" for hl in hook_lines[1:])
                # Add comma if not last
                if i < len(hook_items) - 1:
                    lines[-1] = lines[-1].rstrip() + ","
                lines.append("")
            # Remove last empty line and close
            if lines[-1] == "":
                lines.pop()
            lines.append("  },")
        else:
            # Standard section
            section_json = json.dumps({key: config[key]}, indent=2)
            section_lines = section_json.split("\n")[1:-1]
            lines.extend(section_lines)
            if lines[-1].rstrip().endswith("}"):
                lines[-1] = lines[-1].rstrip() + ","

        lines.append("")
        written_keys.add(key)

    # Write any remaining keys not in our order
    for key, value in config.items():
        if key in written_keys:
            continue
        section_json = json.dumps({key: value}, indent=2)
        section_lines = section_json.split("\n")[1:-1]
        lines.extend(section_lines)
        if lines[-1].rstrip().endswith("}"):
            lines[-1] = lines[-1].rstrip() + ","
        lines.append("")

    # Remove trailing comma from last section
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            lines[i] = lines[i].rstrip().rstrip(",")
            break

    lines.append("}")

    config_path.write_text("\n".join(lines))
