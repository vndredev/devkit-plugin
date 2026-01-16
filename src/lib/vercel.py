"""Vercel deployment setup and management.

TIER 1: May import from core only.
"""

import json
import subprocess
from pathlib import Path

from lib.config import get


def vercel_connect(
    project_name: str | None = None,
    sync_env: bool = True,
) -> list[tuple[str, bool, str]]:
    """Setup Vercel with full automation.

    Args:
        project_name: Vercel project name (defaults to directory name)
        sync_env: Whether to sync environment variables from .env.local

    Returns:
        List of (step, success, message) tuples
    """
    results = []
    root = Path.cwd()

    # 0. Check if deployment is enabled for this project type
    deployment_config = get("deployment", {})
    if not deployment_config.get("enabled", True):
        note = deployment_config.get("note", "Deployment not supported for this project type")
        platforms = deployment_config.get("platforms", [])
        if platforms:
            note += f" Alternatives: {', '.join(platforms)}"
        results.append(("deployment check", False, note))
        return results

    # Check if Vercel is a valid platform
    platforms = deployment_config.get("platforms", ["vercel"])
    if "vercel" not in platforms:
        results.append(
            ("platform check", False, f"Vercel not supported. Use: {', '.join(platforms)}")
        )
        return results

    # 1. Check Vercel CLI
    cli_ok, cli_msg = check_vercel_cli()
    results.append(("vercel cli", cli_ok, cli_msg))
    if not cli_ok:
        return results

    # 2. Link or get project
    link_ok, link_msg = link_project(root, project_name)
    results.append(("vercel link", link_ok, link_msg))
    if not link_ok:
        return results

    # 3. Get project info
    info = get_project_info(root)
    if info:
        results.append(
            ("project info", True, f"{info.get('name', 'unknown')} @ {info.get('org', 'unknown')}")
        )

    # 4. Check GitHub integration
    gh_ok, gh_msg = check_github_integration(info)
    results.append(("github integration", gh_ok, gh_msg))

    # 5. Check production domain
    domain_ok, domain_msg = check_production_domain(info)
    results.append(("production domain", domain_ok, domain_msg))

    # 6. Sync environment variables (if requested)
    if sync_env:
        env_results = sync_env_vars(root)
        results.extend(env_results)

    # 7. Check Neon integration (if DATABASE_URL exists)
    neon_ok, neon_msg = check_neon_integration(info)
    results.append(("neon integration", neon_ok, neon_msg))

    return results


