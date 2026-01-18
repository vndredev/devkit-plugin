#!/usr/bin/env python3
"""SessionStart hook handler.

Displays git status, config info, health check, and dev workflow reminder.
"""

from pathlib import Path
from subprocess import SubprocessError

from arch.check import check_all, format_compact
from core.errors import GitError
from lib.config import get
from lib.git import check_https_with_workflows, git_branch, git_status
from lib.hooks import consume_stdin, get_project_dir, output_response
from lib.sync import sync_all
from lib.version import (
    check_plugin_update,
    get_plugin_dev_recommendation,
    is_plugin_loaded_via_plugin_dir,
)


def main() -> None:
    """Handle SessionStart hook."""
    # Consume stdin (hook data not needed)
    consume_stdin()

    # Check if hook is enabled
    if not get("hooks.session.enabled", True):
        output_response({"hookSpecificOutput": {"hookEventName": "SessionStart"}})
        return

    # Load prompts from config
    prompts = get("hooks.session.prompts", {})
    branch_tpl = prompts.get("branch", "📍 {branch}")
    staged_tpl = prompts.get("staged", "⚡{count} staged")
    modified_tpl = prompts.get("modified", "✏️{count} modified")
    untracked_tpl = prompts.get("untracked", "❓{count} untracked")
    hint_tpl = prompts.get("hint", "Use `/dk` for commands, `/dk dev` for workflow")

    # Gather context - only show what's relevant
    output_lines: list[str] = []
    has_issues = False

    # Dev mode - show (dev) indicator only when loaded via --plugin-dir
    dev_mode_indicator = ""
    try:
        project_dir = get_project_dir()

        if is_plugin_loaded_via_plugin_dir(project_dir):
            dev_mode_indicator = " (dev)"
    except (ImportError, OSError):
        # Fallback to cwd if project dir detection fails
        project_dir = Path.cwd()

    # Git status - compact format
    if get("hooks.session.show_git_status", True):
        try:
            branch = git_branch(cwd=project_dir)
            status = git_status(cwd=project_dir)

            git_parts = [branch_tpl.format(branch=branch) + dev_mode_indicator]
            if status["staged"]:
                git_parts.append(staged_tpl.format(count=len(status["staged"])))
            if status["modified"]:
                git_parts.append(modified_tpl.format(count=len(status["modified"])))
            if status["untracked"]:
                git_parts.append(untracked_tpl.format(count=len(status["untracked"])))

            output_lines.append(" | ".join(git_parts))

            # Workflow reminder if on protected branch
            protected = get("git.protected_branches", ["main", "master"])
            if branch in protected:
                # Check both plan and format enforcement (either enables warning)
                plan_enforce = get("hooks.plan.enforce_workflow", "warn")
                format_enforce = get("hooks.format.enforce_workflow", "warn")
                if plan_enforce != "off" or format_enforce != "off":
                    protected_tpl = prompts.get(
                        "protected_branch",
                        "⚠️ On `{branch}` - use `/dk dev feat|fix|chore <desc>` first!",
                    )
                    output_lines.append("")
                    output_lines.append(protected_tpl.format(branch=branch))
        except (SubprocessError, OSError, GitError):
            pass

    # Health check - auto-sync outdated files if enabled
    try:
        health_results = check_all()

        # Auto-sync if there are sync issues and auto_sync is enabled
        auto_sync_enabled = get("hooks.session.auto_sync", True)
        sync_issues = health_results.get("sync", {}).get("issues", [])

        if auto_sync_enabled and sync_issues:
            # Run sync to fix outdated files
            sync_results = sync_all(root=project_dir, check_plugin_update=False)
            synced_count = sum(1 for _, ok, _ in sync_results if ok)

            if synced_count > 0:
                output_lines.append("")
                output_lines.append(f"📄 Auto-synced {synced_count} file(s)")

            # Re-check health after sync
            health_results = check_all()

        health_warning = format_compact(health_results)
        if health_warning:
            output_lines.append("")
            output_lines.append(health_warning)
            has_issues = True
    except (ImportError, OSError):
        pass

    # Plugin update check - skip in dev mode (we're developing locally)
    if not dev_mode_indicator:
        try:
            update_available, current, latest = check_plugin_update()
            if update_available and latest:
                output_lines.append("")
                output_lines.append(f"🔄 Plugin update: {current or 'unknown'} → {latest}")
                output_lines.append("   Run `/dk plugin update` to update")
                has_issues = True
        except (ImportError, OSError):
            pass

    # Plugin development recommendation - if working on a plugin project
    # but not loaded via --plugin-dir
    try:
        plugin_dev_cmd = get_plugin_dev_recommendation(project_dir)
        if plugin_dev_cmd:
            output_lines.append("")
            output_lines.append("🔌 Plugin project detected - for live testing:")
            output_lines.append(f"   {plugin_dev_cmd}")
            has_issues = True
    except (ImportError, OSError):
        pass

    # HTTPS + Workflows warning - OAuth tokens can't push workflow changes
    try:
        if check_https_with_workflows(cwd=project_dir):
            output_lines.append("")
            output_lines.append("⚠️ HTTPS remote with workflows - can't push workflow changes")
            output_lines.append("   Run: git remote set-url origin git@github.com:USER/REPO.git")
            has_issues = True
    except (SubprocessError, OSError, GitError):
        pass

    # Commands hint - only if no issues (otherwise they know what to fix)
    if not has_issues:
        output_lines.append("")
        output_lines.append(hint_tpl)

    # Output with proper hook format
    result: dict = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(output_lines),
        }
    }

    # Show systemMessage only for warnings (not shown to user, but in Claude context)
    if has_issues:
        warning_tpl = prompts.get(
            "system_warning", "⚠️ Project has issues - check with /dk plugin check"
        )
        result["systemMessage"] = warning_tpl

    output_response(result)


if __name__ == "__main__":
    main()
