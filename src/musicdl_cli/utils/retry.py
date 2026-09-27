"""Retry wrapper for download operations (429/404/network errors)."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from musicdl.exceptions import APIError, DownloadError, NetworkError

T = TypeVar("T")

_RETRYABLE_API_CODES = {429, 404}


def download_with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = 10,
    retry_wait: float = 10.0,
    on_retry: Callable[[int, str], None] | None = None,
) -> T:
    """Call *fn* with automatic retry on 429/404/network errors.

    Args:
        fn: Zero-argument callable that performs the download.
        max_retries: Maximum number of retry attempts after the initial call.
        retry_wait: Seconds to wait between attempts.
        on_retry: Optional callback ``(attempt_number, reason)`` invoked before
            each retry wait.

    Returns:
        The value returned by *fn*.

    Raises:
        The last exception if all retries are exhausted, or a non-retryable
        exception on the first failure.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            if not _is_retryable(exc):
                raise
            last_exc = exc
            if attempt >= max_retries:
                break
            reason = _classify_error(exc)
            if on_retry is not None:
                on_retry(attempt + 1, reason)
            time.sleep(retry_wait)
    raise last_exc  # type: ignore[misc]


def _is_retryable(exc: BaseException) -> bool:
    """Check if an exception is retryable (429, 404, or network error)."""
    if isinstance(exc, NetworkError):
        return True
    if isinstance(exc, APIError):
        return exc.code in _RETRYABLE_API_CODES
    if isinstance(exc, DownloadError):
        return _is_retryable(exc.__cause__) if exc.__cause__ else False
    return False


def _classify_error(exc: BaseException) -> str:
    """Return a short Chinese label for the error type."""
    if isinstance(exc, APIError):
        if exc.code == 429:
            return "限流(429)"
        if exc.code == 404:
            return "未找到(404)"
    if isinstance(exc, DownloadError) and exc.__cause__:
        return _classify_error(exc.__cause__)
    return "网络错误"
