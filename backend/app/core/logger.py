import logging
import sys

# Format definition
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# Third-party libraries that produce noisy output at WARNING/DEBUG level
# when running normally. Suppress them to ERROR-only unless DEBUG mode is on.
_NOISY_LOGGERS = [
    "sentence_transformers",
    "transformers",
    "huggingface_hub",
    "huggingface_hub.utils",
    "filelock",
    "urllib3",
    "httpx",
    "httpcore",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "sqlalchemy.dialects",
    "sqlalchemy.orm",
    "asyncio",
    "multipart",
    "uvicorn.access",
    "faiss",
    "PIL",
    "torch",
]


def setup_logger(name: str = "devmind") -> logging.Logger:
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

    # Suppress noisy third-party loggers
    for lib_name in _NOISY_LOGGERS:
        lib_logger = logging.getLogger(lib_name)
        lib_logger.setLevel(logging.ERROR)
        lib_logger.propagate = False

    return logger


logger = setup_logger()
