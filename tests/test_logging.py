"""Tests for lib/logging.py - Logging and observability service detection."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.logging import (
    PROVIDERS,
    check_env_vars,
    check_package_deps,
    detect_services,
    get_dashboard_urls,
    logging_status,
)


class TestCheckEnvVars:
    """Tests for check_env_vars()."""

    def test_reads_env_file(self, tmp_path):
        """Should read environment variables from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("AXIOM_TOKEN=xxx\nSENTRY_DSN=yyy")

        with patch("lib.logging.get_project_root") as mock_root:
            mock_root.return_value = tmp_path

            env_vars = check_env_vars(tmp_path)

        assert "AXIOM_TOKEN" in env_vars
        assert "SENTRY_DSN" in env_vars

    def test_reads_multiple_env_files(self, tmp_path):
        """Should read from multiple .env files."""
        (tmp_path / ".env").write_text("AXIOM_TOKEN=xxx")
        (tmp_path / ".env.local").write_text("SENTRY_DSN=yyy")
        (tmp_path / ".env.development").write_text("DD_API_KEY=zzz")

        with patch("lib.logging.get_project_root") as mock_root:
            mock_root.return_value = tmp_path

            env_vars = check_env_vars(tmp_path)

        assert "AXIOM_TOKEN" in env_vars
        assert "SENTRY_DSN" in env_vars
        assert "DD_API_KEY" in env_vars

    def test_returns_empty_set_when_no_env_files(self, tmp_path):
        """Should return empty set when no .env files exist."""
        with patch("lib.logging.get_project_root") as mock_root:
            mock_root.return_value = tmp_path

            env_vars = check_env_vars(tmp_path)

        assert env_vars == set()


class TestCheckPackageDeps:
    """Tests for check_package_deps()."""

    def test_reads_package_json_dependencies(self, tmp_path):
        """Should read dependencies from package.json."""
        package_json = tmp_path / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "@sentry/nextjs": "^7.0.0",
                        "pino": "^8.0.0",
                    }
                }
            )
        )

        with patch("lib.logging.get_project_root") as mock_root:
            mock_root.return_value = tmp_path

            deps = check_package_deps(tmp_path)

        assert "@sentry/nextjs" in deps
        assert "pino" in deps

    def test_reads_dev_dependencies(self, tmp_path):
        """Should include devDependencies."""
        package_json = tmp_path / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "devDependencies": {
                        "pino-pretty": "^10.0.0",
                    }
                }
            )
        )

        with patch("lib.logging.get_project_root") as mock_root:
            mock_root.return_value = tmp_path

            deps = check_package_deps(tmp_path)

        assert "pino-pretty" in deps

    def test_returns_empty_set_when_no_package_json(self, tmp_path):
        """Should return empty set when no package.json exists."""
        with patch("lib.logging.get_project_root") as mock_root:
            mock_root.return_value = tmp_path

            deps = check_package_deps(tmp_path)

        assert deps == set()


