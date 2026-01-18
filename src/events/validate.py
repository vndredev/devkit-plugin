#!/usr/bin/env python3
"""PreToolUse hook handler.

Validates branch names, commit messages, and blocks dangerous commands.
"""

import os
import re
from pathlib import Path

from lib.config import get
from lib.git import extract_git_args
from lib.hooks import allow_response, deny_response, output_response, read_hook_input

# Default types if not configured
DEFAULT_TYPES = ["feat", "fix", "chore", "refactor", "test", "docs", "perf", "ci"]


def validate_branch_name(branch: str, prompt_tpl: str) -> tuple[bool, str]:
    """Validate branch name follows convention from config.

    Args:
        branch: Branch name to validate.
        prompt_tpl: Template for error message with {branch} and {pattern} placeholders.

    Returns:
        Tuple of (valid, message).
    """
    protected = get("git.protected_branches", ["main"])
    if branch in protected:
        return True, "Protected branch"

    # Get types from config (fallback to defaults if empty)
    types = get("git.conventions.types", DEFAULT_TYPES)
    if not types:
        types = DEFAULT_TYPES
    types_pattern = "|".join(types)

    # Get branch pattern from config (default: {type}/{description})
    branch_pattern = get("git.conventions.branch_pattern", "{type}/{description}")

    # Convert config pattern to regex
    # {type} -> (feat|fix|...), {description} -> [\w-]+
    regex_pattern = branch_pattern
    regex_pattern = regex_pattern.replace("{type}", f"({types_pattern})")
    regex_pattern = regex_pattern.replace("{description}", r"[\w-]+")
    regex_pattern = f"^{regex_pattern}$"

    if not re.match(regex_pattern, branch):
        # Show human-readable pattern in error
        display_pattern = branch_pattern.replace("{type}", f"{{{types_pattern}}}")
        return False, prompt_tpl.format(branch=branch, pattern=display_pattern)

    return True, "Valid branch name"


def validate_commit_message(
    msg: str, commit_invalid_tpl: str, scope_invalid_tpl: str
) -> tuple[bool, str]:
    """Validate commit message follows convention from config.

    Args:
        msg: Commit message to validate (first line only).
        commit_invalid_tpl: Template for invalid commit with {types} placeholder.
        scope_invalid_tpl: Template for invalid scope with {scope} and {allowed} placeholders.

    Returns:
        Tuple of (valid, message).
    """
    # Get config (fallback to defaults if empty)
    types = get("git.conventions.types", DEFAULT_TYPES)
    if not types:
        types = DEFAULT_TYPES
    scope_mode = get("git.conventions.scopes.mode", "strict")
    allowed_scopes = get("git.conventions.scopes.allowed", [])
    internal_scopes = get("git.conventions.scopes.internal", [])

    # Only validate first line (title)
    first_line = msg.strip().split("\n")[0]

    # Build pattern from config types
    # Supports: type(scope): msg, type(scope)!: msg (breaking change), type!: msg
    types_pattern = "|".join(types)
    pattern = rf"^({types_pattern})(\([^)]+\))?!?: .+"

    match = re.match(pattern, first_line)
    if not match:
        return False, commit_invalid_tpl.format(types=types_pattern)

    # Validate scope if present and mode is strict or warn
    scope_group = match.group(2)
    if scope_group:
        # Remove parentheses to get scope name
        scope = scope_group[1:-1]
        all_valid = allowed_scopes + internal_scopes

        # Check if scope is invalid
        scope_invalid = not all_valid or scope not in all_valid

        if scope_invalid:
            if scope_mode == "strict":
                # Strict mode: reject invalid scopes
                if all_valid:
                    return False, scope_invalid_tpl.format(
                        scope=scope, allowed=", ".join(all_valid)
                    )
                return False, scope_invalid_tpl.format(scope=scope, allowed="(none configured)")
            elif scope_mode == "warn":
                # Warn mode: return warning message but still valid
                if all_valid:
                    warning = f"⚠️ Warning: Unknown scope '{scope}'. Allowed: {', '.join(all_valid)}"
                else:
                    warning = f"⚠️ Warning: Scope '{scope}' used but no scopes configured"
                return True, warning

    return True, "Valid commit message"


