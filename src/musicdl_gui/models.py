"""Data models for musicdl-gui."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class QueueStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class LogLevel(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class QueueItem:
    song_id: int
    title: str
    singer: str
    playlist: str
    quality: str
    output_path: Path
    status: QueueStatus = QueueStatus.PENDING
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    error: str | None = None
    retry_count: int = 0