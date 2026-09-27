# musicdl

对接自部署 NextMusic API 的 Python 库：获取歌单曲目（自动分页）、歌曲信息、播放地址，并下载单曲或整个歌单。

## 安装

```bash
pip install -e ".[dev]"   # 开发模式（含测试依赖）
```

运行环境：Python >= 3.10。依赖：`requests`、`pydantic >= 2`。

## 快速开始

```python
from musicdl import MusicDLConfig, SyncMusicClient, PlaylistService

config = MusicDLConfig(ip="1.2.3.4")  # 不传 ip 则自动获取公网 IP
with SyncMusicClient(config) as client:
    service = PlaylistService(client)
    playlist = service.get_all_tracks("18120707017")   # 自动分页拉取全部曲目
    print(playlist.name, len(playlist.songs))

    # 或逐页迭代
    for track in service.iter_tracks("18120707017"):
        print(track.singer, track.name)
```

### 歌曲信息与播放地址

```python
from musicdl import SyncMusicClient, SongService, QualityLevel

with SyncMusicClient() as client:
    songs = SongService(client)
    info = songs.get_info(1432544572)                      # SongInfo
    url = songs.get_url(1432544572, level=QualityLevel.STANDARD)  # SongUrl（带时效签名）
    print(url.url, url.br, url.size)
```

`level` 支持 `QualityLevel` 枚举或任意字符串（如 `"exhires"`），默认使用 `MusicDLConfig.default_level`。

### 下载

```python
from pathlib import Path
from musicdl import DownloadService, PlaylistService, SongService

with SyncMusicClient() as client:
    songs = SongService(client)
    playlists = PlaylistService(client)
    downloader = DownloadService(
        songs,
        playlists,
        output_dir=Path("music"),
        naming_template="{singer}/{track_number} - {title}",  # 可用 / 建子目录
        progress_callback=lambda done, total: print(done, total),
    )
    # 单曲
    downloader.download_song(1432544572)
    # 歌单（顺序下载；已存在默认跳过）
    paths = downloader.download_playlist(
        "18120707017",
        skip_existing=True,
        skip_failed=False,   # True 时显式跳过失败曲目并继续
    )
```

命名模板占位符：`{id}`、`{singer}`、`{title}`、`{album}`、`{track_number}`、`{playlist}`。占位符值中的 `\/:*?"<>|` 会替换为 `_`，扩展名固定 `.mp3`。

### 配置

`MusicDLConfig`（仅代码配置，不读环境变量）：

| 字段 | 默认值 | 说明 |
| ---- | ---- | ---- |
| `base_url` | `https://nextmusic.toubiec.cn` | API 地址 |
| `timeout` | `30.0` | 请求超时（秒） |
| `max_retries` | `3` | 网络错误 / 5xx 重试次数 |
| `retry_backoff` | `0.5` | 指数退避基数（秒） |
| `ip` | `None` | 手动指定 IP；`None` 时自动获取 |
| `ip_fetch_url` | `https://api.ipify.org?format=json` | 公网 IP 服务；`""` 禁用自动获取 |
| `ip_cache_ttl` | `3600.0` | 自动获取的 IP 缓存时长（秒） |
| `default_level` | `QualityLevel.STANDARD` | 默认音质 |
| `user_agent` | `None` | 自定义 UA |

## 错误处理

库**不吞异常**，所有失败向上抛出，由调用方处理：

- `MusicDLException` — 基类
- `APIError` — 业务 code != 200 或 HTTP 4xx（含 `code`/`message`/`payload`）
- `NetworkError` — 网络失败 / 5xx 重试耗尽（含 `original`）
- `ValidationError` — 响应不是合法 JSON 或结构不符
- `DownloadError` — 下载失败（含 `song_id`/`output_path`/`completed`/`original`）
- `ConfigError` — 配置错误（如缺少 playlist_service、模板占位符错误）
- `IPFetchError` — 自动获取公网 IP 失败

```python
from musicdl import APIError, DownloadError, MusicDLException

try:
    downloader.download_playlist("18120707017")
except DownloadError as exc:
    print("失败曲目:", exc.song_id, "已完成:", exc.completed)
except MusicDLException as exc:
    print("其他错误:", exc)
```

## 测试

```bash
.venv/bin/python -m pytest --cov=musicdl
```

测试全部使用 HTTP mock，不发出真实网络请求。
