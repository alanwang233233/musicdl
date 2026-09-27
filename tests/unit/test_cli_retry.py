"""Tests for musicdl_cli retry utility."""

from unittest.mock import Mock, call

import pytest

from musicdl.exceptions import APIError, DownloadError, NetworkError
from musicdl_cli.utils.retry import download_with_retry


def test_retry_succeeds_first_try():
    fn = Mock(return_value="ok")
    result = download_with_retry(fn, max_retries=3, retry_wait=0)
    assert result == "ok"
    assert fn.call_count == 1


def test_retry_recovers_from_429():
    fn = Mock(side_effect=[APIError(code=429, message="rate limit"), "ok"])
    result = download_with_retry(fn, max_retries=3, retry_wait=0)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_recovers_from_404():
    fn = Mock(side_effect=[APIError(code=404, message="not found"), "ok"])
    result = download_with_retry(fn, max_retries=3, retry_wait=0)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_recovers_from_network_error():
    fn = Mock(side_effect=[NetworkError("timeout"), "ok"])
    result = download_with_retry(fn, max_retries=3, retry_wait=0)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_gives_up_after_max_retries():
    fn = Mock(side_effect=APIError(code=429, message="rate limit"))
    with pytest.raises(APIError):
        download_with_retry(fn, max_retries=2, retry_wait=0)
    assert fn.call_count == 3  # initial + 2 retries


def test_retry_does_not_catch_non_retryable():
    fn = Mock(side_effect=ValueError("bad"))
    with pytest.raises(ValueError):
        download_with_retry(fn, max_retries=3, retry_wait=0)
    assert fn.call_count == 1


def test_retry_calls_on_retry_callback():
    on_retry = Mock()
    fn = Mock(side_effect=[APIError(code=429, message="rl"), APIError(code=404, message="nf"), "ok"])
    result = download_with_retry(fn, max_retries=3, retry_wait=0, on_retry=on_retry)
    assert result == "ok"
    assert on_retry.call_count == 2
    on_retry.assert_has_calls([call(1, "限流(429)"), call(2, "未找到(404)")])