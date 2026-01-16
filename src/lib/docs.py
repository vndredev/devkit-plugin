"""Documentation generator - AUTO/CUSTOM section management.

TIER 1: May import from core only.
"""

import re
from pathlib import Path

from lib.config import get, get_project_root


def generate_arch_docs(format: str = "full") -> str:
    """Generate architecture documentation from config.jsonc.

    Generates layer documentation in different formats for use in
    CLAUDE.md, docs/PLUGIN.md, and README.md.

    Args:
        format: Output format:
            - "full": Complete with Mermaid diagram (for CLAUDE.md)
            - "compact": Table only (for README.md)
            - "minimal": Single line summary

    Returns:
        Markdown-formatted architecture documentation.
    """
    layers = get("arch.layers", {})
    if not layers:
        return ""

    sorted_layers = sorted(layers.items(), key=lambda x: x[1].get("tier", 0))

    if format == "minimal":
        layer_names = " → ".join(name for name, _ in sorted_layers)
        return f"**Layers:** {len(layers)} ({layer_names})"

    if format == "compact":
        lines = [
            "| Layer | Tier | Description |",
            "|-------|------|-------------|",
        ]
        for name, info in sorted_layers:
            tier = info.get("tier", 0)
            desc = info.get("description", "-")
            lines.append(f"| `{name}` | {tier} | {desc} |")
        return "\n".join(lines)

    # format == "full" - with Mermaid diagram
    lines = [
        "## Architecture",
        "",
        "Clean Architecture: Imports nur von niedrigeren Tiers erlaubt.",
        "",
        "| Layer | Tier | Description | May Import |",
        "|-------|------|-------------|------------|",
    ]

    for name, info in sorted_layers:
        tier = info.get("tier", 0)
        desc = info.get("description", "-")
        # Calculate which layers this layer may import from
        may_import = (
            ", ".join(n for n, i in sorted_layers if i.get("tier", 0) < tier) or "stdlib only"
        )
        lines.append(f"| `{name}` | {tier} | {desc} | {may_import} |")

    # Mermaid Diagram
    lines.extend(
        [
            "",
            "```mermaid",
            "graph TD",
        ]
    )

    for i, (name, _info) in enumerate(sorted_layers):
        lines.append(f"    {name}[{name}]")
        if i > 0:
            prev_name = sorted_layers[i - 1][0]
            lines.append(f"    {prev_name} --> {name}")

    lines.append("```")

    return "\n".join(lines)


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


