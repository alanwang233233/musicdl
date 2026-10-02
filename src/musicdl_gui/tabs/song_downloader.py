"""Song downloader tab."""

import flet as ft
from pathlib import Path

from musicdl_gui.api import ApiClient
from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue, _sanitize_filename
from musicdl_gui.models import QueueItem, QueueStatus


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
        self._song_info = None

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
                controls=[self.quality_dropdown, self.download_button],
            ),
            self.progress_bar,
        ]

    async def _show_snack(self, message: str) -> None:
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        self.page.overlay.append(snack)
        self.page.update()

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
            await self._show_snack(f"Error: {exc}")
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
        )
        self._queue.add_item(item)
        self._queue.start()
        await self._show_snack("Added to download queue")