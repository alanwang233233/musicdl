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