"""Retry Policy with exponential backoff and jitter.
"""

from __future__ import annotations

import random
import asyncio
from typing import Any, Union
import httpx

from app.core.logger import logger


class RetryPolicy:
    """Implements exponential backoff and random jitter retry policies."""

    def __init__(self):
        self.retryable_codes = {429, 500, 502, 503, 504}
        self.non_retryable_codes = {400, 401, 403, 404}

    def should_retry(self, error: Any) -> bool:
        """Determines if a given exception or HTTP status code is retryable."""
        # Case 1: Status Code as integer
        if isinstance(error, int):
            if error in self.retryable_codes:
                return True
            if error in self.non_retryable_codes:
                return False
            # Default to true for any other 5xx errors, false for other 4xx
            if 500 <= error < 600:
                return True
            return False

        # Case 2: Exception object
        if isinstance(error, Exception):
            # Check for HTTP status code attributes
            status_code = getattr(error, "status_code", None)
            if status_code is not None:
                return self.should_retry(status_code)

            # Check httpx exception hierarchy
            if isinstance(error, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)):
                return True

            # Check built-in socket/timeout exceptions
            if isinstance(error, (asyncio.TimeoutError, ConnectionError, TimeoutError)):
                return True

            # Check for strings indicating timeout or connection issues
            err_str = str(error).lower()
            if any(w in err_str for w in ("timeout", "connection refused", "connect timed out", "connection reset")):
                return True

        return False

    def get_delay(self, attempt: int, base_delay: float = 2.0) -> float:
        """Calculates backoff delay: min(base * (2^attempt), 30) + jitter (0-500ms)."""
        delay = min(base_delay * (2 ** attempt), 30.0)
        jitter = random.uniform(0.0, 0.5)  # 0 to 500ms
        return delay + jitter


retry_policy = RetryPolicy()
