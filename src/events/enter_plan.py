#!/usr/bin/env python3
"""PreToolUse:EnterPlanMode hook - Shows planning structure before plan creation.

TIER 3: Entry point, may import from all layers.

Shows the planning requirements and structure from config.jsonc
so Claude knows the expected plan format BEFORE creating a plan.
"""

import contextlib
import json
import sys

from lib.config import get


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
    # Consume stdin (hook data) even if not used
    with contextlib.suppress(json.JSONDecodeError):
        json.load(sys.stdin)

    guidance = get_planning_guidance()
    arch_context = get_arch_context()

    # Build result with proper hook format
    result = {"continue": True, "hookSpecificOutput": {"hookEventName": "PreToolUse"}}

    # Add additionalContext if we have guidance
    if guidance or arch_context:
        additional_context = []
        if guidance:
            additional_context.append(guidance)
        if arch_context:
            additional_context.append(arch_context)
        result["additionalContext"] = "\n\n".join(additional_context)

    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # On error, allow but report
        print(json.dumps({"continue": True, "message": f"⚠️ Plan hook error: {e}"}))
        sys.exit(0)
