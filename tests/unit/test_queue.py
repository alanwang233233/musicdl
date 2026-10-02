import asyncio
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.models import QueueItem, QueueStatus


@pytest.fixture
def queue():
    with TemporaryDirectory() as tmpdir:
        queue_file = Path(tmpdir) / "queue.json"
        yield DownloadQueue(queue_file=queue_file)


def test_add_item(queue):
    item = QueueItem(
        song_id=1,
        title="Test",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test.mp3"),
    )
    queue.add_item(item)
    assert len(queue.get_items()) == 1
    assert queue.get_items()[0].song_id == 1


def test_add_playlist(queue):
    from musicdl import Playlist, PlaylistCreator
    playlist = Playlist(
        id=123,
        name="Test Playlist",
        cover_image="",
        song_count=2,
        play_count=0,
        creator=PlaylistCreator(uid=1, avatar="", name="Creator"),
        songs=[],
    )
    queue.add_playlist(playlist, "standard", Path("/tmp"))
    assert len(queue.get_items()) == 0  # No songs in playlist


def test_add_playlist_with_songs(queue):
    from musicdl import Playlist, PlaylistCreator, PlaylistTrack
    playlist = Playlist(
        id=123,
        name="Test Playlist",
        cover_image="",
        song_count=2,
        play_count=0,
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
    queue.add_playlist(playlist, "standard", Path("/tmp"))
    assert len(queue.get_items()) == 2
    assert queue.get_items()[0].song_id == 1
    assert queue.get_items()[1].song_id == 2


def test_remove_item(queue):
    item = QueueItem(
        song_id=1,
        title="Test",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test.mp3"),
    )
    queue.add_item(item)
    queue.remove_item(1)
    assert len(queue.get_items()) == 0


def test_clear_completed(queue):
    item1 = QueueItem(
        song_id=1,
        title="Test1",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test1.mp3"),
        status=QueueStatus.COMPLETED,
    )
    item2 = QueueItem(
        song_id=2,
        title="Test2",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test2.mp3"),
        status=QueueStatus.PENDING,
    )
    queue.add_item(item1)
    queue.add_item(item2)
    queue.clear_completed()
    assert len(queue.get_items()) == 1
    assert queue.get_items()[0].song_id == 2


def test_clear_completed_removes_skipped(queue):
    item1 = QueueItem(
        song_id=1,
        title="Test1",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test1.mp3"),
        status=QueueStatus.SKIPPED,
    )
    item2 = QueueItem(
        song_id=2,
        title="Test2",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test2.mp3"),
        status=QueueStatus.PENDING,
    )
    queue.add_item(item1)
    queue.add_item(item2)
    queue.clear_completed()
    assert len(queue.get_items()) == 1
    assert queue.get_items()[0].song_id == 2


def test_get_items_returns_copy(queue):
    item = QueueItem(
        song_id=1,
        title="Test",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test.mp3"),
    )
    queue.add_item(item)
    items = queue.get_items()
    items.clear()
    assert len(queue.get_items()) == 1


def test_retry_item(queue):
    item = QueueItem(
        song_id=1,
        title="Test",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test.mp3"),
        status=QueueStatus.FAILED,
        error="Some error",
    )
    queue.add_item(item)
    queue.retry_item(1)
    assert queue.get_items()[0].status == QueueStatus.PENDING
    assert queue.get_items()[0].error is None
    assert queue.get_items()[0].retry_count == 1


def test_retry_item_only_failed(queue):
    item = QueueItem(
        song_id=1,
        title="Test",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test.mp3"),
        status=QueueStatus.PENDING,
    )
    queue.add_item(item)
    queue.retry_item(1)
    assert queue.get_items()[0].status == QueueStatus.PENDING
    assert queue.get_items()[0].retry_count == 0


def test_save_and_load_queue(tmp_path):
    queue_file = tmp_path / "queue.json"
    queue = DownloadQueue(queue_file=queue_file)
    item = QueueItem(
        song_id=1,
        title="Test",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test.mp3"),
        status=QueueStatus.COMPLETED,
        progress=1.0,
        downloaded_bytes=1000,
        total_bytes=1000,
        error=None,
        retry_count=0,
    )
    queue.add_item(item)
    queue2 = DownloadQueue(queue_file=queue_file)
    loaded = queue2.get_items()
    assert len(loaded) == 1
    assert loaded[0].song_id == 1
    assert loaded[0].status == QueueStatus.COMPLETED
    assert loaded[0].progress == 1.0
    assert loaded[0].downloaded_bytes == 1000
    assert loaded[0].total_bytes == 1000
    assert loaded[0].retry_count == 0


def test_callbacks(queue):
    events = []
    def on_progress(item):
        events.append(("progress", item.song_id))
    def on_complete(item):
        events.append(("complete", item.song_id))
    def on_error(item, exc):
        events.append(("error", item.song_id))
    def on_status_change(item, status):
        events.append(("status", item.song_id, status))

    queue._on_progress = on_progress
    queue._on_complete = on_complete
    queue._on_error = on_error
    queue._on_status_change = on_status_change

    item = QueueItem(
        song_id=1,
        title="Test",
        singer="Singer",
        playlist="Playlist",
        quality="standard",
        output_path=Path("/tmp/test.mp3"),
    )
    queue.add_item(item)

    queue._notify_progress(item)
    queue._notify_complete(item)
    queue._notify_error(item, Exception("test"))
    queue._notify_status_change(item, QueueStatus.DOWNLOADING)

    assert len(events) == 4
    assert events[0] == ("progress", 1)
    assert events[1] == ("complete", 1)
    assert events[2][0] == "error"
    assert events[3] == ("status", 1, QueueStatus.DOWNLOADING)


@pytest.mark.asyncio
async def test_process_queue_success(tmp_path, monkeypatch):
    queue_file = tmp_path / "queue.json"
    queue = DownloadQueue(queue_file=queue_file)

    from musicdl import Playlist, PlaylistCreator, PlaylistTrack
    from musicdl_gui.config import ConfigManager
    playlist = Playlist(
        id=123,
        name="Test Playlist",
        cover_image="",
        song_count=1,
        play_count=0,
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
        ],
    )
    queue.add_playlist(playlist, "standard", tmp_path / "music")

    config_mgr = ConfigManager()
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    config_mgr.save({
        "base_url": "https://test.example.com",
        "ip": "127.0.0.1",
        "timeout": 5.0,
        "max_retries": 1,
        "output_dir": str(tmp_path / "music"),
        "default_level": "standard",
    })

    from musicdl import SyncMusicClient, SongService, PlaylistService
    from musicdl.services.download import DownloadService

    original_download = DownloadService.download_song
    call_count = {"count": 0}

    def mock_download(self, song_id, level, output):
        call_count["count"] += 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake mp3 data")

    monkeypatch.setattr(DownloadService, "download_song", mock_download)

    queue.start()
    await asyncio.sleep(0.5)
    queue.stop()

    await asyncio.sleep(0.1)
    assert call_count["count"] == 1
    items = queue.get_items()
    assert items[0].status == QueueStatus.COMPLETED
    assert items[0].progress == 1.0


def test_sanitize_filename():
    from musicdl_gui.queue import _sanitize_filename

    # Test slash replacement
    assert _sanitize_filename("a/b") == "a;b"
    assert _sanitize_filename("a/b/c") == "a;b;c"
    assert _sanitize_filename("/a/b/") == ";a;b;"

    # Test other illegal characters replaced with underscore
    assert _sanitize_filename('a:b') == "a_b"
    assert _sanitize_filename('a*b') == "a_b"
    assert _sanitize_filename('a?b') == "a_b"
    assert _sanitize_filename('a"b') == "a_b"
    assert _sanitize_filename('a<b') == "a_b"
    assert _sanitize_filename('a>b') == "a_b"
    assert _sanitize_filename('a|b') == "a_b"
    assert _sanitize_filename('a\0b') == "a_b"

    # Test mixed
    assert _sanitize_filename('a/b:c') == "a;b_c"

    # Test whitespace trimming
    assert _sanitize_filename("  a/b  ") == "a;b"