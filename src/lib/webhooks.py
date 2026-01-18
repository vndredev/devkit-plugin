"""Webhook tunnel management for local development.

TIER 1: May import from core only.

Provides unified webhook management:
- Auto-detect webhook services from project structure
- Start ngrok tunnels with static domains
- Start provider CLIs (Stripe, etc.)
- Show URLs for dashboard configuration
"""

import json
import re
import subprocess
from collections.abc import Generator
from pathlib import Path

from lib.config import get, get_project_root


# Provider CLI commands and detection patterns
PROVIDERS = {
    "stripe": {
        "cli": "stripe",
        "env_patterns": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
        "deps": ["stripe", "@stripe/stripe-js"],
        "default_path": "/api/webhooks/stripe",
        "forward_cmd": ["stripe", "listen", "--forward-to"],
    },
    "livekit": {
        "cli": "livekit-cli",
        "env_patterns": ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"],
        "deps": ["livekit-server-sdk", "@livekit/components-react"],
        "default_path": "/api/webhooks/livekit",
        "forward_cmd": None,  # No CLI forwarding, just ngrok
    },
    "clerk": {
        "cli": None,  # No dedicated CLI
        "env_patterns": ["CLERK_SECRET_KEY", "CLERK_WEBHOOK_SECRET"],
        "deps": ["@clerk/nextjs", "@clerk/clerk-sdk-node"],
        "default_path": "/api/webhooks/clerk",
        "forward_cmd": None,
    },
    "resend": {
        "cli": None,
        "env_patterns": ["RESEND_API_KEY", "RESEND_WEBHOOK_SECRET"],
        "deps": ["resend"],
        "default_path": "/api/webhooks/resend",
        "forward_cmd": None,
    },
}

# Dashboard URLs for webhook configuration
DASHBOARD_URLS = {
    "stripe": "https://dashboard.stripe.com/webhooks",
    "livekit": "https://cloud.livekit.io",
    "clerk": "https://dashboard.clerk.com",
    "resend": "https://resend.com/webhooks",
}


