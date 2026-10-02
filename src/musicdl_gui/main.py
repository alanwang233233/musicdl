"""musicdl-gui - Flet application entry point."""

from typeguard import install_import_hook

# Only install for our modules, not flet (typeguard 4.x has issues with flet's TypeVars)
install_import_hook("musicdl_gui")
install_import_hook("musicdl")

import flet as ft

from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog
from musicdl_gui.playback import (
    PlaybackBar,
    PlaybackDialog,
    PlaybackService,
    TempFileManager,
)
from musicdl_gui.queue import DownloadQueue


def main(page: ft.Page) -> None:
    page.title = "MusicDL GUI"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0

    config_mgr = ConfigManager()
    error_log = ErrorLog()
    download_queue = DownloadQueue()
    temp_manager = TempFileManager()
    api_client = None

    # Clear queue on startup
    download_queue.clear_all()
    temp_manager.initialize()

    from musicdl_gui.tabs.download_queue import DownloadQueueTab
    from musicdl_gui.tabs.error_log import ErrorLogTab
    from musicdl_gui.tabs.playlist_browser import PlaylistBrowserTab
    from musicdl_gui.tabs.settings import SettingsTab
    from musicdl_gui.tabs.song_downloader import SongDownloaderTab

    tabs = ft.Tabs(
        length=5,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Playlist", icon=ft.Icons.QUEUE_MUSIC),
                        ft.Tab(label="Song", icon=ft.Icons.MUSIC_NOTE),
                        ft.Tab(label="Queue", icon=ft.Icons.DOWNLOAD),
                        ft.Tab(label="Settings", icon=ft.Icons.SETTINGS),
                        ft.Tab(label="Errors", icon=ft.Icons.ERROR),
                    ],
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        PlaylistBrowserTab(config_mgr, download_queue, error_log),
                        song_tab := SongDownloaderTab(config_mgr, download_queue, error_log),
                        DownloadQueueTab(download_queue, error_log),
                        SettingsTab(config_mgr),
                        ErrorLogTab(error_log),
                    ],
                ),
            ],
        ),
    )

    # Initialize playback service
    playback_service = PlaybackService(
        queue=download_queue,
        config_manager=config_mgr,
        temp_manager=temp_manager,
        api_client=api_client,  # Will be set when first needed
        page=page,
    )

    # Set playback service on song tab
    song_tab._set_playback_service(playback_service)

    # Create playback bar
    playback_bar = PlaybackBar(
        playback_service=playback_service,
        on_mode_change=lambda mode: setattr(playback_service, "mode", mode),
        on_fullscreen_click=lambda: playback_dialog.show(),
    )

    # Create fullscreen dialog
    playback_dialog = PlaybackDialog(
        playback_service=playback_service,
        on_mode_change=lambda mode: setattr(playback_service, "mode", mode),
    )
    page.overlay.append(playback_dialog)

    # Main layout with playback bar at bottom
    main_content = ft.Column(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                content=tabs,
            ),
            playback_bar,
        ],
    )

    page.add(main_content)

    # Clear queue on app close - use page.on_close in Flet 1.0
    def on_close() -> None:
        download_queue.clear_all()
        temp_manager.cleanup_all()

    page.on_close = on_close


if __name__ == "__main__":
    ft.run(main)