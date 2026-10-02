"""Download queue tab placeholder."""

import flet as ft


class DownloadQueueTab(ft.UserControl):
    def __init__(self, download_queue, error_log):
        super().__init__()
        self._queue = download_queue
        self._error_log = error_log

    def build(self):
        return ft.Container(
            alignment=ft.alignment.center,
            content=ft.Text("Download Queue Tab - Coming Soon", size=24),
        )