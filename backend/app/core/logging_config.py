"""
DevMind Logging Configuration
==============================
Centralised, environment-aware logging setup.

This module MUST be imported before any other app modules so that
logging levels are applied before third-party libraries register
their own handlers or emit their first records.

Usage
-----
    # Always the very first import in main.py / any entrypoint
    import app.core.logging_config  # noqa: F401  (side-effect import)
"""

import logging
import logging.config
import os
import sys

# ---------------------------------------------------------------------------
# Read environment before settings are loaded (avoids import cycle)
# ---------------------------------------------------------------------------
_LOG_LEVEL_ENV = os.environ.get("LOG_LEVEL", "INFO").upper()
_DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")

# In DEBUG mode we keep INFO for DevMind and allow WARNING for libraries.
# In production (default) we silence all third-party noise completely.
_THIRD_PARTY_LEVEL = "DEBUG" if _DEBUG else "WARNING"
_DEVMIND_LEVEL     = "DEBUG" if _DEBUG else _LOG_LEVEL_ENV

# ---------------------------------------------------------------------------
# Coloured / structured format
# ---------------------------------------------------------------------------
_FMT_DEVMIND = "[%(levelname)s] DevMind | %(message)s"
_FMT_PLAIN   = "%(asctime)s  %(levelname)-8s  %(name)s | %(message)s"

# ---------------------------------------------------------------------------
# Complete dictConfig — this is applied *atomically* before any log record
# can be emitted, regardless of import order.
# ---------------------------------------------------------------------------
LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": True,   # silence loggers set up before us

    "formatters": {
        "devmind": {
            "format": _FMT_DEVMIND,
            "datefmt": "%H:%M:%S",
        },
        "plain": {
            "format": _FMT_PLAIN,
            "datefmt": "%H:%M:%S",
        },
    },

    "handlers": {
        "devmind_console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "devmind",
            "level": _DEVMIND_LEVEL,
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },

    # ---------------------------------------------------------------------------
    # Root logger — WARNING by default so nothing noisy leaks through
    # ---------------------------------------------------------------------------
    "root": {
        "level": "WARNING",
        "handlers": ["devmind_console"],
    },

    # ---------------------------------------------------------------------------
    # Named loggers
    # ---------------------------------------------------------------------------
    "loggers": {
        # ── DevMind application ────────────────────────────────────────────────
        "devmind": {
            "level": _DEVMIND_LEVEL,
            "handlers": ["devmind_console"],
            "propagate": False,
        },

        # ── SQLAlchemy — silence completely unless DEBUG ───────────────────────
        "sqlalchemy": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "sqlalchemy.engine.Engine": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "sqlalchemy.pool": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "sqlalchemy.dialects": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "sqlalchemy.orm": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },

        # ── Uvicorn — keep ERROR messages, hide every access line ─────────────
        "uvicorn": {
            "level": "WARNING",
            "handlers": ["devmind_console"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "WARNING",
            "handlers": ["devmind_console"],
            "propagate": False,
        },

        # ── FastAPI / Starlette ───────────────────────────────────────────────
        "fastapi": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },

        # ── HTTP / Network libraries ──────────────────────────────────────────
        "httpx": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "httpcore": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "urllib3": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "requests": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "aiohttp": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },

        # ── AI / ML libraries ─────────────────────────────────────────────────
        "sentence_transformers": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },
        "transformers": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },
        "huggingface_hub": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },
        "huggingface_hub.utils": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },
        "huggingface_hub.utils._headers": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },
        "torch": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },
        "faiss": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },

        # ── File / system libraries ───────────────────────────────────────────
        "filelock": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },
        "watchdog": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "asyncio": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "multipart": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "PIL": {
            "level": "ERROR",
            "handlers": ["null"],
            "propagate": False,
        },

        # ── OpenAI-compatible clients ─────────────────────────────────────────
        "openai": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "groq": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },

        # ── Google AI ─────────────────────────────────────────────────────────
        "google": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },
        "google.generativeai": {
            "level": "WARNING",
            "handlers": ["null"],
            "propagate": False,
        },

        # ── Alembic ───────────────────────────────────────────────────────────
        "alembic": {
            "level": "WARNING",
            "handlers": ["devmind_console"],
            "propagate": False,
        },
    },
}


def apply() -> None:
    """Apply the logging configuration. Idempotent — safe to call multiple times."""
    logging.config.dictConfig(LOGGING_CONFIG)


# Apply immediately on import so the configuration is active before
# any other module has a chance to emit a log record.
apply()
