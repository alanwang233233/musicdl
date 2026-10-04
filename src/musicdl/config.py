"""Configuration for the musicdl library.

Configuration is code-only: pass a ``MusicDLConfig`` instance to the
client constructor. No environment variables or config files are read.
"""

from __future__ import annotations

from dataclasses import dataclass

from musicdl.models import QualityLevel

# 内置公网 IP 获取端点(JSON 或纯文本格式);获取 IP 时并发竞速,首个合法值胜出
IP_FETCH_URLS: tuple[str, ...] = (
    "https://api.ipify.org?format=json",
    "https://4.ident.me",
    "https://checkip.amazonaws.com",
    "https://ipv4.icanhazip.com",
)


@dataclass
class MusicDLConfig:
    """Runtime configuration for API access.

    Attributes:
        base_url: API base URL without trailing slash.
        timeout: Per-request timeout in seconds.
        max_retries: Retry count for network errors and HTTP 5xx.
        retry_backoff: Base delay in seconds for exponential backoff.
        ip: Explicit client IP. When ``None`` the public IP is fetched
            by racing ``IP_FETCH_URLS`` concurrently (cached for
            ``ip_cache_ttl`` seconds); the first valid answer wins.
        ip_fetch_url: Extra endpoint included in the IP race (JSON
            ``{"ip": "..."}`` or plain text), in addition to the built-in
            ``IP_FETCH_URLS``. An empty string disables automatic
            fetching (then ``ip`` is required).
        ip_cache_ttl: How long an automatically fetched IP stays cached.
        default_level: Default quality level for getSongUrl.
        user_agent: Optional custom User-Agent header.
    """

    base_url: str = "https://nextmusic.toubiec.cn"
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 0.5
    ip: str | None = None
    ip_fetch_url: str = "https://api.ipify.org?format=json"
    ip_cache_ttl: float = 3600.0
    default_level: QualityLevel = QualityLevel.STANDARD
    user_agent: str | None = None
