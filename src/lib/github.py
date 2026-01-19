"""GitHub API operations for branch protection.

TIER 1: May import from core only.
"""

import json
import subprocess
from dataclasses import dataclass
from enum import Enum

from core.errors import GitHubError, ProtectionError


class OwnerType(str, Enum):
    """Repository owner type."""

    USER = "user"
    ORGANIZATION = "organization"


class PlanTier(str, Enum):
    """GitHub plan tier."""

    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


@dataclass
class RepoInfo:
    """Repository information."""

    owner: str
    name: str
    owner_type: OwnerType
    plan: PlanTier
    visibility: str
    default_branch: str


def get_repo_info(repo: str | None = None) -> RepoInfo | None:
    """Get repository information including owner type and plan.

    Args:
        repo: GitHub repo in format owner/repo. If None, detect from git remote.

    Returns:
        RepoInfo with detected information, or None if detection fails.
    """
    # Auto-detect repo from git remote if not provided
    if not repo:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            url = result.stdout.strip()
            # Extract owner/repo from various URL formats
            if "github.com" in url:
                # https://github.com/owner/repo.git or git@github.com:owner/repo.git
                if url.startswith("git@"):
                    repo = url.split(":")[-1].replace(".git", "")
                else:
                    repo = url.split("github.com/")[-1].replace(".git", "")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    if not repo or "/" not in repo:
        return None

    owner, name = repo.split("/", 1)

    # Get repo details
    try:
        result = subprocess.run(
            ["gh", "api", f"/repos/{repo}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        repo_data = json.loads(result.stdout)
    except subprocess.TimeoutExpired as e:
        raise GitHubError("GitHub API request timed out") from e
    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to get repo info: {e.stderr if e.stderr else str(e)}") from e
    except json.JSONDecodeError as e:
        raise GitHubError(f"Invalid API response: {e}") from e

    # Determine owner type
    owner_type = (
        OwnerType.ORGANIZATION
        if repo_data.get("owner", {}).get("type") == "Organization"
        else OwnerType.USER
    )

    # Get plan information
    plan = _detect_plan(owner, owner_type)

    return RepoInfo(
        owner=owner,
        name=name,
        owner_type=owner_type,
        plan=plan,
        visibility=repo_data.get("visibility", "public"),
        default_branch=repo_data.get("default_branch", "main"),
    )


def _detect_plan(owner: str, owner_type: OwnerType) -> PlanTier:
    """Detect the GitHub plan tier for an owner.

    Args:
        owner: GitHub username or organization name.
        owner_type: Whether owner is a user or organization.

    Returns:
        Detected plan tier.
    """
    if owner_type == OwnerType.ORGANIZATION:
        # Check organization plan
        try:
            result = subprocess.run(
                ["gh", "api", f"/orgs/{owner}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            org_data = json.loads(result.stdout)
            plan_name = org_data.get("plan", {}).get("name", "free").lower()

            if "enterprise" in plan_name:
                return PlanTier.ENTERPRISE
            elif "team" in plan_name:
                return PlanTier.TEAM
            elif "pro" in plan_name:
                return PlanTier.PRO
            return PlanTier.FREE
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return PlanTier.FREE
    else:
        # Check user plan - users have Pro if they have certain features
        try:
            result = subprocess.run(
                ["gh", "api", f"/users/{owner}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            user_data = json.loads(result.stdout)
            plan_name = user_data.get("plan", {}).get("name", "free").lower()

            if "pro" in plan_name:
                return PlanTier.PRO
            return PlanTier.FREE
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return PlanTier.FREE


def can_use_bypass_actors(repo_info: RepoInfo) -> bool:
    """Check if the repo can use bypass actors in rulesets.

    Bypass actors require:
    - User repos: Pro plan
    - Org repos: Team or Enterprise plan

    Args:
        repo_info: Repository information.

    Returns:
        True if bypass actors can be used.
    """
    if repo_info.owner_type == OwnerType.USER:
        return repo_info.plan == PlanTier.PRO
    else:
        return repo_info.plan in (PlanTier.TEAM, PlanTier.ENTERPRISE)


def create_ruleset(
    repo: str,
    config: dict,
    bypass_actors: bool = True,
) -> tuple[bool, str]:
    """Create or update a branch protection ruleset.

    Args:
        repo: GitHub repo in format owner/repo.
        config: Protection config with keys:
            - require_reviews: Number of required reviews (default: 1)
            - linear_history: Require linear history (default: True)
            - dismiss_stale_reviews: Dismiss stale reviews (default: False)
        bypass_actors: Include admin bypass (requires Pro/Team+).

    Returns:
        Tuple of (success, message).
    """
    require_reviews = config.get("require_reviews", 1)
    linear_history = config.get("linear_history", True)
    dismiss_stale_reviews = config.get("dismiss_stale_reviews", False)

    # Check if ruleset already exists
    existing = check_ruleset_status(repo)
    if existing.get("exists") and existing.get("ruleset_id"):
        # Delete existing ruleset first
        delete_ruleset(repo, existing["ruleset_id"])

    # Build ruleset payload
    rules = []

    if linear_history:
        rules.append({"type": "required_linear_history"})

    if require_reviews > 0:
        rules.append(
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": require_reviews,
                    "dismiss_stale_reviews_on_push": dismiss_stale_reviews,
                    "require_code_owner_review": False,
                },
            }
        )

    payload = {
        "name": "devkit-protection",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "rules": rules,
    }

    # Add bypass actors if supported
    if bypass_actors:
        # RepositoryRole 5 = Admin (repository_admin)
        payload["bypass_actors"] = [
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
        ]

    try:
        subprocess.run(
            ["gh", "api", "-X", "POST", f"/repos/{repo}/rulesets", "--input", "-"],
            input=json.dumps(payload).encode(),
            check=True,
            capture_output=True,
            timeout=30,
        )
        msg = "Created ruleset: devkit-protection"
        if bypass_actors:
            msg += " (with admin bypass)"
        return True, msg
    except subprocess.TimeoutExpired as e:
        raise ProtectionError("Ruleset creation timed out") from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else str(e)
        raise ProtectionError(f"Failed to create ruleset: {stderr}") from e


def check_ruleset_status(repo: str) -> dict:
    """Check if devkit-protection ruleset exists.

    Args:
        repo: GitHub repo in format owner/repo.

    Returns:
        Dict with:
            - exists: bool
            - ruleset_id: int | None
            - enforcement: str | None
            - has_bypass: bool
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"/repos/{repo}/rulesets"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        rulesets = json.loads(result.stdout)

        for ruleset in rulesets:
            if ruleset.get("name") == "devkit-protection":
                return {
                    "exists": True,
                    "ruleset_id": ruleset.get("id"),
                    "enforcement": ruleset.get("enforcement"),
                    "has_bypass": bool(ruleset.get("bypass_actors")),
                }

        return {"exists": False, "ruleset_id": None, "enforcement": None, "has_bypass": False}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return {"exists": False, "ruleset_id": None, "enforcement": None, "has_bypass": False}


def delete_ruleset(repo: str, ruleset_id: int) -> tuple[bool, str]:
    """Delete a ruleset by ID.

    Args:
        repo: GitHub repo in format owner/repo.
        ruleset_id: Ruleset ID to delete.

    Returns:
        Tuple of (success, message).
    """
    try:
        subprocess.run(
            ["gh", "api", "-X", "DELETE", f"/repos/{repo}/rulesets/{ruleset_id}"],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return True, f"Deleted ruleset {ruleset_id}"
    except subprocess.TimeoutExpired:
        return False, "Ruleset deletion timed out"
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else str(e)
        return False, f"Failed to delete ruleset: {stderr}"


def get_protection_recommendation(repo_info: RepoInfo) -> dict:
    """Get protection recommendation based on repo type.

    Args:
        repo_info: Repository information.

    Returns:
        Dict with:
            - can_bypass: bool
            - recommendation: str
            - needs_pat: bool
            - warning: str | None
    """
    can_bypass = can_use_bypass_actors(repo_info)

    if repo_info.owner_type == OwnerType.USER:
        if repo_info.plan == PlanTier.FREE:
            return {
                "can_bypass": False,
                "recommendation": "Create ruleset without admin bypass",
                "needs_pat": True,
                "warning": (
                    "User Free plan cannot use bypass actors. "
                    "RELEASE_PAT secret required for automated releases. "
                    "Upgrade to GitHub Pro for admin bypass."
                ),
            }
        else:
            return {
                "can_bypass": True,
                "recommendation": "Create ruleset with admin bypass",
                "needs_pat": False,
                "warning": None,
            }
    else:
        if repo_info.plan == PlanTier.FREE:
            return {
                "can_bypass": False,
                "recommendation": "Create ruleset with limited features",
                "needs_pat": True,
                "warning": (
                    "Organization Free plan has limited ruleset features. "
                    "RELEASE_PAT secret may be required. "
                    "Upgrade to Team plan for full bypass support."
                ),
            }
        else:
            return {
                "can_bypass": True,
                "recommendation": "Create ruleset with admin bypass",
                "needs_pat": False,
                "warning": None,
            }


def setup_branch_protection(repo: str, config: dict | None = None) -> list[tuple[str, bool, str]]:
    """Setup branch protection based on repo capabilities.

    Args:
        repo: GitHub repo in format owner/repo.
        config: Optional protection config. If None, uses defaults.

    Returns:
        List of (step, success, message) tuples.
    """
    results = []
    config = config or {
        "enabled": True,
        "require_reviews": 1,
        "linear_history": True,
        "admin_bypass": True,
        "dismiss_stale_reviews": False,
    }

    if not config.get("enabled", True):
        results.append(("protection", True, "Disabled in config"))
        return results

    # 1. Get repo info
    try:
        repo_info = get_repo_info(repo)
        if not repo_info:
            results.append(("repo info", False, "Could not detect repo info"))
            return results
        results.append(
            ("repo type", True, f"{repo_info.owner_type.value} ({repo_info.plan.value})")
        )
    except GitHubError as e:
        results.append(("repo info", False, str(e)))
        return results

    # 2. Get recommendation
    recommendation = get_protection_recommendation(repo_info)

    # 3. Check bypass support
    bypass_ok = recommendation["can_bypass"] and config.get("admin_bypass", True)

    # 4. Create ruleset or warn
    try:
        ok, msg = create_ruleset(repo, config, bypass_actors=bypass_ok)
        results.append(("ruleset", ok, msg))
    except ProtectionError as e:
        results.append(("ruleset", False, str(e)))
        return results

    # 5. Add warning if needed
    if recommendation["warning"]:
        results.append(("warning", True, recommendation["warning"]))

    if recommendation["needs_pat"]:
        results.append(
            (
                "action required",
                True,
                "Add RELEASE_PAT secret: gh secret set RELEASE_PAT",
            )
        )

    return results
