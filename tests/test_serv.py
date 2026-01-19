"""Tests for lib/serv.py - Service management for local development."""

from unittest.mock import patch

from lib.serv import (
    get_dev_command,
    serv_start_commands,
    serv_status,
    serv_urls,
)


class TestGetDevCommand:
    """Tests for get_dev_command()."""

    def test_default_values(self):
        """Should return default values when no config."""
        with patch("lib.serv.get") as mock_get:
            mock_get.return_value = {}

            result = get_dev_command()

        assert result["command"] == "npm run dev"
        assert result["port"] == 3000
        assert result["include_webhooks"] is True

    def test_configured_values(self):
        """Should return configured values."""
        with patch("lib.serv.get") as mock_get:
            mock_get.return_value = {
                "command": "bun dev",
                "port": 5000,
                "include_webhooks": False,
            }

            result = get_dev_command()

        assert result["command"] == "bun dev"
        assert result["port"] == 5000
        assert result["include_webhooks"] is False


class TestServStatus:
    """Tests for serv_status()."""

    def test_returns_all_status_fields(self):
        """Should return all required status fields."""
        with patch("lib.serv.get_dev_command") as mock_dev:
            with patch("lib.serv.webhooks_status") as mock_webhooks:
                mock_dev.return_value = {
                    "command": "npm run dev",
                    "port": 3000,
                    "include_webhooks": True,
                }
                mock_webhooks.return_value = {
                    "ngrok": {
                        "installed": True,
                        "message": "ngrok 3.5.0",
                        "domain": "test.ngrok.io",
                        "port": 3000,
                    },
                    "stripe_cli": {
                        "installed": True,
                        "message": "Stripe CLI 1.19.0",
                    },
                    "services": {"stripe": {"path": "/api/webhooks/stripe"}},
                    "service_count": 1,
                }

                status = serv_status()

        assert "dev" in status
        assert status["dev"]["command"] == "npm run dev"
        assert status["dev"]["port"] == 3000
        assert status["dev"]["include_webhooks"] is True
        assert "ngrok" in status
        assert "stripe_cli" in status
        assert "services" in status
        assert status["service_count"] == 1


class TestServStartCommands:
    """Tests for serv_start_commands()."""

    def test_dev_server_command_always_included(self):
        """Should always include dev server command."""
        with patch("lib.serv.get_dev_command") as mock_dev:
            with patch("lib.serv.get") as mock_get:
                mock_dev.return_value = {
                    "command": "npm run dev",
                    "port": 3000,
                    "include_webhooks": False,
                }
                mock_get.return_value = {}

                commands = serv_start_commands()

        assert len(commands) == 1
        assert commands[0]["terminal"] == 1
        assert commands[0]["command"] == "npm run dev"
        assert commands[0]["description"] == "Development server"

    def test_respects_include_webhooks_false(self):
        """Should not include webhook commands when include_webhooks is False."""
        with patch("lib.serv.get_dev_command") as mock_dev:
            with patch("lib.serv.get") as mock_get:
                mock_dev.return_value = {
                    "command": "npm run dev",
                    "port": 3000,
                    "include_webhooks": False,
                }
                mock_get.return_value = {"domain": "test.ngrok.io"}

                commands = serv_start_commands()

        assert len(commands) == 1
        assert commands[0]["command"] == "npm run dev"

    def test_includes_ngrok_when_configured(self):
        """Should include ngrok command when domain is configured."""
        with patch("lib.serv.get_dev_command") as mock_dev:
            with patch("lib.serv.get") as mock_get:
                with patch("lib.serv.check_ngrok_cli") as mock_ngrok:
                    with patch("lib.serv.detect_services") as mock_detect:
                        mock_dev.return_value = {
                            "command": "npm run dev",
                            "port": 3000,
                            "include_webhooks": True,
                        }
                        mock_get.return_value = {"domain": "test.ngrok.io", "port": 3000}
                        mock_ngrok.return_value = (True, "ngrok 3.5.0")
                        mock_detect.return_value = {}

                        commands = serv_start_commands()

        assert len(commands) == 2
        assert commands[1]["terminal"] == 2
        assert "ngrok http 3000 --domain test.ngrok.io" in commands[1]["command"]

    def test_includes_stripe_when_detected(self):
        """Should include Stripe CLI command when Stripe service detected."""
        with patch("lib.serv.get_dev_command") as mock_dev:
            with patch("lib.serv.get") as mock_get:
                with patch("lib.serv.check_ngrok_cli") as mock_ngrok:
                    with patch("lib.serv.check_stripe_cli") as mock_stripe:
                        with patch("lib.serv.detect_services") as mock_detect:
                            mock_dev.return_value = {
                                "command": "npm run dev",
                                "port": 3000,
                                "include_webhooks": True,
                            }
                            mock_get.return_value = {"domain": "test.ngrok.io", "port": 3000}
                            mock_ngrok.return_value = (True, "ngrok 3.5.0")
                            mock_stripe.return_value = (True, "Stripe CLI 1.19.0")
                            mock_detect.return_value = {
                                "stripe": {
                                    "path": "/api/webhooks/stripe",
                                    "provider": "stripe",
                                }
                            }

                            commands = serv_start_commands()

        assert len(commands) == 3
        stripe_cmd = [c for c in commands if "stripe" in c["command"].lower()]
        assert len(stripe_cmd) == 1
        assert "stripe listen --forward-to" in stripe_cmd[0]["command"]


class TestServUrls:
    """Tests for serv_urls()."""

    def test_returns_localhost_url(self):
        """Should always return localhost URL."""
        with patch("lib.serv.get_dev_command") as mock_dev:
            with patch("lib.serv.get") as mock_get:
                with patch("lib.serv.detect_services") as mock_detect:
                    mock_dev.return_value = {
                        "command": "npm run dev",
                        "port": 3000,
                        "include_webhooks": True,
                    }
                    mock_get.return_value = {}
                    mock_detect.return_value = {}

                    urls = serv_urls()

        assert urls["localhost"] == "http://localhost:3000"

    def test_returns_ngrok_url_when_configured(self):
        """Should return ngrok URL when domain configured."""
        with patch("lib.serv.get_dev_command") as mock_dev:
            with patch("lib.serv.get") as mock_get:
                with patch("lib.serv.detect_services") as mock_detect:
                    mock_dev.return_value = {
                        "command": "npm run dev",
                        "port": 3000,
                        "include_webhooks": True,
                    }
                    mock_get.return_value = {"domain": "myapp.ngrok.io"}
                    mock_detect.return_value = {}

                    urls = serv_urls()

        assert urls["ngrok"] == "https://myapp.ngrok.io"

    def test_returns_webhook_urls(self):
        """Should return webhook URLs for detected services."""
        with patch("lib.serv.get_dev_command") as mock_dev:
            with patch("lib.serv.get") as mock_get:
                with patch("lib.serv.detect_services") as mock_detect:
                    mock_dev.return_value = {
                        "command": "npm run dev",
                        "port": 3000,
                        "include_webhooks": True,
                    }
                    mock_get.return_value = {"domain": "myapp.ngrok.io"}
                    mock_detect.return_value = {
                        "stripe": {
                            "path": "/api/webhooks/stripe",
                            "provider": "stripe",
                        }
                    }

                    urls = serv_urls()

        assert len(urls["webhooks"]) == 1
        assert urls["webhooks"][0]["service"] == "stripe"
        assert urls["webhooks"][0]["url"] == "https://myapp.ngrok.io/api/webhooks/stripe"
        assert "stripe.com" in urls["webhooks"][0]["dashboard"]
