"""Synchronous HTTP client for the NextMusic API.

Wraps a single ``requests.Session`` and takes care of header setup,
automatic ``timestamp``/``ip`` injection, retries with exponential
backoff, and converting failures into musicdl exceptions. No business
logic lives here.
"""

from __future__ import annotations

import time
from typing import Any, Mapping

import requests

from musicdl.config import MusicDLConfig
from musicdl.exceptions import (
    APIError,
    ConfigError,
    IPFetchError,
    NetworkError,
    ValidationError,
)

_ACCEPT_LANGUAGE = "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"


class SyncMusicClient:
    """Synchronous API client.

    Args:
        config: Runtime configuration; defaults to ``MusicDLConfig()``.

    Example:
        >>> with SyncMusicClient(MusicDLConfig(ip="1.2.3.4")) as client:
        ...     body = client.post_json("/api/getSongInfo", {"id": "1"})
    """

    def __init__(self, config: MusicDLConfig | None = None) -> None:
        self.config = config if config is not None else MusicDLConfig()
        self._session = requests.Session()
        headers = {
            "Accept": "*/*",
            "Accept-Language": _ACCEPT_LANGUAGE,
            "Content-Type": "application/json",
        }
        if self.config.user_agent:
            headers["User-Agent"] = self.config.user_agent
        self._session.headers.update(headers)
        self._ip_cache: str | None = None
        self._ip_fetched_at: float = 0.0

    @property
    def ip(self) -> str:
        """Client IP used for requests: manual value or fetched public IP.

        Returns:
            The IP string.

        Raises:
            ConfigError: No IP configured and automatic fetching disabled.
            IPFetchError: The IP service could not be reached or replied badly.
        """
        if self.config.ip:
            return self.config.ip
        now = time.monotonic()
        if self._ip_cache is not None and (now - self._ip_fetched_at) < self.config.ip_cache_ttl:
            return self._ip_cache
        self._ip_cache = self._fetch_public_ip()
        self._ip_fetched_at = time.monotonic()
        return self._ip_cache

    def _fetch_public_ip(self) -> str:
        if not self.config.ip_fetch_url:
            raise ConfigError("no IP configured and automatic IP fetching is disabled (ip_fetch_url='')")
        try:
            response = self._session.get(self.config.ip_fetch_url, timeout=self.config.timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise IPFetchError(f"failed to fetch public IP from {self.config.ip_fetch_url}") from exc
        ip = payload.get("ip") if isinstance(payload, dict) else None
        if not isinstance(ip, str) or not ip:
            raise IPFetchError("IP service response does not contain a valid 'ip' field")
        return ip

    def _url(self, endpoint: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def post_json(self, endpoint: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """POST a JSON payload to an API endpoint.

        Automatically injects ``timestamp`` (epoch milliseconds) and ``ip``.
        Retries network errors and HTTP 5xx up to ``config.max_retries``
        times with exponential backoff; HTTP 4xx and business errors
        (``code != 200``) fail immediately.

        Args:
            endpoint: Endpoint path, e.g. ``"/api/getSongInfo"``.
            payload: Business payload without ``timestamp``/``ip``.

        Returns:
            The decoded response body (``{"code": 200, "data": ...}``).

        Raises:
            APIError: HTTP 4xx or response business code != 200.
            NetworkError: Transport failure or HTTP 5xx after all retries.
            ValidationError: Response body is not valid JSON.
            ConfigError / IPFetchError: IP resolution failures.
        """
        body: dict[str, Any] = dict(payload)
        body["timestamp"] = int(time.time() * 1000)
        body["ip"] = self.ip
        url = self._url(endpoint)
        last_error: BaseException | None = None
        for attempt in range(self.config.max_retries + 1):
            if attempt:
                time.sleep(self.config.retry_backoff * (2 ** (attempt - 1)))
            try:
                response = self._session.post(url, json=body, timeout=self.config.timeout)
            except requests.RequestException as exc:
                last_error = exc
                continue
            if response.status_code == 429:
                # Rate limited: parse retryAfter from response and wait
                retry_after = self.config.retry_backoff
                try:
                    rate_data = response.json()
                    if isinstance(rate_data, dict) and "retryAfter" in rate_data:
                        retry_after = max(rate_data["retryAfter"], 0)
                except ValueError:
                    pass
                print(f"  ⏳ 限流 (429)，等待 {retry_after}s 后重试...", end="\r")
                time.sleep(retry_after)
                continue
            if response.status_code >= 500:
                last_error = NetworkError(f"HTTP {response.status_code} from {endpoint}")
                continue
            if response.status_code >= 400:
                raise APIError(code=response.status_code, message=response.text[:500])
            try:
                data = response.json()
            except ValueError as exc:
                raise ValidationError(f"invalid JSON response from {endpoint}", original=exc) from exc
            if not isinstance(data, dict):
                raise ValidationError(f"unexpected response type from {endpoint}: {type(data).__name__}")
            code = data.get("code")
            if code == 429:
                # Business-level rate limit: parse retryAfter from response
                retry_after = self.config.retry_backoff
                if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
                    retry_after = max(data["data"].get("retryAfter", retry_after), 0)
                print(f"  ⏳ 业务限流 (code 429)，等待 {retry_after}s 后重试...", end="\r")
                time.sleep(retry_after)
                continue
            if code != 200:
                message = data.get("message") or data.get("msg") or f"API returned code {code!r}"
                raise APIError(
                    code=int(code) if isinstance(code, int) else -1,
                    message=str(message),
                    payload=data,
                )
            return data
        raise NetworkError(
            f"request to {endpoint} failed after {self.config.max_retries + 1} attempt(s)",
            original=last_error,
        )

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()

    def __enter__(self) -> "SyncMusicClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
