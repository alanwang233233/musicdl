"""Download queue tab - optimized for real-time updates."""

import flet as ft

from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.components.queue_table import QueueTable


class DownloadQueueTab(ft.Column):
    def __init__(self, download_queue: DownloadQueue, error_log: ErrorLog):
        super().__init__(expand=True, spacing=16)
        self._queue = download_queue
        self._error_log = error_log
        self._table = QueueTable(
            on_retry=self._on_retry,
            on_remove=self._on_remove,
        )
        self._refresh_timer = None

        # Toolbar buttons
        self.clear_button = ft.OutlinedButton(
            content=ft.Text("Clear Completed"),
            icon=ft.Icons.CLEAR,
            on_click=self._on_clear,
        )
        self.retry_all_button = ft.OutlinedButton(
            content=ft.Text("Retry Failed"),
            icon=ft.Icons.REFRESH,
            on_click=self._on_retry_all,
        )
        self.clear_test_data_button = ft.OutlinedButton(
            content=ft.Text("Clear Test Data"),
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self._on_clear_test_data,
            style=ft.ButtonStyle(color=ft.Colors.ERROR),
        )

        # Status bar
        self.status_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

        self.controls = [
            ft.Row(
                spacing=8,
                controls=[
                    self.clear_button,
                    self.retry_all_button,
                    self.clear_test_data_button,
                ],
            ),
            ft.Container(
                content=ft.Column(
                    spacing=8,
                    controls=[
                        self.status_text,
                        ft.Container(
                            expand=True,
                            content=self._table,
                            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                            border_radius=8,
                        ),
                    ],
                ),
                expand=True,
            ),
        ]

    def _on_retry(self, song_id: int):
        self._queue.retry_item(song_id)
        self._queue.start()
        self._refresh_table()

    def _on_remove(self, song_id: int):
        self._queue.remove_item(song_id)
        self._refresh_table()

    def _on_clear(self, e):
        self._queue.clear_completed()
        self._refresh_table()

    def _on_clear_test_data(self, e):
        """Remove test data from queue."""
        self._queue.clear_completed()
        self._refresh_table()

    def _on_retry_all(self, e):
        items = self._queue.get_items()
        for item in items:
            if item.status.value == "failed":
                self._queue.retry_item(item.song_id)
        self._queue.start()
        self._refresh_table()

    def _refresh_table(self):
        items = self._queue.get_items()
        self._table.update_items(items)
        self._update_status(items)

    def _update_status(self, items: list):
        pending = sum(1 for i in items if i.status.value == "pending")
        downloading = sum(1 for i in items if i.status.value == "downloading")
        completed = sum(1 for i in items if i.status.value == "completed")
        failed = sum(1 for i in items if i.status.value == "failed")
        total = len(items)
        self.status_text.value = f"Total: {total} | Pending: {pending} | Downloading: {downloading} | Completed: {completed} | Failed: {failed}"
        self.status_text.update()

    def did_mount(self):
        self._refresh_table()
        # Use periodic refresh instead of callbacks for better performance
        self._refresh_timer = self.page.run_interval(self._refresh_table, 500)

    def will_unmount(self):
        if self._refresh_timer:
            self._refresh_timer.cancel()