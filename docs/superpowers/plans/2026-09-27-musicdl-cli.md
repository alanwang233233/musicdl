# musicdl-cli Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `musicdl` 库构建一个基于 Typer + Rich 的命令行工具，支持下载歌单和下载单曲，带 Rich 进度条和 429/404 重试逻辑。

**Architecture:** 新建独立包 `src/musicdl_cli/`，复用现有 `musicdl` 库的 `MusicDLConfig`、`SyncMusicClient`、`PlaylistService`、`SongService`、`DownloadService`。CLI 层只负责参数解析、Rich 输出渲染和重试编排，不包含业务逻辑。重试逻辑从 `download_playlist_249180720.py` 提取为通用工具。

**Tech Stack:** Python ≥3.10, Typer, Rich, requests, pydantic v2, pytest, responses

**Spec:** 设计已在对话中确认（2026-09-27）

## Global Constraints

- Python ≥3.10（使用 `|` union 语法）
- 不引入新的配置文件/环境变量系统 — 纯命令行参数
- 重试策略：429/404/网络错误固定等待 10s，最多 10 次（与现有示例脚本一致）
- 进度显示：Rich `Progress` 组件
- 包名：`musicdl_cli`（下划线，PEP 8）
- 入口点：`musicdl`（console_scripts）
- 所有测试使用 `responses` / `Mock` — 禁止真实网络调用
- 异常不吞掉 — 始终向上传播

---

### Task 1: 项目脚手架与依赖配置

**Files:**
- Create: `src/musicdl_cli/__init__.py`
- Create: `src/musicdl_cli/__main__.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: 无（第一个任务）
- Produces: `musicdl_cli` 包可被导入；`musicdl` 命令可通过 `python -m musicdl_cli` 调用

- [ ] **Step 1: 创建包目录和 __init__.py**

创建 `src/musicdl_cli/__init__.py`：

```python
"""musicdl-cli — Typer + Rich CLI for the musicdl library."""

__version__ = "0.1.0"
```

- [ ] **Step 2: 创建 __main__.py 入口**

创建 `src/musicdl_cli/__main__.py`：

```python
"""Allow running as ``python -m musicdl_cli``."""

from musicdl_cli.main import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 3: 修改 pyproject.toml 添加 CLI 依赖和入口点**

在 `[project.optional-dependencies]` 中添加 `cli` 组，在 `[project.scripts]` 中添加入口点，在 `[tool.hatch.build.targets.wheel]` 中添加 `musicdl_cli` 包：

```toml
[project.optional-dependencies]
cli = [
    "typer>=0.9",
    "rich>=13.0",
]

[project.scripts]
musicdl = "musicdl_cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/musicdl", "src/musicdl_cli"]
```

- [ ] **Step 4: 安装依赖并验证**

```bash
.venv/bin/pip install -e ".[cli]"
python -c "from musicdl_cli.main import app; print('OK')"
```

Expected: 输出 `OK`

- [ ] **Step 5: Commit**

```bash
git add src/musicdl_cli/__init__.py src/musicdl_cli/__main__.py pyproject.toml
git commit -m "feat(cli): scaffold musicdl-cli package with typer and rich deps"
```

---

### Task 2: 共享配置与 Rich 输出工具

**Files:**
- Create: `src/musicdl_cli/ui/__init__.py`
- Create: `src/musicdl_cli/ui/output.py`
- Create: `src/musicdl_cli/utils/__init__.py`
- Create: `src/musicdl_cli/utils/retry.py`
- Create: `tests/unit/test_cli_retry.py`
- Create: `tests/unit/test_cli_output.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `musicdl_cli.ui.output.Console` — Rich Console 单例
  - `musicdl_cli.ui.output.print_playlist_info(playlist: Playlist) -> None` — 打印歌单元数据
  - `musicdl_cli.ui.output.print_track_list(tracks: list[PlaylistTrack]) -> None` — 打印曲目列表
  - `musicdl_cli.utils.retry.download_with_retry(fn, *, max_retries, retry_wait, on_retry) -> Any` — 通用重试包装器

- [ ] **Step 1: 编写重试工具的失败测试**

创建 `tests/unit/test_cli_retry.py`：

```python
"""Tests for musicdl_cli retry utility."""

from unittest.mock import Mock, call

import pytest

from musicdl.exceptions import APIError, DownloadError, NetworkError
from musicdl_cli.utils.retry import download_with_retry


def test_retry_succeeds_first_try():
    fn = Mock(return_value="ok")
    result = download_with_retry(fn, max_retries=3, retry_wait=0)
    assert result == "ok"
    assert fn.call_count == 1