def check_vercel_cli() -> tuple[bool, str]:
    """Check if Vercel CLI is installed and authenticated.

    Returns:
        Tuple of (success, message)
    """
    # Check if installed
    try:
        result = subprocess.run(
            ["vercel", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        version = result.stdout.strip().split("\n")[0]
    except FileNotFoundError:
        return False, "Vercel CLI not installed. Run: npm i -g vercel"
    except subprocess.CalledProcessError:
        return False, "Vercel CLI not working"

    # Check if authenticated
    try:
        result = subprocess.run(
            ["vercel", "whoami"],
            capture_output=True,
            text=True,
            check=True,
        )
        user = result.stdout.strip()
        return True, f"{version} (logged in as {user})"
    except subprocess.CalledProcessError:
        return False, f"{version} - not logged in. Run: vercel login"


def link_project(root: Path, project_name: str | None = None) -> tuple[bool, str]:
    """Link project to Vercel or get existing link.

    Args:
        root: Project root directory
        project_name: Optional project name override

    Returns:
        Tuple of (success, message)
    """
    vercel_dir = root / ".vercel"
    project_json = vercel_dir / "project.json"

    # Already linked
    if project_json.exists():
        try:
            data = json.loads(project_json.read_text())
            name = data.get("projectName", "unknown")
            return True, f"Already linked to {name}"
        except (json.JSONDecodeError, OSError):
            pass  # Corrupted or unreadable file, will try to relink

    # Link project
    try:
        cmd = ["vercel", "link", "--yes"]
        if project_name:
            cmd.extend(["--project", project_name])

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=root,
        )

        # Read the created project.json
        if project_json.exists():
            data = json.loads(project_json.read_text())
            name = data.get("projectName", "unknown")
            return True, f"Linked to {name}"
        return True, "Linked successfully"

    except subprocess.CalledProcessError as e:
        stderr = e.stderr if e.stderr else str(e)
        return False, f"Link failed: {stderr}"


def get_project_info(root: Path) -> dict | None:
    """Get Vercel project information.

    Args:
        root: Project root directory

    Returns:
        Dict with project info or None
    """
    project_json = root / ".vercel" / "project.json"
    if not project_json.exists():
        return None

    try:
        data = json.loads(project_json.read_text())
        info = {
            "project_id": data.get("projectId"),
            "org_id": data.get("orgId"),
            "name": data.get("projectName"),
        }

        # Get more details from Vercel API
        try:
            result = subprocess.run(
                ["vercel", "project", "ls", "--json"],
                capture_output=True,
                text=True,
                check=True,
                cwd=root,
            )
            projects = json.loads(result.stdout)
            for proj in projects:
                if proj.get("name") == info["name"]:
                    info["production_url"] = proj.get("latestDeployment", {}).get("url")
                    info["framework"] = proj.get("framework")
                    break
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass  # API call failed, continue with basic info

        # Get org name
        try:
            result = subprocess.run(
                ["vercel", "whoami"],
                capture_output=True,
                text=True,
                check=True,
            )
            info["org"] = result.stdout.strip()
        except subprocess.CalledProcessError:
            pass  # Not logged in or CLI issue

        return info

    except (json.JSONDecodeError, OSError):
        return None


def check_github_integration(info: dict | None, auto_connect: bool = True) -> tuple[bool, str]:
    """Check if GitHub integration is configured, optionally connect if not.

    Args:
        info: Project info dict
        auto_connect: Whether to automatically connect GitHub if not connected

    Returns:
        Tuple of (success, message)
    """
    if not info or not info.get("project_id"):
        return False, "No project info"

    # Check if git remote points to GitHub
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote = result.stdout.strip()
        if "github.com" not in remote:
            return False, "Remote is not GitHub"

        # Extract owner/repo and build GitHub URL
        if remote.startswith("git@"):
            repo = remote.split(":")[1].replace(".git", "")
        else:
            repo = "/".join(remote.replace(".git", "").split("/")[-2:])

        github_url = f"https://github.com/{repo}"

        # Check if Vercel is connected to GitHub by trying to get git info
        try:
            git_result = subprocess.run(
                ["vercel", "git", "ls"],
                capture_output=True,
                text=True,
                check=True,
            )
            # If we get output with the repo, it's connected
            if repo.lower() in git_result.stdout.lower():
                return True, f"Connected to {repo}"
        except subprocess.CalledProcessError:
            pass  # Not connected, will try to connect

        # Try to connect if auto_connect is enabled
        if auto_connect:
            connect_ok, connect_msg = connect_vercel_github(github_url)
            if connect_ok:
                return True, f"Connected to {repo}"
            return False, f"Auto-connect failed: {connect_msg}"

        return False, f"Not connected to {repo} - run vercel git connect"

    except subprocess.CalledProcessError:
        return False, "No git remote configured"


def connect_vercel_github(github_url: str) -> tuple[bool, str]:
    """Connect Vercel project to GitHub repository.

    Args:
        github_url: Full GitHub URL (https://github.com/owner/repo)

    Returns:
        Tuple of (success, message)
    """
    try:
        subprocess.run(
            ["vercel", "git", "connect", github_url, "--yes"],
            capture_output=True,
            text=True,
            check=True,
        )
        return True, "Connected"
    except subprocess.CalledProcessError as e:
        stderr = e.stderr if e.stderr else str(e)
        return False, stderr


def check_production_domain(info: dict | None) -> tuple[bool, str]:
    """Check if production domain is configured.

    Args:
        info: Project info dict

    Returns:
        Tuple of (success, message)
    """
    if not info or not info.get("name"):
        return False, "No project info"

    try:
        result = subprocess.run(
            ["vercel", "domains", "ls", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        domains = json.loads(result.stdout)

        # Filter domains for this project
        project_domains = [d for d in domains if not d.get("name", "").endswith(".vercel.app")]

        if project_domains:
            domain = project_domains[0].get("name", "unknown")
            return True, domain
        return True, f"{info['name']}.vercel.app (default)"

    except subprocess.CalledProcessError:
        return True, "Using default .vercel.app domain"
    except json.JSONDecodeError:
        return True, "Domain check skipped (invalid JSON response)"


def sync_env_vars(root: Path) -> list[tuple[str, bool, str]]:
    """Sync environment variables from .env.local to Vercel.

    Args:
        root: Project root directory

    Returns:
        List of (step, success, message) tuples
    """
    results = []
    env_file = root / ".env.local"

    if not env_file.exists():
        results.append(("env sync", True, "No .env.local found - skipped"))
        return results

    # Read current Vercel env vars
    try:
        result = subprocess.run(
            ["vercel", "env", "ls", "--json"],
            capture_output=True,
            text=True,
            check=True,
            cwd=root,
        )
        existing_vars = set()
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    var_data = json.loads(line)
                    existing_vars.add(var_data.get("key", ""))
                except json.JSONDecodeError:
                    pass
    except (subprocess.CalledProcessError, OSError):
        existing_vars = set()  # CLI not available, assume no vars

    # Parse .env.local
    env_vars = {}
    sensitive_keywords = ["SECRET", "KEY", "TOKEN", "PASSWORD", "PRIVATE"]

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        # Skip sensitive vars
        is_sensitive = any(kw in key.upper() for kw in sensitive_keywords)
        if is_sensitive:
            results.append((f"env:{key}", True, "Skipped (sensitive)"))
            continue

        # Skip if already exists
        if key in existing_vars:
            results.append((f"env:{key}", True, "Already set"))
            continue

        env_vars[key] = value

    # Report what would be synced
    if env_vars:
        results.append(("env sync", True, f"{len(env_vars)} vars ready to sync (run /dk env sync)"))
    else:
        results.append(("env sync", True, "All vars already synced"))

    return results


def add_env_var(
    key: str, value: str, environments: list[str] | None = None
) -> list[tuple[str, bool, str]]:
    """Add environment variable to Vercel without newline issues.

    Args:
        key: Environment variable name
        value: Environment variable value
        environments: List of environments (production, preview, development)

    Returns:
        List of (step, success, message) tuples
    """
    results = []
    if environments is None:
        environments = ["production", "preview", "development"]

    for env in environments:
        try:
            # Use subprocess with input instead of echo to avoid newline issues
            subprocess.run(
                ["vercel", "env", "add", key, env],
                input=value,
                capture_output=True,
                text=True,
                check=True,
            )
            results.append((f"env:{key}:{env}", True, "Added"))
        except subprocess.CalledProcessError as e:
            stderr = e.stderr if e.stderr else str(e)
            results.append((f"env:{key}:{env}", False, stderr))

    return results


def sync_env_to_vercel(root: Path) -> list[tuple[str, bool, str]]:
    """Actually sync environment variables from .env.local to Vercel.

    Args:
        root: Project root directory

    Returns:
        List of (step, success, message) tuples
    """
    results = []
    env_file = root / ".env.local"

    if not env_file.exists():
        results.append(("env sync", False, "No .env.local found"))
        return results

    # Read current Vercel env vars
    try:
        result = subprocess.run(
            ["vercel", "env", "ls", "--json"],
            capture_output=True,
            text=True,
            check=True,
            cwd=root,
        )
        existing_vars = set()
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    var_data = json.loads(line)
                    existing_vars.add(var_data.get("key", ""))
                except json.JSONDecodeError:
                    pass
    except (subprocess.CalledProcessError, OSError):
        existing_vars = set()  # CLI not available, assume no vars

    # Parse .env.local and sync
    synced = 0
    skipped = 0

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        # Skip if already exists
        if key in existing_vars:
            skipped += 1
            continue

        # Add to Vercel (all environments)
        add_results = add_env_var(key, value)
        results.extend(add_results)
        if all(r[1] for r in add_results):
            synced += 1

    results.append(("env sync", True, f"Synced {synced}, skipped {skipped} existing"))
    return results


def check_neon_integration(info: dict | None) -> tuple[bool, str]:
    """Check if Neon integration is configured.

    Args:
        info: Project info dict

    Returns:
        Tuple of (success, message)
    """
    if not info or not info.get("name"):
        return True, "No database detected"

    # Check if DATABASE_URL exists in Vercel env
    try:
        result = subprocess.run(
            ["vercel", "env", "ls"],
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout

        if "DATABASE_URL" in output:
            # Check if it's per-branch (Neon integration sign)
            if output.count("DATABASE_URL") > 1:
                return True, "Neon integration active (per-branch DB)"
            return True, "DATABASE_URL configured"
        return True, "No DATABASE_URL - Neon integration not needed"

    except subprocess.CalledProcessError:
        return True, "Could not check env vars (CLI error)"


def vercel_deploy(
    production: bool = False,
    prebuilt: bool = False,
) -> tuple[bool, str, str | None]:
    """Deploy to Vercel.

    Args:
        production: Deploy to production
        prebuilt: Use prebuilt output

    Returns:
        Tuple of (success, message, deployment_url)
    """
    cmd = ["vercel", "deploy"]

    if production:
        cmd.append("--prod")
    if prebuilt:
        cmd.append("--prebuilt")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip().split("\n")[-1]
        env = "Production" if production else "Preview"
        return True, f"{env} deployment complete", url

    except subprocess.CalledProcessError as e:
        return False, f"Deploy failed: {e.stderr}", None


def vercel_status() -> dict:
    """Get current Vercel project status.

    Returns:
        Dict with status information
    """
    root = Path.cwd()
    status = {
        "linked": False,
        "project": None,
        "org": None,
        "cli_version": None,
        "logged_in": False,
    }

    # Check CLI
    cli_ok, cli_msg = check_vercel_cli()
    if cli_ok:
        parts = cli_msg.split(" ")
        status["cli_version"] = parts[0] if parts else None
        status["logged_in"] = "logged in" in cli_msg

    # Check project link
    project_json = root / ".vercel" / "project.json"
    if project_json.exists():
        try:
            data = json.loads(project_json.read_text())
            status["linked"] = True
            status["project"] = data.get("projectName")
            status["project_id"] = data.get("projectId")
        except (json.JSONDecodeError, OSError):
            pass  # Corrupted or unreadable project.json

    # Get org
    info = get_project_info(root)
    if info:
        status["org"] = info.get("org")
        status["production_url"] = info.get("production_url")

    return status
