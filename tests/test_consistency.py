"""Tests for arch.consistency module."""

from pathlib import Path
from unittest.mock import patch


class TestModuleTests:
    """Tests for check_module_tests function."""

    def test_check_module_tests_no_violations(self, tmp_path: Path) -> None:
        """Test check_module_tests with all tests present."""
        # Create source file
        src_lib = tmp_path / "src" / "lib"
        src_lib.mkdir(parents=True)
        (src_lib / "config.py").write_text("# config module")

        # Create test file
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_config.py").write_text("# test config")

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {
                        "module_tests": {
                            "enabled": True,
                            "patterns": {"src/lib/*.py": "tests/test_{stem}.py"},
                            "exclude": ["__init__.py"],
                        }
                    }
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_module_tests

            valid, violations = check_module_tests()
            assert valid is True
            assert len(violations) == 0

    def test_check_module_tests_missing_test(self, tmp_path: Path) -> None:
        """Test check_module_tests with missing test file."""
        # Create source file but no test
        src_lib = tmp_path / "src" / "lib"
        src_lib.mkdir(parents=True)
        (src_lib / "webhooks.py").write_text("# webhooks module")

        # Create tests dir but no test file
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {
                        "module_tests": {
                            "enabled": True,
                            "patterns": {"src/lib/*.py": "tests/test_{stem}.py"},
                            "exclude": ["__init__.py"],
                        }
                    }
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_module_tests

            valid, violations = check_module_tests()
            assert valid is False
            assert len(violations) == 1
            assert violations[0]["rule"] == "module_tests"
            assert "webhooks.py" in violations[0]["message"]

    def test_check_module_tests_excludes_init(self, tmp_path: Path) -> None:
        """Test that __init__.py is excluded from checks."""
        # Create __init__.py
        src_lib = tmp_path / "src" / "lib"
        src_lib.mkdir(parents=True)
        (src_lib / "__init__.py").write_text("# init")

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {
                        "module_tests": {
                            "enabled": True,
                            "patterns": {"src/lib/*.py": "tests/test_{stem}.py"},
                            "exclude": ["__init__.py"],
                        }
                    }
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_module_tests

            valid, violations = check_module_tests()
            assert valid is True
            assert len(violations) == 0

    def test_check_module_tests_disabled(self, tmp_path: Path) -> None:
        """Test check_module_tests when disabled."""
        with patch(
            "arch.consistency.get",
            side_effect=lambda key, default=None: {
                "consistency.rules": {"module_tests": {"enabled": False}}
            }.get(key, default),
        ):
            from arch.consistency import check_module_tests

            valid, violations = check_module_tests()
            assert valid is True
            assert len(violations) == 0


class TestHookHandlers:
    """Tests for check_hook_handlers function."""

    def test_check_hook_handlers_all_present(self, tmp_path: Path) -> None:
        """Test check_hook_handlers with all handlers present."""
        # Create handler files
        events_dir = tmp_path / "src" / "events"
        events_dir.mkdir(parents=True)
        (events_dir / "session.py").write_text("# session handler")
        (events_dir / "format.py").write_text("# format handler")

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {"hook_handlers": {"enabled": True}},
                    "hooks": {
                        "session": {"enabled": True},
                        "format": {"enabled": True},
                    },
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_hook_handlers

            valid, violations = check_hook_handlers()
            assert valid is True
            assert len(violations) == 0

    def test_check_hook_handlers_missing_handler(self, tmp_path: Path) -> None:
        """Test check_hook_handlers with missing handler."""
        # Create .claude/settings.json with hook referencing missing file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "settings.json").write_text(
            '{"hooks": {"PreToolUse": [{"command": "scripts/validate.py"}]}}'
        )

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {"hook_handlers": {"enabled": True}},
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_hook_handlers

            valid, violations = check_hook_handlers()
            assert valid is False
            assert len(violations) == 1
            assert violations[0]["rule"] == "hook_handlers"
            assert "validate.py" in violations[0]["message"]


