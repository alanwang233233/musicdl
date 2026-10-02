"""Playlist info card component."""

import flet as ft

from musicdl import Playlist


class PlaylistCard(ft.Card):
    def __init__(self, playlist: Playlist):
        super().__init__()
        self.playlist = playlist
        self.content = ft.Container(
            padding=16,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=16,
                        controls=[
                            ft.Image(
                                src=playlist.cover_image,
                                width=100,
                                height=100,
                                fit=ft.BoxFit.COVER,
                                border_radius=8,
                            ),
                            ft.Column(
                                expand=True,
                                spacing=4,
                                controls=[
                                    ft.Text(
                                        playlist.name,
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"by {playlist.creator.name}",
                                        size=14,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    ft.Text(
                                        f"{playlist.song_count} songs",
                                        size=14,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        )