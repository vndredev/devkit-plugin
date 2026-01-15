"""Layer rules configuration and project scaffolding.

TIER 2: May import from core, lib.
"""

from pathlib import Path

from arch.analyze import analyze_dependencies
from core.types import ProjectType
from lib.config import get, get_project_root

# Default layer presets
LAYER_PRESETS = {
    "small": {
        "lib": {"tier": 0, "patterns": ["src/lib/**", "lib/**"]},
        "entry": {"tier": 1, "patterns": ["src/**", "app/**"]},
    },
    "medium": {
        "core": {"tier": 0, "patterns": ["src/core/**", "src/types/**"]},
        "lib": {"tier": 1, "patterns": ["src/lib/**", "src/utils/**"]},
        "entry": {"tier": 2, "patterns": ["src/app/**", "app/**", "pages/**"]},
    },
    "large": {
        "core": {"tier": 0, "patterns": ["src/core/**", "src/types/**"]},
        "lib": {"tier": 1, "patterns": ["src/lib/**", "src/utils/**"]},
        "services": {"tier": 2, "patterns": ["src/services/**", "src/hooks/**"]},
        "entry": {"tier": 3, "patterns": ["src/app/**", "src/components/**"]},
    },
    "enterprise": {
        "core": {"tier": 0, "patterns": ["src/core/**"]},
        "domain": {"tier": 1, "patterns": ["src/domain/**"]},
        "adapters": {"tier": 2, "patterns": ["src/adapters/**"]},
        "usecases": {"tier": 3, "patterns": ["src/usecases/**"]},
        "entry": {"tier": 4, "patterns": ["src/entry/**", "src/app/**"]},
    },
}


def get_violations(root: Path | None = None) -> list[dict]:
    """Get all layer rule violations.

    Args:
        root: Project root directory (defaults to detected).

    Returns:
        List of violation dicts.
    """
    if root is None:
        root = get_project_root()

    analysis = analyze_dependencies(root)
    return analysis["violations"]


def check_layer_rules(root: Path | None = None) -> tuple[bool, str]:
    """Check if project follows layer rules.

    Args:
        root: Project root directory.

    Returns:
        Tuple of (success, message).
    """
    if root is None:
        root = get_project_root()

    violations = get_violations(root)

    if not violations:
        return True, "All imports follow layer rules"

    lines = [
        f"Found {len(violations)} layer violation(s):",
        "",
    ]

    for v in violations:
        lines.append(f"  {v['file']}:")
        lines.append(f"    {v['message']}")
        lines.append("")

    # Get layer order from config or defaults
    layer_config = get("arch.layers", {})
    if layer_config:
        lines.append("Layer Rules (from config.json):")
        for name, cfg in sorted(layer_config.items(), key=lambda x: x[1].get("tier", 0)):
            lines.append(f"  TIER {cfg.get('tier', 0)}: {name}")
    else:
        lines.extend([
            "Layer Rules:",
            "  TIER 0 (core)   - Only stdlib",
            "  TIER 1 (lib)    - core",
            "  TIER 2 (arch)   - core, lib",
            "  TIER 3 (events) - All layers",
        ])

    return False, "\n".join(lines)


def get_layer_info() -> str:
    """Get information about layer rules.

    Returns:
        Formatted layer information.
    """
    return """# Clean Architecture Layers

## Dependency Rule

Higher layers can import from lower layers, but NOT vice versa.

```
ENTRY POINTS (TIER 4)
       |
   USECASES (TIER 3)
       |
   ADAPTERS (TIER 2)
       |
    DOMAIN (TIER 1)
       |
     CORE (TIER 0)
```

## Layer Descriptions

| Layer | Contains | May Import From |
|-------|----------|-----------------|
| core | Types, errors, constants | Only stdlib |
| domain | Pure business logic | core |
| adapters/lib | I/O operations | core, domain |
| usecases | Orchestration | core, domain, adapters |
| entry | CLI, hooks, routes | All layers |

## Configuration

Define custom layers in config.json:

```json
{
  "arch": {
    "layers": {
      "types": { "tier": 0, "patterns": ["src/types/**"] },
      "lib": { "tier": 1, "patterns": ["src/lib/**"] },
      "app": { "tier": 2, "patterns": ["src/app/**"] }
    }
  }
}
```
"""


# Project templates for scaffolding
PYTHON_TEMPLATE = {
    "src/core/__init__.py": '"""Core module - types, errors."""\n',
    "src/core/types.py": '"""Core types and enums."""\n\nfrom enum import Enum\n',
    "src/core/errors.py": '"""Custom exceptions."""\n\n\nclass AppError(Exception):\n    pass\n',
    "src/lib/__init__.py": '"""Lib module - I/O adapters."""\n',
    "src/lib/config.py": '"""Configuration loading."""\n',
}

NEXTJS_TEMPLATE = {
    "src/types/index.ts": "// Core types\nexport interface Entity {\n  id: string;\n}\n",
    "src/lib/utils.ts": (
        "// Utilities\n"
        "export function cn(...classes: string[]) {\n"
        '  return classes.filter(Boolean).join(" ");\n'
        "}\n"
    ),
}


def init_project(
    root: Path,
    project_type: ProjectType,
    size: str = "medium",
) -> list[str]:
    """Initialize project with Clean Architecture structure.

    Args:
        root: Project root directory.
        project_type: Type of project.
        size: Project size preset.

    Returns:
        List of created files.
    """
    if project_type == ProjectType.PYTHON:
        template = PYTHON_TEMPLATE
    elif project_type in (ProjectType.NEXTJS, ProjectType.TYPESCRIPT):
        template = NEXTJS_TEMPLATE
    else:
        return []

    created = []
    for rel_path, content in template.items():
        file_path = root / rel_path
        if file_path.exists():
            continue

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        created.append(rel_path)

    return created


def get_init_preview(project_type: ProjectType, size: str = "medium") -> str:
    """Get preview of files that would be created.

    Args:
        project_type: Type of project.
        size: Project size preset.

    Returns:
        Formatted preview string.
    """
    if project_type == ProjectType.PYTHON:
        template = PYTHON_TEMPLATE
    elif project_type in (ProjectType.NEXTJS, ProjectType.TYPESCRIPT):
        template = NEXTJS_TEMPLATE
    else:
        return "Unsupported project type"

    lines = [
        f"# Clean Architecture Scaffold ({project_type.value})",
        "",
        "Files to create:",
        "",
    ]

    lines.extend(f"- `{rel_path}`" for rel_path in sorted(template.keys()))

    preset = LAYER_PRESETS.get(size, LAYER_PRESETS["medium"])
    lines.extend([
        "",
        f"Layer preset: {size}",
        "",
    ])

    for name, cfg in sorted(preset.items(), key=lambda x: x[1]["tier"]):
        lines.append(f"- TIER {cfg['tier']}: {name}")

    return "\n".join(lines)