def check_ngrok_cli() -> tuple[bool, str]:
    """Check if ngrok CLI is installed and authenticated.

    Returns:
        Tuple of (success, message)
    """
    try:
        result = subprocess.run(
            ["ngrok", "version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        version = result.stdout.strip()
        return True, f"ngrok {version}"
    except FileNotFoundError:
        return False, "ngrok not installed. Install: brew install ngrok/ngrok/ngrok"
    except subprocess.CalledProcessError:
        return False, "ngrok check failed"


def check_stripe_cli() -> tuple[bool, str]:
    """Check if Stripe CLI is installed and authenticated.

    Returns:
        Tuple of (success, message)
    """
    try:
        result = subprocess.run(
            ["stripe", "version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        version = result.stdout.strip()

        # Check if logged in
        status = subprocess.run(
            ["stripe", "config", "--list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if status.returncode != 0 or "test_mode_api_key" not in status.stdout:
            return False, f"Stripe CLI {version} (not logged in - run: stripe login)"

        return True, f"Stripe CLI {version}"
    except FileNotFoundError:
        return False, "Stripe CLI not installed. Install: brew install stripe/stripe-cli/stripe"
    except subprocess.CalledProcessError:
        return False, "Stripe CLI check failed"


def detect_services(project_root: Path | None = None) -> dict[str, dict]:
    """Auto-detect webhook services from project structure.

    Checks:
    - /api/webhooks/* routes (Next.js)
    - Environment variables (STRIPE_*, LIVEKIT_*, etc.)
    - package.json dependencies

    Args:
        project_root: Project root directory (defaults to cwd)

    Returns:
        Dict of {service_name: {path, provider, detected_from}}
    """
    if project_root is None:
        project_root = get_project_root()

    detected: dict[str, dict] = {}

    # Check config first (explicit configuration takes precedence)
    config_services = get("webhooks.services", {})
    for name, config in config_services.items():
        detected[name] = {
            "path": config.get("path", f"/api/webhooks/{name}"),
            "provider": config.get("provider", "custom"),
            "events": config.get("events", []),
            "detected_from": "config",
        }

    # Check for webhook routes in /api/webhooks/
    api_dir = project_root / "app" / "api" / "webhooks"
    if api_dir.exists():
        for route_dir in api_dir.iterdir():
            if route_dir.is_dir() and (route_dir / "route.ts").exists():
                service_name = route_dir.name
                if service_name not in detected:
                    provider = service_name if service_name in PROVIDERS else "custom"
                    detected[service_name] = {
                        "path": f"/api/webhooks/{service_name}",
                        "provider": provider,
                        "events": [],
                        "detected_from": "route",
                    }

    # Also check pages/api for older Next.js structure
    pages_api = project_root / "pages" / "api" / "webhooks"
    if pages_api.exists():
        for route_file in pages_api.glob("*.ts"):
            service_name = route_file.stem
            if service_name not in detected:
                provider = service_name if service_name in PROVIDERS else "custom"
                detected[service_name] = {
                    "path": f"/api/webhooks/{service_name}",
                    "provider": provider,
                    "events": [],
                    "detected_from": "route",
                }

    # Check environment variables
    env_files = [".env", ".env.local", ".env.development"]
    env_vars: set[str] = set()
    for env_file in env_files:
        env_path = project_root / env_file
        if env_path.exists():
            content = env_path.read_text()
            env_vars.update(re.findall(r"^([A-Z_]+)=", content, re.MULTILINE))

    for provider, info in PROVIDERS.items():
        if provider not in detected:
            if any(pattern in env_vars for pattern in info["env_patterns"]):
                detected[provider] = {
                    "path": info["default_path"],
                    "provider": provider,
                    "events": [],
                    "detected_from": "env",
                }

    # Check package.json dependencies
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            pkg = json.loads(package_json.read_text())
            all_deps = {
                *pkg.get("dependencies", {}).keys(),
                *pkg.get("devDependencies", {}).keys(),
            }

            for provider, info in PROVIDERS.items():
                if provider not in detected:
                    if any(dep in all_deps for dep in info["deps"]):
                        detected[provider] = {
                            "path": info["default_path"],
                            "provider": provider,
                            "events": [],
                            "detected_from": "package.json",
                        }
        except (json.JSONDecodeError, OSError):
            pass

    return detected


def webhooks_status() -> dict:
    """Get comprehensive webhook configuration status.

    Returns:
        Status dictionary with CLI info, detected services, and config
    """
    ngrok_ok, ngrok_msg = check_ngrok_cli()
    stripe_ok, stripe_msg = check_stripe_cli()

    # Get ngrok config
    ngrok_config = get("webhooks.ngrok", {})
    ngrok_domain = ngrok_config.get("domain")
    ngrok_port = ngrok_config.get("port", 3000)

    # Detect services
    services = detect_services()

    return {
        "ngrok": {
            "installed": ngrok_ok,
            "message": ngrok_msg,
            "domain": ngrok_domain,
            "port": ngrok_port,
        },
        "stripe_cli": {
            "installed": stripe_ok,
            "message": stripe_msg,
        },
        "services": services,
        "service_count": len(services),
    }


def webhooks_urls(base_url: str | None = None) -> list[tuple[str, str, str]]:
    """Get webhook URLs for dashboard configuration.

    Args:
        base_url: Base URL (defaults to ngrok domain from config)

    Returns:
        List of (service, webhook_url, dashboard_url) tuples
    """
    if base_url is None:
        ngrok_config = get("webhooks.ngrok", {})
        domain = ngrok_config.get("domain")
        if domain:
            base_url = f"https://{domain}"
        else:
            base_url = "https://YOUR_NGROK_DOMAIN"

    services = detect_services()
    urls = []

    for name, info in services.items():
        webhook_url = f"{base_url}{info['path']}"
        dashboard_url = DASHBOARD_URLS.get(info["provider"], "")
        urls.append((name, webhook_url, dashboard_url))

    return urls


def webhooks_start(
    services: list[str] | None = None,
) -> Generator[tuple[str, bool, str], None, None]:
    """Start webhook tunnels and provider CLIs.

    Yields status updates as (step, success, message) tuples.

    Args:
        services: Specific services to start (defaults to all detected)

    Yields:
        Tuples of (step_name, success, message)
    """
    # Check ngrok
    ngrok_ok, ngrok_msg = check_ngrok_cli()
    yield ("ngrok check", ngrok_ok, ngrok_msg)
    if not ngrok_ok:
        return

    # Get config
    ngrok_config = get("webhooks.ngrok", {})
    domain = ngrok_config.get("domain")
    port = ngrok_config.get("port", 3000)

    if not domain:
        yield (
            "ngrok domain",
            False,
            "No ngrok domain configured. Add webhooks.ngrok.domain to config.jsonc",
        )
        return

    # Detect services
    detected = detect_services()
    if services:
        detected = {k: v for k, v in detected.items() if k in services}

    if not detected:
        yield ("services", False, "No webhook services detected")
        return

    yield ("services detected", True, f"Found {len(detected)}: {', '.join(detected.keys())}")

    # Build ngrok command
    ngrok_cmd = ["ngrok", "http", str(port), "--domain", domain]
    yield ("ngrok command", True, f"ngrok http {port} --domain {domain}")

    # Check for Stripe and prepare its command
    stripe_services = [s for s, info in detected.items() if info["provider"] == "stripe"]
    if stripe_services:
        stripe_ok, stripe_msg = check_stripe_cli()
        if stripe_ok:
            service_info = detected[stripe_services[0]]
            forward_url = f"http://localhost:{port}{service_info['path']}"
            stripe_cmd = ["stripe", "listen", "--forward-to", forward_url]
            yield ("stripe command", True, f"stripe listen --forward-to {forward_url}")
        else:
            yield ("stripe cli", False, stripe_msg)

    # Provide instructions (actual process management is manual or via reference doc)
    yield (
        "ready",
        True,
        f"Run commands in separate terminals. Webhook URL: https://{domain}",
    )


def get_webhook_events(provider: str) -> list[str]:
    """Get common webhook events for a provider.

    Args:
        provider: Provider name (stripe, clerk, etc.)

    Returns:
        List of common event names
    """
    events = {
        "stripe": [
            "checkout.session.completed",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "invoice.paid",
            "invoice.payment_failed",
        ],
        "clerk": [
            "user.created",
            "user.updated",
            "user.deleted",
            "session.created",
            "session.ended",
        ],
        "livekit": [
            "room_started",
            "room_finished",
            "participant_joined",
            "participant_left",
            "track_published",
        ],
        "resend": [
            "email.sent",
            "email.delivered",
            "email.bounced",
            "email.complained",
        ],
    }
    return events.get(provider, [])
