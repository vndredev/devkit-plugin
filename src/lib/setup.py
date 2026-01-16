"""Project setup - init and update workflows.

TIER 1: May import from core only.
"""

import contextlib
import json
import subprocess
from pathlib import Path

from lib.config import clear_cache, get, load_config
from lib.git import run_git
from lib.sync import get_plugin_root, sync_all
from lib.tools import detect_project_type, detect_project_version


def generate_config_jsonc(
    name: str,
    project_type: str,
    version: str,
    github_url: str,
    github_visibility: str,
    deployment: dict,
    managed: dict,
    test_framework: str,
) -> str:
    """Generate JSONC config with comments and grouped sections.

    Args:
        name: Project name
        project_type: python, node, nextjs, etc.
        version: Semantic version
        github_url: GitHub repository URL
        github_visibility: public, private, internal
        deployment: Deployment configuration dict
        managed: Managed files manifest dict
        test_framework: pytest, vitest, jest

    Returns:
        JSONC content string with comments
    """
    managed_json = json.dumps(managed, indent=2)
    # Indent managed section for embedding
    managed_indented = "  " + managed_json.replace("\n", "\n  ")

    deployment_json = json.dumps(deployment, indent=2).replace("\n", "\n  ")

    return f'''{{
  "$schema": "./config.schema.json",

  // ============================================================================
  // IDENTITY - Project information
  // ============================================================================
  "project": {{
    "name": "{name}",
    "type": "{project_type}",
    "version": "{version}"
  }},

  // ============================================================================
  // DEVELOPMENT - Git and GitHub configuration
  // ============================================================================
  "git": {{
    "protected_branches": ["main"],
    "conventions": {{
      "types": ["feat", "fix", "chore", "refactor", "test", "docs", "perf", "ci"],
      "scopes": {{
        "mode": "strict",      // strict=error, warn=warning, off=disabled
        "allowed": [],         // Project-specific scopes
        "internal": ["internal", "review", "ci", "deps"]  // Skip release notes
      }},
      "branch_pattern": "{{type}}/{{description}}"
    }}
  }},

  "github": {{
    "url": "{github_url}",
    "visibility": "{github_visibility}",
    "pr": {{
      "auto_merge": false,     // Enable auto-merge when PR is created
      "delete_branch": true,   // Delete branch after merge
      "merge_method": "squash" // squash, merge, or rebase
    }}
  }},

  // ============================================================================
  // QUALITY - Linters and testing
  // ============================================================================
  "linters": {{
    "preset": "strict",        // strict, relaxed, minimal
    "overrides": {{}}
  }},

  "testing": {{
    "enabled": false,
    "framework": "{test_framework}"
  }},

  // ============================================================================
  // AUTOMATION - Hooks and changelog
  // ============================================================================
  "hooks": {{
    "session": {{
      "enabled": true,
      "show_git_status": true
    }},
    "validate": {{
      "enabled": true,
      "block_force_push": true,
      "block_dangerous_gh": true
    }},
    "format": {{
      "enabled": true,
      "auto_format": true
    }},
    "plan": {{
      "enabled": true
    }}
  }},

  "changelog": {{
    "audience": "developer"    // developer=technical, user=simple
  }},

  // ============================================================================
  // DEPLOYMENT - Platform configuration
  // ============================================================================
  "deployment": {deployment_json},

  // ============================================================================
  // ARCHITECTURE - Layer configuration
  // ============================================================================
  "arch": {{
    "layers": {{}}               // Define layers: {{ "core": {{ "tier": 0 }} }}
  }},

  // ============================================================================
  // MANAGED FILES - Auto-generated files manifest
  // ============================================================================
  "managed": {managed_indented}
}}
'''


