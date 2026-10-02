"""Download queue table component - optimized for real-time updates."""

import flet as ft
from musicdl_gui.models import QueueItem, QueueStatus


class QueueRow(ft.Container):
    """Individual queue row with in-place updates."""

    def __init__(self, item: QueueItem, on_retry, on_remove, index: int):
        super().__init__()
        self.item = item
        self.on_retry = on_retry
        self.on_remove = on_remove
        self.index = index

        self.padding = ft.Padding(left=12, top=8, right=12, bottom=8)
        self.border = ft.Border(
            left=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        )
        self.content = self._build_content()

    def _build_content(self) -> ft.Row:
        status_colors = {
            QueueStatus.PENDING: ft.Colors.GREY,
            QueueStatus.DOWNLOADING: ft.Colors.BLUE,
            QueueStatus.COMPLETED: ft.Colors.GREEN,
            QueueStatus.FAILED: ft.Colors.RED,
            QueueStatus.SKIPPED: ft.Colors.ORANGE,
        }
        status_color = status_colors.get(self.item.status, ft.Colors.GREY)

        # Progress bar with percentage
        progress_bar = ft.ProgressBar(
            value=self.item.progress,
            width=120,
            height=6,
            color=ft.Colors.PRIMARY,
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            visible=self.item.status == QueueStatus.DOWNLOADING,
        )

        # Status badge
        status_badge = ft.Container(
            content=ft.Text(
                self.item.status.value,
                size=11,
                weight=ft.FontWeight.W_500,
                color=ft.Colors.WHITE,
            ),
            padding=ft.Padding(left=8, top=2, right=8, bottom=2),
            border_radius=12,
            bgcolor=status_color,
        )

        # Speed/ETA display
        speed_text = ft.Text(
            self._format_speed_eta(),
            size=10,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

        # Action buttons
        actions = ft.Row(spacing=4)
        if self.item.status == QueueStatus.FAILED:
            actions.controls.append(
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="Retry",
                    icon_size=16,
                    on_click=lambda e: self.on_retry(self.item.song_id),
                )
            )
        actions.controls.append(
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                tooltip="Remove",
                icon_size=16,
                on_click=lambda e: self.on_remove(self.item.song_id),
            )
        )

        return ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(f"{self.index}", size=12, width=30, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(self.item.title, size=12, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(self.item.singer, size=12, width=100, overflow=ft.TextOverflow.ELLIPSIS, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(self.item.playlist, size=12, width=80, overflow=ft.TextOverflow.ELLIPSIS, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(self.item.quality, size=11, width=70, color=ft.Colors.ON_SURFACE_VARIANT),
                progress_bar,
                status_badge,
                speed_text,
                actions,
            ],
        )

    def _format_speed_eta(self) -> str:
        if self.item.total_bytes > 0 and self.item.downloaded_bytes > 0:
            # Speed in KB/s (rough estimate)
            speed_kb = self.item.downloaded_bytes / 1024
            if speed_kb > 0:
                remaining = self.item.total_bytes - self.item.downloaded_bytes
                eta_seconds = remaining / (speed_kb * 1024) if speed_kb > 0 else 0
                if eta_seconds > 60:
                    return f"{speed_kb:.0f} KB/s · ETA {int(eta_seconds/60)}m"
                return f"{speed_kb:.0f} KB/s · ETA {int(eta_seconds)}s"
        return ""

    def update_item(self, item: QueueItem, index: int):
        """Update row with new item data in place."""
        self.item = item
        self.index = index
        self.content = self._build_content()
        self.update()


class QueueTable(ft.ListView):
    """Optimized queue table using ListView for better performance."""

    def __init__(self, on_retry, on_remove):
        super().__init__(
            expand=True,
            spacing=0,
            padding=ft.Padding(left=0, top=8, right=0, bottom=8),
            auto_scroll=False,
        )
        self.on_retry = on_retry
        self.on_remove = on_remove
        self._rows: dict[int, QueueRow] = {}
        self._item_order: list[int] = []

    def update_items(self, items: list[QueueItem]):
        """Update items efficiently - only rebuild changed rows."""
        # Build new order
        new_order = [item.song_id for item in items]
        
        # Update or create rows
        for index, item in enumerate(items):
            if item.song_id in self._rows:
                self._rows[item.song_id].update_item(item, index + 1)
            else:
                row = QueueRow(item, self.on_retry, self.on_remove, index + 1)
                self._rows[item.song_id] = row
                self.controls.append(row)
        
        # Remove rows for items no longer in list
        for song_id in list(self._rows.keys()):
            if song_id not in new_order:
                row = self._rows.pop(song_id)
                self.controls.remove(row)
        
        # Reorder controls to match item order
        self.controls.sort(key=lambda r: r.index if isinstance(r, QueueRow) else 999)
        
        self.update()

    def clear(self):
        """Clear all rows."""
        self._rows.clear()
        self.controls.clear()
        self.update()