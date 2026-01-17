"""Custom exceptions for devkit-plugin.

TIER 0: No internal imports, only Python stdlib.
"""


class DevkitError(Exception):
    """Base exception for devkit-plugin."""

    pass


class ConfigError(DevkitError):
    """Configuration error."""

    pass


class ValidationError(DevkitError):
    """Validation failed."""

    pass


class GitError(DevkitError):
    """Git operation failed."""

    pass


class ArchitectureError(DevkitError):
    """Architecture rule violation."""

    pass


class GitHubError(DevkitError):
    """GitHub API operation failed."""

    pass


class ProtectionError(GitHubError):
    """Branch protection operation failed."""

    pass
