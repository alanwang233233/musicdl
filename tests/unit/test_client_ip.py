"""Tests for public-IP fetching: endpoint racing (JSON and plain-text services)."""

import json

import pytest
import responses

from musicdl import SyncMusicClient
from musicdl.config import IP_FETCH_URLS
from musicdl.exceptions import IPFetchError

BASE = "https://test.example.com"


def make_client(ip=None, ip_fetch_url="https://api.ipify.org?format=json") -> SyncMusicClient:
    from musicdl import MusicDLConfig

    return SyncMusicClient(
        MusicDLConfig(
            base_url=BASE,
            ip=ip,
            ip_fetch_url=ip_fetch_url,
            max_retries=1,
            retry_backoff=0.0,
        )
    )


def _post_call():
    """IP 竞速会并发请求多个端点,POST 调用必须按方法过滤定位。"""
    return next(c for c in responses.calls if c.request.method == "POST")


@pytest.mark.parametrize("url", IP_FETCH_URLS)
@responses.activate
def test_endpoint_returns_valid_ip_for_business_request(url):
    """任一端点返回合法 IP(纯文本或 JSON)都会被采用。"""
    if url == "https://api.ipify.org?format=json":
        responses.add(responses.GET, url, json={"ip": "203.0.113.7"}, status=200)
    else:
        responses.add(responses.GET, url, body="203.0.113.7\n", status=200)
    responses.add(responses.POST, f"{BASE}/api/getSongInfo", json={"code": 200, "data": {}})

    client = make_client(ip=None, ip_fetch_url=url)
    client.post_json("/api/getSongInfo", {"id": "1"})

    body = json.loads(_post_call().request.body)
    assert body["ip"] == "203.0.113.7"


@responses.activate
def test_ip_race_prefers_first_valid_answer():
    """竞速:其余端点返回垃圾值时,首个合法值胜出。"""
    responses.add(responses.GET, "https://4.ident.me", body="203.0.113.7")
    for url in ("https://api.ipify.org?format=json", "https://checkip.amazonaws.com", "https://ipv4.icanhazip.com"):
        responses.add(responses.GET, url, body="garbage")

    client = make_client(ip=None)
    assert client._fetch_public_ip() == "203.0.113.7"


@responses.activate
def test_ip_race_all_invalid_raises_ip_fetch_error():
    for url in IP_FETCH_URLS:
        responses.add(responses.GET, url, body="garbage")

    client = make_client(ip=None)
    with pytest.raises(IPFetchError):
        client._fetch_public_ip()


@responses.activate
def test_json_ip_service_still_supported():
    responses.add(responses.GET, "https://api.ipify.org?format=json", json={"ip": "198.51.100.9"}, status=200)
    responses.add(responses.POST, f"{BASE}/api/getSongInfo", json={"code": 200, "data": {}})

    client = make_client(ip=None)
    client.post_json("/api/getSongInfo", {"id": "1"})

    body = json.loads(_post_call().request.body)
    assert body["ip"] == "198.51.100.9"


@responses.activate
def test_garbage_plain_text_raises_ip_fetch_error():
    responses.add(responses.GET, "https://4.ident.me", body="not-an-ip", status=200)

    client = make_client(ip=None, ip_fetch_url="https://4.ident.me")
    with pytest.raises(IPFetchError):
        client.post_json("/api/getSongInfo", {"id": "1"})


@responses.activate
def test_empty_plain_text_raises_ip_fetch_error():
    responses.add(responses.GET, "https://4.ident.me", body="  \n", status=200)

    client = make_client(ip=None, ip_fetch_url="https://4.ident.me")
    with pytest.raises(IPFetchError):
        client.post_json("/api/getSongInfo", {"id": "1"})
