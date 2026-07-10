"""
DevMind Application Logger
===========================
Provides a single shared ``logger`` instance for all DevMind modules.

This module imports ``logging_config`` as its very first statement so
that the full logging configuration is applied before any third-party
library can emit a record.

Usage
-----
    from app.core.logger import logger

    logger.info("Repository indexed successfully")
    logger.warning("Provider unavailable, switching fallback")
    logger.error("Failed to connect to database")
"""

# ── Logging configuration MUST come first ────────────────────────────────────
import app.core.logging_config  # noqa: F401  (side-effect: applies dictConfig)

import logging


def get_logger(name: str = "devmind") -> logging.Logger:
    """Return a named child of the DevMind root logger.

    All child loggers inherit the handler and level set in logging_config,
    so they will appear with the ``[INFO] DevMind | …`` format automatically.

    Args:
        name: Dot-separated logger name, e.g. ``"devmind.agents"``
              or ``"devmind.chat"``. Defaults to ``"devmind"``.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)


# Shared singleton — drop-in replacement for the previous ``logger``
logger: logging.Logger = get_logger("devmind")
