"""Playback bar UI component."""

import flet as ft

from musicdl_gui.playback.service import PlaybackMode, PlaybackState


class PlaybackBar(ft.Container):
    """Bottom playback bar with controls."""

    def __init__(
        self,
        playback_service,
        on_mode_change,
        on_fullscreen_click,
    ) -> None:
        self._service = playback_service
        self._on_mode_change = on_mode_change
        self._on_fullscreen_click = on_fullscreen_click

        # Playback controls
        self.prev_button = ft.IconButton(
            icon=ft.Icons.SKIP_PREVIOUS,
            icon_size=24,
            on_click=lambda e: self._service.previous_track(),
            tooltip="Previous",
        )
        self.play_pause_button = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_size=32,
            on_click=self._on_play_pause,
            tooltip="Play/Pause",
        )
        self.next_button = ft.IconButton(
            icon=ft.Icons.SKIP_NEXT,
            icon_size=24,
            on_click=lambda e: self._service.next_track(),
            tooltip="Next",
        )

        # Progress bar
        self.progress_slider = ft.Slider(
            min=0,
            max=100,
            value=0,
            expand=True,
            on_change=self._on_slider_change,
            on_change_end=self._on_progress_change_end,
        )

        # Time display
        self.current_time_text = ft.Text("0:00", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
        self.duration_text = ft.Text("0:00", size=11, color=ft.Colors.ON_SURFACE_VARIANT)

        # Mode selector
        self.mode_button = ft.PopupMenuButton(
            icon=ft.Icons.REPEAT,
            tooltip="Playback Mode",
            items=[
                ft.PopupMenuItem(
                    content=ft.Text("Sequential"),
                    on_click=lambda e: self._on_mode_change(PlaybackMode.SEQUENTIAL),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Single Loop"),
                    on_click=lambda e: self._on_mode_change(PlaybackMode.SINGLE_LOOP),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Random"),
                    on_click=lambda e: self._on_mode_change(PlaybackMode.RANDOM),
                ),
            ],
        )

        # Fullscreen button
        self.fullscreen_button = ft.IconButton(
            icon=ft.Icons.FULLSCREEN,
            on_click=lambda e: self._on_fullscreen_click(),
            tooltip="Fullscreen Player",
        )

        # Current track info
        self.track_title = ft.Text("", size=12, weight=ft.FontWeight.W_500, overflow=ft.TextOverflow.ELLIPSIS)
        self.track_artist = ft.Text("", size=11, color=ft.Colors.ON_SURFACE_VARIANT, overflow=ft.TextOverflow.ELLIPSIS)

        super().__init__(
            padding=ft.Padding(16, 8, 16, 8),
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                left=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            ),
            content=ft.Column(
                spacing=4,
                controls=[
                    # Track info row
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.MUSIC_NOTE, size=16, color=ft.Colors.PRIMARY),
                            ft.Column(
                                spacing=1,
                                controls=[
                                    self.track_title,
                                    self.track_artist,
                                ],
                            ),
                        ],
                    ),
                    # Controls row
                    ft.Row(
                        spacing=8,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            self.mode_button,
                            self.prev_button,
                            self.play_pause_button,
                            self.next_button,
                            ft.Container(
                                expand=True,
                                content=ft.Row(
                                    spacing=8,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                                        self.current_time_text,
                                        self.progress_slider,
                                        self.duration_text,
                                    ],
                                ),
                            ),
                            self.fullscreen_button,
                        ],
                    ),
                ],
            ),
        )

        # Register callbacks
        self._service.set_on_track_change(self._on_track_change)
        self._service.set_on_state_change(self._on_state_change)
        self._service.set_on_progress_change(self._on_progress_change)

    def _on_play_pause(self, e) -> None:
        if self._service.state == PlaybackState.PLAYING:
            self._service.pause()
        else:
            self._service.play()

    def _on_slider_change(self, e) -> None:
        # Update time display while dragging
        progress = e.control.value / 100
        duration = self._service.duration
        current = progress * duration
        self.current_time_text.value = self._format_time(current)
        self.current_time_text.update()

    def _on_progress_change_end(self, e) -> None:
        # Seek to new position
        progress = e.control.value / 100
        self._service.seek(progress)

    def _on_track_change(self, item) -> None:
        if item:
            self.track_title.value = item.title
            self.track_artist.value = item.singer
        else:
            self.track_title.value = ""
            self.track_artist.value = ""
        self.track_title.update()
        self.track_artist.update()

    def _on_state_change(self, state: PlaybackState) -> None:
        if state == PlaybackState.PLAYING:
            self.play_pause_button.icon = ft.Icons.PAUSE
            self.play_pause_button.tooltip = "Pause"
        else:
            self.play_pause_button.icon = ft.Icons.PLAY_ARROW
            self.play_pause_button.tooltip = "Play"
        self.play_pause_button.update()

    def _on_progress_change(self, progress: float, duration: float) -> None:
        self.progress_slider.value = progress * 100
        self.current_time_text.value = self._format_time(progress * duration)
        self.duration_text.value = self._format_time(duration)
        self.progress_slider.update()
        self.current_time_text.update()
        self.duration_text.update()

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"