"""Sync system - keeps generated files in sync with config.

TIER 1: May import from core only.
"""

import json
import re
import stat
from pathlib import Path
from typing import Any

from lib.config import get, get_project_root, upgrade_config

# NOTE: lib.docs imports are done lazily in functions to avoid circular imports
# (docs.py imports get_plugin_root and render_template from sync.py)


def get_plugin_root() -> Path:
    """Get the plugin installation root directory."""
    return Path(__file__).parent.parent.parent


def load_presets() -> dict[str, Any]:
    """Load linter presets from templates."""
    presets_file = get_plugin_root() / "templates" / "linters" / "presets.json"
    if presets_file.exists():
        return json.loads(presets_file.read_text())
    return {}


def render_template(template: str, values: dict[str, Any]) -> str:
    """Replace {{var}} placeholders with values.

    Supports both simple keys ({{var}}) and nested keys ({{project.name}}).

    Args:
        template: Template string with {{var}} placeholders.
        values: Dict of values to substitute.

    Returns:
        Rendered string with placeholders replaced.
    """

    def replace_var(match: re.Match) -> str:
        key = match.group(1)
        # Support nested keys like 'project.name'
        parts = key.split(".")
        value = values
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, "")
            else:
                return ""
        # Handle special types
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value) if value else ""

    return re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replace_var, template)


