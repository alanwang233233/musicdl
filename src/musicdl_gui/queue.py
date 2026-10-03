"""Serial download queue management."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from pathlib import Path

from musicdl import DownloadService, Playlist, PlaylistService, SongService
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.models import QueueItem, QueueStatus

DEFAULT_QUEUE_FILE = Path.home() / ".config" / "musicdl-gui" / "queue.json"

_ILLEGAL_CHARS = re.compile(r'[\\:*?"<>|\x00-\x1f]')


def _sanitize_filename(value: str) -> str:
    """Replace characters that are illegal in file names with ``_``,
    but replace ``/`` with ``;`` to preserve readability."""
    return _ILLEGAL_CHARS.sub("_", value.replace("/", ";")).strip()


class DownloadQueue:
    """Serial download queue - processes one item at a time."""

    def __init__(self, queue_file: Path | None = None) -> None:
        self._queue_file = queue_file or DEFAULT_QUEUE_FILE
        self._items: list[QueueItem] = []
        self._current_item: QueueItem | None = None
        self._is_running = False
        self._task: asyncio.Task | None = None
        self._error_log = ErrorLog()
        self._load_queue()

        self._on_progress: Callable[[QueueItem], None] | None = None
        self._on_complete: Callable[[QueueItem], None] | None = None
        self._on_error: Callable[[QueueItem, Exception], None] | None = None
        self._on_status_change: Callable[[QueueItem, QueueStatus], None] | None = None

    def add_item(self, item: QueueItem) -> None:
        self._items.append(item)
        self._save_queue()

    def add_playlist(self, playlist: Playlist, quality: str, output_dir: Path) -> None:
        for idx, track in enumerate(playlist.songs, start=1):
            singer = _sanitize_filename(track.singer)
            title = _sanitize_filename(track.name)
            item = QueueItem(
                song_id=track.id,
                title=track.name,
                singer=track.singer,
                playlist=playlist.name,
                quality=quality,
                output_path=output_dir / f"{singer} - {title}.mp3",
                picimg=track.picimg or "",
            )
            self._items.append(item)
        self._save_queue()

    def add_playlist_single_track(self, playlist: Playlist, track, quality: str, output_dir: Path) -> None:
        """Add a single track from a playlist to the queue."""
        singer = _sanitize_filename(track.singer)
        title = _sanitize_filename(track.name)
        item = QueueItem(
            song_id=track.id,
            title=track.name,
            singer=track.singer,
            playlist=playlist.name,
            quality=quality,
            output_path=output_dir / f"{singer} - {title}.mp3",
            picimg=track.picimg or "",
        )
        self._items.append(item)
        self._save_queue()

    def remove_item(self, song_id: int) -> None:
        self._items = [i for i in self._items if i.song_id != song_id]
        self._save_queue()

    def clear_completed(self) -> None:
        self._items = [
            i for i in self._items
            if i.status not in (QueueStatus.COMPLETED, QueueStatus.SKIPPED)
        ]
        self._save_queue()

    def clear_all(self) -> None:
        """Clear all items and remove the queue file."""
        self._items.clear()
        if self._queue_file.exists():
            self._queue_file.unlink()

    def get_items(self) -> list[QueueItem]:
        return self._items.copy()

    def start(self) -> None:
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.create_task(self._process_queue())

    def stop(self) -> None:
        self._is_running = False
        if self._task:
            self._task.cancel()

    async def _process_queue(self) -> None:
        from musicdl_gui.config import ConfigManager
        config_mgr = ConfigManager()
        config = config_mgr.get_config()

        while self._is_running:
            pending = [i for i in self._items if i.status == QueueStatus.PENDING]
            if not pending:
                break

            item = pending[0]
            self._current_item = item
            item.status = QueueStatus.DOWNLOADING
            self._notify_status_change(item, QueueStatus.DOWNLOADING)

            try:
                from musicdl import SyncMusicClient
                with SyncMusicClient(config) as client:
                    song_service = SongService(client)
                    playlist_service = PlaylistService(client)

                    def progress_callback(downloaded: int, total: int, current_item=item) -> None:
                        current_item.downloaded_bytes = downloaded
                        current_item.total_bytes = total
                        if total > 0:
                            current_item.progress = downloaded / total
                        self._notify_progress(current_item)

                    downloader = DownloadService(
                        song_service,
                        playlist_service,
                        output_dir=item.output_path.parent,
                        progress_callback=progress_callback,
                    )
                    await asyncio.to_thread(
                        downloader.download_song,
                        item.song_id,
                        level=item.quality,
                        output=item.output_path,
                    )
                item.status = QueueStatus.COMPLETED
                item.progress = 1.0
                self._notify_complete(item)
            except Exception as e:  # noqa: BLE001
                item.status = QueueStatus.FAILED
                item.error = str(e)
                self._error_log.log_exception(e, "download_queue", {"song_id": item.song_id})
                self._notify_error(item, e)

            self._save_queue()

        self._is_running = False
        self._current_item = None

    def retry_item(self, song_id: int) -> None:
        for item in self._items:
            if item.song_id == song_id and item.status == QueueStatus.FAILED:
                item.status = QueueStatus.PENDING
                item.error = None
                item.retry_count += 1
        self._save_queue()

    def _save_queue(self) -> None:
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "song_id": i.song_id,
                "title": i.title,
                "singer": i.singer,
                "playlist": i.playlist,
                "quality": i.quality,
                "output_path": str(i.output_path),
                "status": i.status.value,
                "progress": i.progress,
                "downloaded_bytes": i.downloaded_bytes,
                "total_bytes": i.total_bytes,
                "picimg": i.picimg,
                "retry_count": i.retry_count,
            }
            for i in self._items
        ]
        with open(self._queue_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_queue(self) -> None:
        if self._queue_file.exists():
            with open(self._queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._items = [
                QueueItem(
                    song_id=i["song_id"],
                    title=i["title"],
                    singer=i["singer"],
                    playlist=i["playlist"],
                    quality=i["quality"],
                    output_path=Path(i["output_path"]),
                    status=QueueStatus(i["status"]),
                    progress=i.get("progress", 0.0),
                    downloaded_bytes=i.get("downloaded_bytes", 0),
                    total_bytes=i.get("total_bytes", 0),
                    error=i.get("error"),
                    retry_count=i.get("retry_count", 0),
                    picimg=i.get("picimg", ""),
                )
                for i in data
            ]

    def _notify_progress(self, item: QueueItem) -> None:
        if self._on_progress:
            self._on_progress(item)

    def _notify_complete(self, item: QueueItem) -> None:
        if self._on_complete:
            self._on_complete(item)

    def _notify_error(self, item: QueueItem, error: Exception) -> None:
        if self._on_error:
            self._on_error(item, error)

    def _notify_status_change(self, item: QueueItem, status: QueueStatus) -> None:
        if self._on_status_change:
            self._on_status_change(item, status)