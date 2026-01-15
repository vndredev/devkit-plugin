"""Sync system - keeps generated files in sync with config.

TIER 1: May import from core only.
"""

import json
import re
from pathlib import Path

from lib.config import get, get_project_root
from lib.docs import update_claude_md, update_plugin_md, update_readme_md


def get_plugin_root() -> Path:
    """Get the plugin installation root directory."""
    return Path(__file__).parent.parent.parent


def load_presets() -> dict:
    """Load linter presets from templates."""
    presets_file = get_plugin_root() / "templates" / "linters" / "presets.json"
    if presets_file.exists():
        return json.loads(presets_file.read_text())
    return {}


def render_template(template: str, values: dict) -> str:
    """Replace {{var}} placeholders with values."""
    def replace_var(match: re.Match) -> str:
        key = match.group(1)
        value = values.get(key, "")
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    return re.sub(r"\{\{(\w+)\}\}", replace_var, template)


def sync_ruff(root: Path, preset: str, overrides: dict) -> tuple[bool, str]:
    """Generate ruff.toml for Python projects."""
    presets = load_presets()
    python_presets = presets.get("python", {})

    if preset not in python_presets:
        preset = "strict"

    values = python_presets[preset].copy()
    values["preset"] = preset
    values.update(overrides)

    template_file = get_plugin_root() / "templates" / "linters" / "python" / "ruff.toml.template"
    if not template_file.exists():
        return False, "Template not found: ruff.toml.template"

    template = template_file.read_text()
    content = render_template(template, values)

    output_file = root / "ruff.toml"
    output_file.write_text(content)
    return True, f"Generated {output_file}"


def sync_eslint(root: Path, preset: str, overrides: dict) -> tuple[bool, str]:
    """Generate .eslintrc.json for Next.js projects."""
    presets = load_presets()
    nextjs_presets = presets.get("nextjs", {})

    if preset not in nextjs_presets:
        preset = "strict"

    values = nextjs_presets[preset].copy()
    values["preset"] = preset
    values.update(overrides)

    template_file = get_plugin_root() / "templates" / "linters" / "nextjs" / "eslint.json.template"
    if not template_file.exists():
        return False, "Template not found: eslint.json.template"

    template = template_file.read_text()
    content = render_template(template, values)

    output_file = root / ".eslintrc.json"
    output_file.write_text(content)
    return True, f"Generated {output_file}"


def sync_prettier(root: Path, preset: str, overrides: dict) -> tuple[bool, str]:
    """Generate .prettierrc for Next.js projects."""
    presets = load_presets()
    nextjs_presets = presets.get("nextjs", {})

    if preset not in nextjs_presets:
        preset = "strict"

    values = nextjs_presets[preset].copy()
    values["preset"] = preset
    values.update(overrides)

    template_file = get_plugin_root() / "templates" / "linters" / "nextjs" / "prettier.json.template"
    if not template_file.exists():
        return False, "Template not found: prettier.json.template"

    template = template_file.read_text()
    content = render_template(template, values)

    output_file = root / ".prettierrc"
    output_file.write_text(content)
    return True, f"Generated {output_file}"


def sync_markdownlint(root: Path, preset: str, overrides: dict) -> tuple[bool, str]:
    """Generate .markdownlint.json for all projects."""
    presets = load_presets()
    common_presets = presets.get("common", {})

    if preset not in common_presets:
        preset = "strict"

    values = common_presets[preset].copy()
    values["preset"] = preset
    values.update(overrides)

    template_file = get_plugin_root() / "templates" / "linters" / "common" / "markdownlint.json.template"
    if not template_file.exists():
        return False, "Template not found: markdownlint.json.template"

    template = template_file.read_text()
    content = render_template(template, values)

    output_file = root / ".markdownlint.json"
    output_file.write_text(content)
    return True, f"Generated {output_file}"


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
            results.append((f".github/ISSUE_TEMPLATE/{output_name}", True, f"Generated {output_file}"))

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

    Reads from config.managed to determine what to sync.
    Falls back to project-type based sync if managed section is missing.
    """
    if root is None:
        root = get_project_root()

    managed = get("managed", {})

    # If no managed section, use legacy behavior
    if not managed:
        results = []
        results.extend(sync_docs(root))
        results.extend(sync_linters(root))
        results.extend(sync_github(root))
        return results

    results = []
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
        elif doc_type == "template":
            # Template-based docs (like PLUGIN.md) - copy from plugin
            template_path = config.get("template", "")
            if template_path:
                result = _sync_template_file(
                    root, plugin_root, output_path, template_path, values
                )
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
    root: Path, plugin_root: Path, output_path: str, template_path: str, values: dict
) -> tuple[str, bool, str]:
    """Sync a single template file."""
    template_file = plugin_root / "templates" / template_path
    output_file = root / output_path

    if not template_file.exists():
        return output_path, False, f"Template not found: {template_path}"

    template = template_file.read_text()
    content = render_template(template, values)
    output_file.write_text(content)

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
