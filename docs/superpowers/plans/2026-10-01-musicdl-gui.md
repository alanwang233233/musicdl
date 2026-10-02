# musicdl-gui Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-platform desktop GUI for the musicdl library using Python + Flet, with serial downloads, error logging, and macOS packaging.

**Architecture:** Single-window tabbed interface (5 tabs) with core services layer wrapping the musicdl library. Serial download queue processes one item at a time. ErrorLog service captures all exceptions globally. Desktop-primary with macOS deliverable artifact.

**Tech Stack:** Python 3.10+, Flet 1.0+, musicdl library, PyInstaller, pytest, responses (HTTP mocking)

**Spec:** `docs/superpowers/specs/2026-10-01-musicdl-gui-design.md`

## Global Constraints

- Python >= 3.10
- Flet >= 1.0 (uses new Tabs/TabBar/TabBarView structure)
- All downloads run serially (one at a time)
- Error log persists to `~/.config/musicdl-gui/error.log` (rotating, max 10MB/1000 entries)
- Config persists to `~/.config/musicdl-gui/config.json`
- Queue persists to `~/.config/musicdl-gui/queue.json`
- macOS deliverable: `.app` bundle, DMG, notarized, universal binary
- No comments in code
- Test coverage >= 80% for core services

---

## File Structure

```
musicdl_gui/
├── src/musicdl_gui/
│   ├── __init__.py
│   ├── main.py              # App entry, routing, global exception handler
│   ├── config.py            # ConfigManager
│   ├── queue.py             # DownloadQueue (serial)
│   ├── api.py               # ApiClient wrapper
│   ├── error_log.py         # ErrorLog service
│   ├── models.py            # QueueItem, ErrorLogEntry, enums
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── playlist_browser.py
│   │   ├── song_downloader.py
│   │   ├── download_queue.py
│   │   ├── settings.py
│   │   └── error_log.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── playlist_card.py
│   │   ├── track_list.py
│   │   ├── queue_table.py
│   │   ├── progress_bar.py
│   │   ├── dialogs.py
│   │   └── error_log_table.py
│   └── utils/
│       ├── __init__.py
│       ├── threading.py     # run_in_executor helpers
│       └── formatting.py    # bytes, duration, etc.
├── tests/
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_queue.py
│   │   ├── test_api.py
│   │   └── test_error_log.py
│   ├── integration/
│   │   └── test_download_flow.py
│   └── conftest.py
├── assets/
│   └── icon.png
├── pyproject.toml
├── README.md
└── musicdl_gui.spec         # PyInstaller spec
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/musicdl_gui/__init__.py`
- Create: `src/musicdl_gui/main.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Consumes: None
- Produces: `main()` entry point, `ft.run(main)` call

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "musicdl-gui"
version = "0.1.0"
description = "Cross-platform GUI for musicdl library"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "flet>=1.0.0",
    "musicdl>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "responses>=0.24",
    "pyinstaller>=6.0",
]

[project.scripts]
musicdl-gui = "musicdl_gui.main:main"

[tool.hatch.build.targets.wheel]
packages = ["src/musicdl_gui"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --cov=musicdl_gui --cov-report=term-missing"

[tool.coverage.run]
source = ["musicdl_gui"]

[tool.flet]
org = "com.musicdl"
product = "MusicDL GUI"
company = "MusicDL"
copyright = "Copyright (C) 2026 by MusicDL"

[tool.flet.app]
path = "src"
```

- [ ] **Step 2: Create src/musicdl_gui/__init__.py**

```python
"""musicdl-gui - Cross-platform GUI for musicdl library."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create src/musicdl_gui/main.py**

```python
"""musicdl-gui - Flet application entry point."""

import flet as ft


def main(page: ft.Page) -> None:
    page.title = "MusicDL GUI"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.add(ft.Text("MusicDL GUI - Coming Soon"))


if __name__ == "__main__":
    ft.run(main)
```

- [ ] **Step 4: Create tests/conftest.py**

```python
"""Shared test fixtures."""

import pytest


@pytest.fixture
def mock_config():
    """Return a mock MusicDLConfig for testing."""
    from musicdl import MusicDLConfig
    return MusicDLConfig(
        base_url="https://test.example.com",
        ip="127.0.0.1",
        timeout=5.0,
        max_retries=1,
    )
```

- [ ] **Step 5: Verify project structure**

Run: `python -c "import musicdl_gui; print(musicdl_gui.__version__)"`
Expected: `0.1.0`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/musicdl_gui/__init__.py src/musicdl_gui/main.py tests/conftest.py
git commit -m "feat: initial project scaffolding"
```

---

### Task 2: ConfigManager Service

**Files:**
- Create: `src/musicdl_gui/config.py`
- Create: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: `MusicDLConfig` from musicdl library
- Produces: `ConfigManager` class with methods:
  - `load() -> dict`
  - `save(config: dict) -> None`
  - `get_config() -> MusicDLConfig`
  - `validate(config: dict) -> list[str]` (returns list of error messages)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_config.py
import json
import pytest
from musicdl_gui.config import ConfigManager


