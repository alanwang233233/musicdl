"""Download queue tab."""

import flet as ft

from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.components.queue_table import QueueTable


class DownloadQueueTab(ft.Column):
    def __init__(self, download_queue: DownloadQueue, error_log: ErrorLog):
        super().__init__(expand=True, spacing=16)
        self._queue = download_queue
        self._error_log = error_log
        self._table = QueueTable()

        self._table._on_retry = self._on_retry
        self._table._on_remove = self._on_remove

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

        self.controls = [
            ft.Row(
                spacing=8,
                controls=[self.clear_button, self.retry_all_button],
            ),
            ft.Container(
                expand=True,
                content=self._table,
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

    def _on_retry_all(self, e):
        items = self._queue.get_items()
        for item in items:
            if item.status.value == "failed":
                self._queue.retry_item(item.song_id)
        self._queue.start()
        self._refresh_table()

    def _refresh_table(self):
        self._table.update_items(self._queue.get_items())

    def did_mount(self):
        self._refresh_table()
        self._queue._on_complete = lambda item: self._refresh_table()
        self._queue._on_error = lambda item, e: self._refresh_table()
        self._queue._on_status_change = lambda item, status: self._refresh_table()