"""Project consistency validation system.

TIER 2: May import from core and lib.

Validates project invariants:
- Module <-> Tests mapping
- Hooks <-> Handler mapping
- Config <-> Schema sync
- Skill routes <-> Reference docs
- Custom import rules
"""

from pathlib import Path
from typing import Any

from lib.config import get, get_project_root, load_config

# Violation structure type
Violation = dict[str, Any]  # rule, source, expected, message, severity

# Project-type specific defaults
# Note: hook_handlers and skill_routes are enabled for ALL types
# because they check project-local .claude/ folders, not just plugin internals
PROJECT_TYPE_DEFAULTS: dict[str, dict[str, Any]] = {
    "python": {
        "patterns": {"src/lib/*.py": "tests/test_{stem}.py"},
        "exclude": ["__init__.py"],
        "hook_handlers": True,
        "skill_routes": True,
    },
    "plugin": {
        "patterns": {"src/lib/*.py": "tests/test_{stem}.py"},
        "exclude": ["__init__.py"],
        "hook_handlers": True,
        "skill_routes": True,
    },
    "node": {
        "patterns": {
            "src/lib/*.ts": "__tests__/{stem}.test.ts",
            "src/components/*.tsx": "__tests__/{stem}.test.tsx",
        },
        "exclude": ["index.ts", "index.tsx"],
        "hook_handlers": True,
        "skill_routes": True,
    },
    "nextjs": {
        "patterns": {
            "src/lib/*.ts": "__tests__/{stem}.test.ts",
            "src/components/*.tsx": "__tests__/{stem}.test.tsx",
        },
        "exclude": ["index.ts", "index.tsx", "layout.tsx", "page.tsx"],
        "hook_handlers": True,
        "skill_routes": True,
    },
    "typescript": {
        "patterns": {"src/**/*.ts": "__tests__/{stem}.test.ts"},
        "exclude": ["index.ts"],
        "hook_handlers": True,
        "skill_routes": True,
    },
}


def _get_project_type() -> str:
    """Get the project type from config.

    Returns:
        Project type string.
    """
    return get("project.type", "python")


def _get_type_defaults() -> dict[str, Any]:
    """Get defaults for current project type.

    Returns:
        Dict with type-specific defaults.
    """
    project_type = _get_project_type()
    return PROJECT_TYPE_DEFAULTS.get(project_type, PROJECT_TYPE_DEFAULTS["python"])


def _get_patterns_from_config() -> dict[str, str]:
    """Get module-to-test patterns from config.

    Returns:
        Dict of source patterns to test patterns.
    """
    defaults = _get_type_defaults()
    rules = get("consistency.rules", {})
    module_tests = rules.get("module_tests", {})
    return module_tests.get("patterns", defaults["patterns"])


def _get_exclude_patterns() -> list[str]:
    """Get files to exclude from consistency checks.

    Returns:
        List of file names to exclude.
    """
    defaults = _get_type_defaults()
    rules = get("consistency.rules", {})
    module_tests = rules.get("module_tests", {})
    return module_tests.get("exclude", defaults["exclude"])


def _match_glob_pattern(file_path: Path, pattern: str, root: Path) -> bool:
    """Check if a file matches a glob pattern.

    Args:
        file_path: Path to check.
        pattern: Glob pattern (e.g., "src/lib/*.py").
        root: Project root.

    Returns:
        True if file matches pattern.
    """
    import fnmatch

    relative = str(file_path.relative_to(root))
    return fnmatch.fnmatch(relative, pattern)


def _resolve_test_path(source_path: Path, pattern: str, root: Path) -> Path:
    """Resolve expected test file path from source path.

    Args:
        source_path: Source file path.
        pattern: Test pattern with {stem} placeholder.
        root: Project root.

    Returns:
        Expected test file path.
    """
    stem = source_path.stem
    test_pattern = pattern.replace("{stem}", stem)
    return root / test_pattern