def generate_auto_section() -> str:
    """Generate AUTO section content from config.

    Returns:
        Generated AUTO section content.
    """
    # Project info
    project_type = get("project.type", "unknown")
    project_description = get("project.description", "")
    project_principles = get("project.principles", [])

    # Architecture (layers used below for arch_docs)

    lines = []

    # Description (if configured)
    if project_description:
        lines.extend([project_description, ""])

    # Principles section
    lines.append("## Principles")
    lines.append("")

    if project_principles:
        # Use configured principles
        for p in project_principles:
            if " - " in p:
                title, desc = p.split(" - ", 1)
                lines.append(f"- **{title}**: {desc}")
            else:
                lines.append(f"- {p}")
    else:
        # Default principles
        lines.extend(
            [
                "- **Dependency Rule**: Only import from lower tiers",
                "- **Separation**: Each layer has one responsibility",
                "- **Core isolated**: Business logic without external dependencies",
            ]
        )

    # Architecture section (generated from config)
    arch_docs = generate_arch_docs(format="full")
    if arch_docs:
        lines.append("")
        lines.extend(arch_docs.split("\n"))

    # Git Conventions section
    conventions = get("git.conventions", {})
    if conventions:
        lines.extend(
            [
                "",
                "## Git Conventions",
                "",
            ]
        )

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
            scopes_str = ", ".join(internal_scopes)
            lines.append(f"**Internal Scopes (skip release notes):** `{scopes_str}`")
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

        lines.extend(
            [
                "## Testing",
                "",
                f"**Framework:** `{framework}` | **Coverage:** ≥{coverage_min}%",
                "",
            ]
        )

        if required_modules:
            mod_count = len(required_modules)
            lines.append(f"**Required Tests:** {mod_count} modules, {total_funcs} functions")
            lines.append("")

    lines.extend(
        [
            "## Commands",
            "",
            "**CRITICAL:** All commands via `/dk` - run `/dk` without args to see all.",
            "",
            "**YOU MUST use `/dk` commands - NEVER use raw git/gh/vercel commands directly.**",
            "",
            "## Development",
            "",
        ]
    )

    # Type-specific development commands
    if project_type == "python":
        lines.extend(
            [
                "```bash",
                "# YOU MUST use uv run for Python",
                "uv run pytest tests/",
                "uv run python src/...",
                "```",
            ]
        )
    else:
        # Node-based projects (node, nextjs, typescript, javascript)
        test_framework = get("testing.framework", "jest")
        lines.extend(
            [
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
            ]
        )

    # Resources section - documentation tools
    lines.extend(
        [
            "",
            "## Resources",
            "",
            "- **Claude Code docs**: ALWAYS use Task tool with `subagent_type=claude-code-guide`",
            "- **Library docs**: ALWAYS use Context7 MCP (`resolve-library-id` → `query-docs`)",
        ]
    )

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

    For existing projects: Updates AUTO section, preserves CUSTOM section.
    For new projects: Uses templates/CLAUDE.md.template as base structure,
    then fills the AUTO section with generated content.

    Args:
        root: Project root directory. Uses config root if not provided.

    Returns:
        Generated CLAUDE.md content.
    """
    from lib.sync import get_plugin_root, render_template

    if root is None:
        root = get_project_root()

    project_name = get("project.name", "Project")
    project_slogan = get("project.slogan", "")
    layers = get("arch.layers", {})

    # Check for existing CLAUDE.md
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        old_content = claude_md.read_text()
        new_auto = generate_auto_section()
        return merge_sections(old_content, new_auto)

    # Generate from template for new projects
    plugin_root = get_plugin_root()
    template_path = plugin_root / "templates" / "CLAUDE.md.template"

    if template_path.exists():
        # Use template as base structure
        template_content = template_path.read_text()

        # Render template placeholders
        values = {
            "project": {
                "name": project_name,
                "type": get("project.type", "unknown"),
            },
            "arch": {
                "layer_count": str(len(layers)),
            },
        }
        base_content = render_template(template_content, values)

        # Now update the AUTO section with full generated content
        new_auto = generate_auto_section()
        return merge_sections(base_content, new_auto)

    # Fallback: generate without template (for backwards compatibility)
    new_auto = generate_auto_section()
    lines = [f"# {project_name}"]

    if project_slogan:
        lines.extend(["", f"> *{project_slogan}*"])

    lines.extend(
        [
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
        ]
    )

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
    """Generate PLUGIN.md from template.

    Uses templates/docs/PLUGIN.md.template as the source of truth
    and replaces {{arch_docs_full}} placeholder with generated content.

    Returns:
        Generated PLUGIN.md content.

    Raises:
        FileNotFoundError: If template file does not exist.
    """
    from lib.sync import get_plugin_root, render_template

    plugin_root = get_plugin_root()
    template_path = plugin_root / "templates" / "docs" / "PLUGIN.md.template"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template_content = template_path.read_text()

    # Generate architecture documentation for placeholder
    arch_docs = generate_arch_docs(format="full")

    # Render template with values
    values = {
        "arch_docs_full": arch_docs,
    }

    return render_template(template_content, values)


def generate_readme_values() -> dict:
    """Generate values for README.md template.

    Returns:
        Dict with template values.
    """
    project_type = get("project.type", "unknown")

    # Package manager and commands based on project type
    if project_type == "python":
        package_manager = "uv"
        install_command = "uv sync"
        dev_command = "uv run python src/"
        build_command = "uv run pytest"
    else:  # node, nextjs, typescript, javascript
        package_manager = "npm"
        install_command = "npm install"
        dev_command = "npm run dev"
        build_command = "npm run build"

    return {
        "project_name": get("project.name", "Project"),
        "project_slogan": get("project.slogan", ""),
        "project_description": get("project.description", ""),
        "project_type": project_type,
        "package_manager": package_manager,
        "install_command": install_command,
        "dev_command": dev_command,
        "build_command": build_command,
        # Architecture documentation
        "arch_docs_full": generate_arch_docs(format="full"),
        "arch_docs_compact": generate_arch_docs(format="compact"),
        "arch_docs_minimal": generate_arch_docs(format="minimal"),
    }


def update_readme_md(root: Path | None = None) -> tuple[bool, str]:
    """Update README.md - regenerate AUTO sections, keep CUSTOM.

    Args:
        root: Project root directory. Uses config root if not provided.

    Returns:
        Tuple of (success, message).
    """
    if root is None:
        root = get_project_root()

    readme_file = root / "README.md"

    try:
        # Get template
        from lib.sync import get_plugin_root, render_template

        plugin_root = get_plugin_root()
        template_file = plugin_root / "templates" / "docs" / "README.md.template"

        if not template_file.exists():
            return False, "README.md template not found"

        template = template_file.read_text()
        values = generate_readme_values()
        new_content = render_template(template, values)

        # If existing file, preserve CUSTOM sections
        if readme_file.exists():
            old_content = readme_file.read_text()
            old_sections = parse_sections(old_content)

            if old_sections["custom"]:
                # Replace CUSTOM section in new content with old custom
                new_content = re.sub(
                    r"<!-- CUSTOM:START[^>]*-->.*?<!-- CUSTOM:END -->",
                    f"<!-- CUSTOM:START - Your documentation below. Preserved during updates. -->\n{old_sections['custom']}\n<!-- CUSTOM:END -->",
                    new_content,
                    flags=re.DOTALL,
                )

        readme_file.write_text(new_content)
        return True, f"Updated {readme_file}"
    except Exception as e:
        return False, f"Failed to update README.md: {e}"


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
