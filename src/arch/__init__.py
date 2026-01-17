"""Architecture analysis module.

TIER 2: May import from core, lib.
"""

from arch.analyze import (
    analyze_dependencies,
    analyze_project_size,
    analyze_transitive_dependencies,
)
from arch.consistency import (
    check_consistency,
    check_module_tests,
    format_consistency_report,
    get_all_violations,
    get_missing_artifacts,
    get_violation_count,
)
from arch.docs import generate_architecture_md, update_architecture_md
from arch.rules import check_layer_rules, get_violations, init_project
from arch.visualize import (
    generate_ascii_diagram,
    generate_dependency_matrix,
    generate_mermaid_diagram,
)

__all__ = [
    "analyze_dependencies",
    "analyze_project_size",
    "analyze_transitive_dependencies",
    "check_consistency",
    "check_layer_rules",
    "check_module_tests",
    "format_consistency_report",
    "generate_architecture_md",
    "generate_ascii_diagram",
    "generate_dependency_matrix",
    "generate_mermaid_diagram",
    "get_all_violations",
    "get_missing_artifacts",
    "get_violation_count",
    "get_violations",
    "init_project",
    "update_architecture_md",
]
