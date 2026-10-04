"""Fullscreen playback dialog."""

import flet as ft

from musicdl_gui.playback.service import PlaybackMode, PlaybackState


class PlaybackDialog(ft.AlertDialog):
    """Fullscreen playback dialog with progress drag."""

    def __init__(self, page: ft.Page, playback_service, on_mode_change) -> None:
        self._page = page
        self._service = playback_service
        # 存为 _cb 后缀属性,避免遮蔽下方同名的方法(否则模式提示更新成为死代码)
        self._on_mode_change_cb = on_mode_change
        # 用户正在拖动进度条:期间忽略服务的进度回写,避免滑条来回打架
        self._scrubbing = False

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
                    on_click=lambda e: self._on_mode_change_cb(PlaybackMode.SEQUENTIAL),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Single Loop"),
                    on_click=lambda e: self._on_mode_change_cb(PlaybackMode.SINGLE_LOOP),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Random"),
                    on_click=lambda e: self._on_mode_change_cb(PlaybackMode.RANDOM),
                ),
            ],
        )

        # Close button
        self.close_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            on_click=lambda e: self._close(),
            tooltip="Close",
        )

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
        self._service.add_on_track_change(self._on_track_change)
        self._service.add_on_state_change(self._on_state_change)
        self._service.add_on_progress_change(self._on_service_progress_change)
        self._service.add_on_mode_change(self._on_mode_change)

    def _on_play_pause(self, e) -> None:
        if self._service.state == PlaybackState.PLAYING:
            self._service.pause()
        else:
            self._service.play()

    def _on_slider_change(self, e) -> None:
        self._scrubbing = True
        progress = e.control.value / 100
        duration = self._service.duration
        current = progress * duration
        self.current_time.value = self._format_time(current)
        self.current_time.update()

    def _on_progress_change_end(self, e) -> None:
        self._scrubbing = False
        progress = e.control.value / 100
        self._service.seek(progress)

    def _on_track_change(self, item) -> None:
        # 对话框未打开时子控件未挂载到页面,update() 会抛 RuntimeError;
        # 打开时由 show() 统一从服务同步最新状态
        if not self.open:
            return
        if item:
            self.title_text.value = item.title
            self.artist_text.value = item.singer
            # Load cover image from item's picimg
            self.cover_image.src = item.picimg or ""
        else:
            self.title_text.value = ""
            self.artist_text.value = ""
            self.cover_image.src = ""
        # 单次父级 update 批量同步,避免多补丁造成卡顿
        self.update()

    def _on_state_change(self, state: PlaybackState) -> None:
        if not self.open:
            return
        if state == PlaybackState.PLAYING:
            self.play_pause_button.icon = ft.Icons.PAUSE
        else:
            self.play_pause_button.icon = ft.Icons.PLAY_ARROW
        self.play_pause_button.update()

    def _on_service_progress_change(self, progress: float, duration: float) -> None:
        if not self.open:
            return
        if self._scrubbing:
            return  # 拖动期间不回写,避免与拖拽位置互相打架
        self.progress_slider.value = progress * 100
        self.current_time.value = self._format_time(progress * duration)
        self.duration_text.value = self._format_time(duration)
        # 单次父级 update 批量同步三个控件,避免每个事件发多个补丁造成卡顿
        self.update()

    def _cycle_mode(self) -> None:
        modes = [PlaybackMode.SEQUENTIAL, PlaybackMode.SINGLE_LOOP, PlaybackMode.RANDOM]
        current = self._service.mode
        idx = modes.index(current) if current in modes else 0
        next_mode = modes[(idx + 1) % len(modes)]
        self._service.mode = next_mode

    def _on_mode_change(self, mode: PlaybackMode) -> None:
        if not self.open:
            return
        mode_names = {
            PlaybackMode.SEQUENTIAL: "Sequential",
            PlaybackMode.SINGLE_LOOP: "Single Loop",
            PlaybackMode.RANDOM: "Random",
        }
        self.mode_button.tooltip = f"Playback Mode: {mode_names.get(mode, 'Unknown')}"
        self.mode_button.update()

    def _close(self) -> None:
        self._page.pop_dialog()

    def show(self) -> None:
        if self.open:
            return
        # 打开前先用当前播放状态同步一遍(关闭期间的服务回调都被跳过了)
        self._sync_from_service()
        self._page.show_dialog(self)

    def _sync_from_service(self) -> None:
        """Mirror current playback state onto the dialog controls (no update calls)."""
        item = self._service.current_item
        if item:
            self.title_text.value = item.title
            self.artist_text.value = item.singer
            self.cover_image.src = item.picimg or ""
        else:
            self.title_text.value = ""
            self.artist_text.value = ""
            self.cover_image.src = ""
        if self._service.state == PlaybackState.PLAYING:
            self.play_pause_button.icon = ft.Icons.PAUSE
        else:
            self.play_pause_button.icon = ft.Icons.PLAY_ARROW
        self.progress_slider.value = self._service.progress * 100
        self.current_time.value = self._format_time(self._service.progress * self._service.duration)
        self.duration_text.value = self._format_time(self._service.duration)
        mode_names = {
            PlaybackMode.SEQUENTIAL: "Sequential",
            PlaybackMode.SINGLE_LOOP: "Single Loop",
            PlaybackMode.RANDOM: "Random",
        }
        self.mode_button.tooltip = f"Playback Mode: {mode_names.get(self._service.mode, 'Unknown')}"

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"