"""Tests for SyncMusicClient."""

import json
import time

import pytest
import requests
import responses

from musicdl.api import endpoints
from musicdl.client import SyncMusicClient
from musicdl.config import MusicDLConfig
from musicdl.exceptions import APIError, ConfigError, IPFetchError, NetworkError, ValidationError

BASE = "https://nextmusic.toubiec.cn"


def make_client(**overrides) -> SyncMusicClient:
    defaults = dict(ip="1.2.3.4", max_retries=1, retry_backoff=0.0)
    defaults.update(overrides)
    return SyncMusicClient(MusicDLConfig(**defaults))


@responses.activate
def test_post_json_injects_timestamp_and_ip() -> None:
    responses.add(responses.POST, f"{BASE}{endpoints.GET_SONG_INFO}", json={"code": 200, "data": {}}, status=200)
    before = int(time.time() * 1000)
    client = make_client()
    client.post_json(endpoints.GET_SONG_INFO, {"id": "1"})
    after = int(time.time() * 1000)
    body = json.loads(responses.calls[0].request.body)
    assert body["id"] == "1"
    assert body["ip"] == "1.2.3.4"
    assert before <= body["timestamp"] <= after
    assert responses.calls[0].request.headers["Content-Type"] == "application/json"


@responses.activate
def test_auto_fetches_public_ip_and_caches() -> None:
    responses.add(responses.GET, "https://api.ipify.org?format=json", json={"ip": "9.9.9.9"}, status=200)
    responses.add(responses.POST, f"{BASE}{endpoints.GET_SONG_INFO}", json={"code": 200, "data": {}}, status=200)
    client = make_client(ip=None)
    client.post_json(endpoints.GET_SONG_INFO, {"id": "1"})
    client.post_json(endpoints.GET_SONG_INFO, {"id": "2"})
    ip_calls = [c for c in responses.calls if c.request.method == "GET"]
    assert len(ip_calls) == 1
    assert json.loads(responses.calls[1].request.body)["ip"] == "9.9.9.9"


@responses.activate
def test_disabled_ip_fetch_without_ip_raises_config_error() -> None:
    client = make_client(ip=None, ip_fetch_url="")
    with pytest.raises(ConfigError):
        client.post_json(endpoints.GET_SONG_INFO, {"id": "1"})


@responses.activate
def test_ip_fetch_failure_raises_ip_fetch_error() -> None:
    responses.add(responses.GET, "https://api.ipify.org?format=json", status=500)
    client = make_client(ip=None)
    with pytest.raises(IPFetchError):
        client.ip


@responses.activate
def test_non_200_code_raises_api_error() -> None:
    responses.add(responses.POST, f"{BASE}{endpoints.PLAYLIST_TRACKALL}", json={"code": 404, "data": None}, status=200)
    client = make_client()
    with pytest.raises(APIError) as exc_info:
        client.post_json(endpoints.PLAYLIST_TRACKALL, {"id": "1", "limit": 1, "offset": 0})
    assert exc_info.value.code == 404


@responses.activate
def test_http_4xx_raises_api_error_without_retry() -> None:
    responses.add(responses.POST, f"{BASE}{endpoints.GET_SONG_URL}", body="not found", status=404)
    client = make_client()
    with pytest.raises(APIError) as exc_info:
        client.post_json(endpoints.GET_SONG_URL, {"id": "1", "level": "standard"})
    assert exc_info.value.code == 404
    assert len(responses.calls) == 1


@responses.activate
def test_connection_error_retries_then_raises_network_error() -> None:
    responses.add(responses.POST, f"{BASE}{endpoints.GET_SONG_INFO}", body=requests.exceptions.ConnectionError("boom"))
    client = make_client(max_retries=2)
    with pytest.raises(NetworkError) as exc_info:
        client.post_json(endpoints.GET_SONG_INFO, {"id": "1"})
    assert len(responses.calls) == 3  # initial + 2 retries
    assert isinstance(exc_info.value.original, requests.exceptions.ConnectionError)


@responses.activate
def test_http_5xx_retries_then_raises_network_error() -> None:
    responses.add(responses.POST, f"{BASE}{endpoints.GET_SONG_INFO}", status=503)
    client = make_client(max_retries=1)
    with pytest.raises(NetworkError):
        client.post_json(endpoints.GET_SONG_INFO, {"id": "1"})
    assert len(responses.calls) == 2


@responses.activate
def test_invalid_json_raises_validation_error() -> None:
    responses.add(
        responses.POST,
        f"{BASE}{endpoints.GET_SONG_INFO}",
        body="<html>oops</html>",
        status=200,
        content_type="text/html",
    )
    client = make_client()
    with pytest.raises(ValidationError):
        client.post_json(endpoints.GET_SONG_INFO, {"id": "1"})


def test_context_manager_returns_self() -> None:
    with make_client() as client:
        assert isinstance(client, SyncMusicClient)
