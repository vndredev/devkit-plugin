"""Core module - types, errors, constants.

TIER 0: No internal imports, only Python stdlib.

Exports:
- Error types: DevkitError, ConfigError, ValidationError, GitError, ArchitectureError
- Enums: HookType, HookAction, CommitType, ProjectType, ProjectSize
"""

from core.errors import (
    ArchitectureError,
    ConfigError,
    DevkitError,
    GitError,
    ValidationError,
)
from core.types import (
    CommitType,
    HookAction,
    HookType,
    ProjectSize,
    ProjectType,
)

__all__ = [
    "ArchitectureError",
    "CommitType",
    "ConfigError",
    "DevkitError",
    "GitError",
    "HookAction",
    "HookType",
    "ProjectSize",
    "ProjectType",
    "ValidationError",
]