def check_module_tests() -> tuple[bool, list[Violation]]:
    """Check that source modules have corresponding test files.

    Returns:
        Tuple of (all_valid, list of violations).
    """
    rules = get("consistency.rules", {})
    module_tests = rules.get("module_tests", {})

    if not module_tests.get("enabled", True):
        return True, []

    root = get_project_root()
    patterns = _get_patterns_from_config()
    exclude = _get_exclude_patterns()
    violations: list[Violation] = []

    for source_pattern, test_pattern in patterns.items():
        # Find all files matching source pattern
        for source_file in root.glob(source_pattern):
            # Skip excluded files
            if source_file.name in exclude:
                continue

            # Resolve expected test path
            expected_test = _resolve_test_path(source_file, test_pattern, root)

            if not expected_test.exists():
                violations.append(
                    {
                        "rule": "module_tests",
                        "source": str(source_file.relative_to(root)),
                        "expected": str(expected_test.relative_to(root)),
                        "message": f"Missing test file for {source_file.name}",
                        "severity": "warning",
                    }
                )

    return len(violations) == 0, violations


def _check_plugin_hooks(root: Path) -> list[Violation]:
    """Check hooks defined in plugin.json for plugin projects.

    Args:
        root: Project root.

    Returns:
        List of violations.
    """
    import json
    import re

    violations: list[Violation] = []
    plugin_json = root / ".claude-plugin" / "plugin.json"

    if not plugin_json.exists():
        return violations

    try:
        data = json.loads(plugin_json.read_text())
        hooks = data.get("hooks", {})

        for event_name, hook_list in hooks.items():
            for hook_config in hook_list:
                for hook in hook_config.get("hooks", []):
                    command = hook.get("command", "")
                    # Extract Python file from command like "python src/events/session.py"
                    match = re.search(r"python\s+(\S+\.py)", command)
                    if match:
                        handler_path = match.group(1)
                        full_path = root / handler_path
                        if not full_path.exists():
                            violations.append(
                                {
                                    "rule": "hook_handlers",
                                    "source": f"plugin.json:{event_name}",
                                    "expected": handler_path,
                                    "message": f"Hook references missing handler: {handler_path}",
                                    "severity": "error",
                                }
                            )
    except (json.JSONDecodeError, OSError):
        pass

    return violations


def _check_local_hooks(root: Path) -> list[Violation]:
    """Check hooks defined in .claude/settings.json for any project.

    Args:
        root: Project root.

    Returns:
        List of violations.
    """
    import json

    violations: list[Violation] = []
    settings_json = root / ".claude" / "settings.json"

    if not settings_json.exists():
        return violations

    try:
        data = json.loads(settings_json.read_text())
        hooks = data.get("hooks", {})

        for event_name, hook_list in hooks.items():
            if not isinstance(hook_list, list):
                hook_list = [hook_list]
            for hook in hook_list:
                command = hook.get("command", "") if isinstance(hook, dict) else ""
                # Check if command references a file
                if command and not command.startswith("$"):
                    # Could be a file path
                    potential_path = root / command
                    if (
                        command.endswith((".py", ".sh", ".js", ".ts"))
                        and not potential_path.exists()
                    ):
                        violations.append(
                            {
                                "rule": "hook_handlers",
                                "source": f".claude/settings.json:{event_name}",
                                "expected": command,
                                "message": f"Hook references missing file: {command}",
                                "severity": "error",
                            }
                        )
    except (json.JSONDecodeError, OSError):
        pass

    return violations


def check_hook_handlers() -> tuple[bool, list[Violation]]:
    """Check that configured hooks have corresponding handler files.

    Checks both:
    - Plugin projects: plugin.json hooks → handler files
    - Any project: .claude/settings.json hooks → handler files

    Returns:
        Tuple of (all_valid, list of violations).
    """
    rules = get("consistency.rules", {})
    hook_handlers = rules.get("hook_handlers", {})

    if not hook_handlers.get("enabled", True):
        return True, []

    root = get_project_root()
    violations: list[Violation] = []

    # Check plugin.json hooks (for plugin projects)
    violations.extend(_check_plugin_hooks(root))

    # Check .claude/settings.json hooks (for any project)
    violations.extend(_check_local_hooks(root))

    return len(violations) == 0, violations


