"""Logging and observability service detection.

TIER 1: May import from core only.

Provides unified logging/observability management:
- Auto-detect logging services from project structure
- Validate credentials and configuration
- Show status in health report
"""

import json
import re
from pathlib import Path

from lib.config import get, get_project_root


# Provider definitions with detection patterns
PROVIDERS = {
    "axiom": {
        "env_patterns": ["AXIOM_TOKEN", "AXIOM_DATASET", "NEXT_PUBLIC_AXIOM_TOKEN"],
        "deps": [
            "@axiomhq/js",
            "@axiomhq/nextjs",
            "@axiomhq/logging",
            "@axiomhq/react",
            "@axiomhq/winston",
            "@axiomhq/pino",
            "axiom-py",
        ],
        "dashboard": "https://app.axiom.co",
        "description": "Log aggregation and analytics",
    },
    "sentry": {
        "env_patterns": ["SENTRY_DSN", "NEXT_PUBLIC_SENTRY_DSN"],
        "deps": ["@sentry/node", "@sentry/nextjs", "sentry-sdk"],
        "dashboard": "https://sentry.io",
        "description": "Error tracking and performance monitoring",
    },
    "logrocket": {
        "env_patterns": ["LOGROCKET_APP_ID", "NEXT_PUBLIC_LOGROCKET_APP_ID"],
        "deps": ["logrocket", "logrocket-react"],
        "dashboard": "https://app.logrocket.com",
        "description": "Session replay and frontend monitoring",
    },
    "datadog": {
        "env_patterns": ["DD_API_KEY", "DATADOG_API_KEY"],
        "deps": ["dd-trace", "@datadog/browser-logs"],
        "dashboard": "https://app.datadoghq.com",
        "description": "Full-stack observability platform",
    },
    "pino": {
        "env_patterns": [],
        "deps": ["pino", "pino-pretty"],
        "dashboard": None,
        "description": "Fast JSON logger for Node.js",
    },
    "winston": {
        "env_patterns": [],
        "deps": ["winston"],
        "dashboard": None,
        "description": "Versatile logging library for Node.js",
    },
}


def check_env_vars(project_root: Path | None = None) -> set[str]:
    """Read environment variables from .env files.

    Args:
        project_root: Project root directory (defaults to cwd)

    Returns:
        Set of environment variable names found
    """
    if project_root is None:
        project_root = get_project_root()

    env_files = [".env", ".env.local", ".env.development", ".env.production"]
    env_vars: set[str] = set()

    for env_file in env_files:
        env_path = project_root / env_file
        if env_path.exists():
            try:
                content = env_path.read_text()
                env_vars.update(re.findall(r"^([A-Z_][A-Z0-9_]*)=", content, re.MULTILINE))
            except OSError:
                pass

    return env_vars


def check_package_deps(project_root: Path | None = None) -> set[str]:
    """Read dependencies from package.json and pyproject.toml.

    Args:
        project_root: Project root directory (defaults to cwd)

    Returns:
        Set of dependency names found
    """
    if project_root is None:
        project_root = get_project_root()

    deps: set[str] = set()

    # Check package.json
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            pkg = json.loads(package_json.read_text())
            deps.update(pkg.get("dependencies", {}).keys())
            deps.update(pkg.get("devDependencies", {}).keys())
        except (json.JSONDecodeError, OSError):
            pass

    # Check pyproject.toml
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            # Simple extraction of dependencies
            dep_matches = re.findall(r'^\s*"?([a-zA-Z0-9_-]+)"?\s*[>=<]', content, re.MULTILINE)
            deps.update(dep_matches)
        except OSError:
            pass

    return deps


def detect_services(project_root: Path | None = None) -> dict[str, dict]:
    """Auto-detect logging services from project structure.

    Multi-layer detection:
    - Config (explicit configuration takes precedence)
    - Environment variables
    - Package dependencies

    Args:
        project_root: Project root directory (defaults to cwd)

    Returns:
        Dict of {service_name: {provider, detected_from, has_credentials, dashboard}}
    """
    if project_root is None:
        project_root = get_project_root()

    detected: dict[str, dict] = {}

    # Check config first (explicit configuration takes precedence)
    config_services = get("logging.services", {})
    for name, config in config_services.items():
        provider = config.get("provider", name)
        provider_info = PROVIDERS.get(provider, {})
        detected[name] = {
            "provider": provider,
            "detected_from": "config",
            "has_credentials": bool(config.get("env_var")),
            "dashboard": provider_info.get("dashboard"),
            "description": provider_info.get("description", "Custom logging service"),
        }

    # Get env vars and deps for detection
    env_vars = check_env_vars(project_root)
    package_deps = check_package_deps(project_root)

    # Check for known providers
    for provider, info in PROVIDERS.items():
        if provider in detected:
            continue

        # Check environment variables first
        matching_env = [p for p in info["env_patterns"] if p in env_vars]
        if matching_env:
            detected[provider] = {
                "provider": provider,
                "detected_from": "env",
                "has_credentials": True,
                "env_vars_found": matching_env,
                "dashboard": info.get("dashboard"),
                "description": info.get("description", ""),
            }
            continue

        # Check package dependencies
        matching_deps = [d for d in info["deps"] if d in package_deps]
        if matching_deps:
            # Check if we have credentials for services that need them
            has_creds = len(info["env_patterns"]) == 0 or any(
                p in env_vars for p in info["env_patterns"]
            )
            detected[provider] = {
                "provider": provider,
                "detected_from": "package.json",
                "has_credentials": has_creds,
                "deps_found": matching_deps,
                "dashboard": info.get("dashboard"),
                "description": info.get("description", ""),
            }

    return detected


def logging_status(project_root: Path | None = None) -> dict:
    """Get comprehensive logging service status.

    Returns:
        Status dictionary with detected services, credentials info, and config
    """
    if project_root is None:
        project_root = get_project_root()

    # Get logging config
    logging_config = get("logging", {})
    enabled = logging_config.get("enabled", True)

    # Detect services
    services = detect_services(project_root)

    # Count services by status
    with_creds = sum(1 for s in services.values() if s.get("has_credentials"))
    without_creds = sum(1 for s in services.values() if not s.get("has_credentials"))

    # Categorize services
    cloud_services = [name for name, info in services.items() if info.get("dashboard") is not None]
    local_loggers = [name for name, info in services.items() if info.get("dashboard") is None]

    return {
        "enabled": enabled,
        "services": services,
        "service_count": len(services),
        "with_credentials": with_creds,
        "without_credentials": without_creds,
        "cloud_services": cloud_services,
        "local_loggers": local_loggers,
    }


def get_dashboard_urls() -> list[tuple[str, str]]:
    """Get dashboard URLs for configured services.

    Returns:
        List of (service_name, dashboard_url) tuples
    """
    services = detect_services()
    urls = []

    for name, info in services.items():
        if info.get("dashboard"):
            urls.append((name, info["dashboard"]))

    return urls
