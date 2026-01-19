"""MCP server configuration and health checking.

TIER 1: lib layer.
"""

import json
import os
import re
from pathlib import Path

# Required env vars per MCP server
MCP_ENV_REQUIREMENTS: dict[str, list[str]] = {
    "context7": [],  # No env vars needed
    "neon": ["NEON_API_KEY"],
    "stripe": ["STRIPE_SECRET_KEY"],
    "playwright": [],  # No env vars needed
    "axiom": ["AXIOM_TOKEN", "AXIOM_ORG_ID"],
}


def get_shell_config_path() -> Path | None:
    """Get the user's shell config file path.

    Returns:
        Path to ~/.zshrc or ~/.bashrc, or None if neither exists.
    """
    home = Path.home()

    # Prefer zshrc (default on macOS)
    zshrc = home / ".zshrc"
    if zshrc.exists():
        return zshrc

    bashrc = home / ".bashrc"
    if bashrc.exists():
        return bashrc

    return None


def scan_shell_config_for_exports(config_path: Path) -> dict[str, bool]:
    """Scan shell config for export statements.

    Args:
        config_path: Path to shell config file.

    Returns:
        Dict mapping var names to whether they're exported.
    """
    try:
        content = config_path.read_text()
    except OSError:
        return {}

    # Collect all required vars
    all_vars = set()
    for vars_list in MCP_ENV_REQUIREMENTS.values():
        all_vars.update(vars_list)

    result = {}
    for var in all_vars:
        # Match: export VAR=... or export VAR="..."
        pattern = rf"^\s*export\s+{var}\s*="
        result[var] = bool(re.search(pattern, content, re.MULTILINE))

    return result


def check_env_vars_in_environment() -> dict[str, bool]:
    """Check if required env vars are set in current environment.

    Returns:
        Dict mapping var names to whether they're set (non-empty).
    """
    all_vars = set()
    for vars_list in MCP_ENV_REQUIREMENTS.values():
        all_vars.update(vars_list)

    return {var: bool(os.environ.get(var)) for var in all_vars}


def get_mcp_status() -> dict[str, dict]:
    """Get status of all MCP servers.

    Returns:
        Dict mapping server name to status info:
        {
            "server_name": {
                "required_vars": ["VAR1", "VAR2"],
                "missing_vars": ["VAR1"],
                "ready": False,
            }
        }
    """
    env_status = check_env_vars_in_environment()

    result = {}
    for server, required_vars in MCP_ENV_REQUIREMENTS.items():
        missing = [v for v in required_vars if not env_status.get(v)]
        result[server] = {
            "required_vars": required_vars,
            "missing_vars": missing,
            "ready": len(missing) == 0,
        }

    return result


def get_mcp_health_report() -> dict:
    """Get comprehensive MCP health report.

    Returns:
        Dict with shell config info and server status.
    """
    shell_config = get_shell_config_path()
    shell_exports = scan_shell_config_for_exports(shell_config) if shell_config else {}
    env_vars = check_env_vars_in_environment()
    server_status = get_mcp_status()

    ready_count = sum(1 for s in server_status.values() if s["ready"])
    total_count = len(server_status)

    return {
        "shell_config": str(shell_config) if shell_config else None,
        "shell_exports": shell_exports,
        "env_vars": env_vars,
        "servers": server_status,
        "summary": {
            "ready": ready_count,
            "total": total_count,
            "all_ready": ready_count == total_count,
        },
    }


def format_mcp_status() -> str:
    """Format MCP status for display.

    Returns:
        Formatted status string.
    """
    report = get_mcp_health_report()
    lines = []

    lines.append("## MCP Server Status")
    lines.append("")

    # Server status table
    lines.append("| Server | Status | Missing |")
    lines.append("|--------|--------|---------|")

    for server, status in report["servers"].items():
        if status["ready"]:
            icon = "✅"
            missing = "-"
        else:
            icon = "❌"
            missing = ", ".join(status["missing_vars"]) or "-"
        lines.append(f"| {server} | {icon} | {missing} |")

    lines.append("")

    # Summary
    summary = report["summary"]
    lines.append(f"**Ready:** {summary['ready']}/{summary['total']} servers")
    lines.append("")

    # Shell config info
    if report["shell_config"]:
        lines.append(f"**Shell config:** `{report['shell_config']}`")

        # Show which vars are in shell config vs actually set
        missing_in_env = []
        for var, in_shell in report["shell_exports"].items():
            in_env = report["env_vars"].get(var, False)
            if in_shell and not in_env:
                missing_in_env.append(var)

        if missing_in_env:
            lines.append("")
            lines.append("⚠️ **Vars in shell config but not in env** (restart terminal?):")
            for var in missing_in_env:
                lines.append(f"  - `{var}`")
    else:
        lines.append("**Shell config:** Not found (~/.zshrc or ~/.bashrc)")

    return "\n".join(lines)
