"""Error log tab placeholder."""

import flet as ft


class ErrorLogTab(ft.UserControl):
    def __init__(self, error_log):
        super().__init__()
        self._error_log = error_log

    def build(self):
        return ft.Container(
            alignment=ft.alignment.center,
            content=ft.Text("Error Log Tab - Coming Soon", size=24),
        )