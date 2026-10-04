"""musicdl-gui - Flet application entry point."""

import asyncio

from typeguard import install_import_hook

# Only install for our modules, not flet (typeguard 4.x has issues with flet's TypeVars)
install_import_hook("musicdl_gui")
install_import_hook("musicdl")

import flet as ft

from musicdl_gui.config import ConfigManager
from musicdl_gui.error_log import ErrorLog, install_asyncio_exception_handler
from musicdl_gui.playback import (
    PlaybackBar,
    PlaybackDialog,
    PlaybackService,
    TempFileManager,
)
from musicdl_gui.queue import DownloadQueue
from musicdl_gui.snack import show_snack


def main(page: ft.Page) -> None:
    # asyncio 任务内的未处理异常不会走 sys.excepthook,挂到 loop 上才能进错误日志;
    # flet 1.0 在运行中的事件循环内同步调用 main(),但做防御避免版本差异导致启动失败
    try:
        install_asyncio_exception_handler(asyncio.get_running_loop())
    except RuntimeError:
        pass

    page.title = "MusicDL GUI"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0
    # 更大的默认窗口尺寸,且默认大小即为最小大小(窗口不可缩小)
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 1280
    page.window.min_height = 800

    config_mgr = ConfigManager()
    error_log = ErrorLog()
    download_queue = DownloadQueue()
    temp_manager = TempFileManager()
    api_client = None

    # 启动时清空下载队列:queue.json 仅作崩溃兜底,不跨会话恢复任务
    download_queue.clear_all()
    temp_manager.initialize()

    # Initialize playback service first (needed by tabs)
    playback_service = PlaybackService(
        queue=download_queue,
        config_manager=config_mgr,
        temp_manager=temp_manager,
        api_client=api_client,  # Will be set when first needed
        page=page,
    )

    # 播放错误此前没有任何订阅者,用户完全无感知;这里接入错误日志与提示
    def _on_playback_error(message: str) -> None:
        error_log.log_message("ERROR", "playback", message)
        show_snack(page, f"播放错误: {message}")

    playback_service.add_on_error(_on_playback_error)

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
                        PlaylistBrowserTab(config_mgr, download_queue, error_log, playback_service),
                        song_tab := SongDownloaderTab(config_mgr, download_queue, error_log),
                        DownloadQueueTab(download_queue, error_log),
                        SettingsTab(config_mgr),
                        ErrorLogTab(error_log),
                    ],
                ),
            ],
        ),
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
        page=page,
        playback_service=playback_service,
        on_mode_change=lambda mode: setattr(playback_service, "mode", mode),
    )
    # flet 1.0 无需手动放入 overlay:show_dialog 会负责挂载/卸载,
    # 预先 append 会造成双重父级,关闭后子控件脱离页面树导致 update() 报错

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

    # 拦截窗口关闭:flet 1.0 的 page.on_close 是"会话过期"事件而非窗口关闭,
    # 必须用 window.prevent_close + WindowEventType.CLOSE 才能在退出前做清理
    page.window.prevent_close = True

    async def _on_window_event(e: ft.WindowEvent) -> None:
        if e.type == ft.WindowEventType.CLOSE:
            # 退出前删除全部播放临时文件并清空下载队列
            download_queue.clear_all()
            temp_manager.cleanup_all()
            await page.window.destroy()

    page.window.on_event = _on_window_event

    # 会话过期(长时间挂起)时同样清理
    def on_session_close() -> None:
        temp_manager.cleanup_all()

    page.on_close = on_session_close


if __name__ == "__main__":
    ft.run(main)