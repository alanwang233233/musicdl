"""Settings tab placeholder."""

import flet as ft


class SettingsTab(ft.UserControl):
    def __init__(self, config_mgr):
        super().__init__()
        self._config_mgr = config_mgr

    def build(self):
        return ft.Container(
            alignment=ft.alignment.center,
            content=ft.Text("Settings Tab - Coming Soon", size=24),
        )