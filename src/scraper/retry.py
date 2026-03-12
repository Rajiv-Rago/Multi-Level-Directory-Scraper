"""Tenacity-based retry logic for rate limiting and server errors."""

from __future__ import annotations

import functools
from typing import Callable

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

from scraper.fetcher import RateLimitError, ServerError

logger = structlog.get_logger()


def with_retry(fetch_fn: Callable) -> Callable:
    """Wrap a fetch function with retry logic for RateLimitError and ServerError."""

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=5, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    @retry(
        retry=retry_if_exception_type(ServerError),
        wait=wait_fixed(10),
        stop=stop_after_attempt(2),
        reraise=True,
    )
    @functools.wraps(fetch_fn)
    async def wrapper(*args, **kwargs):
        return await fetch_fn(*args, **kwargs)

    return wrapper
