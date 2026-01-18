#!/usr/bin/env python3
"""PreToolUse:EnterPlanMode hook - Shows planning structure before plan creation.

TIER 3: Entry point, may import from all layers.

Shows the planning requirements and structure from config.jsonc
so Claude knows the expected plan format BEFORE creating a plan.

Also enforces workflow: warns/blocks if trying to plan on protected branch
without using /dk dev workflow first.
"""

import json
import subprocess
import sys

from lib.config import get
from lib.hooks import consume_stdin, output_response


def check_protected_branch() -> tuple[str | None, bool]:
    """Check if on protected branch without workflow.

    Returns:
        Tuple of (warning message, is_blocking).
        is_blocking=True means Claude should use /dk dev first.
    """
    # Check enforcement mode
    enforce_mode = get("hooks.plan.enforce_workflow", "warn")
    if enforce_mode == "off":
        return None, False

    # Get current branch
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = result.stdout.strip()
    except Exception:
        return None, False

    # Check if on protected branch
    protected = get("git.protected_branches", ["main", "master"])
    if branch not in protected:
        return None, False

    # On protected branch - warn or block
    prompts = get("hooks.plan.prompts", {})
    msg_tpl = prompts.get(
        "workflow_required",
        "⚠️ You're on `{branch}` - use `/dk dev feat|fix|chore <desc>` to create a "
        "feature branch first. This ensures proper git workflow.",
    )
    msg = msg_tpl.format(branch=branch)

    is_blocking = enforce_mode == "block"
    return msg, is_blocking


def get_planning_guidance() -> str:
    """Get planning guidance from config."""
    # Check if plan hook is enabled
    if not get("hooks.plan.enabled", True):
        return ""

    lines = []

    # Planning requirements
    requirements = get("hooks.plan.planning.requirements", [])
    if requirements:
        lines.extend(["## Planning Requirements", ""])
        lines.extend(f"- {req}" for req in requirements)
        lines.append("")

    # Plan structure
    structure = get("hooks.plan.planning.structure", [])
    if structure:
        lines.extend(["## Expected Plan Structure", ""])
        lines.extend(f"- {section}" for section in structure)
        lines.append("")

    # Project-specific hints
    hints = get("hooks.plan.hints", [])
    if hints:
        lines.extend(["## Hints", ""])
        lines.extend(f"- {hint}" for hint in hints)
        lines.append("")

    return "\n".join(lines)


def get_arch_context() -> str:
    """Get architecture context for planning."""
    layers = get("arch.layers", {})
    if not layers:
        return ""

    lines = ["## Architecture Layers (for reference)"]
    sorted_layers = sorted(layers.items(), key=lambda x: x[1].get("tier", 0))

    for name, info in sorted_layers:
        tier = info.get("tier", 0)
        desc = info.get("description", "")
        patterns = info.get("patterns", [])
        lines.append(f"- **{name}** (Tier {tier}): {desc}")
        if patterns:
            lines.append(f"  Patterns: {', '.join(patterns)}")

    return "\n".join(lines)


def main() -> None:
    """Main entry point for PreToolUse:EnterPlanMode hook."""
    # Consume stdin (hook data not needed)
    consume_stdin()

    # Check if on protected branch
    branch_warning, is_blocking = check_protected_branch()

    guidance = get_planning_guidance()
    arch_context = get_arch_context()

    # Build result with proper hook format
    result: dict = {"continue": True, "hookSpecificOutput": {"hookEventName": "PreToolUse"}}

    # Build additional context
    additional_context = []

    # Branch warning first (most important)
    if branch_warning:
        additional_context.append(branch_warning)
        if is_blocking:
            # Block plan mode on protected branch if enforce_workflow=block
            result["continue"] = False
            result["decision"] = "block"
            result["reason"] = branch_warning

    if guidance:
        additional_context.append(guidance)
    if arch_context:
        additional_context.append(arch_context)

    if additional_context:
        result["hookSpecificOutput"]["additionalContext"] = "\n\n".join(additional_context)

    output_response(result)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # On error, allow but report
        print(json.dumps({"continue": True, "message": f"⚠️ Plan hook error: {e}"}))
        sys.exit(0)