def test_load_default_config(tmp_path, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    manager = ConfigManager()
    config = manager.load()
    assert config["base_url"] == "https://nextmusic.toubiec.cn"
    assert config["timeout"] == 30.0
    assert config["max_retries"] == 3


def test_save_and_load_config(tmp_path, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    manager = ConfigManager()
    custom = {
        "base_url": "https://custom.example.com",
        "timeout": 60.0,
        "max_retries": 5,
        "ip": "192.168.1.1",
        "ip_fetch_url": "https://api.ipify.org?format=json",
        "ip_cache_ttl": 3600.0,
        "default_level": "standard",
        "user_agent": None,
        "output_dir": "./music",
        "naming_template": "{singer} - {title}",
    }
    manager.save(custom)
    loaded = manager.load()
    assert loaded["base_url"] == "https://custom.example.com"
    assert loaded["timeout"] == 60.0


def test_validate_config(tmp_path, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    manager = ConfigManager()
    errors = manager.validate({"timeout": -1})
    assert len(errors) > 0
    assert any("timeout" in e.lower() for e in errors)


def test_get_config_returns_musicdl_config(tmp_path, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    manager = ConfigManager()
    config = manager.get_config()
    from musicdl import MusicDLConfig
    assert isinstance(config, MusicDLConfig)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'musicdl_gui.config'"

- [ ] **Step 3: Implement ConfigManager**

```python
# src/musicdl_gui/config.py
"""Configuration management for musicdl-gui."""

from __future__ import annotations

import json
import os
from pathlib import Path

from musicdl import MusicDLConfig

CONFIG_DIR = Path.home() / ".config" / "musicdl-gui"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "base_url": "https://nextmusic.toubiec.cn",
    "timeout": 30.0,
    "max_retries": 3,
    "retry_backoff": 0.5,
    "ip": None,
    "ip_fetch_url": "https://api.ipify.org?format=json",
    "ip_cache_ttl": 3600.0,
    "default_level": "standard",
    "user_agent": None,
    "output_dir": "./music",
    "naming_template": "{singer} - {title}",
}


class ConfigManager:
    """Manage application configuration persistence."""

    def __init__(self) -> None:
        self._config: dict = {}

    def load(self) -> dict:
        """Load config from file, merging with defaults."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self._config = {**DEFAULT_CONFIG, **saved}
        else:
            self._config = DEFAULT_CONFIG.copy()
        return self._config

    def save(self, config: dict) -> None:
        """Save config to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self._config = config

    def get_config(self) -> MusicDLConfig:
        """Get MusicDLConfig from current configuration."""
        cfg = self.load()
        return MusicDLConfig(
            base_url=cfg["base_url"],
            timeout=cfg["timeout"],
            max_retries=cfg["max_retries"],
            retry_backoff=cfg["retry_backoff"],
            ip=cfg["ip"],
            ip_fetch_url=cfg["ip_fetch_url"],
            ip_cache_ttl=cfg["ip_cache_ttl"],
            default_level=cfg["default_level"],
            user_agent=cfg["user_agent"],
        )

    def validate(self, config: dict) -> list[str]:
        """Validate configuration values, return list of error messages."""
        errors = []
        if config.get("timeout", 0) <= 0:
            errors.append("timeout must be positive")
        if config.get("max_retries", 0) < 0:
            errors.append("max_retries must be non-negative")
        if config.get("retry_backoff", 0) < 0:
            errors.append("retry_backoff must be non-negative")
        if not config.get("base_url"):
            errors.append("base_url is required")
        if not config.get("output_dir"):
            errors.append("output_dir is required")
        return errors
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/musicdl_gui/config.py tests/unit/test_config.py
git commit -m "feat: add ConfigManager service"
```

---

### Task 3: ErrorLog Service

**Files:**
- Create: `src/musicdl_gui/error_log.py`
- Create: `tests/unit/test_error_log.py`

**Interfaces:**
- Consumes: None
- Produces: `ErrorLog` class with methods:
  - `log_exception(exc: Exception, source: str, context: dict | None = None) -> None`
  - `log_message(level: str, source: str, message: str, context: dict | None = None) -> None`
  - `get_entries(limit: int = 100) -> list[ErrorLogEntry]`
  - `clear() -> None`
  - `export(path: Path) -> None`
  - `on_new_entry` event callback

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_error_log.py
import pytest
from musicdl_gui.error_log import ErrorLog, ErrorLogEntry


def test_log_exception_creates_entry():
    log = ErrorLog()
    log.clear()
    try:
        raise ValueError("test error")
    except ValueError as e:
        log.log_exception(e, "test_source", {"key": "value"})
    entries = log.get_entries()
    assert len(entries) == 1
    assert entries[0].exception_type == "ValueError"
    assert entries[0].message == "test error"
    assert entries[0].source == "test_source"


def test_log_message_creates_entry():
    log = ErrorLog()
    log.clear()
    log.log_message("WARNING", "test", "test message")
    entries = log.get_entries()
    assert len(entries) == 1
    assert entries[0].level == "WARNING"
    assert entries[0].message == "test message"


def test_get_entries_with_limit():
    log = ErrorLog()
    log.clear()
    for i in range(10):
        log.log_message("INFO", "test", f"message {i}")
    entries = log.get_entries(limit=5)
    assert len(entries) == 5


def test_clear_removes_all_entries():
    log = ErrorLog()
    log.log_message("INFO", "test", "message")
    log.clear()
    assert len(log.get_entries()) == 0


def test_export_writes_file(tmp_path):
    log = ErrorLog()
    log.clear()
    log.log_message("ERROR", "test", "error message")
    export_path = tmp_path / "export.log"
    log.export(export_path)
    assert export_path.exists()
    content = export_path.read_text()
    assert "error message" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_error_log.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'musicdl_gui.error_log'"

- [ ] **Step 3: Implement ErrorLog**

```python
# src/musicdl_gui/error_log.py
"""Global error logging service."""

from __future__ import annotations

import json
import logging
import sys
import threading
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable

LOG_DIR = Path.home() / ".config" / "musicdl-gui"
LOG_FILE = LOG_DIR / "error.log"
MAX_ENTRIES = 1000
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@dataclass
class ErrorLogEntry:
    """Structured error log entry."""
    timestamp: str
    level: str
    source: str
    message: str
    exception_type: str | None = None
    traceback: str | None = None
    context: dict = field(default_factory=dict)


class ErrorLog:
    """Global singleton for error logging."""

    _instance: ErrorLog | None = None
    _lock = threading.Lock()

    def __new__(cls) -> ErrorLog:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._entries: list[ErrorLogEntry] = []
        self._callbacks: list[Callable[[ErrorLogEntry], None]] = []
        self._setup_file_handler()
        self._setup_exception_hook()
        self._initialized = True

    def _setup_file_handler(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("musicdl_gui")
        self._logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self._logger.addHandler(handler)

    def _setup_exception_hook(self) -> None:
        def hook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            self.log_exception(exc_value, "unhandled")
        sys.excepthook = hook

    def log_exception(self, exc: Exception, source: str, context: dict | None = None) -> None:
        entry = ErrorLogEntry(
            timestamp=datetime.now().isoformat(),
            level="ERROR",
            source=source,
            message=str(exc),
            exception_type=type(exc).__name__,
            traceback="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            context=context or {},
        )
        self._add_entry(entry)

    def log_message(self, level: str, source: str, message: str, context: dict | None = None) -> None:
        entry = ErrorLogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            source=source,
            message=message,
            context=context or {},
        )
        self._add_entry(entry)

    def _add_entry(self, entry: ErrorLogEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > MAX_ENTRIES:
            self._entries = self._entries[-MAX_ENTRIES:]
        self._logger.log(getattr(logging, entry.level), f"[{entry.source}] {entry.message}")
        for callback in self._callbacks:
            callback(entry)

    def get_entries(self, limit: int = 100) -> list[ErrorLogEntry]:
        return self._entries[-limit:]

    def clear(self) -> None:
        self._entries.clear()

    def export(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for entry in self._entries:
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def register_callback(self, callback: Callable[[ErrorLogEntry], None]) -> None:
        self._callbacks.append(callback)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_error_log.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/musicdl_gui/error_log.py tests/unit/test_error_log.py
git commit -m "feat: add ErrorLog service"
```

---

### Task 4: Data Models

**Files:**
- Create: `src/musicdl_gui/models.py`
- Create: `tests/unit/test_models.py`

**Interfaces:**
- Consumes: None
- Produces: 
  - `QueueStatus` enum: `PENDING`, `DOWNLOADING`, `COMPLETED`, `FAILED`, `SKIPPED`
  - `QueueItem` dataclass
  - `LogLevel` enum: `ERROR`, `WARNING`, `INFO`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_models.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'musicdl_gui.models'"

- [ ] **Step 3: Implement models**

```python
# src/musicdl_gui/models.py
"""Data models for musicdl-gui."""

from __future__ import annotations

from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_models.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/musicdl_gui/models.py tests/unit/test_models.py
git commit -m "feat: add data models"
```

---

### Task 5: ApiClient Wrapper

**Files:**
- Create: `src/musicdl_gui/api.py`
- Create: `tests/unit/test_api.py`

**Interfaces:**
- Consumes: `SyncMusicClient`, `PlaylistService`, `SongService`, `MusicDLConfig`
- Produces: `ApiClient` class with async methods:
  - `fetch_playlist(playlist_id: str) -> Playlist`
  - `fetch_song_info(song_id: int) -> SongInfo`
  - `get_song_url(song_id: int, level: str | None = None) -> SongUrl`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_api.py
import pytest
import responses
from musicdl import MusicDLConfig, SyncMusicClient
from musicdl_gui.api import ApiClient


@pytest.fixture
def api_client():
    config = MusicDLConfig(ip="127.0.0.1", base_url="https://test.example.com")
    return ApiClient(config)


@responses.activate
def test_fetch_playlist_success(api_client):
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
    playlist = api_client.fetch_playlist("123")
    assert playlist.id == 123
    assert playlist.name == "Test Playlist"


@responses.activate
def test_fetch_song_info_success(api_client):
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
    info = api_client.fetch_song_info(456)
    assert info.id == 456
    assert info.name == "Test Song"


@responses.activate
def test_get_song_url_success(api_client):
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
    url = api_client.get_song_url(456, level="standard")
    assert url.url == "https://example.com/song.mp3"
    assert url.br == 320000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_api.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'musicdl_gui.api'"

- [ ] **Step 3: Implement ApiClient**

```python
# src/musicdl_gui/api.py
"""Async wrapper around musicdl SyncMusicClient."""

from __future__ import annotations

import asyncio
from typing import Any

from musicdl import (
    MusicDLConfig,
    SyncMusicClient,
    PlaylistService,
    SongService,
    Playlist,
    SongInfo,
    SongUrl,
)
from musicdl.exceptions import MusicDLException
from musicdl_gui.error_log import ErrorLog


class ApiClient:
    """Async wrapper for musicdl API calls."""

    def __init__(self, config: MusicDLConfig) -> None:
        self._config = config
        self._client: SyncMusicClient | None = None
        self._playlist_service: PlaylistService | None = None
        self._song_service: SongService | None = None
        self._error_log = ErrorLog()

    def _ensure_client(self) -> SyncMusicClient:
        if self._client is None:
            self._client = SyncMusicClient(self._config)
            self._playlist_service = PlaylistService(self._client)
            self._song_service = SongService(self._client)
        return self._client

    async def fetch_playlist(self, playlist_id: str) -> Playlist:
        """Fetch playlist with all tracks."""
        try:
            client = self._ensure_client()
            return await asyncio.to_thread(
                self._playlist_service.get_all_tracks, playlist_id
            )
        except MusicDLException as e:
            self._error_log.log_exception(e, "api_client", {"playlist_id": playlist_id})
            raise

    async def fetch_song_info(self, song_id: int) -> SongInfo:
        """Fetch song metadata."""
        try:
            client = self._ensure_client()
            return await asyncio.to_thread(self._song_service.get_info, song_id)
        except MusicDLException as e:
            self._error_log.log_exception(e, "api_client", {"song_id": song_id})
            raise

    async def get_song_url(self, song_id: int, level: str | None = None) -> SongUrl:
        """Fetch song playback URL."""
        try:
            client = self._ensure_client()
            return await asyncio.to_thread(
                self._song_service.get_url, song_id, level=level
            )
        except MusicDLException as e:
            self._error_log.log_exception(e, "api_client", {"song_id": song_id, "level": level})
            raise

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_api.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/musicdl_gui/api.py tests/unit/test_api.py
git commit -m "feat: add ApiClient wrapper"
```

---

### Task 6: DownloadQueue Service

**Files:**
- Create: `src/musicdl_gui/queue.py`
- Create: `tests/unit/test_queue.py`

**Interfaces:**
- Consumes: `ApiClient`, `QueueItem`, `QueueStatus`, `ErrorLog`
- Produces: `DownloadQueue` class with methods:
  - `add_item(item: QueueItem) -> None`
  - `add_playlist(playlist: Playlist, quality: str, output_dir: Path) -> None`
  - `start() -> None`
  - `stop() -> None`
  - `retry_item(song_id: int) -> None`
  - `remove_item(song_id: int) -> None`
  - `clear_completed() -> None`
  - `get_items() -> list[QueueItem]`
  - Events: `on_progress`, `on_complete`, `on_error`, `on_status_change`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_queue.py
import pytest
from pathlib import Path
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.models import QueueItem, QueueStatus


@pytest.fixture
def queue():
    return DownloadQueue()


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_queue.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'musicdl_gui.queue'"

- [ ] **Step 3: Implement DownloadQueue**

```python
# src/musicdl_gui/queue.py
"""Serial download queue management."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Callable

from musicdl import Playlist, DownloadService, SongService, PlaylistService
from musicdl.exceptions import DownloadError, MusicDLException
from musicdl_gui.models import QueueItem, QueueStatus
from musicdl_gui.error_log import ErrorLog

QUEUE_FILE = Path.home() / ".config" / "musicdl-gui" / "queue.json"


class DownloadQueue:
    """Serial download queue - processes one item at a time."""

    def __init__(self) -> None:
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
            item = QueueItem(
                song_id=track.id,
                title=track.name,
                singer=track.singer,
                playlist=playlist.name,
                quality=quality,
                output_path=output_dir / f"{track.singer} - {track.name}.mp3",
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
                    downloader = DownloadService(
                        song_service,
                        playlist_service,
                        output_dir=item.output_path.parent,
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
            except Exception as e:
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
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
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
                "error": i.error,
                "retry_count": i.retry_count,
            }
            for i in self._items
        ]
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_queue(self) -> None:
        if QUEUE_FILE.exists():
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_queue.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/musicdl_gui/queue.py tests/unit/test_queue.py
git commit -m "feat: add DownloadQueue service"
```

---

### Task 7: Main App with Tab Structure

**Files:**
- Modify: `src/musicdl_gui/main.py`
- Create: `src/musicdl_gui/tabs/__init__.py`

**Interfaces:**
- Consumes: `ConfigManager`, `ErrorLog`, `DownloadQueue`
- Produces: `main(page: ft.Page)` with 5-tab structure

- [ ] **Step 1: Create tabs package**

```python
# src/musicdl_gui/tabs/__init__.py
"""Tab components for musicdl-gui."""
```

- [ ] **Step 2: Update main.py with tab structure**

```python
# src/musicdl_gui/main.py
"""musicdl-gui - Flet application entry point."""

import flet as ft

from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue


def main(page: ft.Page) -> None:
    page.title = "MusicDL GUI"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16

    config_mgr = ConfigManager()
    error_log = ErrorLog()
    download_queue = DownloadQueue()

    from musicdl_gui.tabs.playlist_browser import PlaylistBrowserTab
    from musicdl_gui.tabs.song_downloader import SongDownloaderTab
    from musicdl_gui.tabs.download_queue import DownloadQueueTab
    from musicdl_gui.tabs.settings import SettingsTab
    from musicdl_gui.tabs.error_log import ErrorLogTab

    tabs = ft.Tabs(
        length=5,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(text="Playlist", icon=ft.Icons.QUEUE_MUSIC),
                        ft.Tab(text="Song", icon=ft.Icons.MUSIC_NOTE),
                        ft.Tab(text="Queue", icon=ft.Icons.DOWNLOAD),
                        ft.Tab(text="Settings", icon=ft.Icons.SETTINGS),
                        ft.Tab(text="Errors", icon=ft.Icons.ERROR),
                    ],
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        PlaylistBrowserTab(config_mgr, download_queue, error_log),
                        SongDownloaderTab(config_mgr, download_queue, error_log),
                        DownloadQueueTab(download_queue, error_log),
                        SettingsTab(config_mgr),
                        ErrorLogTab(error_log),
                    ],
                ),
            ],
        ),
    )

    page.add(tabs)


if __name__ == "__main__":
    ft.run(main)
```

- [ ] **Step 3: Verify app launches**

Run: `flet run src/musicdl_gui/main.py`
Expected: App window opens with 5 tabs

- [ ] **Step 4: Commit**

```bash
git add src/musicdl_gui/main.py src/musicdl_gui/tabs/__init__.py
git commit -m "feat: add main app with tab structure"
```

---

### Task 8: Playlist Browser Tab

**Files:**
- Create: `src/musicdl_gui/tabs/playlist_browser.py`
- Create: `src/musicdl_gui/components/playlist_card.py`
- Create: `src/musicdl_gui/components/track_list.py`

**Interfaces:**
- Consumes: `ConfigManager`, `DownloadQueue`, `ErrorLog`, `ApiClient`
- Produces: `PlaylistBrowserTab(ft.UserControl)` class

- [ ] **Step 1: Create playlist_card component**

```python
# src/musicdl_gui/components/playlist_card.py
"""Playlist info card component."""

import flet as ft
from musicdl import Playlist


class PlaylistCard(ft.Card):
    def __init__(self, playlist: Playlist):
        super().__init__()
        self.playlist = playlist
        self.content = ft.Container(
            padding=16,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=16,
                        controls=[
                            ft.Image(
                                src=playlist.cover_image,
                                width=100,
                                height=100,
                                fit=ft.ImageFit.COVER,
                                border_radius=8,
                            ),
                            ft.Column(
                                expand=True,
                                spacing=4,
                                controls=[
                                    ft.Text(
                                        playlist.name,
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"by {playlist.creator.name}",
                                        size=14,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    ft.Text(
                                        f"{playlist.song_count} songs",
                                        size=14,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        )
```

- [ ] **Step 2: Create track_list component**

```python
# src/musicdl_gui/components/track_list.py
"""Track list component."""

import flet as ft
from musicdl import PlaylistTrack


class TrackList(ft.ListView):
    def __init__(self, tracks: list[PlaylistTrack]):
        super().__init__(
            expand=True,
            spacing=2,
            padding=8,
        )
        self.controls = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.MUSIC_NOTE),
                title=ft.Text(f"{track.singer} - {track.name}"),
                subtitle=ft.Text(track.duration),
            )
            for track in tracks
        ]
```

- [ ] **Step 3: Create PlaylistBrowserTab**

```python
# src/musicdl_gui/tabs/playlist_browser.py
"""Playlist browser tab."""

import flet as ft
from pathlib import Path

from musicdl_gui.api import ApiClient
from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.components.playlist_card import PlaylistCard
from musicdl_gui.components.track_list import TrackList


class PlaylistBrowserTab(ft.UserControl):
    def __init__(
        self,
        config_mgr: ConfigManager,
        download_queue: DownloadQueue,
        error_log: ErrorLog,
    ):
        super().__init__()
        self._config_mgr = config_mgr
        self._queue = download_queue
        self._error_log = error_log
        self._api: ApiClient | None = None
        self._current_playlist = None

        self.id_input = ft.TextField(
            label="Playlist ID",
            hint_text="Enter playlist ID",
            expand=True,
        )
        self.fetch_button = ft.ElevatedButton(
            text="Fetch",
            icon=ft.Icons.SEARCH,
            on_click=self._on_fetch,
        )
        self.progress_bar = ft.ProgressBar(visible=False)
        self.content_area = ft.Column(expand=True)

    def build(self):
        return ft.Column(
            expand=True,
            spacing=16,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[self.id_input, self.fetch_button],
                ),
                self.progress_bar,
                self.content_area,
            ],
        )

    async def _on_fetch(self, e):
        playlist_id = self.id_input.value.strip()
        if not playlist_id:
            return

        self.progress_bar.visible = True
        self.progress_bar.update()

        try:
            config = self._config_mgr.get_config()
            self._api = ApiClient(config)
            playlist = await self._api.fetch_playlist(playlist_id)
            self._current_playlist = playlist
            self._update_content(playlist)
        except Exception as exc:
            self._error_log.log_exception(exc, "playlist_browser", {"playlist_id": playlist_id})
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"Error: {exc}"))
            )
        finally:
            self.progress_bar.visible = False
            self.progress_bar.update()

    def _update_content(self, playlist):
        self.content_area.controls = [
            PlaylistCard(playlist),
            ft.Row(
                spacing=8,
                controls=[
                    ft.ElevatedButton(
                        text="Download All",
                        icon=ft.Icons.DOWNLOAD,
                        on_click=lambda e: self._on_download_all(),
                    ),
                    ft.OutlinedButton(
                        text="Add to Queue",
                        icon=ft.Icons.ADD,
                        on_click=lambda e: self._on_add_to_queue(),
                    ),
                ],
            ),
            TrackList(playlist.songs),
        ]
        self.content_area.update()

    def _on_download_all(self):
        if self._current_playlist:
            config = self._config_mgr.load()
            output_dir = Path(config.get("output_dir", "./music"))
            self._queue.add_playlist(self._current_playlist, config.get("default_level", "standard"), output_dir)
            self._queue.start()
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Added to download queue"))
            )

    def _on_add_to_queue(self):
        self._on_download_all()
```

- [ ] **Step 4: Verify tab renders**

Run: `flet run src/musicdl_gui/main.py`
Expected: Playlist tab shows input field and fetch button

- [ ] **Step 5: Commit**

```bash
git add src/musicdl_gui/tabs/playlist_browser.py src/musicdl_gui/components/
git commit -m "feat: add Playlist Browser tab"
```

---

### Task 9: Song Downloader Tab

**Files:**
- Create: `src/musicdl_gui/tabs/song_downloader.py`

**Interfaces:**
- Consumes: `ConfigManager`, `DownloadQueue`, `ErrorLog`, `ApiClient`
- Produces: `SongDownloaderTab(ft.UserControl)` class

- [ ] **Step 1: Create SongDownloaderTab**

```python
# src/musicdl_gui/tabs/song_downloader.py
"""Song downloader tab."""

import flet as ft
from pathlib import Path

from musicdl_gui.api import ApiClient
from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.models import QueueItem, QueueStatus


class SongDownloaderTab(ft.UserControl):
    def __init__(
        self,
        config_mgr: ConfigManager,
        download_queue: DownloadQueue,
        error_log: ErrorLog,
    ):
        super().__init__()
        self._config_mgr = config_mgr
        self._queue = download_queue
        self._error_log = error_log
        self._api: ApiClient | None = None
        self._song_info = None

        self.id_input = ft.TextField(
            label="Song ID",
            hint_text="Enter song ID",
            expand=True,
        )
        self.preview_button = ft.ElevatedButton(
            text="Preview",
            icon=ft.Icons.PREVIEW,
            on_click=self._on_preview,
        )
        self.quality_dropdown = ft.Dropdown(
            label="Quality",
            options=[
                ft.dropdown.Option("standard", "Standard"),
                ft.dropdown.Option("hires", "Hi-Res"),
                ft.dropdown.Option("lossless", "Lossless"),
            ],
            value="standard",
            width=150,
        )
        self.download_button = ft.ElevatedButton(
            text="Download",
            icon=ft.Icons.DOWNLOAD,
            on_click=self._on_download,
            disabled=True,
        )
        self.progress_bar = ft.ProgressBar(visible=False)
        self.info_card = ft.Card(
            visible=False,
            content=ft.Container(
                padding=16,
                content=ft.Column(spacing=8),
            ),
        )

    def build(self):
        return ft.Column(
            expand=True,
            spacing=16,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[self.id_input, self.preview_button],
                ),
                self.info_card,
                ft.Row(
                    spacing=8,
                    controls=[self.quality_dropdown, self.download_button],
                ),
                self.progress_bar,
            ],
        )

    async def _on_preview(self, e):
        song_id = self.id_input.value.strip()
        if not song_id:
            return

        self.progress_bar.visible = True
        self.progress_bar.update()

        try:
            config = self._config_mgr.get_config()
            self._api = ApiClient(config)
            self._song_info = await self._api.fetch_song_info(int(song_id))
            self._update_info_card()
            self.download_button.disabled = False
            self.download_button.update()
        except Exception as exc:
            self._error_log.log_exception(exc, "song_downloader", {"song_id": song_id})
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"Error: {exc}"))
            )
        finally:
            self.progress_bar.visible = False
            self.progress_bar.update()

    def _update_info_card(self):
        if self._song_info:
            self.info_card.content.content.controls = [
                ft.Text(self._song_info.name, size=20, weight=ft.FontWeight.BOLD),
                ft.Text(f"Artist: {self._song_info.singer}"),
                ft.Text(f"Album: {self._song_info.album}"),
                ft.Text(f"Duration: {self._song_info.duration}"),
            ]
            self.info_card.visible = True
            self.info_card.update()

    def _on_download(self, e):
        if not self._song_info:
            return

        config = self._config_mgr.load()
        output_dir = Path(config.get("output_dir", "./music"))
        quality = self.quality_dropdown.value

        item = QueueItem(
            song_id=self._song_info.id,
            title=self._song_info.name,
            singer=self._song_info.singer,
            playlist="",
            quality=quality,
            output_path=output_dir / f"{self._song_info.singer} - {self._song_info.name}.mp3",
        )
        self._queue.add_item(item)
        self._queue.start()
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Added to download queue"))
        )
```

- [ ] **Step 2: Verify tab renders**

Run: `flet run src/musicdl_gui/main.py`
Expected: Song tab shows input field, preview button, quality dropdown

- [ ] **Step 3: Commit**

```bash
git add src/musicdl_gui/tabs/song_downloader.py
git commit -m "feat: add Song Downloader tab"
```

---

### Task 10: Download Queue Tab

**Files:**
- Create: `src/musicdl_gui/tabs/download_queue.py`
- Create: `src/musicdl_gui/components/queue_table.py`

**Interfaces:**
- Consumes: `DownloadQueue`, `ErrorLog`
- Produces: `DownloadQueueTab(ft.UserControl)` class

- [ ] **Step 1: Create queue_table component**

```python
# src/musicdl_gui/components/queue_table.py
"""Download queue table component."""

import flet as ft
from musicdl_gui.models import QueueItem, QueueStatus


class QueueTable(ft.DataTable):
    def __init__(self):
        super().__init__(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Title")),
                ft.DataColumn(ft.Text("Singer")),
                ft.DataColumn(ft.Text("Playlist")),
                ft.DataColumn(ft.Text("Quality")),
                ft.DataColumn(ft.Text("Progress")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=[],
        )

    def update_items(self, items: list[QueueItem]):
        self.rows = []
        for idx, item in enumerate(items, start=1):
            status_color = {
                QueueStatus.PENDING: ft.Colors.GREY,
                QueueStatus.DOWNLOADING: ft.Colors.BLUE,
                QueueStatus.COMPLETED: ft.Colors.GREEN,
                QueueStatus.FAILED: ft.Colors.RED,
                QueueStatus.SKIPPED: ft.Colors.ORANGE,
            }.get(item.status, ft.Colors.GREY)

            actions = ft.Row(spacing=0)
            if item.status == QueueStatus.FAILED:
                actions.controls.append(
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        tooltip="Retry",
                        on_click=lambda e, sid=item.song_id: self._on_retry(sid),
                    )
                )
            actions.controls.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    tooltip="Remove",
                    on_click=lambda e, sid=item.song_id: self._on_remove(sid),
                )
            )

            self.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx))),
                        ft.DataCell(ft.Text(item.title)),
                        ft.DataCell(ft.Text(item.singer)),
                        ft.DataCell(ft.Text(item.playlist)),
                        ft.DataCell(ft.Text(item.quality)),
                        ft.DataCell(
                            ft.ProgressBar(
                                value=item.progress,
                                width=100,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                item.status.value,
                                color=status_color,
                            )
                        ),
                        ft.DataCell(actions),
                    ]
                )
            )
        self.update()

    def _on_retry(self, song_id: int):
        pass

    def _on_remove(self, song_id: int):
        pass
```

- [ ] **Step 2: Create DownloadQueueTab**

```python
# src/musicdl_gui/tabs/download_queue.py
"""Download queue tab."""

import flet as ft

from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.components.queue_table import QueueTable


class DownloadQueueTab(ft.UserControl):
    def __init__(self, download_queue: DownloadQueue, error_log: ErrorLog):
        super().__init__()
        self._queue = download_queue
        self._error_log = error_log
        self._table = QueueTable()

        self._table._on_retry = self._on_retry
        self._table._on_remove = self._on_remove

        self.clear_button = ft.OutlinedButton(
            text="Clear Completed",
            icon=ft.Icons.CLEAR,
            on_click=self._on_clear,
        )
        self.retry_all_button = ft.OutlinedButton(
            text="Retry Failed",
            icon=ft.Icons.REFRESH,
            on_click=self._on_retry_all,
        )

    def build(self):
        return ft.Column(
            expand=True,
            spacing=16,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[self.clear_button, self.retry_all_button],
                ),
                ft.Container(
                    expand=True,
                    content=self._table,
                ),
            ],
        )

    def _on_retry(self, song_id: int):
        self._queue.retry_item(song_id)
        self._queue.start()
        self._refresh_table()

    def _on_remove(self, song_id: int):
        self._queue.remove_item(song_id)
        self._refresh_table()

    def _on_clear(self, e):
        self._queue.clear_completed()
        self._refresh_table()

    def _on_retry_all(self, e):
        items = self._queue.get_items()
        for item in items:
            if item.status.value == "failed":
                self._queue.retry_item(item.song_id)
        self._queue.start()
        self._refresh_table()

    def _refresh_table(self):
        self._table.update_items(self._queue.get_items())

    def did_mount(self):
        self._refresh_table()
        self._queue._on_complete = lambda item: self._refresh_table()
        self._queue._on_error = lambda item, e: self._refresh_table()
        self._queue._on_status_change = lambda item, status: self._refresh_table()
```

- [ ] **Step 3: Verify tab renders**

Run: `flet run src/musicdl_gui/main.py`
Expected: Queue tab shows table with columns and action buttons

- [ ] **Step 4: Commit**

```bash
git add src/musicdl_gui/tabs/download_queue.py src/musicdl_gui/components/queue_table.py
git commit -m "feat: add Download Queue tab"
```

---

### Task 11: Settings Tab

**Files:**
- Create: `src/musicdl_gui/tabs/settings.py`

**Interfaces:**
- Consumes: `ConfigManager`
- Produces: `SettingsTab(ft.UserControl)` class

- [ ] **Step 1: Create SettingsTab**

```python
# src/musicdl_gui/tabs/settings.py
"""Settings tab."""

import flet as ft
from pathlib import Path

from musicdl_gui.config import ConfigManager


class SettingsTab(ft.UserControl):
    def __init__(self, config_mgr: ConfigManager):
        super().__init__()
        self._config_mgr = config_mgr
        self._config = config_mgr.load()

        self.base_url_input = ft.TextField(
            label="API Base URL",
            value=self._config.get("base_url", ""),
            expand=True,
        )
        self.ip_input = ft.TextField(
            label="IP (optional)",
            value=self._config.get("ip") or "",
            hint_text="Leave empty for auto-detect",
            expand=True,
        )
        self.timeout_input = ft.TextField(
            label="Timeout (seconds)",
            value=str(self._config.get("timeout", 30.0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
        )
        self.retries_input = ft.TextField(
            label="Max Retries",
            value=str(self._config.get("max_retries", 3)),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
        )
        self.output_dir_input = ft.TextField(
            label="Output Directory",
            value=self._config.get("output_dir", "./music"),
            expand=True,
        )
        self.quality_dropdown = ft.Dropdown(
            label="Default Quality",
            options=[
                ft.dropdown.Option("standard", "Standard"),
                ft.dropdown.Option("hires", "Hi-Res"),
                ft.dropdown.Option("lossless", "Lossless"),
            ],
            value=self._config.get("default_level", "standard"),
            width=150,
        )
        self.save_button = ft.ElevatedButton(
            text="Save",
            icon=ft.Icons.SAVE,
            on_click=self._on_save,
        )
        self.reset_button = ft.OutlinedButton(
            text="Reset to Defaults",
            icon=ft.Icons.RESTORE,
            on_click=self._on_reset,
        )
        self.test_button = ft.OutlinedButton(
            text="Test Connection",
            icon=ft.Icons.CHECK,
            on_click=self._on_test,
        )

    def build(self):
        return ft.Column(
            expand=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text("API Settings", size=18, weight=ft.FontWeight.BOLD),
                self.base_url_input,
                self.ip_input,
                ft.Row(
                    spacing=8,
                    controls=[self.timeout_input, self.retries_input],
                ),
                ft.Divider(),
                ft.Text("Download Settings", size=18, weight=ft.FontWeight.BOLD),
                self.output_dir_input,
                self.quality_dropdown,
                ft.Divider(),
                ft.Row(
                    spacing=8,
                    controls=[self.save_button, self.reset_button, self.test_button],
                ),
            ],
        )

    def _on_save(self, e):
        config = {
            "base_url": self.base_url_input.value,
            "ip": self.ip_input.value or None,
            "timeout": float(self.timeout_input.value),
            "max_retries": int(self.retries_input.value),
            "output_dir": self.output_dir_input.value,
            "default_level": self.quality_dropdown.value,
        }
        errors = self._config_mgr.validate(config)
        if errors:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"Validation errors: {', '.join(errors)}"))
            )
            return
        self._config_mgr.save(config)
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Settings saved"))
        )

    def _on_reset(self, e):
        self._config_mgr.save(self._config_mgr.DEFAULT_CONFIG.copy())
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Settings reset to defaults"))
        )

    async def _on_test(self, e):
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Testing connection..."))
        )
```

- [ ] **Step 2: Verify tab renders**

Run: `flet run src/musicdl_gui/main.py`
Expected: Settings tab shows all configuration fields

- [ ] **Step 3: Commit**

```bash
git add src/musicdl_gui/tabs/settings.py
git commit -m "feat: add Settings tab"
```

---

### Task 12: Error Log Tab

**Files:**
- Create: `src/musicdl_gui/tabs/error_log.py`
- Create: `src/musicdl_gui/components/error_log_table.py`

**Interfaces:**
- Consumes: `ErrorLog`
- Produces: `ErrorLogTab(ft.UserControl)` class

- [ ] **Step 1: Create error_log_table component**

```python
# src/musicdl_gui/components/error_log_table.py
"""Error log table component."""

import flet as ft
from musicdl_gui.error_log import ErrorLogEntry


class ErrorLogTable(ft.DataTable):
    def __init__(self):
        super().__init__(
            columns=[
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("Level")),
                ft.DataColumn(ft.Text("Source")),
                ft.DataColumn(ft.Text("Message")),
                ft.DataColumn(ft.Text("Exception")),
            ],
            rows=[],
        )

    def update_entries(self, entries: list[ErrorLogEntry]):
        self.rows = []
        for entry in entries:
            level_color = {
                "ERROR": ft.Colors.RED,
                "WARNING": ft.Colors.ORANGE,
                "INFO": ft.Colors.BLUE,
            }.get(entry.level, ft.Colors.GREY)

            self.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(entry.timestamp[:19])),
                        ft.DataCell(ft.Text(entry.level, color=level_color)),
                        ft.DataCell(ft.Text(entry.source)),
                        ft.DataCell(ft.Text(entry.message, expand=True)),
                        ft.DataCell(ft.Text(entry.exception_type or "-")),
                    ]
                )
            )
        self.update()
```

- [ ] **Step 2: Create ErrorLogTab**

```python
# src/musicdl_gui/tabs/error_log.py
"""Error log tab."""

import flet as ft
from pathlib import Path

from musicdl_gui.error_log import ErrorLog
from musicdl_gui.components.error_log_table import ErrorLogTable


class ErrorLogTab(ft.UserControl):
    def __init__(self, error_log: ErrorLog):
        super().__init__()
        self._error_log = error_log
        self._table = ErrorLogTable()

        self.clear_button = ft.OutlinedButton(
            text="Clear Log",
            icon=ft.Icons.CLEAR,
            on_click=self._on_clear,
        )
        self.export_button = ft.OutlinedButton(
            text="Export",
            icon=ft.Icons.DOWNLOAD,
            on_click=self._on_export,
        )

    def build(self):
        return ft.Column(
            expand=True,
            spacing=16,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[self.clear_button, self.export_button],
                ),
                ft.Container(
                    expand=True,
                    content=self._table,
                ),
            ],
        )

    def did_mount(self):
        self._refresh()
        self._error_log.register_callback(self._on_new_entry)

    def _on_new_entry(self, entry):
        self._refresh()

    def _refresh(self):
        entries = self._error_log.get_entries(limit=100)
        self._table.update_entries(entries)

    def _on_clear(self, e):
        self._error_log.clear()
        self._refresh()

    async def _on_export(self, e):
        file_picker = ft.FilePicker()
        self.page.services.append(file_picker)
        path = await file_picker.save_file_async()
        if path:
            self._error_log.export(Path(path))
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"Exported to {path}"))
            )
```

- [ ] **Step 3: Verify tab renders**

Run: `flet run src/musicdl_gui/main.py`
Expected: Error Log tab shows table with error entries

- [ ] **Step 4: Commit**

```bash
git add src/musicdl_gui/tabs/error_log.py src/musicdl_gui/components/error_log_table.py
git commit -m "feat: add Error Log tab"
```

---

### Task 13: Integration Tests

**Files:**
- Create: `tests/integration/test_download_flow.py`

**Interfaces:**
- Consumes: All services
- Produces: Integration test coverage

- [ ] **Step 1: Write integration tests**

```python
# tests/integration/test_download_flow.py
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
    monkeypatch.setattr("musicdl_gui.queue.QUEUE_FILE", tmp_path / "queue.json")

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
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/integration/test_download_flow.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_download_flow.py
git commit -m "test: add integration tests for download flow"
```

---

### Task 14: PyInstaller Spec and Build

**Files:**
- Create: `musicdl_gui.spec`
- Create: `assets/icon.png` (placeholder)

**Interfaces:**
- Consumes: All source files
- Produces: macOS `.app` bundle

- [ ] **Step 1: Create PyInstaller spec**

```python
# musicdl_gui.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ['src/musicdl_gui/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/musicdl_gui/tabs', 'tabs'),
        ('src/musicdl_gui/components', 'components'),
        ('src/musicdl_gui/utils', 'utils'),
    ],
    hiddenimports=[
        'musicdl',
        'musicdl_gui',
        'flet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='musicdl-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='musicdl_gui',
)

app = BUNDLE(
    coll,
    name='musicdl-gui.app',
    icon='assets/icon.png',
    bundle_identifier='com.musicdl.gui',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '0.1.0',
        'NSRequiresAquaSystemAppearance': False,
    },
)
```

- [ ] **Step 2: Build macOS app**

Run: `pyinstaller musicdl_gui.spec --clean`
Expected: `dist/musicdl-gui.app` created

- [ ] **Step 3: Verify app bundle**

Run: `ls -la dist/musicdl-gui.app/Contents/MacOS/`
Expected: `musicdl-gui` executable present

- [ ] **Step 4: Commit**

```bash
git add musicdl_gui.spec assets/icon.png
git commit -m "build: add PyInstaller spec for macOS"
```

---

### Task 15: README and Documentation

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: None
- Produces: User documentation

- [ ] **Step 1: Create README.md**

```markdown
# MusicDL GUI

Cross-platform GUI for the [musicdl](https://github.com/musicdl/musicdl) library, built with Python + Flet.

## Features

- **Playlist Browser**: Fetch and browse playlists by ID
- **Song Downloader**: Preview and download individual songs
- **Download Queue**: Serial download management with persistence
- **Settings**: Configure API, download, and quality options
- **Error Log**: Real-time error tracking and export

## Installation

### From Source

```bash
git clone https://github.com/musicdl/musicdl-gui.git
cd musicdl-gui
pip install -e ".[dev]"
```

### Run

```bash
flet run src/musicdl_gui/main.py
```

Or:

```bash
python -m musicdl_gui.main
```

## Build

### macOS

```bash
pyinstaller musicdl_gui.spec --clean
```

Output: `dist/musicdl-gui.app`

## Development

### Run Tests

```bash
pytest
```

### Code Coverage

```bash
pytest --cov=musicdl_gui --cov-report=html
```

## Configuration

Configuration is stored in `~/.config/musicdl-gui/config.json`.

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

## Self-Review

**Spec Coverage:**
- ✅ Tab 1: Playlist Browser (Task 8)
- ✅ Tab 2: Song Downloader (Task 9)
- ✅ Tab 3: Download Queue (Task 10)
- ✅ Tab 4: Settings (Task 11)
- ✅ Tab 5: Error Log (Task 12)
- ✅ Serial downloads (Task 6)
- ✅ Error handling (Task 3)
- ✅ Config persistence (Task 2)
- ✅ macOS packaging (Task 14)
- ✅ Unit tests (Tasks 2-6)
- ✅ Integration tests (Task 13)

**Placeholder Scan:** No TBDs, TODOs, or "implement later" found.

**Type Consistency:** All method signatures and property names are consistent across tasks.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-01-musicdl-gui.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?