"""Tests for lib/logger.py."""

import logging

import pytest


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_with_devkit_prefix(self):
        """Logger name should be prefixed with 'devkit.'."""
        from lib.logger import get_logger

        logger = get_logger("test")
        assert logger.name == "devkit.test"

    def test_returns_same_logger_on_repeated_calls(self):
        """Should return cached logger instance."""
        from lib.logger import get_logger

        logger1 = get_logger("cached")
        logger2 = get_logger("cached")
        assert logger1 is logger2

    def test_logger_has_stream_handler(self):
        """Logger should have a StreamHandler configured."""
        from lib.logger import get_logger

        logger = get_logger("handler_test")
        assert len(logger.handlers) > 0
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_default_level_is_debug(self):
        """Default log level should be DEBUG."""
        from lib.logger import get_logger

        logger = get_logger("level_test")
        assert logger.level == logging.DEBUG

    def test_custom_level_override(self):
        """Should accept custom log level."""
        from lib.logger import get_logger

        logger = get_logger("custom_level", level="WARNING")
        assert logger.level == logging.WARNING

    def test_logger_does_not_propagate(self):
        """Logger should not propagate to root logger."""
        from lib.logger import get_logger

        logger = get_logger("no_propagate")
        assert logger.propagate is False


class TestSetLogLevel:
    """Tests for set_log_level function."""

    def test_sets_level_for_all_loggers(self):
        """Should set level for all cached loggers."""
        from lib.logger import _loggers, get_logger, set_log_level

        # Create some loggers
        logger1 = get_logger("set_level_1")
        logger2 = get_logger("set_level_2")

        # Set level
        set_log_level("ERROR")

        assert logger1.level == logging.ERROR
        assert logger2.level == logging.ERROR

        # Reset for other tests
        set_log_level("DEBUG")