def test_retry_recovers_from_429():
    fn = Mock(side_effect=[APIError(code=429, message="rate limit"), "ok"])
    result = download_with_retry(fn, max_retries=3, retry_wait=0)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_recovers_from_404():
    fn = Mock(side_effect=[APIError(code=404, message="not found"), "ok"])
    result = download_with_retry(fn, max_retries=3, retry_wait=0)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_recovers_from_network_error():
    fn = Mock(side_effect=[NetworkError("timeout"), "ok"])
    result = download_with_retry(fn, max_retries=3, retry_wait=0)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_gives_up_after_max_retries():
    fn = Mock(side_effect=APIError(code=429, message="rate limit"))
    with pytest.raises(APIError):
        download_with_retry(fn, max_retries=2, retry_wait=0)
    assert fn.call_count == 3  # initial + 2 retries


def test_retry_does_not_catch_non_retryable():
    fn = Mock(side_effect=ValueError("bad"))
    with pytest.raises(ValueError):
        download_with_retry(fn, max_retries=3, retry_wait=0)
    assert fn.call_count == 1


def test_retry_calls_on_retry_callback():
    on_retry = Mock()
    fn = Mock(side_effect=[APIError(code=429, message="rl"), APIError(code=404, message="nf"), "ok"])
    result = download_with_retry(fn, max_retries=3, retry_wait=0, on_retry=on_retry)
    assert result == "ok"
    assert on_retry.call_count == 2
    on_retry.assert_has_calls([call(1, "限流(429)"), call(2, "未找到(404)")])
```

- [ ] **Step 2: 运行测试确认失败**

```bash
.venv/bin/python -m pytest tests/unit/test_cli_retry.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'musicdl_cli.utils.retry'`

- [ ] **Step 3: 实现重试工具**

创建 `src/musicdl_cli/utils/__init__.py`：

```python
"""Utility helpers for musicdl-cli."""
```

创建 `src/musicdl_cli/utils/retry.py`：

```python
"""Retry wrapper for download operations (429/404/network errors)."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from musicdl.exceptions import APIError, DownloadError, NetworkError

T = TypeVar("T")

_RETRYABLE_API_CODES = {429, 404}


def download_with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = 10,
    retry_wait: float = 10.0,
    on_retry: Callable[[int, str], None] | None = None,
) -> T:
    """Call *fn* with automatic retry on 429/404/network errors.

    Args:
        fn: Zero-argument callable that performs the download.
        max_retries: Maximum number of retry attempts after the initial call.
        retry_wait: Seconds to wait between attempts.
        on_retry: Optional callback ``(attempt_number, reason)`` invoked before
            each retry wait.

    Returns:
        The value returned by *fn*.

    Raises:
        The last exception if all retries are exhausted, or a non-retryable
        exception on the first failure.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            if not _is_retryable(exc):
                raise
            last_exc = exc
            if attempt >= max_retries:
                break
            reason = _classify_error(exc)
            if on_retry is not None:
                on_retry(attempt + 1, reason)
            time.sleep(retry_wait)
    raise last_exc  # type: ignore[misc]


def _is_retryable(exc: BaseException) -> bool:
    """Check if an exception is retryable (429, 404, or network error)."""
    if isinstance(exc, NetworkError):
        return True
    if isinstance(exc, APIError):
        return exc.code in _RETRYABLE_API_CODES
    if isinstance(exc, DownloadError):
        return _is_retryable(exc.__cause__) if exc.__cause__ else False
    return False


def _classify_error(exc: BaseException) -> str:
    """Return a short Chinese label for the error type."""
    if isinstance(exc, APIError):
        if exc.code == 429:
            return "限流(429)"
        if exc.code == 404:
            return "未找到(404)"
    if isinstance(exc, DownloadError) and exc.__cause__:
        return _classify_error(exc.__cause__)
    return "网络错误"
```

- [ ] **Step 4: 运行测试确认通过**

```bash
.venv/bin/python -m pytest tests/unit/test_cli_retry.py -v
```

Expected: 全部 PASS

- [ ] **Step 5: 编写 Rich 输出工具的失败测试**

创建 `tests/unit/test_cli_output.py`：

```python
"""Tests for musicdl_cli Rich output helpers."""

from musicdl.models import Playlist, PlaylistCreator, PlaylistTrack
from musicdl_cli.ui.output import print_playlist_info, print_track_list


def make_track(song_id: int, name: str, singer: str) -> PlaylistTrack:
    return PlaylistTrack.model_validate(
        {
            "id": song_id,
            "name": name,
            "free": True,
            "album": "专辑",
            "singer": singer,
            "picimg": "https://example.com/c.jpg",
            "duration": "3:00",
            "copyright": 1,
            "time": "2026/09/12 17:25:27",
        }
    )


