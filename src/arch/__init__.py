"""Architecture analysis module.

TIER 2: May import from core, lib.
"""

from arch.analyze import analyze_dependencies, analyze_project_size
from arch.rules import check_layer_rules, get_violations, init_project

__all__ = [
    "analyze_dependencies",
    "analyze_project_size",
    "check_layer_rules",
    "get_violations",
    "init_project",
]
