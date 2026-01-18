"""Health check system - validates plugin state.

TIER 2: May import from core and lib.
"""

import json
import re
from pathlib import Path
from typing import Any

from lib.config import get, get_missing_sections, get_project_root, load_config
from lib.sync import check_user_files, get_plugin_root, get_rendered_template, load_presets

# Constants
MAX_DISPLAY_ITEMS = 5


def check_config() -> tuple[bool, list[str], list[str]]:
    """Validate config against schema and required fields.

    Returns:
        Tuple of (is_valid, list of error messages, list of missing optional sections)
    """
    errors = []

    try:
        config = load_config()
    except Exception as e:
        return False, [f"Config load failed: {e}"], []

    # Check $schema reference - if present, verify file exists
    schema_ref = config.get("$schema")
    if schema_ref:
        # Schema is referenced - check if file exists
        root = get_project_root()
        config_dir = root / ".claude" / ".devkit"
        schema_path = (config_dir / schema_ref).resolve()

        if not schema_path.exists():
            errors.append(f"Schema file missing: {schema_ref} (run /dk plugin update)")

    # Check required fields
    if "project" not in config:
        errors.append("Missing required field: project")
    else:
        if "name" not in config["project"]:
            errors.append("Missing required field: project.name")
        if "type" not in config["project"]:
            errors.append("Missing required field: project.type")

    # Check project type is valid
    project_type = config.get("project", {}).get("type")
    valid_types = ["python", "node", "nextjs", "typescript", "javascript", "plugin"]
    if project_type and project_type not in valid_types:
        errors.append(f"Invalid project.type: {project_type}")

    # Check for missing recommended sections
    missing_sections = get_missing_sections()

    return len(errors) == 0, errors, missing_sections


def _build_check_values() -> dict[str, Any]:
    """Build template values for sync checking.

    Returns:
        Dict of template values.
    """
    project_type = get("project.type", "unknown")
    linters_config = get("linters", {})
    preset = linters_config.get("preset", "strict")
    overrides = linters_config.get("overrides", {})
    presets = load_presets()

    values: dict[str, Any] = {
        "project_name": get("project.name", "Project"),
        "github_url": get("github.url", "https://github.com/owner/repo"),
        "preset": preset,
    }

    # Add preset values based on project type
    if project_type in ("python", "plugin"):
        values.update(presets.get("python", {}).get(preset, {}))
    elif project_type in ("nextjs", "typescript", "javascript"):
        values.update(presets.get("nextjs", {}).get(preset, {}))

    # Add common presets and overrides
    values.update(presets.get("common", {}).get(preset, {}))
    values.update(overrides)
    return values


def _check_managed_category(
    root: Path,
    plugin_root: Path,
    managed: dict[str, Any],
    category: str,
    values: dict[str, Any],
) -> list[tuple[str, bool, str]]:
    """Check sync status for a managed file category.

    Args:
        root: Project root directory.
        plugin_root: Plugin installation root.
        managed: Managed config section.
        category: Category name (linters, github).
        values: Template values.

    Returns:
        List of sync check results.
    """
    results: list[tuple[str, bool, str]] = []
    for output_path, config in managed.get(category, {}).items():
        if not config.get("enabled", True):
            results.append((output_path, True, "disabled"))
            continue

        template_path = config.get("template", "")
        result = _check_file_sync(root, plugin_root, output_path, template_path, values)
        results.append(result)
    return results


def _check_managed_ignore(
    root: Path, plugin_root: Path, managed: dict[str, Any], project_type: str
) -> list[tuple[str, bool, str]]:
    """Check sync status for ignore files.

    Args:
        root: Project root directory.
        plugin_root: Plugin installation root.
        managed: Managed config section.
        project_type: Project type for section headers.

    Returns:
        List of sync check results.
    """
    results: list[tuple[str, bool, str]] = []
    for output_path, config in managed.get("ignore", {}).items():
        if not config.get("enabled", True):
            results.append((output_path, True, "disabled"))
            continue

        template_paths = config.get("template", [])
        if isinstance(template_paths, str):
            template_paths = [template_paths]

        result = _check_ignore_sync(root, plugin_root, output_path, template_paths, project_type)
        results.append(result)
    return results


