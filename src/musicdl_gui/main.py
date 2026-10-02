"""musicdl-gui - Flet application entry point."""

import flet as ft

from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.queue import DownloadQueue


def main(page: ft.Page) -> None:
    page.title = "MusicDL GUI"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16

    config_mgr = ConfigManager()
    error_log = ErrorLog()
    download_queue = DownloadQueue()

    from musicdl_gui.tabs.playlist_browser import PlaylistBrowserTab
    from musicdl_gui.tabs.song_downloader import SongDownloaderTab
    from musicdl_gui.tabs.download_queue import DownloadQueueTab
    from musicdl_gui.tabs.settings import SettingsTab
    from musicdl_gui.tabs.error_log import ErrorLogTab

    tabs = ft.Tabs(
        length=5,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(text="Playlist", icon=ft.Icons.QUEUE_MUSIC),
                        ft.Tab(text="Song", icon=ft.Icons.MUSIC_NOTE),
                        ft.Tab(text="Queue", icon=ft.Icons.DOWNLOAD),
                        ft.Tab(text="Settings", icon=ft.Icons.SETTINGS),
                        ft.Tab(text="Errors", icon=ft.Icons.ERROR),
                    ],
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        PlaylistBrowserTab(config_mgr, download_queue, error_log),
                        SongDownloaderTab(config_mgr, download_queue, error_log),
                        DownloadQueueTab(download_queue, error_log),
                        SettingsTab(config_mgr),
                        ErrorLogTab(error_log),
                    ],
                ),
            ],
        ),
    )

    page.add(tabs)


if __name__ == "__main__":
    ft.run(main)