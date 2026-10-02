import pytest
import responses
from musicdl import MusicDLConfig
from musicdl_gui.api import ApiClient


@pytest.fixture
def api_client():
    config = MusicDLConfig(ip="127.0.0.1", base_url="https://test.example.com")
    return ApiClient(config)


@responses.activate
@pytest.mark.asyncio
async def test_fetch_playlist_success(api_client):
    responses.post(
        "https://test.example.com/api/playlist_trackall",
        json={
            "code": 200,
            "data": {
                "id": 123,
                "name": "Test Playlist",
                "coverImage": "https://example.com/cover.jpg",
                "songCount": 2,
                "playCount": 100,
                "description": None,
                "tags": [],
                "creator": {"uid": 1, "avatar": "", "name": "Creator"},
                "songs": [],
            },
        },
    )
    playlist = await api_client.fetch_playlist("123")
    assert playlist.id == 123
    assert playlist.name == "Test Playlist"


@responses.activate
@pytest.mark.asyncio
async def test_fetch_song_info_success(api_client):
    responses.post(
        "https://test.example.com/api/getSongInfo",
        json={
            "code": 200,
            "data": {
                "id": 456,
                "name": "Test Song",
                "free": True,
                "album": "Test Album",
                "singer": "Test Singer",
                "picimg": "https://example.com/pic.jpg",
                "duration": "03:30",
                "copyright": 0,
                "time": "2024/01/01 00:00:00",
            },
        },
    )
    info = await api_client.fetch_song_info(456)
    assert info.id == 456
    assert info.name == "Test Song"


@responses.activate
@pytest.mark.asyncio
async def test_get_song_url_success(api_client):
    responses.post(
        "https://test.example.com/api/getSongUrl",
        json={
            "code": 200,
            "data": {
                "id": 456,
                "url": "https://example.com/song.mp3",
                "br": 320000,
                "level": "standard",
                "size": 5000000,
                "md5": "abc123",
                "channelLayout": None,
                "effects": None,
                "cookie": {"id": "1", "label": "test", "index": 0},
                "time": "2024/01/01 00:00:00",
            },
        },
    )
    url = await api_client.get_song_url(456, level="standard")
    assert url.url == "https://example.com/song.mp3"
    assert url.br == 320000