def git_init(
    name: str | None = None,
    project_type: str | None = None,
    github_repo: str | None = None,
    visibility: str = "public",
) -> list[tuple[str, bool, str]]:
    """Initialize new project with full setup.

    Args:
        name: Project name (defaults to directory name)
        project_type: python, node, etc. (auto-detected if not provided)
        github_repo: GitHub repo in format owner/repo (optional)
        visibility: GitHub repo visibility (public, private, internal)

    Returns:
        List of (step, success, message) tuples
    """
    results = []
    root = Path.cwd()

    # 1. Git init
    if not (root / ".git").exists():
        try:
            run_git(["init"])
            results.append(("git init", True, "Repository initialized"))
        except Exception as e:
            results.append(("git init", False, str(e)))
            return results
    else:
        results.append(("git init", True, "Already initialized"))

    # 2. Detect/set project type
    if not project_type:
        project_type = detect_project_type(root).value
    results.append(("detect type", True, project_type))

    # 3. Create config
    success, msg = create_config(root, name or root.name, project_type, github_repo)
    results.append(("config.jsonc", success, msg))

    if not success:
        return results

    # Clear config cache to load new config
    clear_cache()

    # 4. Sync managed files
    try:
        sync_results = sync_all()
        results.extend(sync_results)
    except Exception as e:
        results.append(("sync files", False, str(e)))

    # 5. First commit
    try:
        run_git(["add", "-A"])
        run_git(["commit", "-m", "chore: initial commit"])
        results.append(("first commit", True, "Created"))
    except Exception as e:
        results.append(("first commit", False, str(e)))

    # 6. GitHub setup (if requested)
    if github_repo:
        gh_results = setup_github(github_repo, visibility)
        results.extend(gh_results)

    return results


def git_update(force: bool = False) -> list[tuple[str, bool, str]]:
    """Update existing project - sync files and GitHub settings.

    Args:
        force: Overwrite manual changes if True

    Returns:
        List of (step, success, message) tuples
    """
    results = []

    # 1. Check config exists
    try:
        config = load_config()
        if not config:
            return [("config", False, "No config found - run /dk git init first")]
    except Exception as e:
        return [("config", False, f"Config error: {e}")]

    results.append(("config", True, "Valid"))

    # 2. Sync managed files
    try:
        sync_results = sync_all()
        results.extend(sync_results)
    except Exception as e:
        results.append(("sync files", False, str(e)))

    # 3. Check GitHub remote
    github_url = get("github.url", "")
    if github_url:
        repo = github_url.replace("https://github.com/", "")
        gh_results = update_github_settings(repo)
        results.extend(gh_results)
    else:
        results.append(("github", True, "No remote configured"))

    return results