def check_config_schema() -> tuple[bool, list[Violation]]:
    """Check that config keys exist in schema.

    Returns:
        Tuple of (all_valid, list of violations).
    """
    rules = get("consistency.rules", {})
    config_schema = rules.get("config_schema", {})

    if not config_schema.get("enabled", True):
        return True, []

    root = get_project_root()
    violations: list[Violation] = []

    schema_path = root / ".claude" / ".devkit" / "config.schema.json"
    config_path = root / ".claude" / ".devkit" / "config.jsonc"

    if not schema_path.exists() or not config_path.exists():
        return True, []

    try:
        import json

        schema_content = schema_path.read_text()
        schema = json.loads(schema_content)

        # Get top-level properties from schema
        schema_properties = set(schema.get("properties", {}).keys())

        # Get top-level keys from config
        config = load_config()
        config_keys = set(config.keys())

        # Check for keys in config but not in schema
        undefined_keys = config_keys - schema_properties - {"$schema"}
        violations.extend(
            {
                "rule": "config_schema",
                "source": f"config.{key}",
                "expected": "schema property",
                "message": f"Config key '{key}' not defined in schema",
                "severity": "warning",
            }
            for key in undefined_keys
        )

    except (json.JSONDecodeError, OSError):
        pass

    return len(violations) == 0, violations


def _check_plugin_skills(root: Path) -> list[Violation]:
    """Check skills defined in plugin.json for plugin projects.

    Args:
        root: Project root.

    Returns:
        List of violations.
    """
    import json
    import re

    violations: list[Violation] = []
    plugin_json = root / ".claude-plugin" / "plugin.json"

    if not plugin_json.exists():
        return violations

    try:
        data = json.loads(plugin_json.read_text())
        skills_paths = data.get("skills", [])

        for skills_path in skills_paths:
            # Normalize path (remove ./ prefix)
            skills_path = skills_path.lstrip("./")
            skills_dir = root / skills_path

            if not skills_dir.exists():
                violations.append(
                    {
                        "rule": "skill_routes",
                        "source": "plugin.json:skills",
                        "expected": skills_path,
                        "message": f"Skills directory not found: {skills_path}",
                        "severity": "error",
                    }
                )
                continue

            # Find all SKILL.md files
            for skill_md in skills_dir.rglob("SKILL.md"):
                skill_dir = skill_md.parent
                content = skill_md.read_text()

                # Find references to docs like: reference/dev.md
                doc_refs = re.findall(r"reference/([\w-]+\.md)", content)
                ref_dir = skill_dir / "reference"

                for doc_ref in doc_refs:
                    doc_path = ref_dir / doc_ref
                    if not doc_path.exists():
                        rel_skill = skill_md.relative_to(root)
                        violations.append(
                            {
                                "rule": "skill_routes",
                                "source": str(rel_skill),
                                "expected": f"{skill_dir.relative_to(root)}/reference/{doc_ref}",
                                "message": f"SKILL.md references missing doc: {doc_ref}",
                                "severity": "error",
                            }
                        )

    except (json.JSONDecodeError, OSError):
        pass

    return violations