def _check_managed_docs(root: Path, managed: dict[str, Any]) -> list[tuple[str, bool, str]]:
    """Check existence of managed docs.

    Args:
        root: Project root directory.
        managed: Managed config section.

    Returns:
        List of existence check results.
    """
    results: list[tuple[str, bool, str]] = []
    for output_path, config in managed.get("docs", {}).items():
        if not config.get("enabled", True):
            results.append((output_path, True, "disabled"))
            continue

        file_path = root / output_path
        if file_path.exists():
            results.append((output_path, True, "exists"))
        else:
            results.append((output_path, False, "missing"))
    return results


def check_sync() -> list[tuple[str, bool, str]]:
    """Check all managed files are in sync with templates.

    Returns:
        List of (file_path, is_in_sync, message)
    """
    root = get_project_root()
    plugin_root = get_plugin_root()
    managed = get("managed", {})
    project_type = get("project.type", "unknown")
    values = _build_check_values()

    results: list[tuple[str, bool, str]] = []
    results.extend(_check_managed_category(root, plugin_root, managed, "config", values))
    results.extend(_check_managed_category(root, plugin_root, managed, "linters", values))
    results.extend(_check_managed_category(root, plugin_root, managed, "github", values))
    results.extend(_check_managed_ignore(root, plugin_root, managed, project_type))
    results.extend(_check_managed_docs(root, managed))

    return results


def _check_file_sync(
    root: Path, plugin_root: Path, output_path: str, template_path: str, values: dict
) -> tuple[str, bool, str]:
    """Check if a single file is in sync with its template."""
    output_file = root / output_path

    if not output_file.exists():
        return output_path, False, "missing"

    # Generate expected content using shared function
    expected, error = get_rendered_template(plugin_root, template_path, values)
    if error:
        return output_path, False, error.lower()

    actual = output_file.read_text()

    if expected and expected.strip() == actual.strip():
        return output_path, True, "in sync"
    return output_path, False, "outdated"


def _check_ignore_sync(
    root: Path, plugin_root: Path, output_path: str, template_paths: list[str], project_type: str
) -> tuple[str, bool, str]:
    """Check if an ignore file is in sync with its templates."""
    output_file = root / output_path

    if not output_file.exists():
        return output_path, False, "missing"

    # Generate expected content by combining templates
    parts = []
    for template_path in template_paths:
        template_file = plugin_root / "templates" / template_path
        if template_file.exists():
            if "common" not in template_path:
                parts.append(f"\n# === {project_type.upper()} ===\n")
            parts.append(template_file.read_text())

    expected = "\n".join(parts)
    actual = output_file.read_text()

    if expected.strip() == actual.strip():
        return output_path, True, "in sync"
    return output_path, False, "outdated"


def _get_changelog_version(root: Path) -> str | None:
    """Extract latest version from CHANGELOG.md.

    Looks for patterns like:
    - ## [0.19.0]
    - ## 0.19.0
    - # v0.19.0

    Returns:
        Version string or None if not found.
    """
    changelog = root / "CHANGELOG.md"
    if not changelog.exists():
        return None

    try:
        content = changelog.read_text()
        # Match ## [0.19.0], ## 0.19.0, or # v0.19.0
        match = re.search(r"^#+\s*\[?v?(\d+\.\d+\.\d+)\]?", content, re.MULTILINE)
        if match:
            return match.group(1)
    except OSError:
        pass
    return None


