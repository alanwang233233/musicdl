"""Playback service using flet-audio."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from enum import Enum
from pathlib import Path

import flet_audio as fta

from musicdl_gui.api import ApiClient
from musicdl_gui.config import ConfigManager
from musicdl_gui.models import QueueItem
from musicdl_gui.playback.temp_manager import TempFileManager
from musicdl_gui.queue import DownloadQueue


class PlaybackMode(Enum):
    SEQUENTIAL = "sequential"
    SINGLE_LOOP = "single_loop"
    RANDOM = "random"


class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ENDED = "ended"


class PlaybackService:
    """Playback service using flet-audio with different playback modes."""

    def __init__(
        self,
        queue: DownloadQueue,
        config_manager: ConfigManager,
        temp_manager: TempFileManager,
        page,
        api_client: ApiClient | None = None,
    ) -> None:
        self._queue = queue
        self._config_manager = config_manager
        self._temp_manager = temp_manager
        self._api_client = api_client
        self._page = page

        self._mode = PlaybackMode.SEQUENTIAL
        self._state = PlaybackState.STOPPED
        self._current_item: QueueItem | None = None
        self._current_index = -1
        self._playlist: list[QueueItem] = []
        self._progress = 0.0
        self._duration = 0.0

        # Callbacks
        self._on_state_change: Callable[[PlaybackState], None] | None = None
        self._on_progress_change: Callable[[float, float], None] | None = None  # progress, duration
        self._on_track_change: Callable[[QueueItem | None], None] | None = None
        self._on_error: Callable[[str], None] | None = None

        # Audio player
        self._audio: fta.Audio | None = None

    @property
    def mode(self) -> PlaybackMode:
        return self._mode

    @mode.setter
    def mode(self, value: PlaybackMode) -> None:
        self._mode = value

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def current_item(self) -> QueueItem | None:
        return self._current_item

    @property
    def progress(self) -> float:
        return self._progress

    @property
    def duration(self) -> float:
        return self._duration

    def set_playlist(self, items: list[QueueItem]) -> None:
        """Set the playback playlist."""
        self._playlist = items.copy()
        if self._playlist:
            self._current_index = 0
            self._current_item = self._playlist[0]
        else:
            self._current_index = -1
            self._current_item = None
        if self._on_track_change:
            self._on_track_change(self._current_item)

    def add_to_playlist(self, item: QueueItem) -> None:
        """Add item to playlist."""
        self._playlist.append(item)
        if self._current_index == -1:
            self._current_index = 0
            self._current_item = item
            if self._on_track_change:
                self._on_track_change(item)

    def play(self) -> None:
        """Start or resume playback."""
        if self._state == PlaybackState.PLAYING:
            return
        if self._current_item is None and self._playlist:
            self._current_index = 0
            self._current_item = self._playlist[0]
            if self._on_track_change:
                self._on_track_change(self._current_item)
        if self._current_item is None:
            return

        # Resume from pause if audio exists
        if self._state == PlaybackState.PAUSED and self._audio:
            self._state = PlaybackState.PLAYING
            if self._on_state_change:
                self._on_state_change(self._state)
            self._page.run_task(self._audio.resume)
            return

        self._state = PlaybackState.PLAYING
        if self._on_state_change:
            self._on_state_change(self._state)
        if self._state == PlaybackState.PLAYING:
            self._start_playback_task()

    def pause(self) -> None:
        """Pause playback."""
        if self._state != PlaybackState.PLAYING:
            return
        self._state = PlaybackState.PAUSED
        if self._on_state_change:
            self._on_state_change(self._state)
        if self._audio:
            self._page.run_task(self._audio.pause)

    def stop(self) -> None:
        """Stop playback."""
        self._state = PlaybackState.STOPPED
        if self._on_state_change:
            self._on_state_change(self._state)
        if self._audio:
            self._page.run_task(self._audio.pause)
            self._page.run_task(self._audio.release)
            self._audio = None
        self._current_item = None
        self._current_index = -1
        self._progress = 0.0
        self._duration = 0.0
        if self._on_progress_change:
            self._on_progress_change(0.0, 0.0)
        if self._on_track_change:
            self._on_track_change(None)

    def next_track(self) -> None:
        """Play next track."""
        if not self._playlist:
            return
        if self._mode == PlaybackMode.RANDOM:
            self._current_index = random.randrange(len(self._playlist))
        else:
            self._current_index = (self._current_index + 1) % len(self._playlist)
        self._current_item = self._playlist[self._current_index]
        if self._on_track_change:
            self._on_track_change(self._current_item)
        if self._state == PlaybackState.PLAYING:
            self._start_playback_task()

    def previous_track(self) -> None:
        """Play previous track."""
        if not self._playlist:
            return
        if self._mode == PlaybackMode.RANDOM:
            self._current_index = random.randrange(len(self._playlist))
        else:
            self._current_index = (self._current_index - 1) % len(self._playlist)
        self._current_item = self._playlist[self._current_index]
        if self._on_track_change:
            self._on_track_change(self._current_item)
        if self._state == PlaybackState.PLAYING:
            self._start_playback_task()

    def seek(self, position: float) -> None:
        """Seek to position (0.0 to 1.0)."""
        self._progress = max(0.0, min(1.0, position))
        if self._on_progress_change:
            self._on_progress_change(self._progress, self._duration)
        if self._audio and self._duration > 0:
            target_ms = int(self._duration * position * 1000)
            self._page.run_task(self._audio.seek, target_ms)

    def _start_playback_task(self) -> None:
        if self._current_item:
            asyncio.create_task(self._playback_loop())

    async def _playback_loop(self) -> None:
        """Main playback loop - downloads to temp and plays via flet-audio."""
        while self._current_item:
            # Wait if paused
            while self._state == PlaybackState.PAUSED:
                await asyncio.sleep(0.1)

            # Exit if stopped or ended
            if self._state in (PlaybackState.STOPPED, PlaybackState.ENDED):
                break

            item = self._current_item
            try:
                self._state = PlaybackState.BUFFERING
                if self._on_state_change:
                    self._on_state_change(self._state)

                # Download to temp file
                temp_path = await self._download_to_temp(item)
                if not temp_path or not temp_path.exists():
                    raise RuntimeError("Failed to download to temp file")

                self._temp_manager.register_file(temp_path)
                self._temp_manager.get_file_size(temp_path)

                # Get actual duration
                self._duration = await self._get_audio_duration(temp_path)
                self._progress = 0.0
                if self._on_progress_change:
                    self._on_progress_change(0.0, self._duration)

                # Play the audio file
                await self._play_audio_file(temp_path)

                # Playback finished
                self._temp_manager.unregister_file(temp_path)
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

                # Handle next track based on mode
                if self._state in (PlaybackState.STOPPED, PlaybackState.ENDED):
                    break

                if self._mode == PlaybackMode.SINGLE_LOOP:
                    continue  # Replay current
                elif self._mode == PlaybackMode.RANDOM:
                    self._current_index = random.randrange(len(self._playlist))
                else:
                    self._current_index += 1

                if self._current_index >= len(self._playlist):
                    self._state = PlaybackState.ENDED
                    if self._on_state_change:
                        self._on_state_change(self._state)
                    break

                self._current_item = self._playlist[self._current_index]
                if self._on_track_change:
                    self._on_track_change(self._current_item)

            except asyncio.CancelledError:
                break
            except (RuntimeError, ValueError, OSError) as e:
                if self._on_error:
                    self._on_error(str(e))
                # Try next track
                if self._mode == PlaybackMode.RANDOM:
                    self._current_index = random.randrange(len(self._playlist))
                else:
                    self._current_index += 1
                if self._current_index >= len(self._playlist):
                    self._state = PlaybackState.ENDED
                    if self._on_state_change:
                        self._on_state_change(self._state)
                    break
                self._current_item = self._playlist[self._current_index]
                if self._on_track_change:
                    self._on_track_change(self._current_item)

    async def _get_audio_duration(self, file_path: Path) -> float:
        """Get audio duration using ffprobe."""
        try:
            import subprocess
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass
        # Fallback: estimate from file size
        file_size = file_path.stat().st_size
        return (file_size * 8) / (128 * 1000)  # 128 kbps estimate

    async def _play_audio_file(self, file_path: Path) -> None:
        """Play audio file using flet-audio."""
        try:
            # Create audio control
            self._audio = fta.Audio(
                src=str(file_path),
                autoplay=True,
                volume=1.0,
                balance=0.0,
                release_mode=fta.ReleaseMode.STOP,
                on_loaded=lambda _: None,
                on_duration_change=lambda e: self._on_duration_change(e.duration if hasattr(e, 'duration') else 0),
                on_position_change=lambda e: self._on_position_change(e.position if hasattr(e, 'position') else 0),
                on_state_change=lambda e: self._on_flet_audio_state_change(e.state if hasattr(e, 'state') else fta.AudioState.STOPPED),
                on_seek_complete=lambda _: None,
            )
            # Add to page services
            self._page.services.append(self._audio)
            # Play
            await self._audio.play()
            # Wait for playback to complete or be interrupted
            while self._audio and self._state != PlaybackState.STOPPED:
                # Wait if paused
                while self._state == PlaybackState.PAUSED and self._audio:
                    await asyncio.sleep(0.1)
                # Exit if stopped or ended
                if self._state in (PlaybackState.STOPPED, PlaybackState.ENDED):
                    break
                await asyncio.sleep(0.5)
        except (RuntimeError, ValueError, OSError) as e:
            if self._on_error:
                self._on_error(f"Playback error: {e}")
        finally:
            if self._audio:
                try:
                    await self._audio.release()
                except (RuntimeError, ValueError, OSError):
                    pass
                self._audio = None

    def _to_seconds(self, duration) -> float:
        """Convert flet Duration to seconds."""
        if hasattr(duration, 'total_seconds'):
            return duration.total_seconds()
        elif hasattr(duration, 'total_milliseconds'):
            return duration.total_milliseconds() / 1000.0
        elif hasattr(duration, 'in_milliseconds'):
            # in_milliseconds is a property, not a method
            return duration.in_milliseconds / 1000.0
        elif hasattr(duration, 'milliseconds'):
            return duration.milliseconds / 1000.0
        elif isinstance(duration, (int, float)):
            return float(duration) / 1000.0
        return 0.0

    def _on_duration_change(self, duration) -> None:
        """Handle duration change event from flet-audio."""
        duration = self._to_seconds(duration)
        if duration > self._duration:
            self._duration = duration
            if self._on_progress_change:
                self._on_progress_change(self._progress, self._duration)

    def _on_position_change(self, position) -> None:
        """Handle position change event from flet-audio."""
        position = self._to_seconds(position)
        self._progress = position / self._duration if self._duration > 0 else 0.0
        if self._on_progress_change:
            self._on_progress_change(self._progress, self._duration)

    def _on_flet_audio_state_change(self, state) -> None:
        """Handle state change event from flet-audio (converts fta.AudioState to our PlaybackState)."""
        # Map fta.AudioState to our PlaybackState
        if state == fta.AudioState.PLAYING or state == "playing":
            self._state = PlaybackState.PLAYING
        elif state == fta.AudioState.PAUSED or state == "paused":
            self._state = PlaybackState.PAUSED
        elif state == fta.AudioState.STOPPED or state == "stopped":
            self._state = PlaybackState.STOPPED
        elif state == fta.AudioState.COMPLETED or state == "completed":
            self._state = PlaybackState.ENDED
        else:
            # Unknown state, default to STOPPED
            self._state = PlaybackState.STOPPED
        if self._on_state_change:
            self._on_state_change(self._state)

    async def _download_to_temp(self, item: QueueItem) -> Path | None:
        """Download song to temp file."""
        from musicdl import (
            DownloadService,
            PlaylistService,
            SongService,
            SyncMusicClient,
        )
        config = self._config_manager.get_config()
        temp_path = self._temp_manager.get_temp_path(item.song_id)

        try:
            with SyncMusicClient(config) as client:
                song_service = SongService(client)
                playlist_service = PlaylistService(client)
                downloader = DownloadService(
                    song_service,
                    playlist_service,
                    output_dir=temp_path.parent,
                )
                await asyncio.to_thread(
                    downloader.download_song,
                    item.song_id,
                    level=item.quality,
                    output=temp_path,
                )
            return temp_path
        except (RuntimeError, ValueError, OSError):
            return None

    def set_on_state_change(self, callback: Callable[[PlaybackState], None]) -> None:
        self._on_state_change = callback

    def set_on_progress_change(self, callback: Callable[[float, float], None]) -> None:
        self._on_progress_change = callback

    def set_on_track_change(self, callback: Callable[[QueueItem | None], None]) -> None:
        self._on_track_change = callback

    def set_on_error(self, callback: Callable[[str], None]) -> None:
        self._on_error = callback