"""Tests for MusicDLConfig."""

from musicdl.config import MusicDLConfig
from musicdl.models import QualityLevel


def test_defaults() -> None:
    cfg = MusicDLConfig()
    assert cfg.base_url == "https://nextmusic.toubiec.cn"
    assert cfg.timeout == 30.0
    assert cfg.max_retries == 3
    assert cfg.retry_backoff == 0.5
    assert cfg.ip is None
    assert cfg.ip_fetch_url == "https://api.ipify.org?format=json"
    assert cfg.ip_cache_ttl == 3600.0
    assert cfg.default_level is QualityLevel.STANDARD
    assert cfg.user_agent is None


def test_custom_values() -> None:
    cfg = MusicDLConfig(
        base_url="http://localhost:8080",
        timeout=5.0,
        max_retries=0,
        ip="1.2.3.4",
        ip_fetch_url="",
        user_agent="my-agent/1.0",
    )
    assert cfg.base_url == "http://localhost:8080"
    assert cfg.timeout == 5.0
    assert cfg.max_retries == 0
    assert cfg.ip == "1.2.3.4"
    assert cfg.ip_fetch_url == ""
    assert cfg.user_agent == "my-agent/1.0"