"""Logging utilities for devkit-plugin.

TIER 1: May import from core only.

Provides consistent logging across all plugin modules using Python's
standard logging module (terminal strategy).
"""

import logging
import os
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

# Default format for devkit logs
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%H:%M:%S"

# Cache for loggers
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str, level: LogLevel | None = None) -> logging.Logger:
    """Get a configured logger for devkit-plugin.

    Args:
        name: Logger name (will be prefixed with 'devkit.')
        level: Log level override (default: from DEVKIT_LOG_LEVEL env or DEBUG)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger("sync")
        >>> logger.info("Syncing files...")
        20:55:39 | INFO     | devkit.sync | Syncing files...
    """
    full_name = f"devkit.{name}"

    # Return cached logger if exists
    if full_name in _loggers:
        return _loggers[full_name]

    logger = logging.getLogger(full_name)

    # Only configure if no handlers exist
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT))
        logger.addHandler(handler)

        # Set level from parameter, env var, or default
        if level:
            logger.setLevel(getattr(logging, level))
        else:
            env_level = os.environ.get("DEVKIT_LOG_LEVEL", "DEBUG")
            logger.setLevel(getattr(logging, env_level, logging.DEBUG))

        # Don't propagate to root logger
        logger.propagate = False

    _loggers[full_name] = logger
    return logger


def set_log_level(level: LogLevel) -> None:
    """Set log level for all devkit loggers.

    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR)
    """
    log_level = getattr(logging, level, logging.DEBUG)
    for logger in _loggers.values():
        logger.setLevel(log_level)
