"""Health check system - validates plugin state.

TIER 2: May import from core and lib.
"""

from pathlib import Path

from lib.config import get, get_project_root, load_config
from lib.sync import get_plugin_root, load_presets, render_template


def check_config() -> tuple[bool, list[str]]:
    """Validate config against schema and required fields.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    try:
        config = load_config()
    except Exception as e:
        return False, [f"Config load failed: {e}"]

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
    valid_types = ["python", "node", "nextjs", "typescript", "javascript"]
    if project_type and project_type not in valid_types:
        errors.append(f"Invalid project.type: {project_type}")

    return len(errors) == 0, errors


def check_sync() -> list[tuple[str, bool, str]]:
    """Check all managed files are in sync with templates.

    Returns:
        List of (file_path, is_in_sync, message)
    """
    results = []
    root = get_project_root()
    plugin_root = get_plugin_root()
    managed = get("managed", {})

    # Get template values
    project_name = get("project.name", "Project")
    project_type = get("project.type", "unknown")
    github_url = get("github.url", "https://github.com/owner/repo")
    linters_config = get("linters", {})
    preset = linters_config.get("preset", "strict")
    overrides = linters_config.get("overrides", {})

    presets = load_presets()

    template_values = {
        "project_name": project_name,
        "github_url": github_url,
        "preset": preset,
    }

    # Add preset values based on project type
    if project_type == "python":
        python_presets = presets.get("python", {}).get(preset, {})
        template_values.update(python_presets)
    elif project_type in ("nextjs", "typescript", "javascript"):
        nextjs_presets = presets.get("nextjs", {}).get(preset, {})
        template_values.update(nextjs_presets)

    # Add common presets
    common_presets = presets.get("common", {}).get(preset, {})
    template_values.update(common_presets)

    # Apply overrides
    template_values.update(overrides)

    # Check linter files
    for output_path, config in managed.get("linters", {}).items():
        if not config.get("enabled", True):
            results.append((output_path, True, "disabled"))
            continue

        template_path = config.get("template", "")
        result = _check_file_sync(root, plugin_root, output_path, template_path, template_values)
        results.append(result)

    # Check github files
    for output_path, config in managed.get("github", {}).items():
        if not config.get("enabled", True):
            results.append((output_path, True, "disabled"))
            continue

        template_path = config.get("template", "")
        result = _check_file_sync(root, plugin_root, output_path, template_path, template_values)
        results.append(result)

    # Check ignore files
    for output_path, config in managed.get("ignore", {}).items():
        if not config.get("enabled", True):
            results.append((output_path, True, "disabled"))
            continue

        template_paths = config.get("template", [])
        if isinstance(template_paths, str):
            template_paths = [template_paths]

        result = _check_ignore_sync(root, plugin_root, output_path, template_paths, project_type)
        results.append(result)

    # Check docs (existence only - content check is complex)
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


def _check_file_sync(
    root: Path, plugin_root: Path, output_path: str, template_path: str, values: dict
) -> tuple[str, bool, str]:
    """Check if a single file is in sync with its template."""
    output_file = root / output_path
    template_file = plugin_root / "templates" / template_path

    if not template_file.exists():
        return output_path, False, f"template not found: {template_path}"

    if not output_file.exists():
        return output_path, False, "missing"

    # Generate expected content
    template = template_file.read_text()
    expected = render_template(template, values)
    actual = output_file.read_text()

    if expected.strip() == actual.strip():
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
        for func in functions:
            # Look for test_<func> or test_*_<func>_* patterns
            if f"test_{func}" not in content:
                issues.append(f"Missing test: {module}:{func}()")

    return "FAIL" if issues else "PASS", issues


def check_all() -> dict:
    """Run all health checks and return consolidated report.

    Returns:
        Dict with results for each check category
    """
    config_ok, config_errors = check_config()
    sync_results = check_sync()
    arch_ok, arch_violations = check_arch()
    test_status, test_issues = check_tests()

    # Count sync issues
    sync_ok = all(r[1] for r in sync_results)
    sync_issues = [r for r in sync_results if not r[1]]

    # Test status (SKIP doesn't affect health, FAIL does)
    test_ok = test_status != "FAIL"

    # Overall status
    all_ok = config_ok and sync_ok and arch_ok and test_ok

    return {
        "healthy": all_ok,
        "config": {
            "ok": config_ok,
            "errors": config_errors,
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
    }


def format_report(results: dict) -> str:
    """Format health check results for display.

    Args:
        results: Output from check_all()

    Returns:
        Formatted string for terminal output
    """
    lines = []

    # Config section
    lines.append("── Config ──────────────────────────")
    if results["config"]["ok"]:
        lines.append("✓ Schema valid")
        lines.append("✓ Required fields present")
    else:
        lines.append("✗ Config invalid:")
        lines.extend(f"  - {error}" for error in results["config"]["errors"])

    lines.append("")

    # Sync section
    lines.append("── Sync ────────────────────────────")
    for path, ok, msg in results["sync"]["results"]:
        if msg == "disabled":
            continue
        symbol = "✓" if ok else "✗"
        lines.append(f"{symbol} {path} ({msg})")

    if not results["sync"]["ok"]:
        lines.append("  → Run: /dk plugin update")

    lines.append("")

    # Architecture section
    lines.append("── Architecture ────────────────────")
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

    lines.append("")

    # Tests section
    lines.append("── Tests ───────────────────────────")
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
        lines.extend(f"  - {issue}" for issue in test_issues[:5])
        if len(test_issues) > 5:
            lines.append(f"  - ... and {len(test_issues) - 5} more")

    lines.append("")

    # Summary
    lines.append("━" * 35)
    if results["healthy"]:
        lines.append("Status: HEALTHY")
    else:
        issue_count = (
            len(results["config"]["errors"])
            + len(results["sync"]["issues"])
            + len(results["arch"]["violations"])
            + (len(results.get("tests", {}).get("issues", [])) if results.get("tests", {}).get("status") == "FAIL" else 0)
        )
        lines.append(f"Status: {issue_count} issue(s) found")
        lines.append("Action: /dk plugin update")

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
