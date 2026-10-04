"""Playback service using flet-audio."""

from __future__ import annotations

import asyncio
import random
import subprocess
import time
from collections.abc import Callable
from enum import Enum
from pathlib import Path

import flet_audio as fta

from musicdl import MusicDLException
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
        self._playlist: list[QueueItem] = []
        self._history: list[QueueItem] = []
        self._progress = 0.0
        self._duration = 0.0

        # Callbacks - support multiple listeners
        self._on_state_change: list[Callable[[PlaybackState], None]] = []
        self._on_progress_change: list[Callable[[float, float], None]] = []
        self._on_track_change: list[Callable[[QueueItem | None], None]] = []
        self._on_error: list[Callable[[str], None]] = []
        self._on_mode_change: list[Callable[[PlaybackMode], None]] = []

        # Audio player
        self._audio: fta.Audio | None = None
        self._seeking = False
        self._seek_requested_at = 0.0
        # 进度事件节流:两个 UI 组件都要刷新,限制补丁发送频率避免卡顿
        self._last_progress_emit = 0.0
        # 当前曲目是否已自然播完(与 ENDED 区分:ENDED 只表示整个列表播完)
        self._track_completed = False
        # 单曲循环复用的临时文件(同一首歌只下载一次)
        self._single_loop_temp: Path | None = None
        self._single_loop_song: int | None = None
        # 预取:剩余不足 20 秒时后台提前下载下一首
        self._prefetch_tasks: dict[int, asyncio.Task] = {}
        self._prefetched_paths: dict[int, Path] = {}

        # Playback task management
        self._task: asyncio.Task | None = None
        self._generation = 0

    @property
    def mode(self) -> PlaybackMode:
        return self._mode

    @mode.setter
    def mode(self, value: PlaybackMode) -> None:
        if self._mode != value:
            self._mode = value
            for cb in self._on_mode_change:
                cb(value)

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
        self._history = []
        if self._playlist:
            self._current_item = self._playlist[0]
        else:
            self._current_item = None
        for cb in self._on_track_change:
            cb(self._current_item)

    def add_to_playlist(self, item: QueueItem) -> None:
        """Add item to playlist."""
        self._playlist.append(item)
        if self._current_item is None:
            self._current_item = item
            for cb in self._on_track_change:
                cb(item)

    def add_to_playlist_next(self, item: QueueItem) -> None:
        """把曲目插入为下一首播放(当前曲目之后)。

        没有正在播放的曲目时等同于直接入队并作为当前曲目。
        """
        if self._current_item is None:
            self.add_to_playlist(item)
            return
        self._playlist.insert(1, item)

    def play(self) -> None:
        """Start or resume playback."""
        if self._state == PlaybackState.PLAYING:
            return
        if self._current_item is None and self._playlist:
            self._current_item = self._playlist[0]
            for cb in self._on_track_change:
                cb(self._current_item)
        if self._current_item is None:
            return

        # Resume from pause if audio exists
        if self._state == PlaybackState.PAUSED:
            audio = self._audio
            if audio:
                self._state = PlaybackState.PLAYING
                for cb in self._on_state_change:
                    cb(self._state)
                self._safe_audio_call(audio.resume)
                return

        self._state = PlaybackState.PLAYING
        for cb in self._on_state_change:
            cb(self._state)
        if self._state == PlaybackState.PLAYING:
            self._start_playback_task()

    def pause(self) -> None:
        """Pause playback."""
        if self._state != PlaybackState.PLAYING:
            return
        self._state = PlaybackState.PAUSED
        for cb in self._on_state_change:
            cb(self._state)
        audio = self._audio
        if audio:
            self._safe_audio_call(audio.pause)

    def stop(self) -> None:
        """Stop playback."""
        # Invalidate current playback session and cancel its task
        self._generation += 1
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        # 播放已终止,重置 seek 标记,避免残留状态卡住进度更新
        self._seeking = False
        # 取消进行中的预取下载,并清理单曲循环复用的临时文件
        for task in self._prefetch_tasks.values():
            task.cancel()
        self._prefetch_tasks.clear()
        self._discard_single_loop_temp()

        self._state = PlaybackState.STOPPED
        for cb in self._on_state_change:
            cb(self._state)
        # Capture audio reference before setting to None
        audio = self._audio
        self._audio = None
        if audio:
            self._safe_audio_call(audio.pause)
            self._safe_audio_call(audio.release)
        self._current_item = None
        self._playlist = []
        self._history = []
        self._progress = 0.0
        self._duration = 0.0
        for cb in self._on_progress_change:
            cb(0.0, 0.0)
        for cb in self._on_track_change:
            cb(None)

    def next_track(self) -> None:
        """Play next track."""
        if not self._playlist:
            return
        # Move current item to history
        if self._current_item:
            self._history.append(self._current_item)
        # Pop first item
        self._playlist.pop(0)
        # Play new first item
        if self._playlist:
            self._current_item = self._playlist[0]
            for cb in self._on_track_change:
                cb(self._current_item)
            # 无条件重启播放任务(内部自会取消旧任务),与当前状态无关
            self._start_playback_task()
        else:
            self._current_item = None
            self._state = PlaybackState.ENDED
            for cb in self._on_state_change:
                cb(self._state)
            for cb in self._on_track_change:
                cb(None)

    def previous_track(self) -> None:
        """Play previous track."""
        if not self._history:
            return
        # Move current item back to front of playlist (skip if it is already first)
        if self._current_item and (
            not self._playlist or self._playlist[0] is not self._current_item
        ):
            self._playlist.insert(0, self._current_item)
        # Pop last item from history
        self._current_item = self._history.pop()
        self._playlist.insert(0, self._current_item)
        for cb in self._on_track_change:
            cb(self._current_item)
        # 无条件重启播放任务(内部自会取消旧任务),与当前状态无关
        self._start_playback_task()

    def seek(self, position: float) -> None:
        """Seek to position (0.0 to 1.0)."""
        self._seeking = True
        self._seek_requested_at = time.monotonic()
        self._progress = max(0.0, min(1.0, position))
        for cb in self._on_progress_change:
            cb(self._progress, self._duration)
        audio = self._audio
        if audio and self._duration > 0:
            target_ms = int(self._duration * position * 1000)
            self._safe_audio_call(audio.seek, target_ms)

    def _safe_audio_call(self, coro_fn, *args) -> None:
        """Run an audio coroutine on the page loop, swallowing errors from a released audio."""
        try:
            self._page.run_task(coro_fn, *args)
        except Exception:  # noqa: BLE001, S110 - released audio is expected here
            pass

    def _start_playback_task(self) -> None:
        if not self._current_item:
            return
        # Cancel any existing playback task before starting a new one
        if self._task and not self._task.done():
            self._task.cancel()
        self._generation += 1
        gen = self._generation
        self._task = self._page.run_task(self._playback_loop, gen)

    async def _playback_loop(self, generation: int) -> None:
        """Main playback loop - downloads to temp and plays via flet-audio."""
        consecutive_failures = 0

        async def _handle_playback_failure() -> bool:
            """Handle a playback failure: back off, then skip to the next track.

            Returns False when the playback loop should end."""
            nonlocal consecutive_failures
            consecutive_failures += 1
            if consecutive_failures > 5:
                for cb in self._on_error:
                    cb("Too many consecutive failures, stopping playback")
                self._state = PlaybackState.ENDED
                for cb in self._on_state_change:
                    cb(self._state)
                self._playlist = []
                self._current_item = None
                for cb in self._on_track_change:
                    cb(None)
                return False
            # Exponential backoff (capped) to avoid a hot failure loop
            await asyncio.sleep(min(2 ** (consecutive_failures - 1), 30))
            if self._mode == PlaybackMode.SINGLE_LOOP:
                # Retry the current track
                return True
            if self._mode == PlaybackMode.RANDOM:
                # Remove the failed track before reshuffling so it is not replayed
                if self._current_item in self._playlist:
                    self._playlist.remove(self._current_item)
                random.shuffle(self._playlist)
            else:
                # SEQUENTIAL: move the failed track to history and pop it
                if self._current_item:
                    self._history.append(self._current_item)
                if self._playlist:
                    self._playlist.pop(0)

            if not self._playlist:
                self._state = PlaybackState.ENDED
                for cb in self._on_state_change:
                    cb(self._state)
                self._current_item = None
                for cb in self._on_track_change:
                    cb(None)
                return False
            self._current_item = self._playlist[0]
            for cb in self._on_track_change:
                cb(self._current_item)
            return True

        while self._current_item and generation == self._generation:
            # Wait if paused
            while self._state == PlaybackState.PAUSED:
                await asyncio.sleep(0.1)

            # Exit if stopped or ended
            if self._state in (PlaybackState.STOPPED, PlaybackState.ENDED):
                break

            item = self._current_item
            try:
                self._state = PlaybackState.BUFFERING
                for cb in self._on_state_change:
                    cb(self._state)

                # 单曲循环:同一首歌复用已下载的临时文件,只下载一次,播完立即重播
                if (
                    self._mode == PlaybackMode.SINGLE_LOOP
                    and self._single_loop_temp is not None
                    and self._single_loop_song == item.song_id
                    and self._single_loop_temp.exists()
                ):
                    temp_path = self._single_loop_temp
                else:
                    # 离开单曲循环或换歌:丢弃上一首的复用文件
                    self._discard_single_loop_temp()
                    # 优先使用预取结果,否则现场下载
                    temp_path = await self._acquire_temp(item)
                    if self._mode == PlaybackMode.SINGLE_LOOP:
                        self._single_loop_temp = temp_path
                        self._single_loop_song = item.song_id
                    # Get actual duration(单曲循环复用时沿用上一轮时长,立即重播)
                    self._duration = await self._get_audio_duration(temp_path)

                self._progress = 0.0
                for cb in self._on_progress_change:
                    cb(0.0, self._duration)

                # Play the audio file
                await self._play_audio_file(temp_path)

                # Playback finished
                # 会话已被新会话取代时直接退出且不删除临时文件:
                # 新会话使用不同的唯一临时路径,旧文件留给 cleanup_all 统一回收
                if generation != self._generation:
                    break
                # 播放列表被外部改写清空(如 next_track 移除最后一首)时退出
                if self._current_item is None:
                    break

                if not (
                    self._mode == PlaybackMode.SINGLE_LOOP
                    and self._single_loop_temp is not None
                    and temp_path == self._single_loop_temp
                ):
                    # 单曲循环复用的文件保留供重播;其余播完即删
                    self._temp_manager.unregister_file(temp_path)
                    try:
                        temp_path.unlink(missing_ok=True)
                    except OSError:
                        pass

                # A track completed successfully, reset the failure counter
                consecutive_failures = 0

                # Handle next track based on mode
                # 注意:曲目自然播完不再中断循环(ENDED 只在列表耗尽时设置),
                # 否则单曲循环与自动连播都会在第一首播完后停止
                if self._mode == PlaybackMode.SINGLE_LOOP:
                    # Replay current - keep _current_item as is (first in playlist)
                    continue
                elif self._mode == PlaybackMode.RANDOM:
                    # Remove current track before reshuffling so it is not replayed
                    if self._current_item in self._playlist:
                        self._playlist.remove(self._current_item)
                    random.shuffle(self._playlist)
                else:
                    # SEQUENTIAL: pop first item (current), move to history
                    self._history.append(self._current_item)
                    self._playlist.pop(0)

                if not self._playlist:
                    self._state = PlaybackState.ENDED
                    for cb in self._on_state_change:
                        cb(self._state)
                    self._current_item = None
                    for cb in self._on_track_change:
                        cb(None)
                    break

                self._current_item = self._playlist[0]
                for cb in self._on_track_change:
                    cb(self._current_item)

            except asyncio.CancelledError:
                break
            except MusicDLException as e:
                for cb in self._on_error:
                    cb(str(e))
                if not await _handle_playback_failure():
                    break
            except Exception as e:  # noqa: BLE001 - last-resort guard keeps the loop alive
                for cb in self._on_error:
                    cb(f"Unexpected playback error: {e!r}")
                if not await _handle_playback_failure():
                    break

    async def _get_audio_duration(self, file_path: Path) -> float:
        """Get audio duration using ffprobe."""
        try:
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
        try:
            file_size = file_path.stat().st_size
        except OSError:
            return 0.0
        return (file_size * 8) / (128 * 1000)  # 128 kbps estimate

    async def _play_audio_file(self, file_path: Path) -> None:
        """Play audio file using flet-audio."""
        # 上一音频的 seek 完成事件可能已丢失,重置标记避免进度条一直处于 seeking 状态
        self._seeking = False
        if not file_path.exists():
            from musicdl import DownloadError

            raise DownloadError(f"Audio file not found: {file_path}")
        # Convert to file:// URL for flet-audio
        audio = fta.Audio(
            src=file_path.as_uri(),
            autoplay=True,
            volume=1.0,
            balance=0.0,
            release_mode=fta.ReleaseMode.STOP,
        )
        # Bind handlers to this specific audio instance so stale events from a
        # previous audio control cannot corrupt the current playback state.
        audio.on_loaded = lambda _: None
        audio.on_duration_change = lambda e, a=audio: self._on_duration_change(
            a, e.duration if hasattr(e, "duration") else 0
        )
        audio.on_position_change = lambda e, a=audio: self._on_position_change(
            a, e.position if hasattr(e, "position") else 0
        )
        audio.on_state_change = lambda e, a=audio: self._on_flet_audio_state_change(
            a, e.state if hasattr(e, "state") else fta.AudioState.STOPPED
        )
        audio.on_seek_complete = lambda _, a=audio: self._on_seek_complete(a)

        self._audio = audio
        self._track_completed = False
        try:
            # 必须显式注册到根视图的 services 列表:run_task 派生的协程里没有
            # page context,Service 构造时的自动注册不会发生。用"替换"方式注册,
            # 既保证注册生效,又避免 services 列表随播放次数无限增长。
            for stale in [
                s for s in self._page.services if isinstance(s, fta.Audio) and s is not audio
            ]:
                self._page.services.remove(stale)
            self._page.services.append(audio)
            self._page.update()
            # Play
            await audio.play()
            # Wait for playback to complete or be interrupted
            while (
                self._audio is audio
                and not self._track_completed
                and self._state not in (PlaybackState.STOPPED, PlaybackState.ENDED)
            ):
                # Wait if paused
                while self._state == PlaybackState.PAUSED and self._audio is audio:
                    await asyncio.sleep(0.1)
                # Exit if stopped/ended, superseded by a newer audio, or track finished
                if (
                    self._audio is not audio
                    or self._track_completed
                    or self._state in (PlaybackState.STOPPED, PlaybackState.ENDED)
                ):
                    break
                self._maybe_start_prefetch()
                await asyncio.sleep(0.5)
        except Exception as e:  # noqa: BLE001 - flet layer errors must not kill the loop
            for cb in self._on_error:
                cb(f"Playback error: {e}")
        finally:
            if self._audio is audio:
                self._audio = None
            try:
                await audio.release()
            except Exception:  # noqa: BLE001, S110 - already released
                pass

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

    def _on_duration_change(self, audio, duration) -> None:
        """Handle duration change event from flet-audio."""
        if audio is not self._audio:
            return
        duration = self._to_seconds(duration)
        if duration <= 0:
            return
        # 播放器上报的是真实时长。ffprobe 失败时按 128kbps 估算的值可能偏差
        # 数倍(高码率下估算偏长,进度条会提前卡在某个比例),"只增不减"会
        # 永远拒绝纠正,因此直接采用上报值。
        self._duration = duration
        for cb in self._on_progress_change:
            cb(self._progress, self._duration)

    def _on_position_change(self, audio, position) -> None:
        """Handle position change event from flet-audio."""
        if audio is not self._audio:
            return
        if self._seeking:
            # seek 完成事件可能丢失:超过 1 秒后不再抑制进度更新,避免进度条卡死
            if time.monotonic() - self._seek_requested_at < 1.0:
                return
            self._seeking = False
        # 节流:位置事件频率很高,限制到最多约 5 次/秒,足够流畅且不刷爆补丁
        now = time.monotonic()
        if now - self._last_progress_emit < 0.2:
            return
        self._last_progress_emit = now
        position = self._to_seconds(position)
        # 音频尾部上报的位置可能略超已知时长(解码/取整误差),
        # 不钳制会让 Slider.value 超过 max 触发 flet 校验错误
        ratio = position / self._duration if self._duration > 0 else 0.0
        self._progress = min(max(ratio, 0.0), 1.0)
        for cb in self._on_progress_change:
            cb(self._progress, self._duration)

    def _on_seek_complete(self, audio) -> None:
        """Handle seek completion from flet-audio."""
        if audio is self._audio:
            self._seeking = False

    def _on_flet_audio_state_change(self, audio, state) -> None:
        """Handle state change event from flet-audio (converts fta.AudioState to our PlaybackState)."""
        if audio is not self._audio:
            return
        # Map fta.AudioState to our PlaybackState
        if state == fta.AudioState.PLAYING or state == "playing":
            self._state = PlaybackState.PLAYING
        elif state == fta.AudioState.PAUSED or state == "paused":
            self._state = PlaybackState.PAUSED
        elif state == fta.AudioState.STOPPED or state == "stopped":
            self._state = PlaybackState.STOPPED
        elif state == fta.AudioState.COMPLETED or state == "completed":
            # 曲目自然播完:只打完成标记,不改全局状态。
            # 直接置 ENDED 会让播放循环在每首歌播完后退出,
            # 单曲循环/自动连播因此失效;会话是否结束由播放循环按模式决定。
            self._track_completed = True
        else:
            # Unknown state, default to STOPPED
            self._state = PlaybackState.STOPPED
        for cb in self._on_state_change:
            cb(self._state)

    def _discard_single_loop_temp(self) -> None:
        """丢弃单曲循环复用的临时文件(模式切换/切歌/停止时)。"""
        if self._single_loop_temp is None:
            return
        self._temp_manager.unregister_file(self._single_loop_temp)
        try:
            self._single_loop_temp.unlink(missing_ok=True)
        except OSError:
            pass
        self._single_loop_temp = None
        self._single_loop_song = None

    async def _acquire_temp(self, item: QueueItem) -> Path:
        """获取曲目的临时文件:命中预取缓存 > 等待进行中的预取 > 现场下载。"""
        cached = self._prefetched_paths.pop(item.song_id, None)
        if cached is not None and cached.exists():
            return cached
        pending = self._prefetch_tasks.pop(item.song_id, None)
        if pending is not None:
            path = await pending
            if path is not None and path.exists():
                return path
        path = await self._download_to_temp(item)
        self._temp_manager.register_file(path)
        return path

    async def _prefetch_download(self, item: QueueItem) -> Path | None:
        """后台预下载一首歌;失败返回 None(正式播放时会重新下载)。"""
        try:
            path = await self._download_to_temp(item)
        except Exception:  # noqa: BLE001 - 预取失败不打扰用户
            self._prefetch_tasks.pop(item.song_id, None)
            return None
        self._prefetch_tasks.pop(item.song_id, None)
        self._temp_manager.register_file(path)
        self._prefetched_paths[item.song_id] = path
        return path

    def _maybe_start_prefetch(self) -> None:
        """当前歌曲剩余不足 20 秒且存在下一首时,提前在后台下载下一首。

        单曲循环重播当前曲目,无需预取;随机模式下预取目标可能与实际
        下一首不同,预取结果会留在缓存里供后续命中,不影响正确性。
        """
        if self._mode == PlaybackMode.SINGLE_LOOP:
            return
        if self._state != PlaybackState.PLAYING or self._audio is None:
            return
        if len(self._playlist) < 2 or self._duration <= 0:
            return
        if self._duration * (1.0 - self._progress) >= 20.0:
            return
        next_item = self._playlist[1]
        if next_item.song_id in self._prefetched_paths or next_item.song_id in self._prefetch_tasks:
            return
        self._prefetch_tasks[next_item.song_id] = asyncio.create_task(
            self._prefetch_download(next_item)
        )

    async def _download_to_temp(self, item: QueueItem) -> Path:
        """Download song to temp file."""
        from musicdl import (
            DownloadError,
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
        except MusicDLException as e:
            # Wrap as DownloadError with context for proper handling upstream
            raise DownloadError(
                f"Failed to download song {item.song_id} to temp: {e}",
                song_id=item.song_id,
                output_path=temp_path,
                original=e,
            ) from e

    def add_on_state_change(self, callback: Callable[[PlaybackState], None]) -> None:
        self._on_state_change.append(callback)

    def add_on_progress_change(self, callback: Callable[[float, float], None]) -> None:
        self._on_progress_change.append(callback)

    def add_on_track_change(self, callback: Callable[[QueueItem | None], None]) -> None:
        self._on_track_change.append(callback)

    def add_on_error(self, callback: Callable[[str], None]) -> None:
        self._on_error.append(callback)

    def remove_on_state_change(self, callback: Callable[[PlaybackState], None]) -> None:
        if callback in self._on_state_change:
            self._on_state_change.remove(callback)

    def remove_on_progress_change(self, callback: Callable[[float, float], None]) -> None:
        if callback in self._on_progress_change:
            self._on_progress_change.remove(callback)

    def remove_on_track_change(self, callback: Callable[[QueueItem | None], None]) -> None:
        if callback in self._on_track_change:
            self._on_track_change.remove(callback)

    def remove_on_error(self, callback: Callable[[str], None]) -> None:
        if callback in self._on_error:
            self._on_error.remove(callback)

    def add_on_mode_change(self, callback: Callable[[PlaybackMode], None]) -> None:
        self._on_mode_change.append(callback)

    def remove_on_mode_change(self, callback: Callable[[PlaybackMode], None]) -> None:
        if callback in self._on_mode_change:
            self._on_mode_change.remove(callback)