def _get_git_tag_version(root: Path) -> str | None:
    """Get latest git tag version using semver sorting.

    Uses `git tag --sort=-version:refname` to get the latest semver tag
    regardless of branch position. This works correctly on feature branches.

    Returns:
        Version string (without v prefix) or None if not found.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "tag", "--list", "v*", "--sort=-version:refname"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        tags = result.stdout.strip().split("\n")
        tag = tags[0] if tags and tags[0] else None
        # Remove 'v' prefix if present
        return tag.lstrip("v") if tag else None
    except (subprocess.SubprocessError, OSError):
        return None


def check_versions() -> tuple[bool, dict[str, str], list[str]]:
    """Check that all version files are in sync.

    Checks version in:
    - .claude-plugin/plugin.json (version) - authoritative for plugin projects
    - package.json (version) - authoritative for node projects
    - pyproject.toml (project.version) - authoritative for python projects
    - .claude/.devkit/config.jsonc (project.version)
    - CHANGELOG.md (latest version header)
    - Git tags (latest tag)

    Returns:
        Tuple of (all_in_sync, versions_found, list of errors)
    """
    root = get_project_root()
    versions: dict[str, str] = {}
    errors: list[str] = []

    # Check package.json
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            if "version" in data:
                versions["package.json"] = data["version"]
        except (json.JSONDecodeError, OSError):
            pass

    # Check pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            # Simple regex to extract version from [project] section
            match = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                versions["pyproject.toml"] = match.group(1)
        except OSError:
            pass

    # Check plugin.json (Claude plugins)
    plugin_json = root / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        try:
            data = json.loads(plugin_json.read_text())
            if "version" in data:
                # Strip commit suffix for comparison (e.g., "0.19.0-abc1234" -> "0.19.0")
                version = data["version"].split("-")[0]
                versions["plugin.json"] = version
        except (json.JSONDecodeError, OSError):
            pass

    # Check config.jsonc
    config_jsonc = root / ".claude" / ".devkit" / "config.jsonc"
    if config_jsonc.exists():
        try:
            content = config_jsonc.read_text()
            # Extract version from "project" section using regex (JSONC may have comments)
            match = re.search(
                r'"project"\s*:\s*\{[^}]*"version"\s*:\s*"([^"]+)"', content, re.DOTALL
            )
            if match:
                versions["config.jsonc"] = match.group(1)
        except OSError:
            pass

    # Check CHANGELOG.md
    changelog_version = _get_changelog_version(root)
    if changelog_version:
        versions["CHANGELOG.md"] = changelog_version

    # Check Git tags
    git_tag_version = _get_git_tag_version(root)
    if git_tag_version:
        versions["git tag"] = git_tag_version

    # If we have multiple version sources, check they match
    if len(versions) > 1:
        unique_versions = set(versions.values())
        if len(unique_versions) > 1:
            # Find the "authoritative" version (priority: plugin.json > package.json > pyproject.toml)
            authoritative = (
                versions.get("plugin.json")
                or versions.get("package.json")
                or versions.get("pyproject.toml")
            )
            if authoritative:
                for file, version in versions.items():
                    if version != authoritative:
                        errors.append(f"{file} has {version}, expected {authoritative}")

    all_in_sync = len(errors) == 0
    return all_in_sync, versions, errors


def check_arch() -> tuple[bool, list[dict]]:
    """Check layer rule compliance.

    Returns:
        Tuple of (is_compliant, list of violations)
    """
    try:
        from arch.rules import get_violations

        violations = get_violations()
        return len(violations) == 0, violations
    except ImportError:
        return True, []
    except Exception as e:
        return False, [f"Arch check failed: {e}"]


def check_templates() -> tuple[bool, list[str]]:
    """Validate that all required templates exist.

    Templates are the single source of truth for generated files.

    Returns:
        Tuple of (all_exist, list of missing template paths)
    """
    plugin_root = get_plugin_root()

    required_templates = [
        "CLAUDE.md.template",
        "docs/PLUGIN.md.template",
        "docs/README.md.template",
        "claude/statusline.sh.template",
    ]

    missing = []
    for template in required_templates:
        template_path = plugin_root / "templates" / template
        if not template_path.exists():
            missing.append(template)

    return len(missing) == 0, missing


def check_tests() -> tuple[str, list[str]]:
    """Check test coverage against config requirements.

    Returns:
        Tuple of (status, list of issues)
        Status: "PASS", "FAIL", or "SKIP"
    """
    issues = []

    # Check if testing is enabled
    if not get("testing.enabled", False):
        return "SKIP", ["Testing not enabled in config"]

    required = get("testing.required_modules", {})
    if not required:
        return "SKIP", ["No required_modules defined"]

    root = get_project_root()
    tests_dir = root / "tests"

    if not tests_dir.exists():
        return "FAIL", ["tests/ directory missing"]

    for module, functions in required.items():
        # Get test file name from module path
        module_name = Path(module).stem
        test_file = tests_dir / f"test_{module_name}.py"

        if not test_file.exists():
            issues.append(f"Missing: tests/test_{module_name}.py")
            continue

        # Check if required functions have tests
        content = test_file.read_text()
        missing_funcs = [f for f in functions if f"test_{f}" not in content]
        issues.extend(f"Missing test: {module}:{func}()" for func in missing_funcs)

    return "FAIL" if issues else "PASS", issues


def check_consistency_wrapper() -> tuple[bool, dict]:
    """Run consistency checks.

    Returns:
        Tuple of (is_valid, results dict)
    """
    try:
        from arch.consistency import check_consistency

        all_valid, results = check_consistency()
        return all_valid, results
    except ImportError:
        return True, {}
    except Exception:
        return True, {}


def check_all() -> dict:
    """Run all health checks and return consolidated report.

    Returns:
        Dict with results for each check category
    """
    config_ok, config_errors, missing_sections = check_config()
    sync_results = check_sync()
    arch_ok, arch_violations = check_arch()
    templates_ok, templates_missing = check_templates()
    test_status, test_issues = check_tests()
    user_files = check_user_files()
    versions_ok, versions_found, versions_errors = check_versions()
    consistency_ok, consistency_results = check_consistency_wrapper()

    # Count sync issues
    sync_ok = all(r[1] for r in sync_results)
    sync_issues = [r for r in sync_results if not r[1]]

    # Test status (SKIP doesn't affect health, FAIL does)
    test_ok = test_status != "FAIL"

    # User files status (missing or outdated doesn't block health, but reported)
    user_files_issues = [
        (path, status)
        for path, status in user_files.items()
        if not status.get("exists") or status.get("outdated")
    ]

    # Missing sections don't block health, but should be reported
    has_missing = len(missing_sections) > 0

    # Overall status (missing sections are warnings, not errors)
    # Version mismatch and missing templates are errors that affect health
    # Consistency issues are warnings, don't block healthy status
    all_ok = config_ok and sync_ok and arch_ok and test_ok and versions_ok and templates_ok

    return {
        "healthy": all_ok,
        "config": {
            "ok": config_ok,
            "errors": config_errors,
            "missing_sections": missing_sections,
        },
        "sync": {
            "ok": sync_ok,
            "results": sync_results,
            "issues": sync_issues,
        },
        "arch": {
            "ok": arch_ok,
            "violations": arch_violations,
        },
        "templates": {
            "ok": templates_ok,
            "missing": templates_missing,
        },
        "tests": {
            "status": test_status,
            "ok": test_ok,
            "issues": test_issues,
        },
        "versions": {
            "ok": versions_ok,
            "found": versions_found,
            "errors": versions_errors,
        },
        "consistency": {
            "ok": consistency_ok,
            "results": consistency_results,
        },
        "user_files": {
            "status": user_files,
            "issues": user_files_issues,
        },
        "upgradable": has_missing,
    }


def _format_config_section(results: dict[str, Any]) -> list[str]:
    """Format config section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["── Config ──────────────────────────"]

    if results["config"]["ok"]:
        lines.append("✓ Schema valid")
        lines.append("✓ Required fields present")
    else:
        lines.append("✗ Config invalid:")
        lines.extend(f"  - {error}" for error in results["config"]["errors"])

    # Show missing optional sections
    missing = results["config"].get("missing_sections", [])
    if missing:
        lines.append("")
        lines.append(f"⚠ Missing optional sections ({len(missing)}):")
        lines.extend(f"  - {section}" for section in missing[:MAX_DISPLAY_ITEMS])
        if len(missing) > MAX_DISPLAY_ITEMS:
            lines.append(f"  - ... and {len(missing) - MAX_DISPLAY_ITEMS} more")
        lines.append("  → Run: /dk plugin update (adds defaults)")

    return lines