def create_config(
    root: Path,
    name: str,
    project_type: str,
    github_repo: str | None = None,
) -> tuple[bool, str]:
    """Create config.json with managed files based on project type.

    Args:
        root: Project root directory
        name: Project name
        project_type: python, node, nextjs, typescript, javascript
        github_repo: Optional GitHub repo (owner/repo format)

    Returns:
        Tuple of (success, message)
    """
    config_dir = root / ".claude" / ".devkit"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Base managed files (all project types)
    managed = {
        "linters": {
            ".markdownlint.json": {
                "template": "linters/common/markdownlint.json.template",
                "enabled": True,
            },
            ".markdownlintignore": {
                "template": "gitignore/markdownlint.ignore",
                "enabled": True,
            },
        },
        "github": {
            ".github/workflows/claude.yml": {
                "template": "github/workflows/claude.yml.template",
                "enabled": True,
            },
            ".github/workflows/claude-code-review.yml": {
                "template": "github/workflows/claude-code-review.yml.template",
                "enabled": True,
            },
            ".github/ISSUE_TEMPLATE/bug_report.yml": {
                "template": "github/ISSUE_TEMPLATE/bug_report.yml.template",
                "enabled": True,
            },
            ".github/ISSUE_TEMPLATE/feature_request.yml": {
                "template": "github/ISSUE_TEMPLATE/feature_request.yml.template",
                "enabled": True,
            },
            ".github/ISSUE_TEMPLATE/config.yml": {
                "template": "github/ISSUE_TEMPLATE/config.yml.template",
                "enabled": True,
            },
            ".github/PULL_REQUEST_TEMPLATE.md": {
                "template": "github/PULL_REQUEST_TEMPLATE.md.template",
                "enabled": True,
            },
        },
        "docs": {
            "README.md": {
                "type": "auto_sections",
                "enabled": True,
            },
            "CLAUDE.md": {
                "type": "auto_sections",
                "enabled": True,
            },
            "docs/PLUGIN.md": {
                "type": "template",
                "template": "docs/PLUGIN.md.template",
                "enabled": True,
            },
        },
        "ignore": {},
    }

    # Type-specific configuration
    if project_type == "python":
        managed["linters"]["ruff.toml"] = {
            "template": "linters/python/ruff.toml.template",
            "enabled": True,
        }
        managed["github"][".github/workflows/release.yml"] = {
            "template": "github/workflows/release-python.yml.template",
            "enabled": True,
        }
        managed["ignore"][".gitignore"] = {
            "template": ["gitignore/common.gitignore", "gitignore/python.gitignore"],
            "enabled": True,
        }
        test_framework = "pytest"
        # Python projects can't be deployed to Vercel (use Railway, Render, Fly.io)
        deployment = {
            "enabled": False,
            "platforms": ["railway", "render", "fly"],
            "note": "Python projects cannot be deployed to Vercel. Use Railway, Render, or Fly.io.",
        }
    elif project_type == "plugin":
        # Claude plugins are not deployed
        managed["github"][".github/workflows/release.yml"] = {
            "template": "github/workflows/release-python.yml.template",
            "enabled": True,
        }
        managed["ignore"][".gitignore"] = {
            "template": ["gitignore/common.gitignore", "gitignore/python.gitignore"],
            "enabled": True,
        }
        test_framework = "pytest"
        deployment = {
            "enabled": False,
            "platforms": [],
            "note": "Claude plugins are not deployed. They run locally via Claude Code.",
        }
    else:  # node, nextjs, typescript, javascript
        managed["github"][".github/workflows/release.yml"] = {
            "template": "github/workflows/release-node.yml.template",
            "enabled": True,
        }
        managed["ignore"][".gitignore"] = {
            "template": ["gitignore/common.gitignore", "gitignore/nextjs.gitignore"],
            "enabled": True,
        }
        test_framework = "vitest"
        # Node/Next.js projects can be deployed to Vercel
        deployment = {
            "enabled": True,
            "platform": "vercel",
            "platforms": ["vercel", "railway", "render", "netlify"],
            "framework": "nextjs" if project_type == "nextjs" else "other",
            "env_sync": True,
            "production_domain": "",
        }

    # Build github URL and visibility
    github_url = f"https://github.com/{github_repo}" if github_repo else ""
    github_visibility = "public"  # Default to public for branch protection support

    # Detect version from package.json or pyproject.toml
    version = detect_project_version(root)

    # Generate JSONC with comments
    jsonc_content = generate_config_jsonc(
        name=name,
        project_type=project_type,
        version=version,
        github_url=github_url,
        github_visibility=github_visibility,
        deployment=deployment,
        managed=managed,
        test_framework=test_framework,
    )

    config_file = config_dir / "config.jsonc"
    config_file.write_text(jsonc_content)

    # Copy schema (optional, suppress errors)
    with contextlib.suppress(Exception):
        plugin_root = get_plugin_root()
        schema_src = plugin_root / ".claude" / ".devkit" / "config.schema.json"
        if schema_src.exists():
            (config_dir / "config.schema.json").write_text(schema_src.read_text())

    return True, f"Created {config_file}"


def setup_github(repo: str, visibility: str = "public") -> list[tuple[str, bool, str]]:
    """Setup GitHub repo with best practices.

    Args:
        repo: GitHub repo in format owner/repo
        visibility: Repository visibility (public, private, internal)

    Returns:
        List of (step, success, message) tuples
    """
    results = []
    valid_vis = ("public", "private", "internal")
    visibility_flag = f"--{visibility}" if visibility in valid_vis else "--public"

    try:
        # Create or connect repo
        subprocess.run(
            ["gh", "repo", "create", repo, "--source=.", "--push", visibility_flag],
            check=True,
            capture_output=True,
        )
        results.append(("gh repo create", True, f"Created {repo} ({visibility})"))
    except subprocess.CalledProcessError:
        # Repo might already exist, try to set remote
        with contextlib.suppress(Exception):
            run_git(["remote", "add", "origin", f"https://github.com/{repo}.git"])
            results.append(("git remote", True, f"Added origin {repo}"))

        try:
            run_git(["push", "-u", "origin", "main"])
            results.append(("git push", True, "Pushed to origin/main"))
        except Exception as e:
            results.append(("git push", False, str(e)))
            return results

    # Configure settings
    results.extend(update_github_settings(repo))
    return results


