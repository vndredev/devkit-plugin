"""Axiom CLI wrapper for logging/observability management.

TIER 1: May import from core only.

Provides Axiom CLI integration:
- Check CLI installation and authentication
- List and manage datasets
- Execute APL queries
- Stream logs in real-time
- Token validation
"""

import json
import os
import subprocess
from pathlib import Path


def check_cli() -> tuple[bool, str]:
    """Check if Axiom CLI is installed.

    Returns:
        Tuple of (success, version_or_error)
    """
    try:
        result = subprocess.run(
            ["axiom", "version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or "Unknown error"
    except FileNotFoundError:
        return False, "Axiom CLI not installed. Run: brew install axiom"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def check_auth() -> tuple[bool, str]:
    """Check Axiom authentication status.

    Returns:
        Tuple of (authenticated, status_message)
    """
    try:
        result = subprocess.run(
            ["axiom", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "Not authenticated. Run: axiom auth login"
    except FileNotFoundError:
        return False, "Axiom CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def login() -> tuple[bool, str]:
    """Start Axiom authentication flow.

    Note: This is interactive and requires user input.

    Returns:
        Tuple of (success, message)
    """
    try:
        result = subprocess.run(
            ["axiom", "auth", "login"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True, "Successfully authenticated"
        return False, result.stderr.strip() or "Authentication failed"
    except FileNotFoundError:
        return False, "Axiom CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "Authentication timed out"


def list_datasets() -> tuple[bool, list[dict] | str]:
    """List all Axiom datasets.

    Returns:
        Tuple of (success, datasets_list_or_error)
    """
    try:
        result = subprocess.run(
            ["axiom", "dataset", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            try:
                datasets = json.loads(result.stdout)
                return True, datasets
            except json.JSONDecodeError:
                # Fallback: parse text output
                return True, []
        return False, result.stderr.strip() or "Failed to list datasets"
    except FileNotFoundError:
        return False, "Axiom CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def create_dataset(name: str, description: str = "") -> tuple[bool, str]:
    """Create a new Axiom dataset.

    Args:
        name: Dataset name (alphanumeric and hyphens only)
        description: Optional dataset description

    Returns:
        Tuple of (success, message)
    """
    cmd = ["axiom", "dataset", "create", f"--name={name}"]
    if description:
        cmd.append(f"--description={description}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, f"Dataset '{name}' created successfully"
        return False, result.stderr.strip() or "Failed to create dataset"
    except FileNotFoundError:
        return False, "Axiom CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def delete_dataset(name: str, force: bool = False) -> tuple[bool, str]:
    """Delete an Axiom dataset.

    Args:
        name: Dataset name to delete
        force: Skip confirmation (dangerous!)

    Returns:
        Tuple of (success, message)
    """
    cmd = ["axiom", "dataset", "delete", name]
    if force:
        cmd.append("--force")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, f"Dataset '{name}' deleted"
        return False, result.stderr.strip() or "Failed to delete dataset"
    except FileNotFoundError:
        return False, "Axiom CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def query_apl(apl: str, format_output: str = "json") -> tuple[bool, str | list[dict]]:
    """Execute APL (Axiom Processing Language) query.

    Args:
        apl: APL query string (e.g., "['dataset'] | limit 10")
        format_output: Output format (json, table)

    Returns:
        Tuple of (success, results_or_error)
    """
    cmd = ["axiom", "query", apl, f"--format={format_output}"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            if format_output == "json":
                try:
                    return True, json.loads(result.stdout)
                except json.JSONDecodeError:
                    return True, result.stdout.strip()
            return True, result.stdout.strip()
        return False, result.stderr.strip() or "Query failed"
    except FileNotFoundError:
        return False, "Axiom CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "Query timed out"


def ingest_data(dataset: str, data: str | list[dict]) -> tuple[bool, str]:
    """Ingest data into an Axiom dataset.

    Args:
        dataset: Target dataset name
        data: JSON string or list of dicts to ingest

    Returns:
        Tuple of (success, message)
    """
    if isinstance(data, list):
        data = json.dumps(data)

    try:
        result = subprocess.run(
            ["axiom", "ingest", dataset],
            input=data,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "Data ingested successfully"
        return False, result.stderr.strip() or "Ingest failed"
    except FileNotFoundError:
        return False, "Axiom CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "Ingest timed out"


def open_web() -> tuple[bool, str]:
    """Open Axiom dashboard in browser.

    Returns:
        Tuple of (success, message)
    """
    try:
        result = subprocess.run(
            ["axiom", "web"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, "Opening Axiom dashboard..."
        return False, result.stderr.strip() or "Failed to open dashboard"
    except FileNotFoundError:
        return False, "Axiom CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def check_token() -> tuple[bool, dict]:
    """Check AXIOM_TOKEN environment variable.

    Returns:
        Tuple of (has_token, info_dict)
    """
    token = os.environ.get("AXIOM_TOKEN", "")
    dataset = os.environ.get("AXIOM_DATASET", "")
    org_id = os.environ.get("AXIOM_ORG_ID", "")

    # Check .env.local for token
    env_local = Path.cwd() / ".env.local"
    env_token = ""
    if env_local.exists():
        try:
            for line in env_local.read_text().splitlines():
                if line.startswith("AXIOM_TOKEN="):
                    env_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        except OSError:
            pass

    has_token = bool(token or env_token)
    masked_token = ""
    if token:
        masked_token = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"
    elif env_token:
        masked_token = f"{env_token[:8]}...{env_token[-4:]}" if len(env_token) > 12 else "***"

    return has_token, {
        "has_token": has_token,
        "masked_token": masked_token,
        "source": "env" if token else ("env.local" if env_token else None),
        "dataset": dataset or None,
        "org_id": org_id or None,
    }


def validate_token() -> tuple[bool, str]:
    """Validate token by making a test API call.

    Returns:
        Tuple of (valid, message)
    """
    # Try to list datasets as a token validation
    ok, result = list_datasets()
    if ok:
        count = len(result) if isinstance(result, list) else 0
        return True, f"Token valid - {count} datasets accessible"
    return False, f"Token validation failed: {result}"


def send_test_event(dataset: str = "test-logs") -> tuple[bool, str]:
    """Send a test event to verify connectivity.

    Args:
        dataset: Target dataset name

    Returns:
        Tuple of (success, message)
    """
    import time

    test_event = {
        "_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "level": "info",
        "message": "Test event from devkit-plugin",
        "source": "dk-axiom-test",
    }

    return ingest_data(dataset, [test_event])


def axiom_status() -> dict:
    """Get comprehensive Axiom status.

    Returns:
        Dict with CLI, auth, token, and dataset information
    """
    # Check CLI
    cli_ok, cli_info = check_cli()

    # Check auth (only if CLI is installed)
    auth_ok = False
    auth_info = "CLI not installed"
    if cli_ok:
        auth_ok, auth_info = check_auth()

    # Check token
    token_ok, token_info = check_token()

    # List datasets (only if authenticated)
    datasets: list[dict] = []
    if auth_ok:
        ds_ok, ds_result = list_datasets()
        if ds_ok and isinstance(ds_result, list):
            datasets = ds_result

    return {
        "cli_installed": cli_ok,
        "cli_version": cli_info if cli_ok else None,
        "authenticated": auth_ok,
        "auth_info": auth_info if auth_ok else None,
        "token": token_info,
        "datasets": datasets,
        "dataset_count": len(datasets),
        "dashboard": "https://app.axiom.co",
        "token_settings": "https://app.axiom.co/settings/api-tokens",
    }