def make_playlist() -> Playlist:
    return Playlist.model_validate(
        {
            "id": 18120707017,
            "name": "测试歌单",
            "coverImage": "https://example.com/cover.jpg",
            "songCount": 2,
            "playCount": 100,
            "description": "一个测试歌单",
            "tags": ["流行", "电子"],
            "creator": {"uid": 1, "avatar": "https://example.com/a.jpg", "name": "创建者"},
            "songs": [
                make_track(1, "歌曲A", "歌手X").model_dump(),
                make_track(2, "歌曲B", "歌手Y").model_dump(),
            ],
        }
    )


def test_print_playlist_info_runs_without_error(capsys):
    print_playlist_info(make_playlist())
    captured = capsys.readouterr()
    assert "测试歌单" in captured.out
    assert "18120707017" in captured.out


def test_print_track_list_runs_without_error(capsys):
    tracks = [make_track(1, "歌曲A", "歌手X"), make_track(2, "歌曲B", "歌手Y")]
    print_track_list(tracks)
    captured = capsys.readouterr()
    assert "歌曲A" in captured.out
    assert "歌手X" in captured.out
    assert "歌曲B" in captured.out
```

- [ ] **Step 6: 运行测试确认失败**

```bash
.venv/bin/python -m pytest tests/unit/test_cli_output.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'musicdl_cli.ui.output'`

- [ ] **Step 7: 实现 Rich 输出工具**

创建 `src/musicdl_cli/ui/__init__.py`：

```python
"""Rich UI helpers for musicdl-cli."""
```

创建 `src/musicdl_cli/ui/output.py`：

```python
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
```

- [ ] **Step 8: 运行测试确认通过**

```bash
.venv/bin/python -m pytest tests/unit/test_cli_output.py -v
```

Expected: 全部 PASS

- [ ] **Step 9: Commit**

```bash
git add src/musicdl_cli/ui/ src/musicdl_cli/utils/ tests/unit/test_cli_retry.py tests/unit/test_cli_output.py
git commit -m "feat(cli): add retry utility and Rich output helpers"
```

---

### Task 3: Typer CLI 应用与 download song 命令

**Files:**
- Create: `src/musicdl_cli/main.py`
- Create: `src/musicdl_cli/commands/__init__.py`
- Create: `src/musicdl_cli/commands/download.py`
- Create: `tests/unit/test_cli_download_song.py`

**Interfaces:**
- Consumes:
  - `musicdl_cli.utils.retry.download_with_retry(fn, *, max_retries, retry_wait, on_retry) -> Any`
  - `musicdl_cli.ui.output.console` — Rich Console
  - `musicdl.MusicDLConfig`, `SyncMusicClient`, `SongService`, `DownloadService`
- Produces:
  - `musicdl_cli.main:app` — Typer 实例
  - `musicdl_cli.commands.download.app` — 子命令组 `download`
  - CLI 命令: `musicdl download song <SONG_ID>`

- [ ] **Step 1: 编写 download song 的失败测试**

创建 `tests/unit/test_cli_download_song.py`：

```python
"""Tests for the download song CLI command."""

from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from musicdl_cli.main import app

runner = CliRunner()


def test_download_song_requires_song_id():
    result = runner.invoke(app, ["download", "song"])
    assert result.exit_code != 0


def test_download_song_help():
    result = runner.invoke(app, ["download", "song", "--help"])
    assert result.exit_code == 0
    assert "--output-dir" in result.output
    assert "--quality" in result.output
    assert "--ip" in result.output
    assert "--max-retries" in result.output
    assert "--retry-wait" in result.output