class TestDetectServices:
    """Tests for detect_services()."""

    def test_detect_from_config(self, tmp_path):
        """Should detect services from config with credentials."""
        # Create .env file with the token
        env_file = tmp_path / ".env.local"
        env_file.write_text("AXIOM_TOKEN=test-token")

        with patch("lib.logging.get") as mock_get:
            mock_get.return_value = {
                "axiom": {
                    "provider": "axiom",
                    "env_var": "AXIOM_TOKEN",
                }
            }
            with patch("lib.logging.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "axiom" in services
        assert services["axiom"]["detected_from"] == "config"
        assert services["axiom"]["has_credentials"] is True

    def test_detect_from_config_missing_credentials(self, tmp_path):
        """Should detect services from config but mark credentials as missing."""
        # No .env file - credentials missing
        with patch("lib.logging.get") as mock_get:
            mock_get.return_value = {
                "axiom": {
                    "provider": "axiom",
                    "env_var": "AXIOM_TOKEN",
                }
            }
            with patch("lib.logging.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "axiom" in services
        assert services["axiom"]["detected_from"] == "config"
        assert services["axiom"]["has_credentials"] is False

    def test_detect_from_config_with_token_field(self, tmp_path):
        """Should detect services using 'token' field instead of 'env_var'."""
        # Create .env file with the token
        env_file = tmp_path / ".env.local"
        env_file.write_text("AXIOM_TOKEN=test-token")

        with patch("lib.logging.get") as mock_get:
            mock_get.return_value = {
                "axiom": {
                    "provider": "axiom",
                    "token": "AXIOM_TOKEN",  # Using 'token' instead of 'env_var'
                }
            }
            with patch("lib.logging.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "axiom" in services
        assert services["axiom"]["has_credentials"] is True

    def test_detect_from_env_vars(self, tmp_path):
        """Should detect services from environment variables."""
        env_file = tmp_path / ".env.local"
        env_file.write_text("AXIOM_TOKEN=xxx\nAXIOM_DATASET=logs")

        with patch("lib.logging.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.logging.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "axiom" in services
        assert services["axiom"]["detected_from"] == "env"
        assert services["axiom"]["has_credentials"] is True

    def test_detect_from_package_json(self, tmp_path):
        """Should detect services from package.json dependencies."""
        package_json = tmp_path / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "@sentry/nextjs": "^7.0.0",
                    }
                }
            )
        )

        with patch("lib.logging.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.logging.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "sentry" in services
        assert services["sentry"]["detected_from"] == "package.json"
        # No credentials, since no env var
        assert services["sentry"]["has_credentials"] is False

    def test_detect_multiple_providers(self, tmp_path):
        """Should detect multiple logging providers."""
        env_file = tmp_path / ".env"
        env_file.write_text("SENTRY_DSN=https://xxx@sentry.io/123")

        package_json = tmp_path / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "pino": "^8.0.0",
                        "winston": "^3.0.0",
                    }
                }
            )
        )

        with patch("lib.logging.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.logging.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "sentry" in services
        assert "pino" in services
        assert "winston" in services

    def test_no_services_returns_empty(self, tmp_path):
        """Should return empty dict when no services detected."""
        with patch("lib.logging.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.logging.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert services == {}

    def test_local_loggers_dont_need_credentials(self, tmp_path):
        """Local loggers (pino, winston) don't need env credentials."""
        package_json = tmp_path / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "pino": "^8.0.0",
                    }
                }
            )
        )

        with patch("lib.logging.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.logging.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "pino" in services
        # Pino has no env_patterns, so has_credentials should be True
        assert services["pino"]["has_credentials"] is True
        # No dashboard for local loggers
        assert services["pino"]["dashboard"] is None


class TestLoggingStatus:
    """Tests for logging_status()."""

    def test_returns_status_dict(self, tmp_path):
        """Should return comprehensive status dictionary."""
        with patch("lib.logging.get") as mock_get:
            with patch("lib.logging.detect_services") as mock_detect:
                mock_get.return_value = {"enabled": True}
                mock_detect.return_value = {
                    "axiom": {
                        "provider": "axiom",
                        "has_credentials": True,
                        "dashboard": "https://app.axiom.co",
                    },
                    "pino": {
                        "provider": "pino",
                        "has_credentials": True,
                        "dashboard": None,
                    },
                }

                status = logging_status(tmp_path)

        assert status["enabled"] is True
        assert status["service_count"] == 2
        assert status["with_credentials"] == 2
        assert status["without_credentials"] == 0
        assert "axiom" in status["cloud_services"]
        assert "pino" in status["local_loggers"]

    def test_disabled_in_config(self, tmp_path):
        """Should respect enabled=false in config."""
        with patch("lib.logging.get") as mock_get:
            with patch("lib.logging.detect_services") as mock_detect:
                mock_get.return_value = {"enabled": False}
                mock_detect.return_value = {}

                status = logging_status(tmp_path)

        assert status["enabled"] is False


class TestGetDashboardUrls:
    """Tests for get_dashboard_urls()."""

    def test_returns_dashboard_urls(self):
        """Should return dashboard URLs for cloud services."""
        with patch("lib.logging.detect_services") as mock_detect:
            mock_detect.return_value = {
                "axiom": {
                    "provider": "axiom",
                    "dashboard": "https://app.axiom.co",
                },
                "sentry": {
                    "provider": "sentry",
                    "dashboard": "https://sentry.io",
                },
                "pino": {
                    "provider": "pino",
                    "dashboard": None,
                },
            }

            urls = get_dashboard_urls()

        assert len(urls) == 2
        assert ("axiom", "https://app.axiom.co") in urls
        assert ("sentry", "https://sentry.io") in urls

    def test_returns_empty_for_no_services(self):
        """Should return empty list when no services detected."""
        with patch("lib.logging.detect_services") as mock_detect:
            mock_detect.return_value = {}

            urls = get_dashboard_urls()

        assert urls == []


class TestProviders:
    """Tests for PROVIDERS constant."""

    def test_all_providers_have_required_fields(self):
        """All providers should have required fields."""
        required_fields = {"env_patterns", "deps", "dashboard", "description"}

        for name, info in PROVIDERS.items():
            for field in required_fields:
                assert field in info, f"Provider {name} missing field {field}"

    def test_cloud_providers_have_dashboards(self):
        """Cloud providers should have dashboard URLs."""
        cloud_providers = ["axiom", "sentry", "logrocket", "datadog"]

        for name in cloud_providers:
            assert name in PROVIDERS
            assert PROVIDERS[name]["dashboard"] is not None

    def test_local_loggers_no_dashboard(self):
        """Local loggers should not have dashboard URLs."""
        local_loggers = ["pino", "winston"]

        for name in local_loggers:
            assert name in PROVIDERS
            assert PROVIDERS[name]["dashboard"] is None
