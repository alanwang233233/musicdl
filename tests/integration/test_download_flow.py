import pytest
import responses
from pathlib import Path
from musicdl import MusicDLConfig, Playlist, PlaylistCreator, PlaylistTrack
from musicdl_gui.config import ConfigManager
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.models import QueueItem, QueueStatus


@pytest.fixture
def mock_playlist():
    return Playlist(
        id=123,
        name="Test Playlist",
        cover_image="https://example.com/cover.jpg",
        song_count=2,
        play_count=100,
        creator=PlaylistCreator(uid=1, avatar="", name="Creator"),
        songs=[
            PlaylistTrack(
                id=1,
                name="Song 1",
                free=True,
                album="Album",
                singer="Singer 1",
                picimg="",
                duration="03:00",
                copyright=0,
                time="2024/01/01 00:00:00",
            ),
            PlaylistTrack(
                id=2,
                name="Song 2",
                free=True,
                album="Album",
                singer="Singer 2",
                picimg="",
                duration="04:00",
                copyright=0,
                time="2024/01/01 00:00:00",
            ),
        ],
    )


@responses.activate
def test_full_download_flow(tmp_path, mock_playlist, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("musicdl_gui.queue.DEFAULT_QUEUE_FILE", tmp_path / "queue.json")

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
                "songs": [
                    {
                        "id": 1,
                        "name": "Song 1",
                        "free": True,
                        "album": "Album",
                        "singer": "Singer 1",
                        "picimg": "",
                        "duration": "03:00",
                        "copyright": 0,
                        "time": "2024/01/01 00:00:00",
                    },
                    {
                        "id": 2,
                        "name": "Song 2",
                        "free": True,
                        "album": "Album",
                        "singer": "Singer 2",
                        "picimg": "",
                        "duration": "04:00",
                        "copyright": 0,
                        "time": "2024/01/01 00:00:00",
                    },
                ],
            },
        },
    )

    responses.post(
        "https://test.example.com/api/getSongInfo",
        json={
            "code": 200,
            "data": {
                "id": 1,
                "name": "Song 1",
                "free": True,
                "album": "Album",
                "singer": "Singer 1",
                "picimg": "",
                "duration": "03:00",
                "copyright": 0,
                "time": "2024/01/01 00:00:00",
            },
        },
    )

    responses.post(
        "https://test.example.com/api/getSongUrl",
        json={
            "code": 200,
            "data": {
                "id": 1,
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

    responses.get(
        "https://example.com/song.mp3",
        body=b"fake mp3 data",
        content_type="audio/mpeg",
    )

    config_mgr = ConfigManager()
    config_mgr.save({
        "base_url": "https://test.example.com",
        "ip": "127.0.0.1",
        "timeout": 5.0,
        "max_retries": 1,
        "output_dir": str(tmp_path / "music"),
        "default_level": "standard",
    })

    queue = DownloadQueue()
    queue.add_playlist(mock_playlist, "standard", tmp_path / "music")

    assert len(queue.get_items()) == 2
    assert all(i.status == QueueStatus.PENDING for i in queue.get_items())