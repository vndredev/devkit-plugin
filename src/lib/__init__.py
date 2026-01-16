"""Lib module - I/O adapters.

TIER 1: May import from core only.
"""

from core.jsonc import strip_comments
from lib.config import clear_cache, get, get_project_root, load_config
from lib.docs import (
    generate_arch_docs,
    generate_claude_md,
    generate_plugin_md,
    get_docs_status,
    merge_sections,
    parse_sections,
    update_claude_md,
    update_plugin_md,
)
from lib.git import (
    extract_git_args,
    git_branch,
    git_commit,
    git_status,
    is_protected_branch,
    run_git,
)
from lib.hooks import (
    allow_response,
    consume_stdin,
    deny_response,
    load_prompts,
    noop_response,
    output_response,
    read_hook_input,
)
from lib.sync import check_sync_status, render_template, sync_all, sync_docs, sync_linters
from lib.tools import detect_project_type, detect_project_version, format_file, notify, run_linter

__all__ = [
    "allow_response",
    "check_sync_status",
    "clear_cache",
    "consume_stdin",
    "deny_response",
    "detect_project_type",
    "detect_project_version",
    "extract_git_args",
    "format_file",
    "generate_arch_docs",
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
    "load_prompts",
    "merge_sections",
    "noop_response",
    "notify",
    "output_response",
    "parse_sections",
    "read_hook_input",
    "render_template",
    "run_git",
    "run_linter",
    "strip_comments",
    "sync_all",
    "sync_docs",
    "sync_linters",
    "update_claude_md",
    "update_plugin_md",
]
