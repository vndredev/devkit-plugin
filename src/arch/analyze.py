"""Dependency analysis for Clean Architecture.

TIER 2: May import from core, lib.
Supports Python (AST) and TypeScript (regex).
"""

import ast
import contextlib
import re
from collections import defaultdict
from pathlib import Path

from core.types import ProjectSize, ProjectType
from lib.config import get
from lib.tools import detect_project_type

TS_IMPORT_PATTERNS = [
    r"import\s+\w+\s+from\s+['\"]([^'\"]+)['\"]",
    r"import\s+\{[^}]+\}\s+from\s+['\"]([^'\"]+)['\"]",
    r"import\s+\*\s+as\s+\w+\s+from\s+['\"]([^'\"]+)['\"]",
    r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    r"export\s+\{[^}]+\}\s+from\s+['\"]([^'\"]+)['\"]",
]


def count_source_files(root: Path, project_type: ProjectType) -> int:
    """Count source files in project.

    Args:
        root: Project root.
        project_type: Type of project.

    Returns:
        Number of source files.
    """
    extensions = {
        ProjectType.PYTHON: [".py"],
        ProjectType.TYPESCRIPT: [".ts", ".tsx"],
        ProjectType.NEXTJS: [".ts", ".tsx", ".js", ".jsx"],
        ProjectType.JAVASCRIPT: [".js", ".jsx"],
    }

    exts = extensions.get(project_type, [".py", ".ts", ".tsx", ".js", ".jsx"])
    count = 0

    for ext in exts:
        count += len(list(root.rglob(f"*{ext}")))

    # Exclude node_modules, .next, __pycache__, etc.
    return count


def count_lines_of_code(root: Path, project_type: ProjectType) -> int:
    """Count lines of code in project.

    Args:
        root: Project root.
        project_type: Type of project.

    Returns:
        Total lines of code.
    """
    extensions = {
        ProjectType.PYTHON: [".py"],
        ProjectType.TYPESCRIPT: [".ts", ".tsx"],
        ProjectType.NEXTJS: [".ts", ".tsx", ".js", ".jsx"],
        ProjectType.JAVASCRIPT: [".js", ".jsx"],
    }

    exts = extensions.get(project_type, [".py", ".ts", ".tsx", ".js", ".jsx"])
    exclude_dirs = {"node_modules", ".next", "__pycache__", ".venv", "dist", "build"}
    total = 0

    for ext in exts:
        for filepath in root.rglob(f"*{ext}"):
            # Skip excluded directories
            if any(d in filepath.parts for d in exclude_dirs):
                continue
            with contextlib.suppress(OSError, UnicodeDecodeError):
                total += len(filepath.read_text().splitlines())

    return total


def analyze_project_size(root: Path) -> dict:
    """Analyze project size and recommend architecture.

    Args:
        root: Project root directory.

    Returns:
        Dict with size info and recommendation.
    """
    project_type = detect_project_type(root)
    files = count_source_files(root, project_type)
    loc = count_lines_of_code(root, project_type)

    if files < 10 or loc < 500:
        size = ProjectSize.SMALL
        layers = 2
        recommendation = ["lib", "entry"]
    elif files < 30 or loc < 2000:
        size = ProjectSize.MEDIUM
        layers = 3
        recommendation = ["core", "lib", "entry"]
    elif files < 100 or loc < 10000:
        size = ProjectSize.LARGE
        layers = 4
        recommendation = ["core", "lib", "services", "entry"]
    else:
        size = ProjectSize.ENTERPRISE
        layers = 5
        recommendation = ["core", "domain", "adapters", "usecases", "entry"]

    return {
        "project_type": project_type.value,
        "size": size.value,
        "files": files,
        "loc": loc,
        "recommended_layers": layers,
        "recommended_structure": recommendation,
    }


