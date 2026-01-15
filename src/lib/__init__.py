"""Lib module - I/O adapters.

TIER 1: May import from core only.
"""

from lib.config import clear_cache, get, get_project_root, load_config
from lib.docs import (
    generate_claude_md,
    generate_plugin_md,
    get_docs_status,
    merge_sections,
    parse_sections,
    render_template,
    update_claude_md,
    update_plugin_md,
)
from lib.git import git_branch, git_commit, git_status, is_protected_branch, run_git
from lib.sync import check_sync_status, sync_all, sync_docs, sync_linters
from lib.tools import detect_project_type, format_file, notify, run_linter

__all__ = [
    "check_sync_status",
    "clear_cache",
    "detect_project_type",
    "format_file",
    "generate_claude_md",
    "generate_plugin_md",
    "get",
    "get_docs_status",
    "get_project_root",
    "git_branch",
    "git_commit",
    "git_status",
    "is_protected_branch",
    "load_config",
    "merge_sections",
    "notify",
    "parse_sections",
    "render_template",
    "run_git",
    "run_linter",
    "sync_all",
    "sync_docs",
    "sync_linters",
    "update_claude_md",
    "update_plugin_md",
]
