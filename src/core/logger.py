"""
ScrapeGuard — Centralized Logging Module.

Provides a pre-configured Loguru logger with:
  • Automatic log rotation (prevents disk bloat)
  • Retention policy (auto-deletes stale log files)
  • Structured formatting for easy parsing
  • Thread-safe file sinks

Usage:
    from src.core.logger import logger
    logger.info("Scrape cycle completed for {target}", target="example.com")
"""

import sys

from loguru import logger as _loguru_logger

from config.settings import (
    LOG_FILE_PATH,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_RETENTION,
    LOG_ROTATION,
)


def _configure_logger() -> "loguru.Logger":
    """
    Configure and return the global Loguru logger instance.

    Removes default stderr sink, then adds:
      1. A stdout sink (INFO+) for console visibility.
      2. A file sink with rotation & retention for persistent storage.

    Returns:
        Configured Loguru logger instance.
    """
    # Remove all default sinks to prevent duplicate output
    _loguru_logger.remove()

    # Console sink — human-readable, INFO level and above
    _loguru_logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level="INFO",
        colorize=True,
        backtrace=False,
        diagnose=False,
    )

    # File sink — full debug output, rotated & retained
    _loguru_logger.add(
        LOG_FILE_PATH,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        enqueue=True,          # Thread-safe writes via queue
        backtrace=True,
        diagnose=True,
    )

    _loguru_logger.info("Logger initialized — rotation={rot}, retention={ret}",
                        rot=LOG_ROTATION, ret=LOG_RETENTION)
    return _loguru_logger


# Module-level singleton: import `logger` anywhere in the project
logger = _configure_logger()
