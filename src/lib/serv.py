"""Service management for local development.

TIER 1: May import from core only.

Provides unified service management:
- Get dev server command from config
- Start all development services (dev server, ngrok, provider CLIs)
- Show URLs for all services
- Status overview of all services
"""

from lib.config import get
from lib.webhooks import (
    DASHBOARD_URLS,
    check_ngrok_cli,
    check_stripe_cli,
    detect_services,
    webhooks_status,
)


def get_dev_command() -> dict:
    """Get development server command from config.

    Returns:
        Dict with 'command', 'port', 'include_webhooks' keys
    """
    dev_config = get("dev", {})
    return {
        "command": dev_config.get("command", "npm run dev"),
        "port": dev_config.get("port", 3000),
        "include_webhooks": dev_config.get("include_webhooks", True),
    }


def serv_status() -> dict:
    """Get comprehensive service status.

    Returns:
        Status dictionary with dev server, webhooks, and all service info
    """
    dev_config = get_dev_command()
    webhook_status = webhooks_status()

    return {
        "dev": {
            "command": dev_config["command"],
            "port": dev_config["port"],
            "include_webhooks": dev_config["include_webhooks"],
        },
        "ngrok": webhook_status["ngrok"],
        "stripe_cli": webhook_status["stripe_cli"],
        "services": webhook_status["services"],
        "service_count": webhook_status["service_count"],
    }


def serv_start_commands() -> list[dict]:
    """Get list of commands to start all services.

    Returns a list of dicts with terminal number, command, and description.
    Respects 'include_webhooks' setting.

    Returns:
        List of {terminal: int, command: str, description: str}
    """
    dev_config = get_dev_command()
    commands = []

    # Terminal 1: Dev server
    commands.append(
        {
            "terminal": 1,
            "command": dev_config["command"],
            "description": "Development server",
        }
    )

    # Check if webhooks should be included
    if not dev_config["include_webhooks"]:
        return commands

    # Terminal 2: ngrok (if configured)
    ngrok_config = get("webhooks.ngrok", {})
    ngrok_domain = ngrok_config.get("domain")
    ngrok_port = ngrok_config.get("port", dev_config["port"])

    if ngrok_domain:
        ngrok_ok, _ = check_ngrok_cli()
        if ngrok_ok:
            commands.append(
                {
                    "terminal": 2,
                    "command": f"ngrok http {ngrok_port} --domain {ngrok_domain}",
                    "description": "ngrok tunnel",
                }
            )

    # Terminal 3: Stripe CLI (if Stripe service detected)
    services = detect_services()
    stripe_services = [s for s, info in services.items() if info.get("provider") == "stripe"]

    if stripe_services:
        stripe_ok, _ = check_stripe_cli()
        if stripe_ok:
            service_info = services[stripe_services[0]]
            port = ngrok_port
            forward_url = f"http://localhost:{port}{service_info['path']}"
            commands.append(
                {
                    "terminal": 3,
                    "command": f"stripe listen --forward-to {forward_url}",
                    "description": "Stripe CLI webhook forwarding",
                }
            )

    return commands


def serv_urls() -> dict:
    """Get all service URLs.

    Returns:
        Dict with localhost, ngrok, and webhook URLs
    """
    dev_config = get_dev_command()
    port = dev_config["port"]

    urls = {
        "localhost": f"http://localhost:{port}",
        "ngrok": None,
        "webhooks": [],
    }

    # ngrok URL
    ngrok_config = get("webhooks.ngrok", {})
    ngrok_domain = ngrok_config.get("domain")
    if ngrok_domain:
        urls["ngrok"] = f"https://{ngrok_domain}"

    # Webhook URLs
    services = detect_services()
    base_url = urls["ngrok"] or urls["localhost"]

    for name, info in services.items():
        webhook_url = f"{base_url}{info['path']}"
        dashboard_url = DASHBOARD_URLS.get(info.get("provider", ""), "")
        urls["webhooks"].append(
            {
                "service": name,
                "url": webhook_url,
                "dashboard": dashboard_url,
                "provider": info.get("provider", "custom"),
            }
        )

    return urls
