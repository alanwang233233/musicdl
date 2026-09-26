"""Tests for PlaylistService."""

import json

import pytest
import responses

from musicdl.api import endpoints
from musicdl.client import SyncMusicClient
from musicdl.config import MusicDLConfig
from musicdl.exceptions import APIError
from musicdl.services.playlist import PlaylistService

BASE = "https://nextmusic.toubiec.cn"
URL = f"{BASE}{endpoints.PLAYLIST_TRACKALL}"


@pytest.fixture
def service() -> PlaylistService:
    client = SyncMusicClient(MusicDLConfig(ip="1.2.3.4", max_retries=0, retry_backoff=0.0))
    return PlaylistService(client, page_size=2)


def add_page(fixture: dict, status: int = 200) -> None:
    responses.add(responses.POST, URL, json=fixture, status=status)


@responses.activate
def test_get_tracks_single_page(service: PlaylistService, load_fixture) -> None:
    add_page(load_fixture("playlist_page1.json"))
    pl = service.get_tracks("18120707017", limit=500, offset=0)
    assert pl.name == "正太"
    assert pl.song_count == 3
    assert len(pl.songs) == 2
    body = json.loads(responses.calls[0].request.body)
    assert body["id"] == "18120707017"
    assert body["limit"] == 500
    assert body["offset"] == 0
    assert "timestamp" in body and "ip" in body


@responses.activate
def test_get_all_tracks_paginates_until_song_count(service: PlaylistService, load_fixture) -> None:
    add_page(load_fixture("playlist_page1.json"))
    add_page(load_fixture("playlist_page2.json"))
    pl = service.get_all_tracks(18120707017)
    assert len(pl.songs) == 3
    assert [s.id for s in pl.songs] == [1432544572, 1432544573, 1432544574]
    assert pl.name == "正太"
    assert len(responses.calls) == 2
    second = json.loads(responses.calls[1].request.body)
    assert second["offset"] == 2


@responses.activate
def test_iter_tracks_stops_on_empty_page(service: PlaylistService, load_fixture) -> None:
    add_page(load_fixture("playlist_page1.json"))
    add_page(load_fixture("playlist_page_empty.json"))
    tracks = list(service.iter_tracks("18120707017"))
    assert len(tracks) == 2
    assert len(responses.calls) == 2


@responses.activate
def test_get_all_tracks_empty_playlist(load_fixture) -> None:
    client = SyncMusicClient(MusicDLConfig(ip="1.2.3.4", max_retries=0, retry_backoff=0.0))
    svc = PlaylistService(client, page_size=2)
    add_page(load_fixture("playlist_page_empty.json"))
    pl = svc.get_all_tracks("1")
    assert pl.songs == []
    assert len(responses.calls) == 1


@responses.activate
def test_api_error_propagates(service: PlaylistService) -> None:
    add_page({"code": 404, "data": None})
    with pytest.raises(APIError):
        service.get_tracks("1", limit=10, offset=0)