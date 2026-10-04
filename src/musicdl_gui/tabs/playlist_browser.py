"""Playlist browser tab."""

import random
from pathlib import Path

import flet as ft

from musicdl import MusicDLException
from musicdl_gui.api import ApiClient
from musicdl_gui.components.playlist_card import PlaylistCard
from musicdl_gui.components.track_list import TrackList
from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.input_utils import extract_id
from musicdl_gui.models import QueueItem
from musicdl_gui.playback import PlaybackMode, PlaybackService, PlaybackState
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.snack import show_snack


class PlaylistBrowserTab(ft.Column):
    def __init__(
        self,
        config_mgr: ConfigManager,
        download_queue: DownloadQueue,
        error_log: ErrorLog,
        playback_service: PlaybackService,
    ):
        super().__init__(expand=True, spacing=16)
        self._config_mgr = config_mgr
        self._queue = download_queue
        self._error_log = error_log
        self._playback_service = playback_service
        self._api: ApiClient | None = None
        self._api_config = None
        self._current_playlist = None

        self.id_input = ft.TextField(
            label="Playlist ID",
            hint_text="Enter playlist ID",
            expand=True,
        )
        self.fetch_button = ft.FilledButton(
            content=ft.Text("Fetch"),
            icon=ft.Icons.SEARCH,
            on_click=self._on_fetch,
        )
        self.progress_bar = ft.ProgressBar(visible=False)
        self.content_area = ft.Column(expand=True)

        self.controls = [
            ft.Row(
                spacing=8,
                controls=[self.id_input, self.fetch_button],
            ),
            self.progress_bar,
            self.content_area,
        ]

    async def _show_snack(self, message: str) -> None:
        show_snack(self.page, message)

    async def _on_fetch(self, e):
        # 支持直接输入 ID 或粘贴形如 https://music.xxx.com/xxx?id=2249180720 的链接
        playlist_id = extract_id(self.id_input.value)
        if not playlist_id:
            return

        # Lock button during fetch
        self.fetch_button.disabled = True
        self.fetch_button.update()

        self.progress_bar.visible = True
        self.progress_bar.update()

        try:
            config = self._config_mgr.get_config()
            if self._api is None or self._api_config != config:
                if self._api is not None:
                    self._api.close()
                self._api = ApiClient(config)
                self._api_config = config
            playlist = await self._api.fetch_playlist(playlist_id)
            self._current_playlist = playlist
            self._update_content(playlist)
        except MusicDLException as exc:
            self._error_log.log_exception(exc, "playlist_browser", {"playlist_id": playlist_id})
            await self._show_snack(f"Error: {exc}")
        finally:
            self.progress_bar.visible = False
            self.progress_bar.update()
            # Unlock button
            self.fetch_button.disabled = False
            self.fetch_button.update()

    def _update_content(self, playlist):
        self.content_area.controls = [
            PlaylistCard(playlist),
            ft.Row(
                spacing=8,
                controls=[
                    ft.FilledButton(
                        content=ft.Text("Download All"),
                        icon=ft.Icons.DOWNLOAD,
                        on_click=self._on_download_all,
                    ),
                    ft.OutlinedButton(
                        content=ft.Text("Play"),
                        icon=ft.Icons.PLAY_ARROW,
                        on_click=self._on_play_all,
                    ),
                ],
            ),
            TrackList(
                tracks=playlist.songs,
                on_download=self._on_track_download,
                on_play=self._on_track_play,
                on_play_next=self._on_track_play_next,
            ),
        ]
        self.content_area.update()

    async def _on_track_download(self, track):
        """Download a single track from the playlist."""
        if not self._current_playlist:
            await self._show_snack("No playlist loaded")
            return
        config = self._config_mgr.load()
        output_dir = Path(config.get("output_dir", "./music"))
        self._queue.add_playlist_single_track(self._current_playlist, track, config.get("default_level", "standard"), output_dir)
        self._queue.start()
        await self._show_snack(f"Downloading: {track.singer} - {track.name}")

    def _make_playback_item(self, track, config: dict) -> QueueItem:
        """Build the playback QueueItem for one playlist track."""
        output_dir = Path(config.get("output_dir", "./music"))
        return QueueItem(
            song_id=track.id,
            title=track.name,
            singer=track.singer,
            playlist=self._current_playlist.name,
            quality=config.get("default_level", "standard"),
            output_path=output_dir / f"{track.singer} - {track.name}.mp3",
            picimg=track.picimg or "",
        )

    async def _on_track_play(self, track):
        """Play a single track from the playlist."""
        if not self._current_playlist:
            await self._show_snack("No playlist loaded")
            return
        config = self._config_mgr.load()
        item = self._make_playback_item(track, config)
        # 先停止当前播放,避免旧曲目在替换播放列表后继续占用临时文件(对齐 song_downloader._on_play 的修复)
        self._playback_service.stop()
        # Add to playback service and play
        self._playback_service.set_playlist([item])
        self._playback_service.play()
        await self._show_snack(f"Playing: {track.singer} - {track.name}")

    async def _on_play_all(self):
        """把整个歌单加入播放列表。

        随机模式下先打乱再放入;正在播放(或缓冲)时只入队、不打断当前曲目,
        新歌排在当前队列末尾;否则立即开始播放。
        """
        if not self._current_playlist:
            await self._show_snack("No playlist loaded")
            return
        config = self._config_mgr.load()
        items = [self._make_playback_item(track, config) for track in self._current_playlist.songs]
        if not items:
            await self._show_snack("歌单没有可播放的歌曲")
            return
        if self._playback_service.mode == PlaybackMode.RANDOM:
            random.shuffle(items)
        for item in items:
            self._playback_service.add_to_playlist(item)
        if self._playback_service.state in (PlaybackState.PLAYING, PlaybackState.BUFFERING):
            # 正在播放:只入队,不打断当前曲目
            await self._show_snack(f"已加入播放列表({len(items)} 首)")
            return
        self._playback_service.play()
        first = items[0]
        await self._show_snack(f"开始播放:{first.singer} - {first.title}(共 {len(items)} 首)")

    async def _on_track_play_next(self, track):
        """把单曲插入为下一首播放(当前曲目之后)。"""
        if not self._current_playlist:
            await self._show_snack("No playlist loaded")
            return
        config = self._config_mgr.load()
        item = self._make_playback_item(track, config)
        self._playback_service.add_to_playlist_next(item)
        await self._show_snack(f"下一首播放:{track.singer} - {track.name}")

    async def _on_download_all(self):
        if self._current_playlist:
            config = self._config_mgr.load()
            output_dir = Path(config.get("output_dir", "./music"))
            self._queue.add_playlist(self._current_playlist, config.get("default_level", "standard"), output_dir)
            self._queue.start()
            await self._show_snack("Added to download queue")