from musicdl_gui.models import QueueItem, QueueStatus, LogLevel


def test_queue_item_creation():
    item = QueueItem(
        song_id=123,
        title="Test Song",
        singer="Test Singer",
        playlist="Test Playlist",
        quality="standard",
        output_path="/tmp/test.mp3",
    )
    assert item.song_id == 123
    assert item.status == QueueStatus.PENDING
    assert item.progress == 0.0


def test_queue_status_enum():
    assert QueueStatus.PENDING.value == "pending"
    assert QueueStatus.DOWNLOADING.value == "downloading"
    assert QueueStatus.COMPLETED.value == "completed"
    assert QueueStatus.FAILED.value == "failed"
    assert QueueStatus.SKIPPED.value == "skipped"


def test_log_level_enum():
    assert LogLevel.ERROR.value == "ERROR"
    assert LogLevel.WARNING.value == "WARNING"
    assert LogLevel.INFO.value == "INFO"