"""Port interfaces for Clean Architecture.

TIER 0: No internal imports, only Python stdlib.

Ports define contracts that adapters must implement.
This allows the core to depend on abstractions, not implementations.

Usage:
    # In core/lib - define what you need
    class ConfigPort(Protocol):
        def get(self, key: str) -> Any: ...

    # In lib - implement the port
    class ConfigAdapter:
        def get(self, key: str) -> Any:
            return load_config().get(key)
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConfigPort(Protocol):
    """Port for configuration access.

    Implemented by: lib.config
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        ...

    def get_project_root(self) -> Any:
        """Get project root directory."""
        ...

    def load_config(self) -> dict[str, Any]:
        """Load full configuration."""
        ...


@runtime_checkable
class GitPort(Protocol):
    """Port for Git operations.

    Implemented by: lib.git
    """

    def status(self) -> dict[str, list[str]]:
        """Get git status with staged, modified, untracked files."""
        ...

    def branch(self) -> str:
        """Get current branch name."""
        ...

    def commit(self, message: str) -> tuple[bool, str]:
        """Create a commit with the given message."""
        ...


@runtime_checkable
class SyncPort(Protocol):
    """Port for file synchronization.

    Implemented by: lib.sync
    """

    def sync_all(self) -> list[tuple[str, bool, str]]:
        """Sync all managed files."""
        ...

    def render_template(self, template: str, values: dict[str, Any]) -> str:
        """Render a template with values."""
        ...


@runtime_checkable
class DocsPort(Protocol):
    """Port for documentation generation.

    Implemented by: lib.docs
    """

    def generate_arch_docs(self, format: str = "full") -> str:
        """Generate architecture documentation."""
        ...

    def update_claude_md(self) -> tuple[bool, str]:
        """Update CLAUDE.md file."""
        ...


@runtime_checkable
class AnalyzerPort(Protocol):
    """Port for architecture analysis.

    Implemented by: arch.analyze
    """

    def analyze_dependencies(self) -> dict[str, Any]:
        """Analyze project dependencies and violations."""
        ...

    def analyze_transitive_dependencies(self) -> dict[str, Any]:
        """Analyze transitive dependency chains."""
        ...


@runtime_checkable
class VisualizerPort(Protocol):
    """Port for architecture visualization.

    Implemented by: arch.visualize
    """

    def generate_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram."""
        ...

    def generate_ascii_diagram(self) -> str:
        """Generate ASCII diagram."""
        ...


def verify_port(implementation: Any, port: type) -> bool:
    """Verify that an implementation satisfies a port.

    Args:
        implementation: Object to verify.
        port: Protocol class to check against.

    Returns:
        True if implementation satisfies the port.

    Example:
        from lib import config
        from core.ports import ConfigPort, verify_port

        assert verify_port(config, ConfigPort)
    """
    return isinstance(implementation, port)
