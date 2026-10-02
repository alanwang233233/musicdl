"""Download queue tab - optimized for real-time updates."""

import asyncio

import flet as ft

from musicdl_gui.components.queue_table import QueueTable
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue


class DownloadQueueTab(ft.Column):
    def __init__(self, download_queue: DownloadQueue, error_log: ErrorLog):
        super().__init__(expand=True, spacing=16)
        self._queue = download_queue
        self._error_log = error_log
        self._table = QueueTable(
            on_retry=self._on_retry,
            on_remove=self._on_remove,
        )
        self._refresh_task = None

        # Toolbar buttons
        self.clear_button = ft.OutlinedButton(
            content=ft.Text("Clear Completed"),
            icon=ft.Icons.CLEAR,
            on_click=self._on_clear,
        )
        self.clear_all_button = ft.OutlinedButton(
            content=ft.Text("Clear All"),
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self._on_clear_all,
            style=ft.ButtonStyle(color=ft.Colors.ERROR),
        )
        self.stop_button = ft.OutlinedButton(
            content=ft.Text("Stop"),
            icon=ft.Icons.STOP,
            on_click=self._on_stop,
            style=ft.ButtonStyle(color=ft.Colors.ERROR),
        )
        self.retry_all_button = ft.OutlinedButton(
            content=ft.Text("Retry Failed"),
            icon=ft.Icons.REFRESH,
            on_click=self._on_retry_all,
        )

        # Status bar
        self.status_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

        self.controls = [
            ft.Row(
                spacing=8,
                controls=[
                    self.clear_button,
                    self.clear_all_button,
                    self.stop_button,
                    self.retry_all_button,
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
                            border=ft.Border(
                                left=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                            ),
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

    def _on_clear_all(self, e):
        self._queue.clear_all()
        self._refresh_table()

    def _on_stop(self, e):
        self._queue.stop()
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

    async def _refresh_loop(self):
        """Periodic refresh loop."""
        while True:
            await asyncio.sleep(0.5)
            self._refresh_table()

    def did_mount(self):
        self._refresh_table()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    def will_unmount(self):
        if self._refresh_task:
            self._refresh_task.cancel()