"""Core module - types, errors, constants, ports.

TIER 0: No internal imports, only Python stdlib.

Exports:
- Error types: DevkitError, ConfigError, ValidationError, GitError, ArchitectureError
- Enums: HookType, HookAction, CommitType, ProjectType, ProjectSize
- Ports: ConfigPort, GitPort, SyncPort, DocsPort, AnalyzerPort, VisualizerPort
- Layer Guard: enable_layer_guard, disable_layer_guard, LayerViolationError
"""

from core.errors import (
    ArchitectureError,
    ConfigError,
    DevkitError,
    GitError,
    ValidationError,
)
from core.jsonc import strip_comments
from core.layer_guard import (
    LayerViolationError,
    clear_violations,
    disable_layer_guard,
    enable_layer_guard,
    format_violations_report,
    get_violations,
    is_enabled,
)
from core.ports import (
    AnalyzerPort,
    ConfigPort,
    DocsPort,
    GitPort,
    SyncPort,
    VisualizerPort,
    verify_port,
)
from core.types import (
    CommitType,
    HookAction,
    HookType,
    ProjectSize,
    ProjectType,
)

__all__ = [
    "AnalyzerPort",
    "ArchitectureError",
    "CommitType",
    "ConfigError",
    "ConfigPort",
    "DevkitError",
    "DocsPort",
    "GitError",
    "GitPort",
    "HookAction",
    "HookType",
    "LayerViolationError",
    "ProjectSize",
    "ProjectType",
    "SyncPort",
    "ValidationError",
    "VisualizerPort",
    "clear_violations",
    "disable_layer_guard",
    "enable_layer_guard",
    "format_violations_report",
    "get_violations",
    "is_enabled",
    "strip_comments",
    "verify_port",
]
