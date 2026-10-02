"""Song downloader tab placeholder."""

import flet as ft


class SongDownloaderTab(ft.UserControl):
    def __init__(self, config_mgr, download_queue, error_log):
        super().__init__()
        self._config_mgr = config_mgr
        self._queue = download_queue
        self._error_log = error_log

    def build(self):
        return ft.Container(
            alignment=ft.alignment.center,
            content=ft.Text("Song Downloader Tab - Coming Soon", size=24),
        )