def is_org_repo(repo: str) -> bool:
    """Check if repo belongs to an organization (not personal).

    Args:
        repo: GitHub repo in format owner/repo

    Returns:
        True if org repo, False if personal
    """
    owner = repo.split("/")[0]
    try:
        result = subprocess.run(
            ["gh", "api", f"/users/{owner}"],
            capture_output=True,
            text=True,
            check=True,
        )
        import json

        data = json.loads(result.stdout)
        return data.get("type") == "Organization"
    except Exception:
        return False


def configure_actions_permissions(repo: str) -> tuple[bool, str]:
    """Configure GitHub Actions permissions for org repos.

    Enables workflow write permissions so GITHUB_TOKEN can push commits.

    Args:
        repo: GitHub repo in format owner/repo

    Returns:
        Tuple of (success, message)
    """
    try:
        # Enable Actions and set permissions
        subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "PUT",
                f"/repos/{repo}/actions/permissions",
                "-f",
                "enabled=true",
                "-f",
                "allowed_actions=all",
            ],
            capture_output=True,
            check=True,
        )
        # Set workflow permissions to read-write
        subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "PUT",
                f"/repos/{repo}/actions/permissions/workflow",
                "-f",
                "default_workflow_permissions=write",
                "-F",
                "can_approve_pull_request_reviews=true",
            ],
            capture_output=True,
            check=True,
        )
        return True, "Actions permissions configured (write access)"
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        return False, f"Failed: {stderr}"


def update_github_settings(repo: str) -> list[tuple[str, bool, str]]:
    """Update GitHub repo settings and branch protection.

    Reads settings from config.json:
    - github.pr.merge_method: squash (default), merge, or rebase
    - github.pr.delete_branch: delete branch after merge (default: true)

    Args:
        repo: GitHub repo in format owner/repo

    Returns:
        List of (step, success, message) tuples
    """
    results = []

    # Check if org repo and configure Actions permissions
    if is_org_repo(repo):
        ok, msg = configure_actions_permissions(repo)
        results.append(("actions permissions", ok, msg))
        results.append(("release token", True, "Using GITHUB_TOKEN (org repo)"))
    else:
        results.append(("release token", True, "Needs RELEASE_PAT secret (personal repo)"))

    # Read PR settings from config
    merge_method = get("github.pr.merge_method", "squash")
    delete_branch = get("github.pr.delete_branch", True)

    # Build merge settings based on config
    allow_squash = "true" if merge_method == "squash" else "false"
    allow_merge = "true" if merge_method == "merge" else "false"
    allow_rebase = "true" if merge_method == "rebase" else "false"
    delete_on_merge = "true" if delete_branch else "false"

    # Repo settings from config
    try:
        subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "PATCH",
                f"/repos/{repo}",
                "-f",
                f"allow_squash_merge={allow_squash}",
                "-f",
                f"allow_merge_commit={allow_merge}",
                "-f",
                f"allow_rebase_merge={allow_rebase}",
                "-f",
                f"delete_branch_on_merge={delete_on_merge}",
                "-f",
                "squash_merge_commit_title=PR_TITLE",
            ],
            check=True,
            capture_output=True,
        )
        msg = f"merge={merge_method}, delete_branch={delete_branch}"
        results.append(("repo settings", True, msg))
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        results.append(("repo settings", False, stderr))

    # Branch protection (requires all fields for GitHub API)
    try:
        protection = json.dumps(
            {
                "required_status_checks": None,
                "enforce_admins": False,
                "required_pull_request_reviews": None,
                "restrictions": None,
                "required_linear_history": True,
                "allow_force_pushes": False,
                "allow_deletions": False,
            }
        )
        subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "PUT",
                f"/repos/{repo}/branches/main/protection",
                "--input",
                "-",
            ],
            input=protection.encode(),
            check=True,
            capture_output=True,
        )
        results.append(("branch protection", True, "Linear history, no force push"))
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        results.append(("branch protection", False, stderr))

    return results
