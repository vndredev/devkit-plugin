"""Documentation generator - AUTO/CUSTOM section management.

TIER 1: May import from core only.
"""

import re
from pathlib import Path

from lib.config import get, get_project_root


def parse_sections(content: str) -> dict[str, str]:
    """Parse AUTO and CUSTOM sections from markdown.

    Args:
        content: Markdown content with section markers.

    Returns:
        Dict with 'auto', 'custom', 'before_auto', 'after_custom' keys.
    """
    result = {
        "auto": "",
        "custom": "",
        "before_auto": "",
        "after_custom": "",
    }

    # Find AUTO section
    auto_match = re.search(
        r"(.*?)<!-- AUTO:START[^>]*-->\s*(.*?)\s*<!-- AUTO:END -->(.*)$",
        content,
        re.DOTALL,
    )
    if auto_match:
        result["before_auto"] = auto_match.group(1).strip()
        result["auto"] = auto_match.group(2).strip()
        remaining = auto_match.group(3)
    else:
        remaining = content

    # Find CUSTOM section
    custom_match = re.search(
        r"<!-- CUSTOM:START[^>]*-->\s*(.*?)\s*<!-- CUSTOM:END -->(.*)$",
        remaining,
        re.DOTALL,
    )
    if custom_match:
        result["custom"] = custom_match.group(1).strip()
        result["after_custom"] = custom_match.group(2).strip()

    return result


