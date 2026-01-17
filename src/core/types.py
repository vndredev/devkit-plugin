"""Core types and enums.

TIER 0: No internal imports, only Python stdlib.
"""

from enum import Enum


class ProjectType(str, Enum):
    """Supported project types.

    Base types: python, node
    Framework types: nextjs, typescript, javascript (all node-based)
    Special types: claude-code-plugin (Claude Code plugins)
    """

    PYTHON = "python"
    NODE = "node"
    NEXTJS = "nextjs"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    CLAUDE_PLUGIN = "claude-code-plugin"
    UNKNOWN = "unknown"

    def is_node_based(self) -> bool:
        """Check if project type is Node.js based."""
        return self in (
            ProjectType.NODE,
            ProjectType.NEXTJS,
            ProjectType.TYPESCRIPT,
            ProjectType.JAVASCRIPT,
        )

    def is_plugin(self) -> bool:
        """Check if project type is a Claude Code plugin."""
        return self == ProjectType.CLAUDE_PLUGIN


class ProjectSize(str, Enum):
    """Project size categories for architecture recommendations."""

    SMALL = "small"  # < 10 files, 2 layers
    MEDIUM = "medium"  # 10-30 files, 3 layers
    LARGE = "large"  # 30-100 files, 4 layers
    ENTERPRISE = "enterprise"  # 100+ files, 5 layers


class CommitType(str, Enum):
    """Conventional commit types."""

    FEAT = "feat"
    FIX = "fix"
    CHORE = "chore"
    REFACTOR = "refactor"
    TEST = "test"
    DOCS = "docs"
    PERF = "perf"
    CI = "ci"


class HookType(str, Enum):
    """Claude Code hook types."""

    SESSION_START = "SessionStart"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"


class HookAction(str, Enum):
    """Hook response actions."""

    ALLOW = "allow"
    DENY = "deny"
    MODIFY = "modify"


# Changelog section mapping
CHANGELOG_SECTIONS = {
    CommitType.FEAT: "Added",
    CommitType.FIX: "Fixed",
    CommitType.REFACTOR: "Changed",
    CommitType.PERF: "Changed",
    CommitType.TEST: "Tests",
    CommitType.DOCS: "Documentation",
    CommitType.CHORE: "Maintenance",
    CommitType.CI: "Maintenance",
}
