"""Regression tests for QueueTable display updates."""

from pathlib import Path

from musicdl_gui.components.queue_table import QueueRow
from musicdl_gui.models import QueueItem, QueueStatus
from musicdl_gui.queue import DownloadQueue


def _item(**overrides) -> QueueItem:
    defaults = {
        "song_id": 1,
        "title": "Song",
        "singer": "Singer",
        "playlist": "",
        "quality": "standard",
        "output_path": Path("/tmp/song.mp3"),
    }
    defaults.update(overrides)
    return QueueItem(**defaults)


def _noop(*_args):
    return None


def test_row_rebuilds_when_item_mutates_in_place():
    """queue.get_items() 返回同一批可变对象:状态在对象上原地变化时行必须重建。

    此前的实现拿对象与自身比较(update_item 收到的就是 row.item 本身),
    永远判定"未变化"导致 Queue 页显示完全冻结。
    """
    item = _item()
    row = QueueRow(item, _noop, _noop, 1)
    first_content = row.content

    item.status = QueueStatus.DOWNLOADING
    item.progress = 0.5
    item.downloaded_bytes = 500
    row.update_item(item, 1)

    assert row.content is not first_content
    assert row._snapshot == (QueueStatus.DOWNLOADING, 0.5, 500, 0, 1)


def test_row_skips_rebuild_when_display_state_unchanged():
    item = _item()
    row = QueueRow(item, _noop, _noop, 1)
    first_content = row.content

    row.update_item(item, 1)

    assert row.content is first_content


def test_row_rebuilds_on_index_change():
    item = _item()
    row = QueueRow(item, _noop, _noop, 1)
    first_content = row.content

    row.update_item(item, 2)

    assert row.content is not first_content


def test_row_snapshot_tracks_progress_completion():
    item = _item()
    row = QueueRow(item, _noop, _noop, 1)

    item.status = QueueStatus.COMPLETED
    item.progress = 1.0
    row.update_item(item, 1)
    completed_content = row.content

    # 值不再变化时不得反复重建
    row.update_item(item, 1)
    assert row.content is completed_content


def test_remove_item_by_identity_keeps_duplicate_entries(tmp_path):
    """重复入队的同一首歌是两个独立条目:按身份删除不应误删另一条。"""
    queue = DownloadQueue(queue_file=tmp_path / "queue.json")
    a = _item(output_path=Path("/tmp/a.mp3"))
    b = _item(output_path=Path("/tmp/b.mp3"))
    queue.add_item(a)
    queue.add_item(b)

    queue.remove_item(b)

    remaining = queue.get_items()
    assert len(remaining) == 1
    assert remaining[0] is a


def test_remove_item_by_song_id_still_supported(tmp_path):
    """按 song_id(int)删除的旧用法保持兼容。"""
    queue = DownloadQueue(queue_file=tmp_path / "queue.json")
    a = _item()
    duplicate = _item(output_path=Path("/tmp/b.mp3"))
    queue.add_item(a)
    queue.add_item(duplicate)

    queue.remove_item(1)

    assert queue.get_items() == []
