"""Playlist browser tab."""

import flet as ft
from pathlib import Path

from musicdl_gui.api import ApiClient
from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.components.playlist_card import PlaylistCard
from musicdl_gui.components.track_list import TrackList


class PlaylistBrowserTab(ft.Column):
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
                    ft.FilledButton(
                        content=ft.Text("Download All"),
                        icon=ft.Icons.DOWNLOAD,
                        on_click=lambda e: self._on_download_all(),
                    ),
                    ft.OutlinedButton(
                        content=ft.Text("Add to Queue"),
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