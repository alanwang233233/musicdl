"""Rich-based output formatting for musicdl-cli."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from musicdl.models import Playlist, PlaylistTrack

console = Console()


def print_playlist_info(playlist: Playlist) -> None:
    """Print playlist metadata as a Rich table."""
    table = Table(title=f"歌单: {playlist.name}", show_header=False)
    table.add_column("字段", style="cyan")
    table.add_column("值", style="white")
    table.add_row("ID", str(playlist.id))
    table.add_row("歌曲数", str(playlist.song_count))
    table.add_row("播放量", str(playlist.play_count))
    table.add_row("创建者", f"{playlist.creator.name} (UID: {playlist.creator.uid})")
    table.add_row("标签", ", ".join(playlist.tags) if playlist.tags else "无")
    table.add_row("简介", playlist.description or "无")
    console.print(table)


def print_track_list(tracks: list[PlaylistTrack]) -> None:
    """Print tracks as a numbered Rich table."""
    table = Table(title=f"曲目列表 (共 {len(tracks)} 首)")
    table.add_column("#", style="dim", width=4)
    table.add_column("歌名", style="white")
    table.add_column("歌手", style="cyan")
    table.add_column("专辑", style="green")
    table.add_column("时长", style="yellow")
    table.add_column("免费", width=5)
    for i, track in enumerate(tracks, 1):
        table.add_row(
            str(i),
            track.name,
            track.singer,
            track.album,
            track.duration,
            "是" if track.free else "否",
        )
    console.print(table)