def _check_local_skills(root: Path) -> list[Violation]:
    """Check skills defined in .claude/skills/ for any project.

    Args:
        root: Project root.

    Returns:
        List of violations.
    """
    import re

    violations: list[Violation] = []
    skills_dir = root / ".claude" / "skills"

    if not skills_dir.exists():
        return violations

    # Find all SKILL.md files in local skills
    for skill_md in skills_dir.rglob("SKILL.md"):
        skill_dir = skill_md.parent
        try:
            content = skill_md.read_text()

            # Find references to docs like: reference/dev.md
            doc_refs = re.findall(r"reference/([\w-]+\.md)", content)
            ref_dir = skill_dir / "reference"

            for doc_ref in doc_refs:
                doc_path = ref_dir / doc_ref
                if not doc_path.exists():
                    rel_skill = skill_md.relative_to(root)
                    violations.append(
                        {
                            "rule": "skill_routes",
                            "source": str(rel_skill),
                            "expected": f"{skill_dir.relative_to(root)}/reference/{doc_ref}",
                            "message": f"SKILL.md references missing doc: {doc_ref}",
                            "severity": "error",
                        }
                    )
        except OSError:
            pass

    return violations


def _check_local_commands(root: Path) -> list[Violation]:
    """Check slash commands defined in .claude/commands/ for any project.

    Args:
        root: Project root.

    Returns:
        List of violations.
    """
    import re

    violations: list[Violation] = []
    commands_dir = root / ".claude" / "commands"

    if not commands_dir.exists():
        return violations

    # Find all .md files in commands (slash commands are markdown files)
    for cmd_md in commands_dir.rglob("*.md"):
        try:
            content = cmd_md.read_text()

            # Find references to docs like: reference/dev.md or ../skills/dk/reference/dev.md
            doc_refs = re.findall(r"reference/([\w-]+\.md)", content)
            ref_dir = cmd_md.parent / "reference"

            for doc_ref in doc_refs:
                doc_path = ref_dir / doc_ref
                if not doc_path.exists():
                    rel_cmd = cmd_md.relative_to(root)
                    violations.append(
                        {
                            "rule": "skill_routes",
                            "source": str(rel_cmd),
                            "expected": f"{cmd_md.parent.relative_to(root)}/reference/{doc_ref}",
                            "message": f"Command references missing doc: {doc_ref}",
                            "severity": "error",
                        }
                    )
        except OSError:  # noqa: PERF203
            pass

    return violations


def check_skill_routes() -> tuple[bool, list[Violation]]:
    """Check that skill and command definitions are valid.

    Checks:
    - Plugin projects: plugin.json skills → SKILL.md → reference docs
    - Any project: .claude/skills/ → SKILL.md → reference docs
    - Any project: .claude/commands/ → *.md → reference docs

    Returns:
        Tuple of (all_valid, list of violations).
    """
    rules = get("consistency.rules", {})
    skill_routes = rules.get("skill_routes", {})

    if not skill_routes.get("enabled", True):
        return True, []

    root = get_project_root()
    violations: list[Violation] = []

    # Check plugin.json skills (for plugin projects)
    violations.extend(_check_plugin_skills(root))

    # Check .claude/skills/ (for any project with local skills)
    violations.extend(_check_local_skills(root))

    # Check .claude/commands/ (for any project with slash commands)
    violations.extend(_check_local_commands(root))

    return len(violations) == 0, violations


def check_custom_imports() -> tuple[bool, list[Violation]]:
    """Check custom import rules (deny/require patterns).

    Returns:
        Tuple of (all_valid, list of violations).
    """
    rules = get("consistency.rules", {})
    custom_imports = rules.get("custom_imports", {})

    if not custom_imports.get("enabled", False):
        return True, []

    root = get_project_root()
    violations: list[Violation] = []

    deny_rules = custom_imports.get("deny", [])
    # require_rules = custom_imports.get("require", [])  # Future enhancement

    for deny_rule in deny_rules:
        # Parse rule: "src/hooks/* -> @prisma/client"
        if " -> " not in deny_rule:
            continue

        source_pattern, forbidden_import = deny_rule.split(" -> ", 1)

        # Find all files matching source pattern
        for source_file in root.glob(source_pattern):
            if source_file.is_file():
                try:
                    content = source_file.read_text()

                    # Check for import
                    import_patterns = [
                        f'import "{forbidden_import}"',
                        f"import '{forbidden_import}'",
                        f'from "{forbidden_import}"',
                        f"from '{forbidden_import}'",
                        f"import {forbidden_import}",
                        f"from {forbidden_import} import",
                    ]

                    for import_pattern in import_patterns:
                        if import_pattern in content:
                            violations.append(
                                {
                                    "rule": "custom_imports",
                                    "source": str(source_file.relative_to(root)),
                                    "expected": f"no import of {forbidden_import}",
                                    "message": f"Forbidden import '{forbidden_import}' in {source_file.name}",
                                    "severity": "error",
                                }
                            )
                            break

                except OSError:
                    pass

    return len(violations) == 0, violations


