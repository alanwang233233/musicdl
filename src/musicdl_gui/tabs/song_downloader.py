"""Song downloader tab."""

from pathlib import Path

import flet as ft

from musicdl import MusicDLException
from musicdl_gui.api import ApiClient
from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.input_utils import extract_id
from musicdl_gui.models import QueueItem
from musicdl_gui.playback import PlaybackService, TempFileManager
from musicdl_gui.queue import DownloadQueue, _sanitize_filename
from musicdl_gui.snack import show_snack


class SongDownloaderTab(ft.Column):
    def __init__(
        self,
        config_mgr: ConfigManager,
        download_queue: DownloadQueue,
        error_log: ErrorLog,
    ):
        super().__init__(expand=True, spacing=16)
        self._config_mgr = config_mgr
        self._queue = download_queue
        self._error_log = error_log
        self._api: ApiClient | None = None
        self._api_config = None
        self._song_info = None
        self._playback_service: PlaybackService | None = None
        self._temp_manager = TempFileManager()

        self.id_input = ft.TextField(
            label="Song ID",
            hint_text="Enter song ID",
            expand=True,
        )
        self.preview_button = ft.FilledButton(
            content=ft.Text("Preview"),
            icon=ft.Icons.PREVIEW,
            on_click=self._on_preview,
        )
        self.play_button = ft.FilledButton(
            content=ft.Text("Play"),
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._on_play,
            disabled=True,
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
        self.download_button = ft.FilledButton(
            content=ft.Text("Download"),
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

        self.controls = [
            ft.Row(
                spacing=8,
                controls=[self.id_input, self.preview_button],
            ),
            self.info_card,
            ft.Row(
                spacing=8,
                controls=[self.quality_dropdown, self.play_button, self.download_button],
            ),
            self.progress_bar,
        ]

    def _set_playback_service(self, playback_service: PlaybackService) -> None:
        """Set the playback service (called after initialization)."""
        self._playback_service = playback_service

    async def _show_snack(self, message: str) -> None:
        show_snack(self.page, message)

    async def _on_preview(self, e):
        # 支持直接输入 ID 或粘贴形如 https://music.xxx.com/xxx?id=2249180720 的链接
        song_id = extract_id(self.id_input.value)
        if not song_id:
            return

        # Convert song ID before locking the UI - fail fast on non-numeric input
        try:
            numeric_id = int(song_id)
        except ValueError:
            await self._show_snack(f"无效的歌曲 ID: {song_id}")
            return

        # Lock button during preview
        self.preview_button.disabled = True
        self.preview_button.update()

        self.progress_bar.visible = True
        self.progress_bar.update()

        try:
            config = self._config_mgr.get_config()
            if self._api is None or self._api_config != config:
                if self._api is not None:
                    self._api.close()
                self._api = ApiClient(config)
                self._api_config = config
            self._song_info = await self._api.fetch_song_info(numeric_id)
            self._update_info_card()
            self.download_button.disabled = False
            self.download_button.update()
            self.play_button.disabled = False
            self.play_button.update()
        except MusicDLException as exc:
            self._error_log.log_exception(exc, "song_downloader", {"song_id": song_id})
            await self._show_snack(f"Error: {exc}")
        finally:
            self.progress_bar.visible = False
            self.progress_bar.update()
            # Unlock button
            self.preview_button.disabled = False
            self.preview_button.update()

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

    async def _on_play(self, e):
        if not self._song_info or not self._playback_service:
            return

        # Lock button during playback start
        self.play_button.disabled = True
        self.play_button.update()

        try:
            # Stop any existing playback, clear queue and UI
            self._playback_service.stop()

            # Create new playlist with this track as first item
            item = QueueItem(
                song_id=self._song_info.id,
                title=self._song_info.name,
                singer=self._song_info.singer,
                playlist="",
                quality=self.quality_dropdown.value,
                output_path=Path(""),
                picimg=self._song_info.picimg or "",
            )
            self._playback_service.set_playlist([item])
            self._playback_service.play()
            await self._show_snack("Playing...")
        except MusicDLException as exc:
            self._error_log.log_exception(exc, "song_downloader", {"song_id": self._song_info.id})
            await self._show_snack(f"Error: {exc}")
        finally:
            self.play_button.disabled = False
            self.play_button.update()

    async def _on_download(self, e):
        if not self._song_info:
            return

        config = self._config_mgr.load()
        output_dir = Path(config.get("output_dir", "./music"))
        quality = self.quality_dropdown.value

        singer = _sanitize_filename(self._song_info.singer)
        title = _sanitize_filename(self._song_info.name)
        item = QueueItem(
            song_id=self._song_info.id,
            title=self._song_info.name,
            singer=self._song_info.singer,
            playlist="",
            quality=quality,
            output_path=output_dir / f"{singer} - {title}.mp3",
            picimg=self._song_info.picimg or "",
        )
        self._queue.add_item(item)
        self._queue.start()
        await self._show_snack("Added to download queue")