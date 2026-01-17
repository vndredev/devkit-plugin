"""Tests for lib/webhooks.py - Webhook tunnel management."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.webhooks import (
    check_ngrok_cli,
    check_stripe_cli,
    detect_services,
    get_webhook_events,
    webhooks_status,
    webhooks_urls,
    webhooks_start,
)


class TestCheckNgrokCli:
    """Tests for check_ngrok_cli()."""

    def test_ngrok_installed(self):
        """Should return success when ngrok is installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ngrok version 3.5.0")

            ok, msg = check_ngrok_cli()

            assert ok is True
            assert "ngrok" in msg

    def test_ngrok_not_installed(self):
        """Should return failure when ngrok is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            ok, msg = check_ngrok_cli()

            assert ok is False
            assert "not installed" in msg


class TestCheckStripeCli:
    """Tests for check_stripe_cli()."""

    def test_stripe_installed_and_logged_in(self):
        """Should return success when Stripe CLI is installed and logged in."""
        with patch("subprocess.run") as mock_run:
            version_result = MagicMock(stdout="stripe version 1.19.0")
            config_result = MagicMock(stdout="test_mode_api_key = sk_test_xxx", returncode=0)

            mock_run.side_effect = [version_result, config_result]

            ok, msg = check_stripe_cli()

            assert ok is True
            assert "Stripe CLI" in msg

    def test_stripe_not_installed(self):
        """Should return failure when Stripe CLI is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            ok, msg = check_stripe_cli()

            assert ok is False
            assert "not installed" in msg

    def test_stripe_not_logged_in(self):
        """Should return failure when not logged in."""
        with patch("subprocess.run") as mock_run:
            version_result = MagicMock(stdout="stripe version 1.19.0")
            config_result = MagicMock(stdout="", returncode=0)

            mock_run.side_effect = [version_result, config_result]

            ok, msg = check_stripe_cli()

            assert ok is False
            assert "not logged in" in msg


