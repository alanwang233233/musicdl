"""Tests for SongService."""

import json

import pytest
import responses

from musicdl.api import endpoints
from musicdl.client import SyncMusicClient
from musicdl.config import MusicDLConfig
from musicdl.exceptions import APIError
from musicdl.models import QualityLevel, SongInfo, SongUrl
from musicdl.services.song import SongService

BASE = "https://nextmusic.toubiec.cn"
INFO_URL = f"{BASE}{endpoints.GET_SONG_INFO}"
SONG_URL = f"{BASE}{endpoints.GET_SONG_URL}"


@pytest.fixture
def service() -> SongService:
    client = SyncMusicClient(MusicDLConfig(ip="1.2.3.4", max_retries=0, retry_backoff=0.0))
    return SongService(client)


@responses.activate
def test_get_info_returns_song_info(service: SongService, load_fixture) -> None:
    responses.add(responses.POST, INFO_URL, json=load_fixture("song_info.json"), status=200)
    info = service.get_info(1432544572)
    assert isinstance(info, SongInfo)
    assert info.name == "想想念念"
    body = json.loads(responses.calls[0].request.body)
    assert body["id"] == "1432544572"
    assert "timestamp" in body and "ip" in body


@responses.activate
def test_get_url_default_level_is_standard(service: SongService, load_fixture) -> None:
    responses.add(responses.POST, SONG_URL, json=load_fixture("song_url.json"), status=200)
    url = service.get_url(1432544572)
    assert isinstance(url, SongUrl)
    assert url.level == "standard"
    body = json.loads(responses.calls[0].request.body)
    assert body["level"] == "standard"
    assert body["id"] == "1432544572"


@responses.activate
def test_get_url_accepts_string_level(service: SongService, load_fixture) -> None:
    responses.add(responses.POST, SONG_URL, json=load_fixture("song_url.json"), status=200)
    service.get_url("1432544572", level="exhires")
    body = json.loads(responses.calls[0].request.body)
    assert body["level"] == "exhires"


@responses.activate
def test_get_url_converts_enum_level(service: SongService, load_fixture) -> None:
    responses.add(responses.POST, SONG_URL, json=load_fixture("song_url.json"), status=200)
    service.get_url(1, level=QualityLevel.STANDARD)
    body = json.loads(responses.calls[0].request.body)
    assert body["level"] == "standard"
    assert isinstance(body["level"], str)


@responses.activate
def test_api_error_propagates(service: SongService) -> None:
    responses.add(responses.POST, INFO_URL, json={"code": 404, "data": None}, status=200)
    with pytest.raises(APIError):
        service.get_info(1)


@responses.activate
def test_get_url_api_error_propagates(service: SongService) -> None:
    responses.add(responses.POST, SONG_URL, json={"code": 404, "data": None}, status=200)
    with pytest.raises(APIError):
        service.get_url(1)
