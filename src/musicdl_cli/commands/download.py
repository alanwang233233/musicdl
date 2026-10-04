"""Download commands: playlist and song."""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import typer
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from musicdl import (
    DownloadService,
    MusicDLConfig,
    PlaylistService,
    QualityLevel,
    SongService,
    SyncMusicClient,
)
from musicdl.exceptions import APIError, DownloadError
from musicdl.filename import sanitize_filename as _sanitize_filename
from musicdl_cli.ui.output import console, print_playlist_info, print_track_list
from musicdl_cli.utils.retry import download_with_retry

app = typer.Typer(help="下载歌单或单曲", no_args_is_help=True)


def _create_client_and_downloader(
    ip: str | None,
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


def _print_summary(paths: list[Path], skipped: list[Path], failed: list[tuple]) -> None:
    """Print the final download summary (shared by abort and finish paths)."""
    console.print(f"完成！成功下载 {len(paths)} 首，跳过 {len(skipped)} 首，失败 {len(failed)} 首")
    for p in paths:
        console.print(f"  ✓ {p.name}")
    if skipped:
        console.print("\n跳过列表:")
        for p in skipped:
            console.print(f"  ⊘ {p.name}")
    if failed:
        console.print("\n失败列表:")
        for track_err, err in failed:
            console.print(f"  ✗ {track_err.singer} - {track_err.name}: {err}")


@app.command("song")
def download_song(
    song_id: str = typer.Argument(..., help="歌曲 ID"),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o", help="输出目录"),
    quality: QualityLevel = typer.Option(QualityLevel.STANDARD, "--quality", "-q", case_sensitive=False, help="音质: standard/hires/lossless"),
    ip: str | None = typer.Option(None, "--ip", help="客户端 IP（默认自动获取）"),
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
        except Exception as exc:  # noqa: BLE001 - report any download failure to the user
            progress.update(task, description=f"[red]✗ 失败: {exc}[/red]")
            console.print(f"  [red]✗ 下载失败:[/red] {exc}")
            raise typer.Exit(code=1)


@app.command("playlist")
def download_playlist(
    playlist_id: str = typer.Argument(..., help="歌单 ID"),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o", help="输出目录"),
    quality: QualityLevel = typer.Option(QualityLevel.STANDARD, "--quality", "-q", case_sensitive=False, help="音质: standard/hires/lossless"),
    ip: str | None = typer.Option(None, "--ip", help="客户端 IP（默认自动获取）"),
    max_retries: int = typer.Option(10, "--max-retries", help="最大重试次数"),
    retry_wait: float = typer.Option(10.0, "--retry-wait", help="重试等待秒数"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing", help="跳过已存在的文件"),
    skip_failed: bool = typer.Option(False, "--skip-failed", help="跳过失败的歌曲继续下载"),
) -> None:
    """下载歌单中的全部歌曲。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    config = MusicDLConfig(ip=ip, default_level=quality)

    with SyncMusicClient(config) as client:
        playlist_service = PlaylistService(client)
        song_service = SongService(client)
        downloader = DownloadService(
            song_service,
            playlist_service,
            output_dir=output_dir,
            naming_template="{singer} - {title}",
            progress_callback=lambda done, total: (
                console.print(f"  进度: {done}/{total} bytes" if total > 0 else f"  进度: {done} bytes", end="\r")
            ),
        )

        console.print(f"正在获取歌单 {playlist_id} 信息...")
        playlist = playlist_service.get_all_tracks(playlist_id)

        print_playlist_info(playlist)
        print_track_list(playlist.songs)

        console.print(f"\n开始下载到: {output_dir}")
        console.print("-" * 50)

        paths: list[Path] = []
        failed: list[tuple] = []
        skipped: list[Path] = []

        for i, track in enumerate(playlist.songs, 1):
            safe_singer = _sanitize_filename(track.singer)
            safe_name = _sanitize_filename(track.name)

            console.print(f"\n[{i}/{len(playlist.songs)}] {track.singer} - {track.name}")

            def _download_one_track(track=track, safe_singer=safe_singer, safe_name=safe_name) -> tuple[Path, bool]:
                """Returns (path, was_skipped)."""
                # 只取一次 URL(此前每首歌调两次 getSongUrl);按真实扩展名精确
                # 判断已存在,弃用 glob(歌名含 [ ] ? * 时会误判导致静默丢歌)
                url_info = song_service.get_url(track.id, level=quality)
                if not url_info.url:
                    raise APIError(code=404, message="Song URL is null/unavailable")
                parsed = urllib.parse.urlparse(url_info.url)
                ext = Path(parsed.path).suffix or ".mp3"
                target_path = output_dir / f"{safe_singer} - {safe_name}{ext}"
                if skip_existing and target_path.exists():
                    return target_path, True
                return downloader.download_song(
                    track.id,
                    level=quality,
                    output=target_path,
                    url_info=url_info,
                ), False

            def _on_retry(attempt: int, reason: str) -> None:
                console.print(f"  [yellow]⏳ {reason}，等待 {retry_wait}s 后重试 ({attempt}/{max_retries})...[/yellow]")

            try:
                path, was_skipped = download_with_retry(
                    _download_one_track,
                    max_retries=max_retries,
                    retry_wait=retry_wait,
                    on_retry=_on_retry,
                )
                if path.exists() and path.stat().st_size == 0:
                    # Should not happen, but safety check
                    raise DownloadError("Downloaded file is empty", song_id=track.id, output_path=path)
                if was_skipped:
                    skipped.append(path)
                    console.print(f"  ⊘ 已存在，跳过: {path.name}")
                else:
                    paths.append(path)
                    console.print(f"  ✓ 已下载: {path.name}")
            except Exception as e:  # noqa: BLE001 - per-track failure is reported, not fatal
                failed.append((track, e))
                console.print(f"  ✗ 失败: {e}")
                if e.__cause__:
                    console.print(f"     原因: {e.__cause__}")
                elif e.__context__:
                    console.print(f"     上下文: {e.__context__}")
                if not skip_failed:
                    console.print(f"\n{'='*50}")
                    _print_summary(paths, skipped, failed)
                    raise typer.Exit(code=1)

        console.print(f"\n{'='*50}")
        _print_summary(paths, skipped, failed)

        if failed and not skip_failed:
            raise typer.Exit(code=1)