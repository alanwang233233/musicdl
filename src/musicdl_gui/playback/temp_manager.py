"""Temporary file manager for playback."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


class TempFileManager:
    """Manages temporary files for playback."""

    def __init__(self) -> None:
        self._temp_dir = Path(tempfile.gettempdir()) / "musicdl-gui-playback"
        self._current_files: set[Path] = set()

    @property
    def temp_dir(self) -> Path:
        return self._temp_dir

    def initialize(self) -> None:
        """Initialize temp directory and clean up old files."""
        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._current_files.clear()

    def get_temp_path(self, song_id: int, extension: str = ".mp3") -> Path:
        """Get a temporary file path for a song."""
        return self._temp_dir / f"song_{song_id}{extension}"

    def register_file(self, path: Path) -> None:
        """Register a file for cleanup tracking."""
        self._current_files.add(path)

    def unregister_file(self, path: Path) -> None:
        """Unregister a file from cleanup tracking."""
        self._current_files.discard(path)

    def cleanup_all(self) -> None:
        """Clean up all registered files and the temp directory."""
        for path in self._current_files:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
        self._current_files.clear()
        try:
            if self._temp_dir.exists():
                shutil.rmtree(self._temp_dir, ignore_errors=True)
        except OSError:
            pass

    def get_file_size(self, path: Path) -> int:
        """Get file size in bytes."""
        try:
            return path.stat().st_size
        except OSError:
            return 0