def check_consistency() -> tuple[bool, dict[str, tuple[bool, list[Violation]]]]:
    """Run all consistency checks.

    Returns:
        Tuple of (all_valid, dict of check_name -> (valid, violations)).
    """
    if not get("consistency.enabled", True):
        return True, {}

    results: dict[str, tuple[bool, list[Violation]]] = {}

    # Run each check
    results["module_tests"] = check_module_tests()
    results["hook_handlers"] = check_hook_handlers()
    results["config_schema"] = check_config_schema()
    results["skill_routes"] = check_skill_routes()
    results["custom_imports"] = check_custom_imports()

    # Overall status
    all_valid = all(result[0] for result in results.values())

    return all_valid, results


def get_violation_count() -> int:
    """Get total number of consistency violations.

    Returns:
        Total violation count.
    """
    _, results = check_consistency()
    return sum(len(violations) for _, violations in results.values())


def get_all_violations() -> list[Violation]:
    """Get all consistency violations as flat list.

    Returns:
        List of all violations.
    """
    _, results = check_consistency()
    all_violations: list[Violation] = []
    for _, violations in results.values():
        all_violations.extend(violations)
    return all_violations


def get_missing_artifacts(file_path: str) -> list[str]:
    """Get missing artifacts for a specific file.

    Used by PostToolUse hook to show hints for new files.

    Args:
        file_path: Path to the file being created/edited.

    Returns:
        List of missing artifact paths.
    """
    root = get_project_root()
    patterns = _get_patterns_from_config()
    exclude = _get_exclude_patterns()
    missing: list[str] = []

    file_path_obj = Path(file_path)
    if not file_path_obj.is_absolute():
        file_path_obj = root / file_path

    # Check if file matches any source pattern
    for source_pattern, test_pattern in patterns.items():
        if _match_glob_pattern(file_path_obj, source_pattern, root):
            # Skip excluded files
            if file_path_obj.name in exclude:
                continue

            # Check if test exists
            expected_test = _resolve_test_path(file_path_obj, test_pattern, root)
            if not expected_test.exists():
                missing.append(str(expected_test.relative_to(root)))

    return missing


def format_consistency_report(results: dict[str, tuple[bool, list[Violation]]]) -> str:
    """Format consistency check results for display.

    Args:
        results: Output from check_consistency().

    Returns:
        Formatted string for terminal output.
    """
    lines: list[str] = ["── Consistency ─────────────────────"]

    all_violations: list[Violation] = []
    for _, violations in results.values():
        all_violations.extend(violations)

    if not all_violations:
        lines.append("✓ All consistency checks passed")
    else:
        lines.append(f"✗ {len(all_violations)} consistency violation(s):")
        for v in all_violations:
            severity_icon = "⚠️" if v["severity"] == "warning" else "❌"
            lines.append(f"  {severity_icon} [{v['rule']}] {v['message']}")
            if v.get("expected"):
                lines.append(f"     Expected: {v['expected']}")

    return "\n".join(lines)


def format_compact(results: dict[str, tuple[bool, list[Violation]]]) -> str | None:
    """Format consistency results for session start (compact).

    Args:
        results: Output from check_consistency().

    Returns:
        Compact warning string, or None if no issues.
    """
    violation_count = sum(len(violations) for _, violations in results.values())

    if violation_count == 0:
        return None

    return f"⚠️ {violation_count} consistency issue(s) - run /dk plugin check"
