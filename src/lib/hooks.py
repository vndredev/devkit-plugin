"""Shared hook utilities.

TIER 1: May import from core only.
"""

import contextlib
import json
import sys
from typing import Any


def read_hook_input() -> dict[str, Any]:
    """Read and parse hook input from stdin.

    Returns:
        Parsed hook data dict, or empty dict if parsing fails.
    """
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def consume_stdin() -> None:
    """Consume stdin without parsing.

    Use this when hook data is not needed but stdin must be consumed.
    """
    with contextlib.suppress(json.JSONDecodeError):
        json.load(sys.stdin)


def output_response(response: dict[str, Any]) -> None:
    """Output hook response as JSON.

    Args:
        response: Response dict to output.
    """
    print(json.dumps(response))


def noop_response(hook_name: str = "PostToolUse") -> None:
    """Output empty response for a hook.

    Args:
        hook_name: Hook event name (default: PostToolUse).
    """
    output_response({"hookSpecificOutput": {"hookEventName": hook_name}})


def allow_response(hook_name: str = "PreToolUse") -> None:
    """Output allow response and exit.

    Args:
        hook_name: Hook event name (default: PreToolUse).
    """
    output_response({"continue": True, "hookSpecificOutput": {"hookEventName": hook_name}})
    sys.exit(0)


def deny_response(reason: str, hook_name: str = "PreToolUse") -> None:
    """Output deny response and exit.

    Args:
        reason: Reason for denial.
        hook_name: Hook event name (default: PreToolUse).
    """
    output_response(
        {
            "hookSpecificOutput": {
                "hookEventName": hook_name,
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )
    sys.exit(0)


def load_prompts(hook_path: str, defaults: dict[str, str]) -> dict[str, str]:
    """Load prompt templates from config.

    Args:
        hook_path: Config path to hook prompts (e.g., "hooks.session.prompts").
        defaults: Default prompts if not configured.

    Returns:
        Dict of prompt templates.
    """
    # Import here to avoid circular imports
    from lib.config import get

    prompts = get(hook_path, {})
    result = defaults.copy()
    result.update(prompts)
    return result