class TestConfigSchema:
    """Tests for check_config_schema function."""

    def test_check_config_schema_valid(self, tmp_path: Path) -> None:
        """Test check_config_schema with valid config."""
        # Create schema and config files
        devkit_dir = tmp_path / ".claude" / ".devkit"
        devkit_dir.mkdir(parents=True)

        (devkit_dir / "config.schema.json").write_text(
            '{"properties": {"project": {}, "hooks": {}}}'
        )
        (devkit_dir / "config.jsonc").write_text('{"project": {}, "hooks": {}}')

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch("arch.consistency.load_config", return_value={"project": {}, "hooks": {}}),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {"config_schema": {"enabled": True}}
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_config_schema

            valid, violations = check_config_schema()
            assert valid is True
            assert len(violations) == 0

    def test_check_config_schema_undefined_key(self, tmp_path: Path) -> None:
        """Test check_config_schema with undefined config key."""
        devkit_dir = tmp_path / ".claude" / ".devkit"
        devkit_dir.mkdir(parents=True)
        (devkit_dir / "config.schema.json").write_text('{"properties": {"project": {}}}')
        (devkit_dir / "config.jsonc").write_text('{"project": {}, "unknown_key": {}}')

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch("arch.consistency.load_config", return_value={"project": {}, "unknown_key": {}}),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {"config_schema": {"enabled": True}}
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_config_schema

            valid, violations = check_config_schema()
            assert valid is False
            assert len(violations) == 1
            assert "unknown_key" in violations[0]["message"]


class TestSkillRoutes:
    """Tests for check_skill_routes function."""

    def test_check_skill_routes_all_present(self, tmp_path: Path) -> None:
        """Test check_skill_routes with all docs present."""
        # Create .claude/skills/ with SKILL.md and referenced docs
        skills_dir = tmp_path / ".claude" / "skills" / "myskill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("See reference/dev.md for details")

        # Create referenced doc
        ref_dir = skills_dir / "reference"
        ref_dir.mkdir()
        (ref_dir / "dev.md").write_text("# Dev docs")

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {"skill_routes": {"enabled": True}}
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_skill_routes

            valid, violations = check_skill_routes()
            assert valid is True
            assert len(violations) == 0

    def test_check_skill_routes_missing_doc(self, tmp_path: Path) -> None:
        """Test check_skill_routes with missing referenced doc."""
        # Create .claude/skills/ with SKILL.md referencing missing doc
        skills_dir = tmp_path / ".claude" / "skills" / "myskill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("See reference/missing.md for details")

        # Create reference dir but not the file
        ref_dir = skills_dir / "reference"
        ref_dir.mkdir()

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {"skill_routes": {"enabled": True}}
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_skill_routes

            valid, violations = check_skill_routes()
            assert valid is False
            assert len(violations) == 1
            assert "missing.md" in violations[0]["message"]


class TestCustomImports:
    """Tests for check_custom_imports function."""

    def test_check_custom_imports_no_violations(self, tmp_path: Path) -> None:
        """Test check_custom_imports with clean imports."""
        # Create file without forbidden import
        hooks_dir = tmp_path / "src" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "useData.ts").write_text('import { useState } from "react"')

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {
                        "custom_imports": {
                            "enabled": True,
                            "deny": ["src/hooks/* -> @prisma/client"],
                        }
                    }
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_custom_imports

            valid, violations = check_custom_imports()
            assert valid is True
            assert len(violations) == 0

    def test_check_custom_imports_forbidden_import(self, tmp_path: Path) -> None:
        """Test check_custom_imports with forbidden import."""
        hooks_dir = tmp_path / "src" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "useData.ts").write_text('import { prisma } from "@prisma/client"')

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {
                        "custom_imports": {
                            "enabled": True,
                            "deny": ["src/hooks/* -> @prisma/client"],
                        }
                    }
                }.get(key, default),
            ),
        ):
            from arch.consistency import check_custom_imports

            valid, violations = check_custom_imports()
            assert valid is False
            assert len(violations) == 1
            assert "@prisma/client" in violations[0]["message"]

    def test_check_custom_imports_disabled(self, tmp_path: Path) -> None:
        """Test check_custom_imports when disabled."""
        with patch(
            "arch.consistency.get",
            side_effect=lambda key, default=None: {
                "consistency.rules": {"custom_imports": {"enabled": False}}
            }.get(key, default),
        ):
            from arch.consistency import check_custom_imports

            valid, violations = check_custom_imports()
            assert valid is True
            assert len(violations) == 0


