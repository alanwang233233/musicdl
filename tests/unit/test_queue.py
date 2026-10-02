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