def _format_sync_section(results: dict[str, Any]) -> list[str]:
    """Format sync section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["── Sync ────────────────────────────"]

    for path, ok, msg in results["sync"]["results"]:
        if msg == "disabled":
            continue
        symbol = "✓" if ok else "✗"
        lines.append(f"{symbol} {path} ({msg})")

    if not results["sync"]["ok"]:
        lines.append("  → Run: /dk plugin update")

    return lines


def _format_arch_section(results: dict[str, Any]) -> list[str]:
    """Format architecture section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["── Architecture ────────────────────"]

    if results["arch"]["ok"]:
        layers = get("arch.layers", {})
        if layers:
            sorted_layers = sorted(layers.items(), key=lambda x: x[1].get("tier", 0))
            layer_str = " → ".join(f"{name} ({cfg['tier']})" for name, cfg in sorted_layers)
            lines.append("✓ Layer rules compliant")
            lines.append(f"  {layer_str}")
        else:
            lines.append("✓ No layers configured")
    else:
        lines.append("✗ Layer violations:")
        lines.extend(f"  - {violation}" for violation in results["arch"]["violations"])

    return lines


def _format_templates_section(results: dict[str, Any]) -> list[str]:
    """Format templates section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["── Templates ───────────────────────"]

    templates_data = results.get("templates", {})
    templates_ok = templates_data.get("ok", True)
    templates_missing = templates_data.get("missing", [])

    if templates_ok:
        lines.append("✓ All required templates present")
    else:
        lines.append("✗ Missing templates:")
        for template in templates_missing:
            lines.append(f"  - templates/{template}")
        lines.append("  → Plugin installation may be corrupted")

    return lines


def _format_tests_section(results: dict[str, Any]) -> list[str]:
    """Format tests section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["── Tests ───────────────────────────"]

    test_status = results.get("tests", {}).get("status", "SKIP")
    test_issues = results.get("tests", {}).get("issues", [])

    if test_status == "SKIP":
        lines.append("○ Skipped (testing not enabled)")
    elif test_status == "PASS":
        required = get("testing.required_modules", {})
        total_funcs = sum(len(funcs) for funcs in required.values())
        lines.append(f"✓ All required tests present ({total_funcs} functions)")
    else:
        lines.append(f"✗ Missing tests ({len(test_issues)} issues):")
        lines.extend(f"  - {issue}" for issue in test_issues[:MAX_DISPLAY_ITEMS])
        if len(test_issues) > MAX_DISPLAY_ITEMS:
            lines.append(f"  - ... and {len(test_issues) - MAX_DISPLAY_ITEMS} more")

    return lines


