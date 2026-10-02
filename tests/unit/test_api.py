import pytest
import responses
import asyncio
from musicdl import MusicDLConfig
from musicdl.exceptions import NetworkError, APIError
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


@responses.activate
@pytest.mark.asyncio
async def test_fetch_playlist_network_error_retries(api_client):
    import requests
    def raise_connection_error(request):
        raise requests.ConnectionError("Network error")

    responses.add_callback(
        responses.POST,
        "https://test.example.com/api/playlist_trackall",
        callback=raise_connection_error,
    )
    with pytest.raises(NetworkError):
        await api_client.fetch_playlist("123")
    # Library retries 4 times (max_retries=3) + wrapper retries 4 times
    assert responses.assert_call_count("https://test.example.com/api/playlist_trackall", 16)


@responses.activate
@pytest.mark.asyncio
async def test_fetch_playlist_rate_limit_retries(api_client):
    responses.post(
        "https://test.example.com/api/playlist_trackall",
        json={"code": 429, "message": "Rate limited", "data": {"retryAfter": 0.01}},
    )
    responses.post(
        "https://test.example.com/api/playlist_trackall",
        json={
            "code": 200,
            "data": {
                "id": 123,
                "name": "Test Playlist",
                "coverImage": "https://example.com/cover.jpg",
                "songCount": 0,
                "playCount": 0,
                "description": None,
                "tags": [],
                "creator": {"uid": 1, "avatar": "", "name": "Creator"},
                "songs": [],
            },
        },
    )
    playlist = await api_client.fetch_playlist("123")
    assert playlist.id == 123


@responses.activate
@pytest.mark.asyncio
async def test_fetch_song_info_api_error(api_client):
    responses.post(
        "https://test.example.com/api/getSongInfo",
        json={"code": 404, "message": "Not found"},
    )
    with pytest.raises(APIError) as exc:
        await api_client.fetch_song_info(999)
    assert exc.value.code == 404


@responses.activate
@pytest.mark.asyncio
async def test_get_song_url_api_error(api_client):
    responses.post(
        "https://test.example.com/api/getSongUrl",
        json={"code": 500, "message": "Server error"},
    )
    with pytest.raises(APIError) as exc:
        await api_client.get_song_url(999)
    assert exc.value.code == 500


@responses.activate
@pytest.mark.asyncio
async def test_close_cleans_up_client(api_client):
    responses.post(
        "https://test.example.com/api/playlist_trackall",
        json={
            "code": 200,
            "data": {
                "id": 123,
                "name": "Test Playlist",
                "coverImage": "https://example.com/cover.jpg",
                "songCount": 0,
                "playCount": 0,
                "description": None,
                "tags": [],
                "creator": {"uid": 1, "avatar": "", "name": "Creator"},
                "songs": [],
            },
        },
    )
    await api_client.fetch_playlist("123")
    api_client.close()
    assert api_client._client is None