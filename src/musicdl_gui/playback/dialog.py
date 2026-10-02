"""Fullscreen playback dialog."""

import flet as ft

from musicdl_gui.playback.service import PlaybackMode, PlaybackState


class PlaybackDialog(ft.AlertDialog):
    """Fullscreen playback dialog with progress drag."""

    def __init__(self, playback_service, on_mode_change) -> None:
        self._service = playback_service
        self._on_mode_change = on_mode_change

        # Album art / cover
        self.cover_image = ft.Image(
            src="",
            width=300,
            height=300,
            fit=ft.BoxFit.COVER,
            border_radius=12,
        )

        # Track info
        self.title_text = ft.Text("", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
        self.artist_text = ft.Text("", size=16, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER)

        # Progress
        self.progress_slider = ft.Slider(
            min=0,
            max=100,
            value=0,
            on_change=self._on_slider_change,
            on_change_end=self._on_progress_change_end,
        )
        self.current_time = ft.Text("0:00", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.duration_text = ft.Text("0:00", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

        # Controls
        self.prev_button = ft.IconButton(
            icon=ft.Icons.SKIP_PREVIOUS,
            icon_size=28,
            on_click=lambda e: self._service.previous_track(),
        )
        self.play_pause_button = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_size=48,
            on_click=self._on_play_pause,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.PRIMARY,
                color=ft.Colors.ON_PRIMARY,
            ),
        )
        self.next_button = ft.IconButton(
            icon=ft.Icons.SKIP_NEXT,
            icon_size=28,
            on_click=lambda e: self._service.next_track(),
        )

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

        # Close button
        self.close_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            on_click=lambda e: self._close(),
            tooltip="Close",
        )

        # Progress time
        self.current_time = ft.Text("0:00", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.duration_text = ft.Text("0:00", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

        super().__init__(
            modal=True,
            content=ft.Container(
                width=400,
                padding=24,
                content=ft.Column(
                    spacing=20,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        # Close button row
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            controls=[self.close_button],
                        ),
                        # Album art
                        self.cover_image,
                        # Track info
                        ft.Column(
                            spacing=4,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                self.title_text,
                                self.artist_text,
                            ],
                        ),
                        # Progress
                        ft.Row(
                            spacing=8,
                            controls=[
                                self.current_time,
                                self.progress_slider,
                                self.duration_text,
                            ],
                        ),
                        # Controls
                        ft.Row(
                            spacing=16,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.SHUFFLE,
                                    icon_size=20,
                                    on_click=lambda e: setattr(self._service, "mode", PlaybackMode.RANDOM),
                                    tooltip="Shuffle",
                                ),
                                self.prev_button,
                                self.play_pause_button,
                                self.next_button,
                                ft.IconButton(
                                    icon=ft.Icons.REPEAT,
                                    icon_size=20,
                                    on_click=lambda e: self._cycle_mode(),
                                    tooltip="Repeat Mode",
                                ),
                            ],
                        ),
                        # Mode display
                        ft.Text(
                            "",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            ),
        )

        # Register callbacks
        self._service.set_on_track_change(self._on_track_change)
        self._service.set_on_state_change(self._on_state_change)
        self._service.set_on_progress_change(self._on_service_progress_change)

    def _on_play_pause(self, e) -> None:
        if self._service.state == PlaybackState.PLAYING:
            self._service.pause()
        else:
            self._service.play()

    def _on_slider_change(self, e) -> None:
        progress = e.control.value / 100
        duration = self._service.duration
        current = progress * duration
        self.current_time.value = self._format_time(current)
        self.current_time.update()

    def _on_progress_change_end(self, e) -> None:
        progress = e.control.value / 100
        self._service.seek(progress)

    def _on_track_change(self, item) -> None:
        if item:
            self.title_text.value = item.title
            self.artist_text.value = item.singer
            # In real implementation, fetch cover image
            # self.cover_image.src = item.picimg or ""
        else:
            self.title_text.value = ""
            self.artist_text.value = ""
        self.title_text.update()
        self.artist_text.update()

    def _on_state_change(self, state: PlaybackState) -> None:
        if state == PlaybackState.PLAYING:
            self.play_pause_button.icon = ft.Icons.PAUSE
        else:
            self.play_pause_button.icon = ft.Icons.PLAY_ARROW
        self.play_pause_button.update()

    def _on_service_progress_change(self, progress: float, duration: float) -> None:
        self.progress_slider.value = progress * 100
        self.current_time.value = self._format_time(progress * duration)
        self.duration_text.value = self._format_time(duration)
        self.progress_slider.update()
        self.current_time.update()
        self.duration_text.update()

    def _cycle_mode(self) -> None:
        modes = [PlaybackMode.SEQUENTIAL, PlaybackMode.SINGLE_LOOP, PlaybackMode.RANDOM]
        current = self._service.mode
        idx = modes.index(current) if current in modes else 0
        next_mode = modes[(idx + 1) % len(modes)]
        self._service.mode = next_mode

    def _close(self) -> None:
        self.open = False
        self.update()

    def show(self) -> None:
        self.open = True
        self.update()

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"