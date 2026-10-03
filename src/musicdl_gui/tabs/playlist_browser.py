"""Playlist browser tab."""

from pathlib import Path

import flet as ft

from musicdl import MusicDLException
from musicdl_gui.api import ApiClient
from musicdl_gui.components.playlist_card import PlaylistCard
from musicdl_gui.components.track_list import TrackList
from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.models import QueueItem
from musicdl_gui.playback import PlaybackService
from musicdl_gui.queue import DownloadQueue


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
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        self.page.overlay.append(snack)
        self.page.update()

    async def _on_fetch(self, e):
        playlist_id = self.id_input.value.strip()
        if not playlist_id:
            return

        # Lock button during fetch
        self.fetch_button.disabled = True
        self.fetch_button.update()

        self.progress_bar.visible = True
        self.progress_bar.update()

        try:
            config = self._config_mgr.get_config()
            self._api = ApiClient(config)
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
                        on_click=lambda e: self._on_download_all(),
                    ),
                    ft.OutlinedButton(
                        content=ft.Text("Add to Queue"),
                        icon=ft.Icons.ADD,
                        on_click=lambda e: self._on_add_to_queue(),
                    ),
                ],
            ),
            TrackList(
                tracks=playlist.songs,
                on_download=self._on_track_download,
                on_play=self._on_track_play,
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

    async def _on_track_play(self, track):
        """Play a single track from the playlist."""
        if not self._current_playlist:
            await self._show_snack("No playlist loaded")
            return
        config = self._config_mgr.load()
        output_dir = Path(config.get("output_dir", "./music"))
        item = QueueItem(
            song_id=track.id,
            title=track.name,
            singer=track.singer,
            playlist=self._current_playlist.name,
            quality=config.get("default_level", "standard"),
            output_path=output_dir / f"{track.singer} - {track.name}.mp3",
            picimg=track.picimg or "",
        )
        # Add to playback service and play
        self._playback_service.set_playlist([item])
        self._playback_service.play()
        await self._show_snack(f"Playing: {track.singer} - {track.name}")

    async def _on_download_all(self):
        if self._current_playlist:
            config = self._config_mgr.load()
            output_dir = Path(config.get("output_dir", "./music"))
            self._queue.add_playlist(self._current_playlist, config.get("default_level", "standard"), output_dir)
            self._queue.start()
            await self._show_snack("Added to download queue")

    async def _on_add_to_queue(self):
        await self._on_download_all()