def extract_commit_message(cmd: str) -> str | None:
    """Extract commit message from git commit command.

    Handles both simple -m "msg" and HEREDOC syntax.

    Args:
        cmd: Full git commit command string.

    Returns:
        Commit message or None if not found.
    """
    # Try HEREDOC first: git commit -m "$(cat <<'EOF'\nmessage\nEOF\n)"
    heredoc_patterns = [
        r'-m\s+"\$\(cat\s+<<[\'"]?EOF[\'"]?\s*\n(.+?)\nEOF',  # <<EOF or <<'EOF'
        r"-m\s+'\$\(cat\s+<<['\"]?EOF['\"]?\s*\n(.+?)\nEOF",  # single quotes
    ]
    for pattern in heredoc_patterns:
        match = re.search(pattern, cmd, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Try simple -m "message" or -m 'message'
    simple_patterns = [
        r'-m\s+"([^"]+)"',  # -m "message"
        r"-m\s+'([^']+)'",  # -m 'message'
    ]
    for pattern in simple_patterns:
        match = re.search(pattern, cmd)
        if match:
            return match.group(1)

    return None


# Default blocked gh commands (used if not configured)
DEFAULT_BLOCKED_GH_COMMANDS = [
    "gh repo delete",
    "gh secret delete",
    "gh api -X DELETE",
]

# Commands that must use /dk alternatives
DK_COMMAND_MAPPINGS = {
    "gh pr create": "/dk git pr",
    "gh pr merge": "/dk git pr merge",
    "vercel deploy": "/dk vercel deploy",
    "vercel env": "/dk vercel env",
}


def is_plugin_self_development() -> bool:
    """Check if we're developing the devkit-plugin itself.

    When working in the plugin's own directory, we need to allow raw commands
    because /dk workflows internally use these commands.

    Note: Hooks run from CLAUDE_PLUGIN_ROOT, so we must check CLAUDE_PROJECT_DIR
    (the user's actual project directory) instead of cwd.

    Returns:
        True if CLAUDE_PROJECT_DIR matches CLAUDE_PLUGIN_ROOT (self-development mode).
    """
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")

    if not plugin_root or not project_dir:
        return False

    try:
        plugin_path = Path(plugin_root).resolve()
        project_path = Path(project_dir).resolve()
        return project_path == plugin_path
    except (OSError, ValueError):
        return False


def validate_dk_enforcement(cmd: str) -> tuple[bool, str]:
    """Check if command should use /dk alternative.

    Only checks if the command STARTS with a blocked command (not substring match).
    This avoids false positives in commit messages or other text.

    Args:
        cmd: Full command string.

    Returns:
        Tuple of (valid, message). If invalid, message contains the /dk alternative.
    """
    cmd_stripped = cmd.strip()
    for raw_cmd, dk_cmd in DK_COMMAND_MAPPINGS.items():
        if cmd_stripped.startswith(raw_cmd):
            return False, f"🚫 Use `{dk_cmd}` instead of `{raw_cmd}`"
    return True, ""


def validate_gh_command(
    cmd: str, gh_blocked_tpl: str, pr_missing_body_tpl: str
) -> tuple[bool, str]:
    """Validate gh CLI commands.

    Blocks dangerous commands like repo delete, secret delete.
    Blocked commands are read from config (hooks.validate.blocked_commands).

    Args:
        cmd: Full command string.
        gh_blocked_tpl: Template for blocked command with {cmd} placeholder.
        pr_missing_body_tpl: Template for missing PR body.

    Returns:
        Tuple of (valid, message).
    """
    # Get blocked commands from config (fallback to defaults)
    blocked_commands = get("hooks.validate.blocked_commands", DEFAULT_BLOCKED_GH_COMMANDS)

    # Check for blocked commands
    for blocked in blocked_commands:
        if blocked in cmd:
            return False, gh_blocked_tpl.format(cmd=blocked)

    # Warn if pr create without --body (should use template)
    if "gh pr create" in cmd and "--body" not in cmd:
        return False, pr_missing_body_tpl

    return True, "Valid gh command"


def main() -> None:
    """Handle PreToolUse hook."""
    # Read hook data
    hook_data = read_hook_input()
    if not hook_data:
        allow_response()
        return

    # Check if hook is enabled
    if not get("hooks.validate.enabled", True):
        allow_response()
        return

    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})

    # Only validate Bash commands
    if tool_name != "Bash":
        allow_response()
        return

    # Load prompts from config
    prompts = get("hooks.validate.prompts", {})
    branch_invalid_tpl = prompts.get("branch_invalid", "Branch '{branch}' should match: {pattern}")
    commit_invalid_tpl = prompts.get(
        "commit_invalid", "Commit should match: type(scope): message (types: {types})"
    )
    scope_invalid_tpl = prompts.get("scope_invalid", "Unknown scope '{scope}'. Allowed: {allowed}")
    force_push_tpl = prompts.get(
        "force_push_blocked", "Force push is blocked. Use --force-with-lease if needed."
    )
    gh_blocked_tpl = prompts.get(
        "gh_blocked", "Blocked: '{cmd}' - too dangerous for automatic execution"
    )
    pr_missing_body_tpl = prompts.get(
        "pr_missing_body", "gh pr create requires --body with PR template"
    )

    command = tool_input.get("command", "")

    # Enforce /dk commands (check first, before other validations)
    # Skip enforcement when developing the plugin itself (self-development mode)
    enforce_dk = get("hooks.validate.enforce_dk_commands", True)
    if enforce_dk and not is_plugin_self_development():
        valid, msg = validate_dk_enforcement(command)
        if not valid:
            deny_response(msg)
            return

    # Validate gh commands
    if command.startswith("gh "):
        block_gh = get("hooks.validate.block_dangerous_gh", True)
        if block_gh:
            valid, msg = validate_gh_command(command, gh_blocked_tpl, pr_missing_body_tpl)
            if not valid:
                deny_response(msg)
                return
        allow_response()
        return

    # Validate git commands
    if not command.startswith("git "):
        allow_response()
        return

    subcmd, args = extract_git_args(command)

    # Block dangerous commands (--force-with-lease is allowed as safe alternative)
    block_force = get("hooks.validate.block_force_push", True)
    has_force_with_lease = "--force-with-lease" in args
    is_force_push = (
        subcmd == "push" and ("--force" in args or "-f" in args) and not has_force_with_lease
    )
    if block_force and is_force_push:
        deny_response(force_push_tpl)
        return

    # Validate branch creation
    if subcmd == "checkout" and "-b" in args:
        try:
            idx = args.index("-b")
            if idx + 1 < len(args):
                branch = args[idx + 1]
                valid, msg = validate_branch_name(branch, branch_invalid_tpl)
                if not valid:
                    deny_response(msg)
        except (ValueError, IndexError):
            pass

    # Validate commit message (supports both -m "msg" and HEREDOC)
    if subcmd == "commit" and "-m" in command:
        msg = extract_commit_message(command)
        if msg:
            valid, result_msg = validate_commit_message(msg, commit_invalid_tpl, scope_invalid_tpl)
            if not valid:
                deny_response(result_msg)
                return
            # Check if result_msg is a warning (warn mode)
            if result_msg.startswith("⚠️"):
                output_response(
                    {
                        "continue": True,
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "additionalContext": result_msg,
                        },
                    }
                )
                return

    # All validations passed
    allow_response()
    return


if __name__ == "__main__":
    main()
