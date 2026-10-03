"""Track list component with right-click context menu."""

import inspect
from collections.abc import Callable

import flet as ft

from musicdl import PlaylistTrack


class TrackList(ft.ListView):
    def __init__(
        self,
        tracks: list[PlaylistTrack],
        on_download: Callable,
        on_play: Callable,
    ) -> None:
        super().__init__(
            expand=True,
            spacing=2,
            padding=8,
        )
        self._on_download_cb = on_download
        self._on_play_cb = on_play

        self.controls = [
            self._create_track_tile(track, index)
            for index, track in enumerate(tracks)
        ]

    def _run_callback(self, callback: Callable | None, track: PlaylistTrack) -> None:
        """Invoke a callback, scheduling it on the page loop when it is async."""
        if callback is None or self.page is None:
            return
        if inspect.iscoroutinefunction(callback):
            self.page.run_task(callback, track)
        else:
            callback(track)

    def _create_track_tile(self, track: PlaylistTrack, index: int) -> ft.Container:
        """Create a track tile with context menu."""
        # Create menu items - PopupMenuItem in Flet 1.0 doesn't support leading parameter
        menu_items = [
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PLAY_ARROW, size=16),
                        ft.Text("Play"),
                    ],
                    spacing=8,
                ),
                on_click=lambda e, t=track: self._run_callback(self._on_play_cb, t),
            ),
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DOWNLOAD, size=16),
                        ft.Text("Download"),
                    ],
                    spacing=8,
                ),
                on_click=lambda e, t=track: self._run_callback(self._on_download_cb, t),
            ),
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ADD, size=16),
                        ft.Text("Add to Queue"),
                    ],
                    spacing=8,
                ),
                on_click=lambda e, t=track: self._on_add_to_queue(t),
            ),
        ]

        return ft.Container(
            content=ft.Row(
                expand=True,
                controls=[
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.MUSIC_NOTE),
                        title=ft.Text(f"{track.singer} - {track.name}"),
                        subtitle=ft.Text(track.duration),
                        dense=True,
                    ),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        items=menu_items,
                    ),
                ],
            ),
            padding=ft.Padding(0, 0, 8, 0),
            expand=True,
        )

    def _on_add_to_queue(self, track: PlaylistTrack) -> None:
        # Could add to download queue
        pass

    def update_tracks(self, tracks: list[PlaylistTrack]) -> None:
        """Update tracks list."""
        self.controls = [
            self._create_track_tile(track, index)
            for index, track in enumerate(tracks)
        ]
        self.update()