def _format_versions_section(results: dict[str, Any]) -> list[str]:
    """Format versions section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["── Versions ────────────────────────"]

    versions_data = results.get("versions", {})
    versions_found = versions_data.get("found", {})
    versions_errors = versions_data.get("errors", [])
    versions_ok = versions_data.get("ok", True)

    if not versions_found:
        lines.append("○ No version files found")
    elif versions_ok:
        # All versions match - show the version
        version = next(iter(versions_found.values()))
        files = ", ".join(versions_found.keys())
        lines.append(f"✓ All in sync: {version}")
        lines.append(f"  ({files})")
    else:
        lines.append("✗ Version mismatch:")
        for file, version in versions_found.items():
            lines.append(f"  - {file}: {version}")
        lines.append("  → Run: /dk plugin update (syncs versions)")

    return lines


def _format_consistency_section(results: dict[str, Any]) -> list[str]:
    """Format consistency section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["── Consistency ─────────────────────"]

    consistency_data = results.get("consistency", {})
    consistency_ok = consistency_data.get("ok", True)
    consistency_results = consistency_data.get("results", {})

    if not consistency_results:
        lines.append("○ Skipped (not configured)")
        return lines

    if consistency_ok:
        lines.append("✓ All consistency checks passed")
    else:
        # Count total violations
        all_violations = []
        for _, violations in consistency_results.values():
            all_violations.extend(violations)

        lines.append(f"✗ {len(all_violations)} consistency violation(s):")
        for v in all_violations[:MAX_DISPLAY_ITEMS]:
            severity_icon = "⚠" if v.get("severity") == "warning" else "✗"
            lines.append(f"  {severity_icon} [{v['rule']}] {v['message']}")
        if len(all_violations) > MAX_DISPLAY_ITEMS:
            lines.append(f"  ... and {len(all_violations) - MAX_DISPLAY_ITEMS} more")

    return lines