def get_rendered_template(
    plugin_root: Path,
    template_path: str,
    values: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Load and render a template file.

    Args:
        plugin_root: Plugin installation root directory.
        template_path: Relative path to template from templates/.
        values: Dict of values to substitute.

    Returns:
        Tuple of (rendered_content, error_message).
        If successful: (content, None)
        If failed: (None, error_message)
    """
    template_file = plugin_root / "templates" / template_path

    if not template_file.exists():
        return None, f"Template not found: {template_path}"

    template = template_file.read_text()
    content = render_template(template, values)
    return content, None


def _sync_linter_config(
    root: Path,
    preset: str,
    overrides: dict[str, Any],
    preset_category: str,
    template_path: str,
    output_name: str,
) -> tuple[bool, str]:
    """Generic linter config sync.

    Args:
        root: Project root directory.
        preset: Preset name (e.g., 'strict', 'relaxed').
        overrides: Custom overrides to apply.
        preset_category: Category in presets.json (e.g., 'python', 'nextjs').
        template_path: Relative path to template from templates/linters/.
        output_name: Output filename.

    Returns:
        Tuple of (success, message).
    """
    presets = load_presets()
    category_presets = presets.get(preset_category, {})

    if preset not in category_presets:
        preset = "strict"

    values = category_presets[preset].copy()
    values["preset"] = preset
    values.update(overrides)

    template_file = get_plugin_root() / "templates" / "linters" / template_path
    if not template_file.exists():
        return False, f"Template not found: {template_path}"

    template = template_file.read_text()
    content = render_template(template, values)

    output_file = root / output_name
    output_file.write_text(content)
    return True, f"Generated {output_file}"


def sync_ruff(root: Path, preset: str, overrides: dict) -> tuple[bool, str]:
    """Generate ruff.toml for Python projects."""
    return _sync_linter_config(
        root,
        preset,
        overrides,
        preset_category="python",
        template_path="python/ruff.toml.template",
        output_name="ruff.toml",
    )


def sync_eslint(root: Path, preset: str, overrides: dict) -> tuple[bool, str]:
    """Generate .eslintrc.json for Next.js projects."""
    return _sync_linter_config(
        root,
        preset,
        overrides,
        preset_category="nextjs",
        template_path="nextjs/eslint.json.template",
        output_name=".eslintrc.json",
    )


def sync_prettier(root: Path, preset: str, overrides: dict) -> tuple[bool, str]:
    """Generate .prettierrc for Next.js projects."""
    return _sync_linter_config(
        root,
        preset,
        overrides,
        preset_category="nextjs",
        template_path="nextjs/prettier.json.template",
        output_name=".prettierrc",
    )


def sync_markdownlint(root: Path, preset: str, overrides: dict) -> tuple[bool, str]:
    """Generate .markdownlint.json for all projects."""
    return _sync_linter_config(
        root,
        preset,
        overrides,
        preset_category="common",
        template_path="common/markdownlint.json.template",
        output_name=".markdownlint.json",
    )


def sync_gitignore(root: Path, project_type: str) -> tuple[bool, str]:
    """Generate .gitignore by combining common + project-type templates."""
    plugin_root = get_plugin_root()
    gitignore_dir = plugin_root / "templates" / "gitignore"

    parts = []

    # Common ignore (always included)
    common_file = gitignore_dir / "common.gitignore"
    if common_file.exists():
        parts.append(common_file.read_text())

    # Project-type specific
    type_file = gitignore_dir / f"{project_type}.gitignore"
    if type_file.exists():
        parts.append(f"\n# === {project_type.upper()} ===\n")
        parts.append(type_file.read_text())

    if not parts:
        return False, "No gitignore templates found"

    content = "\n".join(parts)
    output_file = root / ".gitignore"
    output_file.write_text(content)
    return True, f"Generated {output_file}"


def sync_markdownlintignore(root: Path) -> tuple[bool, str]:
    """Generate .markdownlintignore."""
    template_file = get_plugin_root() / "templates" / "gitignore" / "markdownlint.ignore"
    if not template_file.exists():
        return False, "Template not found: markdownlint.ignore"

    content = template_file.read_text()
    output_file = root / ".markdownlintignore"
    output_file.write_text(content)
    return True, f"Generated {output_file}"


def sync_prettierignore(root: Path) -> tuple[bool, str]:
    """Generate .prettierignore."""
    template_file = get_plugin_root() / "templates" / "gitignore" / "prettier.ignore"
    if not template_file.exists():
        return False, "Template not found: prettier.ignore"

    content = template_file.read_text()
    output_file = root / ".prettierignore"
    output_file.write_text(content)
    return True, f"Generated {output_file}"


def sync_github(root: Path) -> list[tuple[str, bool, str]]:
    """Sync GitHub workflows and issue templates."""
    # Lazy import to avoid circular imports
    from lib.docs import generate_arch_docs

    results = []
    plugin_root = get_plugin_root()
    github_templates = plugin_root / "templates" / "github"

    if not github_templates.exists():
        return [(".github", False, "GitHub templates not found")]

    # Get project values for template rendering
    project_name = get("project.name", "Project")
    project_type = get("project.type", "unknown")
    github_url = get("github.url", "https://github.com/owner/repo")

    values = {
        "project_name": project_name,
        "github_url": github_url,
        # Architecture documentation for templates
        "arch_docs_full": generate_arch_docs(format="full"),
        "arch_docs_compact": generate_arch_docs(format="compact"),
        "arch_docs_minimal": generate_arch_docs(format="minimal"),
    }

    # Ensure .github directories exist
    github_dir = root / ".github"
    workflows_dir = github_dir / "workflows"
    issue_template_dir = github_dir / "ISSUE_TEMPLATE"

    workflows_dir.mkdir(parents=True, exist_ok=True)
    issue_template_dir.mkdir(parents=True, exist_ok=True)

    # Variant templates (project-type specific)
    variant_templates = {"release-python.yml", "release-node.yml"}

    # Sync workflows
    workflows_src = github_templates / "workflows"
    if workflows_src.exists():
        for template_file in workflows_src.glob("*.template"):
            output_name = template_file.stem  # Remove .template extension

            # Skip variant templates - handle separately
            if output_name in variant_templates:
                continue

            template = template_file.read_text()
            content = render_template(template, values)
            output_file = workflows_dir / output_name
            output_file.write_text(content)
            results.append((f".github/workflows/{output_name}", True, f"Generated {output_file}"))

        # Choose correct release variant based on project type
        if project_type == "python":
            release_template = workflows_src / "release-python.yml.template"
        else:
            release_template = workflows_src / "release-node.yml.template"

        if release_template.exists():
            template = release_template.read_text()
            content = render_template(template, values)
            output_file = workflows_dir / "release.yml"
            output_file.write_text(content)
            results.append((".github/workflows/release.yml", True, f"Generated {output_file}"))

    # Sync issue templates
    issue_src = github_templates / "ISSUE_TEMPLATE"
    if issue_src.exists():
        for template_file in issue_src.glob("*.template"):
            output_name = template_file.stem  # Remove .template extension
            template = template_file.read_text()
            content = render_template(template, values)
            output_file = issue_template_dir / output_name
            output_file.write_text(content)
            results.append(
                (f".github/ISSUE_TEMPLATE/{output_name}", True, f"Generated {output_file}")
            )

    return results


def sync_linters(root: Path | None = None) -> list[tuple[str, bool, str]]:
    """Generate linter configs based on project type and preset."""
    if root is None:
        root = get_project_root()

    project_type = get("project.type", "unknown")
    linters_config = get("linters", {})
    preset = linters_config.get("preset", "strict")
    overrides = linters_config.get("overrides", {})

    results = []

    # Project-type specific linters
    if project_type == "python":
        results.append(("ruff.toml", *sync_ruff(root, preset, overrides)))
    elif project_type in ("nextjs", "typescript", "javascript"):
        results.append((".eslintrc.json", *sync_eslint(root, preset, overrides)))
        results.append((".prettierrc", *sync_prettier(root, preset, overrides)))
        results.append((".prettierignore", *sync_prettierignore(root)))

    # Common linters (all projects)
    results.append((".markdownlint.json", *sync_markdownlint(root, preset, overrides)))
    results.append((".markdownlintignore", *sync_markdownlintignore(root)))

    # Gitignore (all projects)
    results.append((".gitignore", *sync_gitignore(root, project_type)))

    return results


def sync_docs(root: Path | None = None) -> list[tuple[str, bool, str]]:
    """Sync documentation files."""
    # Lazy import to avoid circular imports
    from lib.docs import update_claude_md, update_plugin_md

    if root is None:
        root = get_project_root()

    results = []

    success, msg = update_claude_md(root)
    results.append(("CLAUDE.md", success, msg))

    success, msg = update_plugin_md(root)
    results.append(("docs/PLUGIN.md", success, msg))

    return results


def sync_all(root: Path | None = None) -> list[tuple[str, bool, str]]:
    """Sync all generated files based on managed config.

    Also upgrades config.jsonc with missing optional sections.
    Reads from config.managed to determine what to sync.
    Falls back to project-type based sync if managed section is missing.
    """
    # Lazy imports to avoid circular imports
    from lib.docs import (
        generate_arch_docs,
        update_claude_md,
        update_plugin_md,
        update_readme_md,
    )

    if root is None:
        root = get_project_root()

    results = []

    # First: upgrade config with missing sections
    _ok, upgraded_sections = upgrade_config()
    if upgraded_sections:
        results.extend(
            (f"config: {section}", True, "added default") for section in upgraded_sections
        )

    managed = get("managed", {})

    # If no managed section, use legacy behavior
    if not managed:
        results.extend(sync_docs(root))
        results.extend(sync_linters(root))
        results.extend(sync_github(root))
        return results

    plugin_root = get_plugin_root()

    # Get values for template rendering
    project_name = get("project.name", "Project")
    project_type = get("project.type", "unknown")
    github_url = get("github.url", "https://github.com/owner/repo")
    linters_config = get("linters", {})
    preset = linters_config.get("preset", "strict")
    overrides = linters_config.get("overrides", {})

    presets = load_presets()

    # Build template values
    values = {
        "project_name": project_name,
        "github_url": github_url,
        "preset": preset,
        # Architecture documentation for templates
        "arch_docs_full": generate_arch_docs(format="full"),
        "arch_docs_compact": generate_arch_docs(format="compact"),
        "arch_docs_minimal": generate_arch_docs(format="minimal"),
    }

    # Add preset values based on project type
    if project_type == "python":
        python_presets = presets.get("python", {}).get(preset, {})
        values.update(python_presets)
    elif project_type in ("nextjs", "typescript", "javascript"):
        nextjs_presets = presets.get("nextjs", {}).get(preset, {})
        values.update(nextjs_presets)

    # Add common presets
    common_presets = presets.get("common", {}).get(preset, {})
    values.update(common_presets)
    values.update(overrides)

    # Sync linters
    for output_path, config in managed.get("linters", {}).items():
        if not config.get("enabled", True):
            continue
        template_path = config.get("template", "")
        result = _sync_template_file(root, plugin_root, output_path, template_path, values)
        results.append(result)

    # Sync github files
    for output_path, config in managed.get("github", {}).items():
        if not config.get("enabled", True):
            continue
        template_path = config.get("template", "")

        # Ensure parent directories exist
        output_file = root / output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)

        result = _sync_template_file(root, plugin_root, output_path, template_path, values)
        results.append(result)

    # Sync ignore files
    for output_path, config in managed.get("ignore", {}).items():
        if not config.get("enabled", True):
            continue
        template_paths = config.get("template", [])
        if isinstance(template_paths, str):
            template_paths = [template_paths]
        result = _sync_ignore_file(root, plugin_root, output_path, template_paths, project_type)
        results.append(result)

    # Sync docs
    for output_path, config in managed.get("docs", {}).items():
        if not config.get("enabled", True):
            continue

        doc_type = config.get("type", "")

        # Ensure parent directory exists
        output_file = root / output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_path == "CLAUDE.md":
            # CLAUDE.md: auto_sections (project-specific, preserves CUSTOM)
            success, msg = update_claude_md(root)
        elif output_path == "README.md":
            # README.md: auto_sections (template + CUSTOM)
            success, msg = update_readme_md(root)
        elif output_path == "docs/ARCHITECTURE.md":
            # ARCHITECTURE.md: generated by arch layer (arch.docs.update_architecture_md)
            # Cannot be called from lib layer due to tier constraints
            # Check if file exists, generation must be triggered separately
            arch_file = root / output_path
            if arch_file.exists():
                success, msg = True, "exists (run arch.docs.update_architecture_md to regenerate)"
            else:
                success, msg = False, "missing (run arch.docs.update_architecture_md to generate)"
        elif doc_type == "template":
            # Template-based docs (like PLUGIN.md) - copy from plugin
            template_path = config.get("template", "")
            if template_path:
                result = _sync_template_file(root, plugin_root, output_path, template_path, values)
                output_path, success, msg = result
            else:
                success, msg = False, f"No template specified for {output_path}"
        elif output_path == "docs/PLUGIN.md":
            # Legacy: auto_generate PLUGIN.md (fallback)
            success, msg = update_plugin_md(root)
        else:
            success, msg = False, f"Unknown doc type: {output_path}"

        results.append((output_path, success, msg))

    return results


def _sync_template_file(
    root: Path,
    plugin_root: Path,
    output_path: str,
    template_path: str,
    values: dict[str, Any],
) -> tuple[str, bool, str]:
    """Sync a single template file."""
    content, error = get_rendered_template(plugin_root, template_path, values)
    if error:
        return output_path, False, error

    output_file = root / output_path
    output_file.write_text(content)  # type: ignore[arg-type]
    return output_path, True, f"Generated {output_file}"


def _sync_ignore_file(
    root: Path, plugin_root: Path, output_path: str, template_paths: list[str], project_type: str
) -> tuple[str, bool, str]:
    """Sync an ignore file by combining templates."""
    parts = []

    for template_path in template_paths:
        template_file = plugin_root / "templates" / template_path
        if template_file.exists():
            # Add section header for non-common templates
            if "common" not in template_path:
                parts.append(f"\n# === {project_type.upper()} ===\n")
            parts.append(template_file.read_text())

    if not parts:
        return output_path, False, "No templates found"

    content = "\n".join(parts)
    output_file = root / output_path
    output_file.write_text(content)

    return output_path, True, f"Generated {output_file}"


def check_sync_status(root: Path | None = None) -> dict[str, bool]:
    """Check if files exist (basic status check)."""
    if root is None:
        root = get_project_root()

    project_type = get("project.type", "unknown")

    status = {
        "CLAUDE.md": (root / "CLAUDE.md").exists(),
        "docs/PLUGIN.md": (root / "docs" / "PLUGIN.md").exists(),
        ".markdownlint.json": (root / ".markdownlint.json").exists(),
        ".gitignore": (root / ".gitignore").exists(),
        ".github/workflows": (root / ".github" / "workflows").exists(),
    }

    if project_type == "python":
        status["ruff.toml"] = (root / "ruff.toml").exists()
    elif project_type in ("nextjs", "typescript", "javascript"):
        status[".eslintrc.json"] = (root / ".eslintrc.json").exists()
        status[".prettierrc"] = (root / ".prettierrc").exists()

    return status


def get_claude_config_dir() -> Path:
    """Get Claude Code config directory.

    Respects CLAUDE_CONFIG_DIR environment variable.
    Falls back to ~/.claude/ if not set.
    """
    import os

    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        return Path(config_dir)
    return Path.home() / ".claude"


def install_user_files() -> list[tuple[str, bool, str]]:
    """Install plugin user files to Claude config directory.

    Installs:
    - statusline.sh: Claude Code status line script

    Respects CLAUDE_CONFIG_DIR environment variable.

    Returns:
        List of (file, success, message) tuples.
    """
    results = []
    plugin_root = get_plugin_root()
    claude_dir = get_claude_config_dir()

    # Ensure ~/.claude exists
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Install statusline.sh
    template_file = plugin_root / "templates" / "claude" / "statusline.sh.template"
    target_file = claude_dir / "statusline.sh"

    # Display path (use ~ for home directory)
    display_path = str(target_file).replace(str(Path.home()), "~")

    if template_file.exists():
        try:
            content = template_file.read_text()
            target_file.write_text(content)

            # Make executable (chmod +x)
            current_mode = target_file.stat().st_mode
            target_file.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            results.append((display_path, True, "Installed"))
        except Exception as e:
            results.append((display_path, False, str(e)))
    else:
        results.append((display_path, False, "Template not found"))

    return results


def check_user_files() -> dict[str, dict[str, Any]]:
    """Check status of user files in Claude config directory.

    Respects CLAUDE_CONFIG_DIR environment variable.

    Returns:
        Dict with file status: {file: {exists, current, outdated, configured}}.
    """
    plugin_root = get_plugin_root()
    claude_dir = get_claude_config_dir()

    status = {}

    # Check statusline.sh
    template_file = plugin_root / "templates" / "claude" / "statusline.sh.template"
    target_file = claude_dir / "statusline.sh"

    # Display path (use ~ for home directory)
    display_path = str(target_file).replace(str(Path.home()), "~")

    if template_file.exists():
        template_content = template_file.read_text()
        target_exists = target_file.exists()
        target_content = target_file.read_text() if target_exists else ""

        # Check if statusline is configured in Claude Code settings
        settings_file = claude_dir / "settings.json"
        configured = False
        if settings_file.exists():
            try:
                settings = json.loads(settings_file.read_text())
                # Claude Code uses camelCase: statusLine
                statusline_config = settings.get("statusLine", {})
                command = statusline_config.get("command", "")
                # Accept both the display path and the absolute path
                configured = command in (display_path, str(target_file))
            except (json.JSONDecodeError, KeyError):
                configured = False

        status[display_path] = {
            "exists": target_exists,
            "current": target_content == template_content if target_exists else False,
            "outdated": target_exists and target_content != template_content,
            "configured": configured,
        }
    else:
        status[display_path] = {
            "exists": False,
            "current": False,
            "outdated": False,
            "configured": False,
            "error": "Template not found",
        }

    return status
