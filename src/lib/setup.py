"""Project setup - init and update workflows.

TIER 1: May import from core only.
"""

import json
import subprocess
from pathlib import Path

from lib.config import get, load_config, clear_cache
from lib.git import run_git
from lib.sync import sync_all, get_plugin_root
from lib.tools import detect_project_type


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
    results.append(("config.json", success, msg))

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
            return [("config", False, "No config.json found - run /dk git init first")]
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
        },
        "docs": {"CLAUDE.md": {"type": "auto_sections", "enabled": True}},
        "ignore": {},
    }

    # Type-specific files
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

    # Build github URL and visibility
    github_url = f"https://github.com/{github_repo}" if github_repo else ""
    github_visibility = "public"  # Default to public for branch protection support

    config = {
        "$schema": "./config.schema.json",
        "project": {
            "name": name,
            "type": project_type,
            "version": "0.0.0",
        },
        "hooks": {
            "session": {"enabled": True, "show_git_status": True},
            "validate": {"enabled": True, "block_force_push": True},
            "format": {"enabled": True, "auto_format": True},
            "plan": {"enabled": True},
        },
        "git": {
            "protected_branches": ["main"],
            "conventions": {
                "types": [
                    "feat",
                    "fix",
                    "chore",
                    "refactor",
                    "test",
                    "docs",
                    "perf",
                    "ci",
                ],
                "scopes": {
                    "mode": "strict",
                    "allowed": [],
                    "internal": ["internal", "review", "ci", "deps"],
                },
                "branch_pattern": "{type}/{description}",
            },
        },
        "github": {"url": github_url, "visibility": github_visibility},
        "arch": {"layers": {}},
        "linters": {"preset": "strict", "overrides": {}},
        "managed": managed,
        "testing": {"enabled": False, "framework": test_framework},
    }

    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps(config, indent=2))

    # Copy schema
    try:
        plugin_root = get_plugin_root()
        schema_src = plugin_root / ".claude" / ".devkit" / "config.schema.json"
        if schema_src.exists():
            (config_dir / "config.schema.json").write_text(schema_src.read_text())
    except Exception:
        pass  # Schema is optional

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
    visibility_flag = f"--{visibility}" if visibility in ("public", "private", "internal") else "--public"

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
        try:
            run_git(["remote", "add", "origin", f"https://github.com/{repo}.git"])
            results.append(("git remote", True, f"Added origin {repo}"))
        except Exception:
            # Remote might already exist
            pass

        try:
            run_git(["push", "-u", "origin", "main"])
            results.append(("git push", True, "Pushed to origin/main"))
        except Exception as e:
            results.append(("git push", False, str(e)))
            return results

    # Configure settings
    results.extend(update_github_settings(repo))
    return results


def update_github_settings(repo: str) -> list[tuple[str, bool, str]]:
    """Update GitHub repo settings and branch protection.

    Args:
        repo: GitHub repo in format owner/repo

    Returns:
        List of (step, success, message) tuples
    """
    results = []

    # Repo settings: squash merge only
    try:
        subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "PATCH",
                f"/repos/{repo}",
                "-f",
                "allow_squash_merge=true",
                "-f",
                "allow_merge_commit=false",
                "-f",
                "allow_rebase_merge=false",
                "-f",
                "delete_branch_on_merge=true",
                "-f",
                "squash_merge_commit_title=PR_TITLE",
            ],
            check=True,
            capture_output=True,
        )
        results.append(("repo settings", True, "Squash merge only"))
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