def _format_user_files_section(results: dict[str, Any]) -> list[str]:
    """Format user files section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["── User Files ──────────────────────"]

    user_files = results.get("user_files", {}).get("status", {})
    user_issues = results.get("user_files", {}).get("issues", [])

    if not user_files:
        lines.append("○ No user files configured")
    else:
        for path, status in user_files.items():
            if status.get("error"):
                lines.append(f"✗ {path} ({status['error']})")
            elif not status.get("exists"):
                lines.append(f"✗ {path} (missing)")
            elif status.get("outdated"):
                lines.append(f"⚠ {path} (outdated)")
            elif not status.get("configured", True):
                lines.append(f"⚠ {path} (not configured in settings.json)")
            else:
                lines.append(f"✓ {path} (current)")

    if user_issues:
        lines.append("  → Run: /dk plugin update (installs)")

    # Check for unconfigured statusline
    for path, status in user_files.items():
        if "statusline.sh" in path and status.get("exists") and not status.get("configured", True):
            lines.append("")
            lines.append("  ⚠ Statusline not activated in Claude Code!")
            lines.append("  → Add to settings.json:")
            lines.append(f'    "statusLine": {{ "command": "{path}" }}')
            break

    return lines


def _format_summary(results: dict[str, Any]) -> list[str]:
    """Format summary section of health report.

    Args:
        results: Health check results.

    Returns:
        List of formatted lines.
    """
    lines = ["━" * 35]

    if results["healthy"]:
        lines.append("Status: HEALTHY")
    else:
        issue_count = (
            len(results["config"]["errors"])
            + len(results["sync"]["issues"])
            + len(results["arch"]["violations"])
            + len(results.get("templates", {}).get("missing", []))
            + len(results.get("versions", {}).get("errors", []))
            + (
                len(results.get("tests", {}).get("issues", []))
                if results.get("tests", {}).get("status") == "FAIL"
                else 0
            )
        )
        lines.append(f"Status: {issue_count} issue(s) found")
        lines.append("Action: /dk plugin update")

    # User files warning (separate from health status)
    user_issues = results.get("user_files", {}).get("issues", [])
    if user_issues:
        lines.append("")
        lines.append(f"⚠ User files need update ({len(user_issues)} files)")

    return lines


def format_report(results: dict[str, Any]) -> str:
    """Format health check results for display.

    Args:
        results: Output from check_all()

    Returns:
        Formatted string for terminal output
    """
    sections = [
        _format_config_section(results),
        _format_versions_section(results),
        _format_sync_section(results),
        _format_arch_section(results),
        _format_templates_section(results),
        _format_tests_section(results),
        _format_consistency_section(results),
        _format_user_files_section(results),
        _format_summary(results),
    ]

    lines: list[str] = []
    for section in sections:
        lines.extend(section)
        lines.append("")

    # Remove trailing empty line
    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def format_compact(results: dict) -> str | None:
    """Format health check results for session start (compact).

    Args:
        results: Output from check_all()

    Returns:
        Compact warning string, or None if healthy
    """
    if results["healthy"]:
        return None

    # Categorize issues for clear reporting
    categories: dict[str, list[str]] = {
        "config": [],
        "sync": [],
        "arch": [],
        "versions": [],
        "templates": [],
        "tests": [],
        "consistency": [],
    }

    # Config errors
    categories["config"].extend(results["config"]["errors"])

    # Sync issues
    for path, _ok, msg in results["sync"]["issues"]:
        categories["sync"].append(f"{path}: {msg}")

    # Architecture violations
    for v in results["arch"]["violations"]:
        categories["arch"].append(v["message"])

    # Missing templates
    for template in results.get("templates", {}).get("missing", []):
        categories["templates"].append(f"templates/{template}")

    # Version mismatch errors
    categories["versions"].extend(results.get("versions", {}).get("errors", []))

    # Test issues
    if results.get("tests", {}).get("status") == "FAIL":
        categories["tests"].extend(results["tests"]["issues"])

    # Consistency violations
    consistency_results = results.get("consistency", {}).get("results", {})
    for _, violations in consistency_results.values():
        for v in violations:
            categories["consistency"].append(f"{v['rule']}: {v['message']}")

    # Build summary with category counts
    category_labels = {
        "config": "Config",
        "sync": "Sync",
        "arch": "Arch",
        "versions": "Version",
        "templates": "Template",
        "tests": "Test",
        "consistency": "Consistency",
    }

    active_categories = [(k, v) for k, v in categories.items() if v]
    total_issues = sum(len(v) for _, v in active_categories)

    if total_issues == 0:
        return None

    # Build header with category breakdown
    category_summary = ", ".join(
        f"{len(issues)} {category_labels[cat]}" for cat, issues in active_categories
    )
    lines = [f"⚠️ Plugin issues: {category_summary}"]

    # Show up to 3 specific issues
    shown = 0
    for cat, issues in active_categories:
        for issue in issues:
            if shown >= 3:
                break
            lines.append(f"   • [{category_labels[cat]}] {issue}")
            shown += 1
        if shown >= 3:
            break

    remaining = total_issues - shown
    if remaining > 0:
        lines.append(f"   ... and {remaining} more")

    lines.append("   Run: /dk plugin check")

    return "\n".join(lines)