class TestDetectServices:
    """Tests for detect_services()."""

    def test_detect_from_config(self, tmp_path):
        """Should detect services from config."""
        with patch("lib.webhooks.get") as mock_get:
            mock_get.return_value = {
                "stripe": {
                    "path": "/api/webhooks/stripe",
                    "provider": "stripe",
                }
            }
            with patch("lib.webhooks.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "stripe" in services
        assert services["stripe"]["path"] == "/api/webhooks/stripe"
        assert services["stripe"]["detected_from"] == "config"

    def test_detect_from_routes(self, tmp_path):
        """Should detect services from API routes."""
        # Create app/api/webhooks/stripe/route.ts
        webhook_dir = tmp_path / "app" / "api" / "webhooks" / "stripe"
        webhook_dir.mkdir(parents=True)
        (webhook_dir / "route.ts").write_text("export async function POST() {}")

        with patch("lib.webhooks.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.webhooks.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "stripe" in services
        assert services["stripe"]["path"] == "/api/webhooks/stripe"
        assert services["stripe"]["detected_from"] == "route"

    def test_detect_from_env(self, tmp_path):
        """Should detect services from environment variables."""
        env_file = tmp_path / ".env.local"
        env_file.write_text("STRIPE_SECRET_KEY=sk_test_xxx\nSTRIPE_WEBHOOK_SECRET=whsec_xxx")

        with patch("lib.webhooks.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.webhooks.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "stripe" in services
        assert services["stripe"]["detected_from"] == "env"

    def test_detect_from_package_json(self, tmp_path):
        """Should detect services from package.json dependencies."""
        package_json = tmp_path / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "@clerk/nextjs": "^4.0.0",
                    }
                }
            )
        )

        with patch("lib.webhooks.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.webhooks.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert "clerk" in services
        assert services["clerk"]["detected_from"] == "package.json"

    def test_no_services_detected(self, tmp_path):
        """Should return empty dict when no services detected."""
        with patch("lib.webhooks.get") as mock_get:
            mock_get.return_value = {}
            with patch("lib.webhooks.get_project_root") as mock_root:
                mock_root.return_value = tmp_path

                services = detect_services(tmp_path)

        assert services == {}


class TestWebhooksStatus:
    """Tests for webhooks_status()."""

    def test_returns_status_dict(self, tmp_path):
        """Should return comprehensive status dictionary."""
        with patch("lib.webhooks.check_ngrok_cli") as mock_ngrok:
            with patch("lib.webhooks.check_stripe_cli") as mock_stripe:
                with patch("lib.webhooks.get") as mock_get:
                    with patch("lib.webhooks.detect_services") as mock_detect:
                        mock_ngrok.return_value = (True, "ngrok 3.5.0")
                        mock_stripe.return_value = (True, "Stripe CLI 1.19.0")
                        mock_get.return_value = {"domain": "test.ngrok.io", "port": 3000}
                        mock_detect.return_value = {"stripe": {"path": "/api/webhooks/stripe"}}

                        status = webhooks_status()

        assert "ngrok" in status
        assert status["ngrok"]["installed"] is True
        assert status["ngrok"]["domain"] == "test.ngrok.io"
        assert "stripe_cli" in status
        assert "services" in status
        assert status["service_count"] == 1


class TestWebhooksUrls:
    """Tests for webhooks_urls()."""

    def test_returns_urls_with_domain(self):
        """Should return webhook URLs with configured domain."""
        with patch("lib.webhooks.get") as mock_get:
            with patch("lib.webhooks.detect_services") as mock_detect:
                mock_get.return_value = {"domain": "myapp.ngrok.io"}
                mock_detect.return_value = {
                    "stripe": {
                        "path": "/api/webhooks/stripe",
                        "provider": "stripe",
                    }
                }

                urls = webhooks_urls()

        assert len(urls) == 1
        assert urls[0][0] == "stripe"
        assert urls[0][1] == "https://myapp.ngrok.io/api/webhooks/stripe"
        assert "stripe.com" in urls[0][2]

    def test_uses_custom_base_url(self):
        """Should use custom base URL when provided."""
        with patch("lib.webhooks.detect_services") as mock_detect:
            mock_detect.return_value = {
                "clerk": {
                    "path": "/api/webhooks/clerk",
                    "provider": "clerk",
                }
            }

            urls = webhooks_urls(base_url="https://custom.example.com")

        assert urls[0][1] == "https://custom.example.com/api/webhooks/clerk"


class TestWebhooksStart:
    """Tests for webhooks_start()."""

    def test_fails_if_ngrok_not_installed(self):
        """Should fail early if ngrok not installed."""
        with patch("lib.webhooks.check_ngrok_cli") as mock_ngrok:
            mock_ngrok.return_value = (False, "ngrok not installed")

            results = list(webhooks_start())

        assert results[0][1] is False
        assert "not installed" in results[0][2]

    def test_fails_if_no_domain_configured(self):
        """Should fail if no ngrok domain configured."""
        with patch("lib.webhooks.check_ngrok_cli") as mock_ngrok:
            with patch("lib.webhooks.get") as mock_get:
                mock_ngrok.return_value = (True, "ngrok 3.5.0")
                mock_get.return_value = {}

                results = list(webhooks_start())

        domain_result = [r for r in results if "domain" in r[0]]
        assert len(domain_result) == 1
        assert domain_result[0][1] is False

    def test_detects_services_and_generates_commands(self):
        """Should detect services and generate commands."""
        with patch("lib.webhooks.check_ngrok_cli") as mock_ngrok:
            with patch("lib.webhooks.check_stripe_cli") as mock_stripe:
                with patch("lib.webhooks.get") as mock_get:
                    with patch("lib.webhooks.detect_services") as mock_detect:
                        mock_ngrok.return_value = (True, "ngrok 3.5.0")
                        mock_stripe.return_value = (True, "Stripe CLI 1.19.0")
                        mock_get.return_value = {"domain": "test.ngrok.io", "port": 3000}
                        mock_detect.return_value = {
                            "stripe": {
                                "path": "/api/webhooks/stripe",
                                "provider": "stripe",
                            }
                        }

                        results = list(webhooks_start())

        # Should have ngrok command
        ngrok_cmd = [r for r in results if "ngrok command" in r[0]]
        assert len(ngrok_cmd) == 1
        assert "ngrok http 3000" in ngrok_cmd[0][2]

        # Should have stripe command
        stripe_cmd = [r for r in results if "stripe command" in r[0]]
        assert len(stripe_cmd) == 1
        assert "stripe listen" in stripe_cmd[0][2]


class TestGetWebhookEvents:
    """Tests for get_webhook_events()."""

    def test_stripe_events(self):
        """Should return common Stripe events."""
        events = get_webhook_events("stripe")

        assert "checkout.session.completed" in events
        assert "customer.subscription.created" in events

    def test_clerk_events(self):
        """Should return common Clerk events."""
        events = get_webhook_events("clerk")

        assert "user.created" in events
        assert "user.deleted" in events

    def test_unknown_provider(self):
        """Should return empty list for unknown provider."""
        events = get_webhook_events("unknown")

        assert events == []
