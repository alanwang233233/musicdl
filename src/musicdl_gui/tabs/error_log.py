"""Error log tab."""

import flet as ft
from pathlib import Path

from musicdl_gui.error_log import ErrorLog
from musicdl_gui.components.error_log_table import ErrorLogTable


class ErrorLogTab(ft.Column):
    def __init__(self, error_log: ErrorLog):
        super().__init__(expand=True, spacing=16)
        self._error_log = error_log
        self._table = ErrorLogTable()

        self.clear_button = ft.OutlinedButton(
            content=ft.Text("Clear Log"),
            icon=ft.Icons.CLEAR,
            on_click=self._on_clear,
        )
        self.export_button = ft.OutlinedButton(
            content=ft.Text("Export"),
            icon=ft.Icons.DOWNLOAD,
            on_click=self._on_export,
        )

        self.controls = [
            ft.Row(
                spacing=8,
                controls=[self.clear_button, self.export_button],
            ),
            ft.Container(
                expand=True,
                content=self._table,
            ),
        ]

    def did_mount(self):
        self._refresh()
        self._error_log.register_callback(self._on_new_entry)

    def _on_new_entry(self, entry):
        self._refresh()

    def _refresh(self):
        entries = self._error_log.get_entries(limit=100)
        self._table.update_entries(entries)

    def _on_clear(self, e):
        self._error_log.clear()
        self._refresh()

    async def _on_export(self, e):
        file_picker = ft.FilePicker()
        self.page.services.append(file_picker)
        path = await file_picker.save_file_async()
        if path:
            self._error_log.export(Path(path))
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"Exported to {path}"))
            )