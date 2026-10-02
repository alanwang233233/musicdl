"""Download queue table component."""

import flet as ft
from musicdl_gui.models import QueueItem, QueueStatus


class QueueTable(ft.DataTable):
    def __init__(self):
        super().__init__(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Title")),
                ft.DataColumn(ft.Text("Singer")),
                ft.DataColumn(ft.Text("Playlist")),
                ft.DataColumn(ft.Text("Quality")),
                ft.DataColumn(ft.Text("Progress")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=[],
        )

    def update_items(self, items: list[QueueItem]):
        self.rows = []
        for idx, item in enumerate(items, start=1):
            status_color = {
                QueueStatus.PENDING: ft.Colors.GREY,
                QueueStatus.DOWNLOADING: ft.Colors.BLUE,
                QueueStatus.COMPLETED: ft.Colors.GREEN,
                QueueStatus.FAILED: ft.Colors.RED,
                QueueStatus.SKIPPED: ft.Colors.ORANGE,
            }.get(item.status, ft.Colors.GREY)

            actions = ft.Row(spacing=0)
            if item.status == QueueStatus.FAILED:
                actions.controls.append(
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        tooltip="Retry",
                        on_click=lambda e, sid=item.song_id: self._on_retry(sid),
                    )
                )
            actions.controls.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    tooltip="Remove",
                    on_click=lambda e, sid=item.song_id: self._on_remove(sid),
                )
            )

            self.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx))),
                        ft.DataCell(ft.Text(item.title)),
                        ft.DataCell(ft.Text(item.singer)),
                        ft.DataCell(ft.Text(item.playlist)),
                        ft.DataCell(ft.Text(item.quality)),
                        ft.DataCell(
                            ft.ProgressBar(
                                value=item.progress,
                                width=100,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                item.status.value,
                                color=status_color,
                            )
                        ),
                        ft.DataCell(actions),
                    ]
                )
            )
        self.update()

    def _on_retry(self, song_id: int):
        pass

    def _on_remove(self, song_id: int):
        pass