def extract_python_imports(file_path: Path) -> list[str]:
    """Extract imports from a Python file using AST.

    Args:
        file_path: Path to Python file.

    Returns:
        List of imported module names.
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])

    return imports


def extract_ts_imports(file_path: Path) -> list[str]:
    """Extract imports from a TypeScript/JavaScript file using regex.

    Args:
        file_path: Path to TS/JS file.

    Returns:
        List of imported paths.
    """
    try:
        content = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        return []

    imports = []
    for pattern in TS_IMPORT_PATTERNS:
        imports.extend(re.findall(pattern, content))

    return imports


def normalize_ts_import(imp: str, file_path: Path, root: Path) -> str | None:
    """Normalize TypeScript import to layer name.

    Args:
        imp: Import path (e.g., '@/lib/utils', '../core/types').
        file_path: File containing the import.
        root: Project root.

    Returns:
        Layer name or None if external.
    """
    # Skip external packages
    if not imp.startswith(".") and not imp.startswith("@/"):
        return None

    # Handle @/ alias (maps to src/)
    if imp.startswith("@/"):
        imp = imp[2:]  # Remove @/

    # Get first directory as layer
    parts = imp.split("/")
    if parts:
        layer = parts[0].lstrip(".")
        if layer in ("", ".."):
            # Relative import, resolve from file path
            try:
                resolved = (file_path.parent / imp).resolve()
                rel = resolved.relative_to(root / "src")
                layer = rel.parts[0] if rel.parts else None
            except (ValueError, IndexError):
                return None
        return layer

    return None


def get_dependency_graph(
    root: Path,
    project_type: ProjectType,
) -> dict[str, list[str]]:
    """Build dependency graph for project.

    Args:
        root: Project root directory.
        project_type: Type of project.

    Returns:
        Dict mapping file paths to their imports.
    """
    graph: dict[str, list[str]] = {}
    exclude_dirs = {"node_modules", ".next", "__pycache__", ".venv", "dist", "build"}

    if project_type == ProjectType.PYTHON:
        src_dir = root / "src"
        if not src_dir.exists():
            src_dir = root / "hooks"
        if not src_dir.exists():
            return graph

        for py_file in src_dir.rglob("*.py"):
            if any(d in py_file.parts for d in exclude_dirs):
                continue

            rel_path = str(py_file.relative_to(root))
            imports = extract_python_imports(py_file)

            # Filter to project imports
            layers = list(get("arch.layers", {}).keys())
            if not layers:
                layers = [
                    "core",
                    "lib",
                    "arch",
                    "events",
                    "domain",
                    "adapters",
                    "usecases",
                    "entry",
                ]

            project_imports = [imp for imp in imports if imp in layers]
            if project_imports:
                graph[rel_path] = project_imports

    else:  # TypeScript/JavaScript/Next.js
        src_dir = root / "src"
        if not src_dir.exists():
            src_dir = root / "app"
        if not src_dir.exists():
            return graph

        for ts_file in src_dir.rglob("*"):
            if ts_file.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            if any(d in ts_file.parts for d in exclude_dirs):
                continue

            rel_path = str(ts_file.relative_to(root))
            imports = extract_ts_imports(ts_file)

            # Normalize imports to layer names
            layers = []
            for imp in imports:
                layer = normalize_ts_import(imp, ts_file, root)
                if layer:
                    layers.append(layer)

            if layers:
                graph[rel_path] = layers

    return graph


def analyze_dependencies(root: Path) -> dict:
    """Analyze project dependencies and detect violations.

    Args:
        root: Project root directory.

    Returns:
        Analysis result with graph, violations, and stats.
    """
    project_type = detect_project_type(root)
    graph = get_dependency_graph(root, project_type)
    size_info = analyze_project_size(root)

    # Load layer rules from config
    layer_config = get("arch.layers", {})

    # Build layer order from config or use defaults
    if layer_config:
        layer_order = {name: cfg.get("tier", 0) for name, cfg in layer_config.items()}
    else:
        # Default Python layers
        layer_order = {
            "core": 0,
            "lib": 1,
            "arch": 2,
            "events": 3,
            "domain": 1,
            "adapters": 2,
            "usecases": 3,
            "entry": 4,
        }

    violations = []
    layer_stats: dict[str, int] = defaultdict(int)

    for file_path, imports in graph.items():
        # Determine source layer from file path
        parts = Path(file_path).parts
        if len(parts) < 2:
            continue

        source_module = parts[1]  # src/MODULE/... or hooks/MODULE/...
        source_layer = layer_order.get(source_module)

        if source_layer is None:
            continue

        layer_stats[source_module] += 1

        # Check each import
        for imp in imports:
            target_layer = layer_order.get(imp)
            if target_layer is None:
                continue

            # Violation: importing from higher layer
            # (except entry which can import anything)
            max_tier = max(layer_order.values())
            if source_layer < max_tier and target_layer > source_layer:
                msg = (
                    f"{source_module} (TIER {source_layer}) "
                    f"cannot import from {imp} (TIER {target_layer})"
                )
                violations.append(
                    {
                        "file": file_path,
                        "source_layer": source_module,
                        "imports": imp,
                        "target_layer": target_layer,
                        "message": msg,
                    }
                )

    return {
        "project_type": project_type.value,
        "size": size_info,
        "graph": graph,
        "violations": violations,
        "stats": {
            "total_files": len(graph),
            "layers": dict(layer_stats),
            "violation_count": len(violations),
        },
    }


def analyze_transitive_dependencies(root: Path) -> dict:
    """Find transitive layer violations (A→B→C chains).

    Detects indirect violations where A imports B and B imports C,
    but A should not have access to C based on layer rules.

    Args:
        root: Project root directory.

    Returns:
        Dict with transitive violations and dependency chains.
    """
    project_type = detect_project_type(root)
    graph = get_dependency_graph(root, project_type)

    # Load layer rules from config
    layer_config = get("arch.layers", {})
    if layer_config:
        layer_order = {name: cfg.get("tier", 0) for name, cfg in layer_config.items()}
    else:
        layer_order = {
            "core": 0,
            "lib": 1,
            "arch": 2,
            "events": 3,
            "domain": 1,
            "adapters": 2,
            "usecases": 3,
            "entry": 4,
        }

    # Build layer-to-layer dependency map
    layer_deps: dict[str, set[str]] = defaultdict(set)

    for file_path, imports in graph.items():
        parts = Path(file_path).parts
        if len(parts) < 2:
            continue
        source_layer = parts[1]
        for imp in imports:
            if imp in layer_order:
                layer_deps[source_layer].add(imp)

    # Find transitive dependencies (A→B→C)
    transitive_violations = []
    chains = []

    for layer_a, direct_deps in layer_deps.items():
        tier_a = layer_order.get(layer_a, -1)
        if tier_a == -1:
            continue

        for layer_b in direct_deps:
            tier_b = layer_order.get(layer_b, -1)
            if tier_b == -1:
                continue

            # Check what B imports (transitive)
            for layer_c in layer_deps.get(layer_b, set()):
                tier_c = layer_order.get(layer_c, -1)
                if tier_c == -1:
                    continue

                # Record chain
                chain = f"{layer_a} → {layer_b} → {layer_c}"
                chains.append(
                    {
                        "chain": chain,
                        "tiers": f"T{tier_a} → T{tier_b} → T{tier_c}",
                    }
                )

                # Check for transitive violation
                # (A imports B imports C, but A should not access C directly)
                if tier_c < tier_a:
                    transitive_violations.append(
                        {
                            "source": layer_a,
                            "via": layer_b,
                            "target": layer_c,
                            "message": (
                                f"{layer_a} (T{tier_a}) has transitive access to "
                                f"{layer_c} (T{tier_c}) via {layer_b}"
                            ),
                        }
                    )

    return {
        "layer_dependencies": {k: list(v) for k, v in layer_deps.items()},
        "chains": chains,
        "transitive_violations": transitive_violations,
        "stats": {
            "total_chains": len(chains),
            "violation_count": len(transitive_violations),
        },
    }


def format_analysis_report(analysis: dict) -> str:
    """Format analysis result as readable report.

    Args:
        analysis: Result from analyze_dependencies().

    Returns:
        Formatted report string.
    """
    size = analysis["size"]
    lines = [
        "# Architecture Analysis",
        "",
        f"**Project Type:** {analysis['project_type']}",
        f"**Size:** {size['size']} ({size['files']} files, ~{size['loc']} LoC)",
        f"**Recommended Layers:** {size['recommended_layers']}",
        "",
        f"**Files Analyzed:** {analysis['stats']['total_files']}",
        "",
        "## Layer Distribution",
    ]

    for layer, count in sorted(analysis["stats"]["layers"].items()):
        lines.append(f"- **{layer}**: {count} files")

    if analysis["violations"]:
        lines.extend(
            [
                "",
                f"## Violations ({len(analysis['violations'])})",
                "",
            ]
        )
        lines.extend(f"- **{v['file']}**: {v['message']}" for v in analysis["violations"])
    else:
        lines.extend(
            [
                "",
                "## No Violations",
                "",
                "All imports follow layer rules.",
            ]
        )

    return "\n".join(lines)
