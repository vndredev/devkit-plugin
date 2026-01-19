"""Tests for MCP server configuration and health checking."""

import pytest
from pathlib import Path
from unittest.mock import patch

from lib.mcp import (
    MCP_ENV_REQUIREMENTS,
    get_shell_config_path,
    scan_shell_config_for_exports,
    check_env_vars_in_environment,
    get_mcp_status,
    get_mcp_health_report,
    format_mcp_status,
)


class TestGetShellConfigPath:
    """Tests for get_shell_config_path."""

    def test_returns_zshrc_if_exists(self, tmp_path: Path, monkeypatch):
        """Prefers zshrc over bashrc."""
        zshrc = tmp_path / ".zshrc"
        zshrc.touch()
        bashrc = tmp_path / ".bashrc"
        bashrc.touch()

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = get_shell_config_path()
        assert result == zshrc

    def test_returns_bashrc_if_no_zshrc(self, tmp_path: Path, monkeypatch):
        """Falls back to bashrc if zshrc doesn't exist."""
        bashrc = tmp_path / ".bashrc"
        bashrc.touch()

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = get_shell_config_path()
        assert result == bashrc

    def test_returns_none_if_neither_exists(self, tmp_path: Path, monkeypatch):
        """Returns None if no shell config found."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = get_shell_config_path()
        assert result is None


class TestScanShellConfigForExports:
    """Tests for scan_shell_config_for_exports."""

    def test_finds_export_statements(self, tmp_path: Path):
        """Detects export VAR=value statements."""
        config = tmp_path / ".zshrc"
        config.write_text("""
# Some comment
export NEON_API_KEY=secret123
export STRIPE_SECRET_KEY="sk_test_xxx"
echo "not an export"
""")
        result = scan_shell_config_for_exports(config)
        assert result.get("NEON_API_KEY") is True
        assert result.get("STRIPE_SECRET_KEY") is True

    def test_detects_missing_exports(self, tmp_path: Path):
        """Returns False for vars not exported."""
        config = tmp_path / ".zshrc"
        config.write_text("# Empty config\n")

        result = scan_shell_config_for_exports(config)
        assert result.get("NEON_API_KEY") is False
        assert result.get("AXIOM_TOKEN") is False

    def test_handles_file_read_error(self, tmp_path: Path):
        """Returns empty dict on file read error."""
        config = tmp_path / "nonexistent"
        result = scan_shell_config_for_exports(config)
        assert result == {}

    def test_handles_indented_exports(self, tmp_path: Path):
        """Handles exports with leading whitespace."""
        config = tmp_path / ".zshrc"
        config.write_text("  export AXIOM_TOKEN=token123\n")

        result = scan_shell_config_for_exports(config)
        assert result.get("AXIOM_TOKEN") is True


class TestCheckEnvVarsInEnvironment:
    """Tests for check_env_vars_in_environment."""

    def test_detects_set_vars(self, monkeypatch):
        """Detects env vars that are set."""
        monkeypatch.setenv("NEON_API_KEY", "test_key")
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")

        result = check_env_vars_in_environment()
        assert result.get("NEON_API_KEY") is True
        assert result.get("STRIPE_SECRET_KEY") is True

    def test_detects_unset_vars(self, monkeypatch):
        """Detects env vars that are not set."""
        monkeypatch.delenv("NEON_API_KEY", raising=False)
        monkeypatch.delenv("AXIOM_TOKEN", raising=False)

        result = check_env_vars_in_environment()
        assert result.get("NEON_API_KEY") is False
        assert result.get("AXIOM_TOKEN") is False

    def test_empty_string_is_false(self, monkeypatch):
        """Empty string env var is considered unset."""
        monkeypatch.setenv("NEON_API_KEY", "")

        result = check_env_vars_in_environment()
        assert result.get("NEON_API_KEY") is False


class TestGetMcpStatus:
    """Tests for get_mcp_status."""

    def test_server_ready_when_all_vars_set(self, monkeypatch):
        """Server is ready when all required vars are set."""
        monkeypatch.setenv("NEON_API_KEY", "test_key")

        result = get_mcp_status()
        assert result["neon"]["ready"] is True
        assert result["neon"]["missing_vars"] == []

    def test_server_not_ready_when_vars_missing(self, monkeypatch):
        """Server not ready when required vars are missing."""
        monkeypatch.delenv("NEON_API_KEY", raising=False)

        result = get_mcp_status()
        assert result["neon"]["ready"] is False
        assert "NEON_API_KEY" in result["neon"]["missing_vars"]

    def test_server_ready_with_no_requirements(self, monkeypatch):
        """Servers with no env requirements are always ready."""
        result = get_mcp_status()
        assert result["context7"]["ready"] is True
        assert result["playwright"]["ready"] is True

    def test_returns_all_servers(self):
        """Returns status for all configured servers."""
        result = get_mcp_status()
        for server in MCP_ENV_REQUIREMENTS:
            assert server in result


class TestGetMcpHealthReport:
    """Tests for get_mcp_health_report."""

    def test_includes_shell_config(self, tmp_path: Path, monkeypatch):
        """Report includes shell config path."""
        zshrc = tmp_path / ".zshrc"
        zshrc.write_text("export NEON_API_KEY=test\n")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = get_mcp_health_report()
        assert result["shell_config"] == str(zshrc)

    def test_includes_server_status(self, tmp_path: Path, monkeypatch):
        """Report includes all server statuses."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = get_mcp_health_report()
        assert "servers" in result
        for server in MCP_ENV_REQUIREMENTS:
            assert server in result["servers"]

    def test_summary_counts_ready_servers(self, monkeypatch):
        """Summary correctly counts ready servers."""
        result = get_mcp_health_report()
        assert result["summary"]["ready"] >= 2
        assert result["summary"]["total"] == len(MCP_ENV_REQUIREMENTS)


class TestFormatMcpStatus:
    """Tests for format_mcp_status."""

    def test_returns_markdown_table(self, tmp_path: Path, monkeypatch):
        """Returns formatted markdown with table."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = format_mcp_status()
        assert "## MCP Server Status" in result
        assert "| Server | Status | Missing |" in result

    def test_shows_ready_servers_with_checkmark(self, tmp_path: Path, monkeypatch):
        """Ready servers show checkmark."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = format_mcp_status()
        assert "✅" in result

    def test_shows_missing_vars_for_not_ready(self, tmp_path: Path, monkeypatch):
        """Not ready servers show missing vars."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("NEON_API_KEY", raising=False)

        result = format_mcp_status()
        assert "NEON_API_KEY" in result

    def test_shows_summary(self, tmp_path: Path, monkeypatch):
        """Shows ready/total summary."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = format_mcp_status()
        assert "**Ready:**" in result
        assert f"/{len(MCP_ENV_REQUIREMENTS)} servers" in result
