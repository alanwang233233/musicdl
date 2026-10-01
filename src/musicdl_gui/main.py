"""musicdl-gui - Flet application entry point."""

import flet as ft


def main(page: ft.Page) -> None:
    page.title = "MusicDL GUI"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.add(ft.Text("MusicDL GUI - Coming Soon"))


if __name__ == "__main__":
    ft.run(main)