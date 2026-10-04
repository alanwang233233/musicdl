"""Synchronous HTTP client for the NextMusic API.

Wraps a single ``requests.Session`` and takes care of header setup,
automatic ``timestamp``/``ip`` injection, retries with exponential
backoff, and converting failures into musicdl exceptions. No business
logic lives here.
"""

from __future__ import annotations

import ipaddress
import logging
import queue
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

import requests
from typing_extensions import Self

from musicdl.config import IP_FETCH_URLS, MusicDLConfig
from musicdl.exceptions import (
    APIError,
    ConfigError,
    IPFetchError,
    NetworkError,
    ValidationError,
)

_ACCEPT_LANGUAGE = "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
_MAX_RETRY_AFTER = 60.0

logger = logging.getLogger(__name__)


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
        self._ip_lock = threading.Lock()

    @property
    def ip(self) -> str:
        """Client IP used for requests: manual value or fetched public IP.

        The public IP is fetched by racing all ``IP_FETCH_URLS`` endpoints
        concurrently; the first valid answer wins and the rest are abandoned.

        Returns:
            The IP string.

        Raises:
            ConfigError: No IP configured and automatic fetching disabled.
            IPFetchError: No endpoint returned a valid IP in time.
        """
        if self.config.ip:
            return self.config.ip
        now = time.monotonic()
        if self._ip_cache is not None and (now - self._ip_fetched_at) < self.config.ip_cache_ttl:
            return self._ip_cache
        with self._ip_lock:
            # double-check:并发请求时另一个线程可能已完成获取
            if self._ip_cache is not None and (
                time.monotonic() - self._ip_fetched_at
            ) < self.config.ip_cache_ttl:
                return self._ip_cache
            self._ip_cache = self._fetch_public_ip()
            self._ip_fetched_at = time.monotonic()
            return self._ip_cache

    def _ip_endpoints(self) -> tuple[str, ...]:
        """参与竞速的端点:全部内置端点 + 配置的自定义端点(如有)。"""
        endpoints = list(IP_FETCH_URLS)
        custom = self.config.ip_fetch_url
        if custom and custom not in endpoints:
            endpoints.insert(0, custom)
        return tuple(endpoints)

    def _request_ip_from(self, url: str, put: Callable[[str | None], None]) -> None:
        """请求单个 IP 端点,把结果(合法 IP 或 None)放入结果队列。"""
        try:
            response = requests.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except (requests.RequestException, ValueError):
            put(None)
            return
        put(self._extract_ip(response))

    def _fetch_public_ip(self) -> str:
        """并发竞速所有 IP 端点,哪个最先返回合法值就用哪个。

        端点跑在守护线程里:拿到首个合法结果立即返回,其余请求的结果被
        丢弃并随进程结束终止,不会阻塞调用方。
        """
        if not self.config.ip_fetch_url:
            raise ConfigError(
                "no IP configured and automatic IP fetching is disabled (ip_fetch_url='')"
            )
        endpoints = self._ip_endpoints()
        results: queue.Queue[str | None] = queue.Queue()
        for url in endpoints:
            threading.Thread(
                target=self._request_ip_from,
                args=(url, results.put),
                name=f"musicdl-ip-{url.split('//')[-1]}",
                daemon=True,
            ).start()

        deadline = time.monotonic() + self.config.timeout + 1.0
        remaining = len(endpoints)
        while remaining:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                break
            try:
                ip = results.get(timeout=timeout)
            except queue.Empty:
                break
            remaining -= 1
            if ip:
                return ip
        raise IPFetchError(
            f"no valid public IP from {len(endpoints)} endpoint(s) "
            f"(tried: {', '.join(endpoints)})"
        )

    @staticmethod
    def _extract_ip(response: requests.Response) -> str | None:
        """Extract the public IP from a JSON (``{"ip": ...}``) or plain-text response.

        Plain-text services (4.ident.me / checkip.amazonaws.com / ipv4.icanhazip.com)
        return the bare address; every extracted value must parse as a valid IP.
        """
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("ip"), str) and payload["ip"].strip():
            candidate = payload["ip"].strip()
        else:
            candidate = response.text.strip()
        if not candidate:
            return None
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return None
        return candidate

    def _url(self, endpoint: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    @staticmethod
    def _parse_retry_after(response: requests.Response, fallback: float) -> float:
        """Extract a bounded ``retryAfter`` (seconds) from a 429 response body.

        Server-controlled values are capped at ``_MAX_RETRY_AFTER`` and
        non-numeric values fall back to the configured backoff.
        """
        try:
            rate_data = response.json()
        except ValueError:
            return fallback
        raw = rate_data.get("retryAfter") if isinstance(rate_data, dict) else None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return min(max(float(raw), 0.0), _MAX_RETRY_AFTER)
        return fallback

    def post_json(self, endpoint: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """POST a JSON payload to an API endpoint.

        Automatically injects ``timestamp`` (epoch milliseconds) and ``ip``.
        Retries network errors, HTTP 5xx and rate limits (HTTP 429 or
        business code 429) up to ``config.max_retries`` times with
        exponential backoff; other HTTP 4xx and business errors fail
        immediately.

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
        body["ip"] = self.ip
        url = self._url(endpoint)
        last_error: BaseException | None = None
        waited = False
        for attempt in range(self.config.max_retries + 1):
            # 时间戳在每次尝试前刷新:429 等待可能很久,携带陈旧时间戳会被拒绝
            body["timestamp"] = int(time.time() * 1000)
            if attempt and not waited:
                time.sleep(self.config.retry_backoff * (2 ** (attempt - 1)))
            waited = False
            try:
                response = self._session.post(url, json=body, timeout=self.config.timeout)
            except requests.RequestException as exc:
                last_error = exc
                continue
            if response.status_code == 429:
                # Rate limited: parse retryAfter from response and wait
                retry_after = self._parse_retry_after(response, self.config.retry_backoff)
                last_error = APIError(code=429, message=f"rate limited (retry after {retry_after}s)")
                logger.info("rate limited (HTTP 429), waiting %ss before retry", retry_after)
                time.sleep(retry_after)
                waited = True
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
                payload_data = data.get("data")
                raw = payload_data.get("retryAfter") if isinstance(payload_data, dict) else None
                if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                    retry_after = min(max(float(raw), 0.0), _MAX_RETRY_AFTER)
                last_error = APIError(
                    code=429,
                    message=f"rate limited (retry after {retry_after}s)",
                    payload=data,
                )
                logger.info("rate limited (business 429), waiting %ss before retry", retry_after)
                time.sleep(retry_after)
                waited = True
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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