def test_download_song_invokes_download_service(tmp_path: Path):
    mock_downloader = Mock()
    mock_downloader.download_song.return_value = tmp_path / "test.mp3"

    with patch("musicdl_cli.commands.download._create_download_service") as mock_factory:
        mock_factory.return_value = mock_downloader
        result = runner.invoke(app, ["download", "song", "12345", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    mock_downloader.download_song.assert_called_once()
    call_kwargs = mock_downloader.download_song.call_args
    assert call_kwargs[0][0] == "12345"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
.venv/bin/python -m pytest tests/unit/test_cli_download_song.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'musicdl_cli.main'`

- [ ] **Step 3: 实现 Typer 应用和 download song 命令**

创建 `src/musicdl_cli/main.py`：

```python
"""musicdl-cli — Typer application entry point."""

import typer

from musicdl_cli.commands.download import app as download_app

app = typer.Typer(
    name="musicdl",
    help="musicdl — NextMusic API 命令行工具",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(download_app, name="download")


@app.callback()
def main() -> None:
    """musicdl CLI — 下载歌单和单曲。"""
```

创建 `src/musicdl_cli/commands/__init__.py`：

```python
"""CLI command groups."""
```

创建 `src/musicdl_cli/commands/download.py`：

```python
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


def _create_download_service(
    ip: Optional[str],
    output_dir: Path,
    quality: str,
    max_retries: int,
    retry_wait: float,
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

    def _do_download() -> Path:
        config = MusicDLConfig(ip=ip, default_level=quality)
        with SyncMusicClient(config) as client:
            song_service = SongService(client)
            downloader = DownloadService(
                song_service,
                output_dir=output_dir,
                naming_template="{singer} - {title}",
            )
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
.venv/bin/python -m pytest tests/unit/test_cli_download_song.py -v
```

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/musicdl_cli/main.py src/musicdl_cli/commands/ tests/unit/test_cli_download_song.py
git commit -m "feat(cli): add download song command with Typer and Rich progress"
```

---

### Task 4: download playlist 命令

**Files:**
- Modify: `src/musicdl_cli/commands/download.py`
- Create: `tests/unit/test_cli_download_playlist.py`

**Interfaces:**
- Consumes:
  - `musicdl_cli.utils.retry.download_with_retry`
  - `musicdl_cli.ui.output.console`, `print_playlist_info`, `print_track_list`
  - `musicdl.PlaylistService.get_all_tracks(playlist_id) -> Playlist`
  - `musicdl.DownloadService.download_playlist(playlist, ...) -> list[Path]`
- Produces:
  - CLI 命令: `musicdl download playlist <PLAYLIST_ID>`

- [ ] **Step 1: 编写 download playlist 的失败测试**

创建 `tests/unit/test_cli_download_playlist.py`：

```python
"""Tests for the download playlist CLI command."""

from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from musicdl_cli.main import app

runner = CliRunner()


def test_download_playlist_requires_playlist_id():
    result = runner.invoke(app, ["download", "playlist"])
    assert result.exit_code != 0


def test_download_playlist_help():
    result = runner.invoke(app, ["download", "playlist", "--help"])
    assert result.exit_code == 0
    assert "--output-dir" in result.output
    assert "--quality" in result.output
    assert "--ip" in result.output
    assert "--max-retries" in result.output
    assert "--retry-wait" in result.output
    assert "--skip-existing" in result.output
    assert "--skip-failed" in result.output


def test_download_playlist_invokes_services(tmp_path: Path):
    mock_playlist = Mock()
    mock_playlist.name = "测试歌单"
    mock_playlist.songs = []

    mock_playlist_service = Mock()
    mock_playlist_service.get_all_tracks.return_value = mock_playlist

    mock_downloader = Mock()
    mock_downloader.download_playlist.return_value = []

    with (
        patch("musicdl_cli.commands.download.PlaylistService") as MockPlaylistService,
        patch("musicdl_cli.commands.download.DownloadService") as MockDownloadService,
    ):
        MockPlaylistService.return_value = mock_playlist_service
        MockDownloadService.return_value = mock_downloader
        result = runner.invoke(app, ["download", "playlist", "123", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    mock_playlist_service.get_all_tracks.assert_called_once_with("123")
    mock_downloader.download_playlist.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
.venv/bin/python -m pytest tests/unit/test_cli_download_playlist.py -v
```

Expected: FAIL — `download playlist` 命令不存在

- [ ] **Step 3: 实现 download playlist 命令**

在 `src/musicdl_cli/commands/download.py` 中追加：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
.venv/bin/python -m pytest tests/unit/test_cli_download_playlist.py -v
```

Expected: 全部 PASS

- [ ] **Step 5: 运行完整测试套件确认无回归**

```bash
.venv/bin/python -m pytest -v
```

Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add src/musicdl_cli/commands/download.py tests/unit/test_cli_download_playlist.py
git commit -m "feat(cli): add download playlist command"
```

---

### Task 5: 集成验证与最终检查

**Files:**
- 无新文件

**Interfaces:**
- Consumes: 所有前面的任务
- Produces: 可工作的 `musicdl` CLI

- [ ] **Step 1: 安装并验证 CLI 入口点**

```bash
.venv/bin/pip install -e ".[cli]"
musicdl --help
```

Expected: 显示帮助信息，包含 `download` 子命令

- [ ] **Step 2: 验证 download song 帮助**

```bash
musicdl download song --help
```

Expected: 显示所有选项

- [ ] **Step 3: 验证 download playlist 帮助**

```bash
musicdl download playlist --help
```

Expected: 显示所有选项

- [ ] **Step 4: 运行完整测试套件**

```bash
.venv/bin/python -m pytest --cov=musicdl --cov=musicdl_cli -v
```

Expected: 全部 PASS，覆盖率报告正常

- [ ] **Step 5: 最终 Commit（如有遗漏）**

```bash
git status
# 如果有未提交的修改：
git add -A
git commit -m "chore(cli): final integration verification"
```
