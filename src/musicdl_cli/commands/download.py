"""Download commands: playlist and song."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from musicdl import DownloadService, MusicDLConfig, PlaylistService, SongService, SyncMusicClient
from musicdl_cli.ui.output import console
from musicdl_cli.utils.retry import download_with_retry

app = typer.Typer(help="下载歌单或单曲", no_args_is_help=True)


def _create_client_and_downloader(
    ip: Optional[str],
    output_dir: Path,
    quality: str,
) -> tuple[SyncMusicClient, DownloadService]:
    """Create SyncMusicClient and DownloadService from CLI options."""
    config = MusicDLConfig(ip=ip, default_level=quality)
    client = SyncMusicClient(config)
    song_service = SongService(client)
    playlist_service = PlaylistService(client)
    downloader = DownloadService(
        song_service,
        playlist_service,
        output_dir=output_dir,
        naming_template="{singer} - {title}",
    )
    return client, downloader


@app.command("song")
def download_song(
    song_id: str = typer.Argument(..., help="歌曲 ID"),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o", help="输出目录"),
    quality: str = typer.Option("standard", "--quality", "-q", help="音质: standard/hires/lossless"),
    ip: Optional[str] = typer.Option(None, "--ip", help="客户端 IP（默认自动获取）"),
    max_retries: int = typer.Option(10, "--max-retries", help="最大重试次数"),
    retry_wait: float = typer.Option(10.0, "--retry-wait", help="重试等待秒数"),
) -> None:
    """下载单首歌曲。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    client, downloader = _create_client_and_downloader(ip, output_dir, quality)

    def _do_download() -> Path:
        with client:
            return downloader.download_song(song_id, level=quality)

    def _on_retry(attempt: int, reason: str) -> None:
        console.print(f"  [yellow]⏳ {reason}，等待 {retry_wait}s 后重试 ({attempt}/{max_retries})...[/yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"下载歌曲 {song_id}...", total=None)
        try:
            path = download_with_retry(
                _do_download,
                max_retries=max_retries,
                retry_wait=retry_wait,
                on_retry=_on_retry,
            )
            progress.update(task, completed=1)
            console.print(f"  [green]✓ 已下载:[/green] {path}")
        except Exception as exc:
            progress.update(task, description=f"[red]✗ 失败: {exc}[/red]")
            console.print(f"  [red]✗ 下载失败:[/red] {exc}")
            raise typer.Exit(code=1)


@app.command("playlist")
def download_playlist(
    playlist_id: str = typer.Argument(..., help="歌单 ID"),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o", help="输出目录"),
    quality: str = typer.Option("standard", "--quality", "-q", help="音质: standard/hires/lossless"),
    ip: Optional[str] = typer.Option(None, "--ip", help="客户端 IP（默认自动获取）"),
    max_retries: int = typer.Option(10, "--max-retries", help="最大重试次数"),
    retry_wait: float = typer.Option(10.0, "--retry-wait", help="重试等待秒数"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing", help="跳过已存在的文件"),
    skip_failed: bool = typer.Option(False, "--skip-failed", help="跳过失败的歌曲继续下载"),
) -> None:
    """下载歌单中的全部歌曲。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    def _do_download() -> list[Path]:
        config = MusicDLConfig(ip=ip, default_level=quality)
        with SyncMusicClient(config) as client:
            playlist_service = PlaylistService(client)
            song_service = SongService(client)
            downloader = DownloadService(
                song_service,
                playlist_service,
                output_dir=output_dir,
                naming_template="{singer} - {title}",
            )
            playlist = playlist_service.get_all_tracks(playlist_id)
            console.print(f"\n[bold]正在下载歌单:[/bold] {playlist.name} (共 {len(playlist.songs)} 首)")
            return downloader.download_playlist(
                playlist,
                level=quality,
                skip_existing=skip_existing,
                skip_failed=skip_failed,
            )

    def _on_retry(attempt: int, reason: str) -> None:
        console.print(f"  [yellow]⏳ {reason}，等待 {retry_wait}s 后重试 ({attempt}/{max_retries})...[/yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"下载歌单 {playlist_id}...", total=None)
        try:
            paths = download_with_retry(
                _do_download,
                max_retries=max_retries,
                retry_wait=retry_wait,
                on_retry=_on_retry,
            )
            progress.update(task, completed=1)
            console.print(f"\n[green]✓ 完成！成功下载 {len(paths)} 首[/green]")
        except Exception as exc:
            progress.update(task, description=f"[red]✗ 失败: {exc}[/red]")
            console.print(f"  [red]✗ 下载失败:[/red] {exc}")
            raise typer.Exit(code=1)
