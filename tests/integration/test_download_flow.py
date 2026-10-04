import asyncio

import pytest
import responses

from musicdl import Playlist, PlaylistCreator, PlaylistTrack
from musicdl_gui.config import ConfigManager
from musicdl_gui.models import QueueStatus
from musicdl_gui.queue import DownloadQueue


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
async def test_full_download_flow(tmp_path, mock_playlist, monkeypatch):
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

    # 真正执行下载:轮询等待队列处理完成(下载运行在 to_thread 线程中)
    queue.start()
    for _ in range(200):
        await asyncio.sleep(0.05)
        statuses = [i.status for i in queue.get_items()]
        if all(s in (QueueStatus.COMPLETED, QueueStatus.FAILED) for s in statuses):
            break

    items = queue.get_items()
    statuses = [i.status for i in items]
    assert all(s == QueueStatus.COMPLETED for s in statuses), statuses
    assert all(i.error is None for i in items)

    # 文件确实落盘且非空
    out1 = tmp_path / "music" / "Singer 1 - Song 1.mp3"
    out2 = tmp_path / "music" / "Singer 2 - Song 2.mp3"
    assert out1.exists() and out1.stat().st_size > 0
    assert out2.exists() and out2.stat().st_size > 0

    # mock 的 API 端点被真实消费(getSongUrl + 音频流,每首歌一次)
    assert len(responses.calls) >= 4