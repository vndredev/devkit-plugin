"""Health check system - validates plugin state.

TIER 2: May import from core and lib.
"""

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
    if project_type == "python":
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


def check_arch() -> tuple[bool, list[str]]:
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


def check_all() -> dict:
    """Run all health checks and return consolidated report.

    Returns:
        Dict with results for each check category
    """
    config_ok, config_errors, missing_sections = check_config()
    sync_results = check_sync()
    arch_ok, arch_violations = check_arch()
    test_status, test_issues = check_tests()
    user_files = check_user_files()

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
    all_ok = config_ok and sync_ok and arch_ok and test_ok

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
        "tests": {
            "status": test_status,
            "ok": test_ok,
            "issues": test_issues,
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
        _format_sync_section(results),
        _format_arch_section(results),
        _format_tests_section(results),
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

    issues = list(results["config"]["errors"])

    for path, _ok, msg in results["sync"]["issues"]:
        issues.append(f"{path} {msg}")

    issues.extend(results["arch"]["violations"])

    # Add test issues if testing failed
    if results.get("tests", {}).get("status") == "FAIL":
        issues.extend(results["tests"]["issues"])

    if not issues:
        return None

    lines = [f"⚠️ Plugin: {len(issues)} issue(s) found"]
    lines.extend(f"   - {issue}" for issue in issues[:3])  # Show max 3
    if len(issues) > 3:
        lines.append(f"   - ... and {len(issues) - 3} more")
    lines.append("   Run: /dk plugin check (details) or /dk plugin update (fix)")

    return "\n".join(lines)
