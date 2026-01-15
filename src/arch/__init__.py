"""Architecture analysis module.

TIER 2: May import from core, lib.
"""

from arch.analyze import (
    analyze_dependencies,
    analyze_project_size,
    analyze_transitive_dependencies,
)
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
    "check_layer_rules",
    "generate_ascii_diagram",
    "generate_dependency_matrix",
    "generate_mermaid_diagram",
    "get_violations",
    "init_project",
]
