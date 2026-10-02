"""Error log table component."""

import flet as ft
from musicdl_gui.error_log import ErrorLogEntry


class ErrorLogTable(ft.DataTable):
    def __init__(self):
        super().__init__(
            columns=[
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("Level")),
                ft.DataColumn(ft.Text("Source")),
                ft.DataColumn(ft.Text("Message")),
                ft.DataColumn(ft.Text("Exception")),
            ],
            rows=[],
        )

    def update_entries(self, entries: list[ErrorLogEntry]):
        self.rows = []
        for entry in entries:
            level_color = {
                "ERROR": ft.Colors.RED,
                "WARNING": ft.Colors.ORANGE,
                "INFO": ft.Colors.BLUE,
            }.get(entry.level, ft.Colors.GREY)

            self.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(entry.timestamp[:19])),
                        ft.DataCell(ft.Text(entry.level, color=level_color)),
                        ft.DataCell(ft.Text(entry.source)),
                        ft.DataCell(ft.Text(entry.message, expand=True)),
                        ft.DataCell(ft.Text(entry.exception_type or "-")),
                    ]
                )
            )
        self.update()