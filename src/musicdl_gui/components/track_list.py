"""Track list component."""

import flet as ft
from musicdl import PlaylistTrack


class TrackList(ft.ListView):
    def __init__(self, tracks: list[PlaylistTrack]):
        super().__init__(
            expand=True,
            spacing=2,
            padding=8,
        )
        self.controls = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.MUSIC_NOTE),
                title=ft.Text(f"{track.singer} - {track.name}"),
                subtitle=ft.Text(track.duration),
            )
            for track in tracks
        ]