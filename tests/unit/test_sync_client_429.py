"""Tests for 429 rate-limit handling in SyncMusicClient."""

import json
import time as time_module

import pytest
import responses

from musicdl import MusicDLConfig, SyncMusicClient
from musicdl.exceptions import APIError, NetworkError

URL = "https://test.example.com/api/ping"


def _config(max_retries: int = 3) -> MusicDLConfig:
    return MusicDLConfig(
        base_url="https://test.example.com",
        ip="127.0.0.1",
        max_retries=max_retries,
        retry_backoff=0.5,
    )


@pytest.fixture
def sleeps(monkeypatch):
    """Capture time.sleep calls so tests stay fast and can assert waits."""
    recorded: list[float] = []
    monkeypatch.setattr(time_module, "sleep", recorded.append)
    return recorded


@responses.activate
def test_http_429_retry_after_is_capped(sleeps):
    # 服务端返回超大的 retryAfter 也不能让进程睡一天
    responses.post(URL, json={"retryAfter": 86400}, status=429)
    responses.post(URL, json={"code": 200, "data": {"ok": True}})

    with SyncMusicClient(_config()) as client:
        body = client.post_json("/api/ping", {})

    assert body["code"] == 200
    assert sleeps and max(sleeps) <= 60.0


@responses.activate
def test_http_429_non_numeric_retry_after_falls_back(sleeps):
    # 字符串 retryAfter 此前会抛裸 TypeError,必须回退到配置退避
    responses.post(URL, json={"retryAfter": "soon"}, status=429)
    responses.post(URL, json={"code": 200, "data": {"ok": True}})

    with SyncMusicClient(_config()) as client:
        body = client.post_json("/api/ping", {})

    assert body["code"] == 200
    assert sleeps[0] == pytest.approx(0.5)


@responses.activate
def test_business_429_is_bounded_and_retried(sleeps):
    responses.post(URL, json={"code": 429, "data": {"retryAfter": 9999}})
    responses.post(URL, json={"code": 200, "data": {"ok": True}})

    with SyncMusicClient(_config()) as client:
        body = client.post_json("/api/ping", {})

    assert body["code"] == 200
    assert sleeps and max(sleeps) <= 60.0


@responses.activate
def test_429_does_not_sleep_twice_per_attempt(sleeps):
    # 429 已等待 retryAfter,同一轮不能再叠加指数退避
    responses.post(URL, json={"retryAfter": 2}, status=429)
    responses.post(URL, json={"code": 200, "data": {"ok": True}})

    with SyncMusicClient(_config(max_retries=3)) as client:
        client.post_json("/api/ping", {})

    assert sleeps == [2.0]


@responses.activate
def test_429_exhaustion_raises_network_error_with_api_context(sleeps):
    for _ in range(4):
        responses.post(URL, json={"retryAfter": 1}, status=429)

    # 限流耗尽后不能丢上下文:NetworkError.original 必须携带 429 信息
    with (
        pytest.raises(NetworkError) as exc_info,
        SyncMusicClient(_config(max_retries=3)) as client,
    ):
        client.post_json("/api/ping", {})

    assert isinstance(exc_info.value.original, APIError)
    assert exc_info.value.original.code == 429


@responses.activate
def test_timestamp_refreshed_between_attempts(monkeypatch, sleeps):
    # 时间戳必须在每次尝试前刷新,而不是循环外计算一次(429 等待后旧时间戳会被拒绝)
    bodies: list[dict] = []

    def _capture(req):
        bodies.append(json.loads(req.body))
        return 429, {}, json.dumps({"retryAfter": 1})

    clock = {"value": 1_000_000}

    def _tick_time():
        clock["value"] += 5_000
        return clock["value"]

    monkeypatch.setattr(time_module, "time", _tick_time)

    def _respond_ok(req):
        bodies.append(json.loads(req.body))
        return 200, {}, json.dumps({"code": 200, "data": {"ok": True}})

    responses.add_callback(responses.POST, URL, callback=_capture, content_type="application/json")
    responses.add_callback(responses.POST, URL, callback=_respond_ok, content_type="application/json")

    with SyncMusicClient(_config()) as client:
        client.post_json("/api/ping", {})

    assert len(bodies) == 2
    assert bodies[0]["timestamp"] != bodies[1]["timestamp"]
