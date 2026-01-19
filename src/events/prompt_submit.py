#!/usr/bin/env python3
"""UserPromptSubmit hook - enforces plugin rules on every prompt.

TIER 3: events layer.

Injects critical workflow rules and constraints with every user prompt
to ensure Claude follows the plugin conventions consistently.
"""

import json
import sys

from lib.config import get
from lib.git import git_branch, is_protected_branch
from lib.hooks import output_response, read_hook_input


def build_rules_context(branch: str, on_protected: bool) -> str:
    """Build comprehensive rules context for Claude.

    Args:
        branch: Current git branch name.
        on_protected: Whether on protected branch.

    Returns:
        Rules context string.
    """
    lines = ["<user-prompt-submit-hook>"]
    lines.append(f"Current branch: `{branch}` {'(protected)' if on_protected else ''}")
    lines.append("")

    # Critical workflow rules
    lines.append("## CRITICAL RULES - YOU MUST FOLLOW")
    lines.append("")

    # Branch-specific rules
    if on_protected:
        lines.append("### Protected Branch Rules")
        lines.append("- For ANY code changes: suggest `/dk dev feat|fix|chore <desc>` FIRST")
        lines.append("- Example: `/dk dev fix auth-bug` creates branch + enters plan mode")
        lines.append("- Questions/analysis: no branch needed")
        lines.append("")

    # Plan mode rules for feat/refactor branches
    if branch.startswith(("feat/", "refactor/")):
        lines.append("### Plan Mode Required")
        lines.append("- This branch requires plan approval before code changes")
        lines.append("- Use `EnterPlanMode` → create plan → `ExitPlanMode` to approve")
        lines.append("")

    # Universal rules
    lines.append("### Command Enforcement")
    lines.append("- NEVER use raw `git`, `gh`, `vercel` commands directly")
    lines.append("- ALWAYS use `/dk` commands: `/dk git pr`, `/dk vercel deploy`, etc.")
    lines.append("- For PRs: ONLY use `/dk git pr` (never `gh pr create`)")
    lines.append("")

    lines.append("### Architecture Rules")
    lines.append("- Respect layer boundaries (imports only from lower tiers)")
    lines.append("- If you see 'LAYER VIOLATION' error: fix IMMEDIATELY")
    lines.append("")

    lines.append("### After Code Changes")
    lines.append("- ALWAYS offer to create PR: 'Shall I create a PR? (`/dk git pr`)'")
    lines.append("")

    lines.append("</user-prompt-submit-hook>")

    return "\n".join(lines)


def main() -> None:
    """Handle UserPromptSubmit hook."""
    _ = read_hook_input()  # Consume stdin (hook protocol)

    # Check if hook is enabled
    if not get("hooks.prompt_submit.enabled", True):
        output_response({})
        return

    # Check enforcement mode
    enforce_mode = get("hooks.prompt_submit.enforce_workflow", "warn")
    if enforce_mode == "off":
        output_response({})
        return

    # Get current branch
    try:
        branch = git_branch()
    except Exception:
        # Not in git repo - still inject basic rules
        branch = "unknown"

    protected = get("git.protected_branches", ["main", "master"])
    on_protected = is_protected_branch(protected)

    # Build comprehensive rules context
    rules_context = build_rules_context(branch, on_protected)

    output_response(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": rules_context,
            }
        }
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # On error, allow but report
        print(json.dumps({"continue": True, "message": f"⚠️ Prompt submit hook error: {e}"}))
        sys.exit(0)
