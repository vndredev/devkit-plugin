"""Architecture analysis module.

TIER 2: May import from core, lib.
"""

from .analyze import (
    analyze_dependencies,
    analyze_project_size,
    analyze_transitive_dependencies,
    extract_imports_from_content,
)
from .consistency import (
    check_consistency,
    check_module_tests,
    format_consistency_report,
    get_all_violations,
    get_missing_artifacts,
    get_violation_count,
)
from .discovery import (
    find_duplicates_for_name,
    find_similar_code,
    format_matches_report,
    scan_codebase,
)
from .docs import generate_architecture_md, update_architecture_md
from .rules import check_layer_rules, get_violations, init_project
from .visualize import (
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
    "extract_imports_from_content",
    "find_duplicates_for_name",
    "find_similar_code",
    "format_consistency_report",
    "format_matches_report",
    "generate_architecture_md",
    "generate_ascii_diagram",
    "generate_dependency_matrix",
    "generate_mermaid_diagram",
    "get_all_violations",
    "get_missing_artifacts",
    "get_violation_count",
    "get_violations",
    "init_project",
    "scan_codebase",
    "update_architecture_md",
]