def render_template(template: str, values: dict) -> str:
    """Replace {{var}} placeholders with values.

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
        return str(value) if value else ""

    return re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replace_var, template)


def generate_auto_section() -> str:
    """Generate AUTO section content from config.

    Returns:
        Generated AUTO section content.
    """
    # Project info
    project_type = get("project.type", "unknown")
    project_description = get("project.description", "")
    project_principles = get("project.principles", [])

    # Architecture
    layers = get("arch.layers", {})
    layer_count = len(layers)

    lines = []

    # Description (if configured)
    if project_description:
        lines.extend([project_description, ""])

    # Principles section
    lines.append("## Principles")
    lines.append("")

    if project_principles:
        # Use configured principles
        lines.extend(
            f"- **{p.split(' - ')[0]}**: {' - '.join(p.split(' - ')[1:])}" if " - " in p else f"- {p}"
            for p in project_principles
        )
    else:
        # Default principles
        lines.extend([
            "- **Dependency Rule**: Only import from lower tiers",
            "- **Separation**: Each layer has one responsibility",
            "- **Core isolated**: Business logic without external dependencies",
        ])

    lines.extend([
        "",
        "## Architecture",
        "",
        f"- **Type:** {project_type}",
        f"- **Layers:** {layer_count}",
    ])

    if layers:
        lines.append("")
        lines.append("| Layer | Tier |")
        lines.append("|-------|------|")
        for name, info in sorted(layers.items(), key=lambda x: x[1].get("tier", 0)):
            tier = info.get("tier", 0)
            lines.append(f"| {name} | {tier} |")

    # Git Conventions section
    conventions = get("git.conventions", {})
    if conventions:
        lines.extend([
            "",
            "## Git Conventions",
            "",
        ])

        # Types
        types = conventions.get("types", [])
        if types:
            lines.append(f"**Commit Types:** `{' | '.join(types)}`")
            lines.append("")

        # Scopes
        scopes = conventions.get("scopes", {})
        allowed_scopes = scopes.get("allowed", [])
        internal_scopes = scopes.get("internal", [])
        scope_mode = scopes.get("mode", "strict")

        if allowed_scopes or internal_scopes:
            lines.append(f"**Scope Mode:** `{scope_mode}`")
            lines.append("")

        if allowed_scopes:
            lines.append("**Allowed Scopes:**")
            lines.append("")
            lines.append("| Scope | Usage |")
            lines.append("|-------|-------|")
            scope_descriptions = {
                "git": "Git workflow, PRs, branches",
                "arch": "Architecture, layer rules",
                "dev": "Development workflow",
                "lib": "Library layer",
                "core": "Core layer",
                "events": "Hook handlers",
                "plugin": "Plugin system",
                "docs": "Documentation",
                "sync": "File sync system",
                "check": "Health checks",
                "test": "Test infrastructure",
            }
            for scope in allowed_scopes:
                desc = scope_descriptions.get(scope, "-")
                lines.append(f"| `{scope}` | {desc} |")
            lines.append("")

        if internal_scopes:
            lines.append(f"**Internal Scopes (skip release notes):** `{', '.join(internal_scopes)}`")
            lines.append("")

        # Branch pattern
        branch_pattern = conventions.get("branch_pattern", "")
        if branch_pattern:
            lines.append(f"**Branch Pattern:** `{branch_pattern}`")
            lines.append("")
            lines.append("Example: `feat/add-login`, `fix/button-styling`")
            lines.append("")

    # Testing section
    testing = get("testing", {})
    if testing.get("enabled"):
        framework = testing.get("framework", "pytest")
        coverage_min = testing.get("coverage", {}).get("minimum", 80)
        required_modules = testing.get("required_modules", {})
        total_funcs = sum(len(funcs) for funcs in required_modules.values())

        lines.extend([
            "## Testing",
            "",
            f"**Framework:** `{framework}` | **Coverage:** ≥{coverage_min}%",
            "",
        ])

        if required_modules:
            lines.append(f"**Required Tests:** {len(required_modules)} modules, {total_funcs} functions")
            lines.append("")

    lines.extend([
        "## Commands",
        "",
        "All commands via `/dk` - run `/dk` without args to see all.",
        "",
        "## Development",
        "",
    ])

    # Type-specific development commands
    if project_type == "python":
        lines.extend([
            "```bash",
            "# Always use uv run for Python",
            "uv run pytest tests/",
            "uv run python src/...",
            "```",
        ])
    else:
        # Node-based projects (node, nextjs, typescript, javascript)
        test_framework = get("testing.framework", "jest")
        lines.extend([
            "```bash",
            "# Development",
            "npm run dev",
            "",
            "# Testing",
            f"npm test  # {test_framework}",
            "",
            "# Build",
            "npm run build",
            "```",
        ])

    return "\n".join(lines)


def merge_sections(old_content: str, new_auto: str) -> str:
    """Merge new AUTO content while preserving CUSTOM sections.

    Args:
        old_content: Existing CLAUDE.md content.
        new_auto: New AUTO section content.

    Returns:
        Merged content with updated AUTO and preserved CUSTOM.
    """
    sections = parse_sections(old_content)

    # Build new content
    lines = []

    # Header (before AUTO)
    if sections["before_auto"]:
        lines.append(sections["before_auto"])
        lines.append("")

    # AUTO section
    lines.append("<!-- AUTO:START - Generated by devkit-plugin. DO NOT EDIT. -->")
    lines.append(new_auto)
    lines.append("<!-- AUTO:END -->")
    lines.append("")

    # CUSTOM section
    lines.append("<!-- CUSTOM:START - Your documentation below. Preserved during updates. -->")
    if sections["custom"]:
        lines.append(sections["custom"])
    else:
        lines.append("## Project Specific")
        lines.append("")
        lines.append("_Add your documentation here._")
    lines.append("<!-- CUSTOM:END -->")

    # After CUSTOM
    if sections["after_custom"]:
        lines.append("")
        lines.append(sections["after_custom"])

    return "\n".join(lines)


def generate_claude_md(root: Path | None = None) -> str:
    """Generate complete CLAUDE.md content.

    Args:
        root: Project root directory. Uses config root if not provided.

    Returns:
        Generated CLAUDE.md content.
    """
    if root is None:
        root = get_project_root()

    project_name = get("project.name", "Project")
    project_slogan = get("project.slogan", "")

    # Check for existing CLAUDE.md
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        old_content = claude_md.read_text()
        new_auto = generate_auto_section()
        return merge_sections(old_content, new_auto)

    # Generate from scratch
    new_auto = generate_auto_section()
    lines = [f"# {project_name}"]

    if project_slogan:
        lines.extend(["", f"> *{project_slogan}*"])

    lines.extend([
        "",
        "<!-- AUTO:START - Generated by devkit-plugin. DO NOT EDIT. -->",
        new_auto,
        "<!-- AUTO:END -->",
        "",
        "<!-- CUSTOM:START - Your documentation below. Preserved during updates. -->",
        "## Project Specific",
        "",
        "_Add your documentation here._",
        "<!-- CUSTOM:END -->",
    ])

    return "\n".join(lines)


def update_claude_md(root: Path | None = None) -> tuple[bool, str]:
    """Update CLAUDE.md - regenerate AUTO, keep CUSTOM.

    Args:
        root: Project root directory. Uses config root if not provided.

    Returns:
        Tuple of (success, message).
    """
    if root is None:
        root = get_project_root()

    claude_md = root / "CLAUDE.md"

    try:
        content = generate_claude_md(root)
        claude_md.write_text(content)
        return True, f"Updated {claude_md}"
    except Exception as e:
        return False, f"Failed to update CLAUDE.md: {e}"


def get_docs_status(root: Path | None = None) -> dict:
    """Get status of CLAUDE.md documentation.

    Args:
        root: Project root directory. Uses config root if not provided.

    Returns:
        Dict with 'exists', 'has_auto', 'has_custom' keys.
    """
    if root is None:
        root = get_project_root()

    claude_md = root / "CLAUDE.md"

    if not claude_md.exists():
        return {"exists": False, "has_auto": False, "has_custom": False}

    content = claude_md.read_text()
    return {
        "exists": True,
        "has_auto": "<!-- AUTO:START" in content,
        "has_custom": "<!-- CUSTOM:START" in content,
    }


def generate_plugin_md() -> str:
    """Generate PLUGIN.md - documents plugin internals.

    Returns:
        Generated PLUGIN.md content.
    """
    project_name = get("project.name", "Plugin")
    project_type = get("project.type", "unknown")
    layers = get("arch.layers", {})

    lines = [
        f"# {project_name} - Plugin Internals",
        "",
        "> Auto-generated documentation. Do not edit manually.",
        "",
        "## Overview",
        "",
        f"Claude Code plugin for {project_type} projects.",
        "",
        "## Architecture",
        "",
        "Clean Architecture with dependency rule: higher tiers import from lower only.",
        "",
        "```",
    ]

    # Layer diagram
    sorted_layers = sorted(layers.items(), key=lambda x: x[1].get("tier", 0))
    for name, info in sorted_layers:
        tier = info.get("tier", 0)
        lines.append(f"src/{name}/  (TIER {tier})")

    lines.extend([
        "```",
        "",
        "| Layer | Tier | Responsibility |",
        "|-------|------|----------------|",
    ])

    layer_descriptions = {
        "core": "Pure functions, no I/O",
        "lib": "I/O adapters (config, git, tools)",
        "arch": "Architecture analysis",
        "events": "Claude Code hook handlers",
    }

    for name, info in sorted_layers:
        tier = info.get("tier", 0)
        desc = layer_descriptions.get(name, "-")
        lines.append(f"| {name} | {tier} | {desc} |")

    # Events section
    lines.extend([
        "",
        "## Events (Hooks)",
        "",
        "| Event | Handler | Action |",
        "|-------|---------|--------|",
    ])

    event_handlers = [
        ("SessionStart", "session.py", "Show git status, load config"),
        ("PreToolUse", "validate.py", "Block force push, validate commits"),
        ("PostToolUse", "format.py", "Auto-format edited files"),
        ("ExitPlanMode", "plan.py", "Inject development instructions"),
    ]

    for event, handler, action in event_handlers:
        lines.append(f"| {event} | {handler} | {action} |")

    # Config section
    lines.extend([
        "",
        "## Configuration",
        "",
        "Location: `.claude/.devkit/config.json`",
        "",
        "### Project",
        "",
        "| Field | Description |",
        "|-------|-------------|",
        "| `project.name` | Project name |",
        "| `project.type` | python, nextjs, typescript, javascript |",
        "| `project.slogan` | Tagline for docs |",
        "| `project.description` | Brief description |",
        "| `project.principles` | Array of principles |",
        "",
        "### Git Conventions",
        "",
        "| Field | Description |",
        "|-------|-------------|",
        "| `git.protected_branches` | Branches protected from force push |",
        "| `git.conventions.types` | Allowed commit types |",
        "| `git.conventions.scopes.mode` | strict, warn, or off |",
        "| `git.conventions.scopes.allowed` | Allowed scope names |",
        "| `git.conventions.scopes.internal` | Scopes that skip release notes |",
        "",
        "### Architecture",
        "",
        "| Field | Description |",
        "|-------|-------------|",
        "| `arch.layers.<name>.tier` | Layer tier (0=innermost) |",
        "",
        "### Managed Files",
        "",
        "| Field | Description |",
        "|-------|-------------|",
        "| `managed.linters` | Linter config files |",
        "| `managed.github` | Workflows, issue templates |",
        "| `managed.docs` | Documentation files |",
        "| `managed.ignore` | Ignore files |",
        "",
        "## Skills",
        "",
        "All commands via `/dk <module>`. See `/dk` for full list.",
        "",
        "| Module | Purpose |",
        "|--------|---------|",
        "| dev | Feature development workflow |",
        "| git | PR, branch, issue management |",
        "| arch | Layer analysis, scaffolding |",
        "| docs | Documentation generation |",
        "| env | Environment variable sync |",
        "| vercel | Deployment |",
        "| neon | Database branch management |",
    ])

    return "\n".join(lines)


def update_plugin_md(root: Path | None = None) -> tuple[bool, str]:
    """Update PLUGIN.md with generated content.

    Args:
        root: Project root directory. Uses config root if not provided.

    Returns:
        Tuple of (success, message).
    """
    if root is None:
        root = get_project_root()

    docs_dir = root / "docs"
    docs_dir.mkdir(exist_ok=True)
    plugin_md = docs_dir / "PLUGIN.md"

    try:
        content = generate_plugin_md()
        plugin_md.write_text(content)
        return True, f"Updated {plugin_md}"
    except Exception as e:
        return False, f"Failed to update PLUGIN.md: {e}"