class TestCheckConsistency:
    """Tests for check_consistency function."""

    def test_check_consistency_disabled(self) -> None:
        """Test check_consistency when globally disabled."""
        with patch(
            "arch.consistency.get",
            side_effect=lambda key, default=None: {"consistency.enabled": False}.get(key, default),
        ):
            from arch.consistency import check_consistency

            valid, results = check_consistency()
            assert valid is True
            assert results == {}


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_violation_count(self, tmp_path: Path) -> None:
        """Test get_violation_count returns correct count."""
        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch("arch.consistency.load_config", return_value={}),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.enabled": True,
                    "consistency.rules": {},
                }.get(key, default),
            ),
        ):
            from arch.consistency import get_violation_count

            count = get_violation_count()
            assert isinstance(count, int)

    def test_get_missing_artifacts(self, tmp_path: Path) -> None:
        """Test get_missing_artifacts for new file."""
        src_lib = tmp_path / "src" / "lib"
        src_lib.mkdir(parents=True)
        new_file = src_lib / "newmodule.py"
        new_file.write_text("# new module")

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with (
            patch("arch.consistency.get_project_root", return_value=tmp_path),
            patch(
                "arch.consistency.get",
                side_effect=lambda key, default=None: {
                    "consistency.rules": {
                        "module_tests": {
                            "enabled": True,
                            "patterns": {"src/lib/*.py": "tests/test_{stem}.py"},
                            "exclude": ["__init__.py"],
                        }
                    }
                }.get(key, default),
            ),
        ):
            from arch.consistency import get_missing_artifacts

            missing = get_missing_artifacts(str(new_file))
            assert "tests/test_newmodule.py" in missing

    def test_format_consistency_report_no_violations(self) -> None:
        """Test format_consistency_report with no violations."""
        from arch.consistency import format_consistency_report

        results = {"module_tests": (True, []), "hook_handlers": (True, [])}
        report = format_consistency_report(results)

        assert "Consistency" in report
        assert "passed" in report

    def test_format_consistency_report_with_violations(self) -> None:
        """Test format_consistency_report with violations."""
        from arch.consistency import format_consistency_report

        results = {
            "module_tests": (
                False,
                [
                    {
                        "rule": "module_tests",
                        "source": "src/lib/foo.py",
                        "expected": "tests/test_foo.py",
                        "message": "Missing test file for foo.py",
                        "severity": "warning",
                    }
                ],
            )
        }
        report = format_consistency_report(results)

        assert "Consistency" in report
        assert "1 consistency violation" in report
        assert "module_tests" in report
        assert "foo.py" in report

    def test_format_compact_no_issues(self) -> None:
        """Test format_compact with no issues."""
        from arch.consistency import format_compact

        results = {"module_tests": (True, [])}
        result = format_compact(results)

        assert result is None

    def test_format_compact_with_issues(self) -> None:
        """Test format_compact with issues."""
        from arch.consistency import format_compact

        results = {
            "module_tests": (
                False,
                [
                    {
                        "rule": "module_tests",
                        "message": "Missing test",
                        "severity": "warning",
                    }
                ],
            )
        }
        result = format_compact(results)

        assert result is not None
        assert "1 consistency issue" in result
        assert "/dk plugin check" in result
