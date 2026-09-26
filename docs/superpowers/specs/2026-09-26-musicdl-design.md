# musicdl 设计文档

日期：2026-09-26
状态：已确认

## 1. 概述

`musicdl` 是一个 Python 库，用于对接自部署音乐 API（`https://nextmusic.toubiec.cn/api/*`），提供以下能力：

- 获取歌单全部曲目（自动分页）
- 获取歌曲详情
- 获取歌曲播放地址（可选音质等级）
- 下载单曲 / 批量下载歌单

### 已确认的约束与决策

| 决策点 | 结论 |
| ---- | ---- |
| 项目结构 | 模块化分层结构 |
| CLI | **不需要** |
| 异步 | 仅同步（`requests`） |
| 配置管理 | 仅代码配置（构造参数 / 配置类） |
| IP 获取 | 自动获取公网 IP，可手动覆盖 |
| 分页 | 自动分页生成器 |
| 下载 | 独立 DownloadService，**单线程**，**无断点续传**，**无 MD5 校验**，保留进度回调与命名模板 |
| 错误处理原则 | **库不吞异常**：任何失败一律向上抛出自定义异常，不静默跳过、不隐藏报错；异常处理由调用方负责 |
| 语言 | 代码英文标识符；docstring / 文档使用英文或中英混合，README 中文 |

### 接口清单（来自用户提供文档）

| 端点 | 方法 | 功能 |
| ---- | ---- | ---- |
| `/api/playlist_trackall` | POST | 歌单信息 + 分页曲目 |
| `/api/getSongInfo` | POST | 歌曲详情 |
| `/api/getSongUrl` | POST | 歌曲播放地址 |

所有请求体均必填 `timestamp`（毫秒时间戳）与 `ip`（客户端公网 IP），`Content-Type: application/json` 必填。

> 隐私约束：严禁在网上搜索该 API 的相关信息；仅允许搜索 Python 库相关的通用资料（如 requests、pydantic 用法）。

## 2. 架构

```
musicdl/
├── src/musicdl/
│   ├── __init__.py           # 公共 API 导出
│   ├── config.py             # MusicDLConfig 配置类
│   ├── models/               # 数据模型层（Pydantic v2）
│   │   ├── __init__.py
│   │   ├── enums.py          # QualityLevel, CopyrightType
│   │   ├── playlist.py       # Playlist, PlaylistCreator, PlaylistTrack
│   │   └── song.py           # SongInfo, SongUrl, CookieInfo
│   ├── api/                  # API 接口定义层
│   │   ├── __init__.py
│   │   └── endpoints.py      # 端点路径常量
│   ├── client/               # HTTP 客户端层
│   │   ├── __init__.py
│   │   └── sync_client.py    # SyncMusicClient
│   ├── services/             # 业务服务层
│   │   ├── __init__.py
│   │   ├── playlist.py       # PlaylistService
│   │   ├── song.py           # SongService
│   │   └── download.py       # DownloadService
│   └── exceptions/           # 异常层
│       ├── __init__.py
│       └── errors.py
├── tests/                    # pytest 单元测试
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_models.py
│   │   ├── test_client.py
│   │   ├── test_services.py
│   │   └── test_download.py
│   └── fixtures/             # 响应 JSON 固定数据
├── pyproject.toml
├── README.md
└── docs/superpowers/specs/   # 本设计文档及后续实施计划
```

### 分层职责

| 层 | 职责 | 依赖 |
| ---- | ---- | ---- |
| `models` | Pydantic 数据模型、枚举，负责响应数据验证与序列化 | pydantic |
| `api` | 端点路径常量，不含逻辑 | 无 |
| `client` | HTTP 调用：headers 组装、timestamp/ip 注入、重试、错误转换 | requests, api, exceptions |
| `services` | 业务编排：分页、下载流程、路径命名 | client, models |
| `exceptions` | 异常体系 | 无 |

## 3. 配置设计（`config.py`）

```python
class MusicDLConfig:
    base_url: str = "https://nextmusic.toubiec.cn"
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 0.5          # 指数退避基数（秒）
    ip: str | None = None               # 手动指定 IP；None 时自动获取
    ip_fetch_url: str = "https://api.ipify.org?format=json"
    ip_cache_ttl: float = 3600.0        # 自动获取的 IP 缓存时长（秒）
    default_level: QualityLevel = QualityLevel.STANDARD
    user_agent: str | None = None       # 可选自定义 UA
```

- 通过构造函数 / dataclass 字段传入，**不读取环境变量**。
- 公网 IP 自动获取：调用 `ip_fetch_url`（JSON 返回 `{"ip": "..."}`），成功后按 TTL 缓存；`ip_fetch_url` 设为空字符串可禁用自动获取（此时必须手动传 `ip`，否则抛 `ConfigError`）。

## 4. 数据模型（`models/`）

使用 Pydantic v2，字段命名采用 Python 惯例 `snake_case`，通过 `alias` 映射 API 原始 `camelCase` 字段（如 `picimg`、`coverImage`、`songCount`），解析时 `populate_by_name=True`。

### 枚举

- `QualityLevel(str, Enum)`：文档明确给出的取值 `STANDARD = "standard"`。服务层参数类型为 `QualityLevel | str`，既可用枚举也可用任意字符串（如文档未列明的其他音质值）直接透传。
- `CopyrightType(int, Enum)`：`COPYRIGHT = 1`、`NO_COPYRIGHT = 0`、`OTHER = 2`；未知值宽容解析为 `OTHER`。

### 模型

| 模型 | 关键字段 | 来源 |
| ---- | ---- | ---- |
| `PlaylistCreator` | `uid`, `avatar`, `name` | playlist_trackall |
| `PlaylistTrack` | `id`, `name`, `free`, `album`, `singer`, `picimg`, `duration`, `copyright`, `time` | playlist_trackall / getSongInfo（同构） |
| `Playlist` | `id`, `name`, `cover_image`, `song_count`, `play_count`, `description`, `tags`, `creator`, `songs` | playlist_trackall |
| `SongInfo` | 同 `PlaylistTrack` 结构 | getSongInfo |
| `CookieInfo` | `id`, `label`, `index` | getSongUrl |
| `SongUrl` | `id`, `url`, `br`, `level`, `size`, `md5`, `channel_layout`, `effects`, `cookie`, `time` | getSongUrl |

`duration` 保留 `mm:ss` 原始字符串；`time` 解析为 `datetime`（`%Y/%m/%d %H:%M:%S`），解析失败时保留字符串（宽松模式）。

## 5. HTTP 客户端（`client/sync_client.py`）

```python
class SyncMusicClient:
    def __init__(self, config: MusicDLConfig | None = None) -> None: ...
    def post_json(self, endpoint: str, payload: dict) -> dict: ...
    def close(self) -> None: ...
    def __enter__(self) -> ...: ...
    def __exit__(self, *exc) -> None: ...
```

行为：

1. 持有单个 `requests.Session`；支持上下文管理器。
2. 默认 headers：`Content-Type: application/json`、`Accept: *//*`、`Accept-Language`、可选 UA。不发送 `sec-*` 头（后端一般不校验）。
3. 每次请求自动注入 `timestamp`（`int(time.time() * 1000)`）与 `ip`（缓存/手动值）。
4. 重试策略：对网络错误与 5xx 响应重试，最多 `max_retries` 次，指数退避；4xx 不重试。
5. 错误转换：
   - 传输层异常 → `NetworkError`
   - 响应 `code != 200` → `APIError(code, message)`
   - JSON 解析失败 → `ValidationError`
6. 不放业务逻辑（分页等在 services 层）。

## 6. 服务层（`services/`）

### PlaylistService

```python
class PlaylistService:
    def __init__(self, client: SyncMusicClient, page_size: int = 500) -> None: ...
    def get_tracks(self, playlist_id: str | int, *, limit: int, offset: int) -> Playlist: ...
    def iter_tracks(self, playlist_id: str | int, *, page_size: int | None = None) -> Iterator[PlaylistTrack]:
        """自动分页：offset 每次 +limit，直到 songs 为空或达到 song_count。"""
    def get_all_tracks(self, playlist_id: str | int, *, page_size: int | None = None) -> Playlist:
        """拉取全部分页并返回 songs 完整的 Playlist。"""
```

分页终止条件：`songs` 为空 **或** 累计数量 ≥ `song_count` **或** 单页返回数 < `limit`。

### SongService

```python
class SongService:
    def __init__(self, client: SyncMusicClient) -> None: ...
    def get_info(self, song_id: str | int) -> SongInfo: ...
    def get_url(self, song_id: str | int, *, level: QualityLevel | str | None = None) -> SongUrl: ...
```

### DownloadService

```python
class DownloadService:
    def __init__(
        self,
        song_service: SongService,
        *,
        output_dir: Path = Path("."),
        naming_template: str = "{singer} - {title}",  # 相对 output_dir，不含扩展名
        progress_callback: Callable[[int, int], None] | None = None,  # (downloaded, total)
    ) -> None: ...

    def download_song(self, song_id: str | int, *, level=None, output: Path | None = None) -> Path: ...
    def download_playlist(
        self,
        playlist: Playlist | str | int,
        *,
        level=None,
        output_dir: Path | None = None,
        skip_existing: bool = True,
    ) -> list[Path]: ...
```

- 单线程顺序下载；流式写入（`iter_content`）。
- `progress_callback`：每次块写入后回调 `(已下载字节数, 总字节数)`，`total` 来自 `SongUrl.size`，未知时传 `-1`。
- `naming_template` 支持占位符：`{singer}`、`{title}`、`{album}`、`{id}`、`{track_number}`、`{playlist}`；非法文件名字符替换为 `_`，自动处理路径分隔（占位符中可包含 `/` 建子目录）。
- 扩展名固定 `.mp3`（API 返回 MP3 直链）。
- 下载失败（网络/HTTP 错误）→ `DownloadError`，**始终向上抛出，不捕获、不静默跳过**。
  - `download_song`：失败直接抛 `DownloadError`。
  - `download_playlist`：任一曲目失败立即抛 `DownloadError`（携带 `song_id` 与已完成列表等上下文），由调用方决定是否继续。库本身不吞异常。

## 7. 异常体系（`exceptions/errors.py`）

```
MusicDLException(Exception)          # 基类
├── ConfigError                      # 配置缺失/无效（如无法确定 ip）
├── IPFetchError                     # 自动获取公网 IP 失败
├── APIError                         # code != 200；携带 code、message、payload
├── NetworkError                     # 传输层失败；携带原始异常
├── ValidationError                  # 响应结构不符合预期（Pydantic）
└── DownloadError                    # 下载过程失败；携带 song_id、output_path、已完成路径列表（如可用）及原始异常
```

说明：client 层仅做异常**类型转换**（如 `requests` 异常 → `NetworkError`、非 200 → `APIError`），通过 `raise ... from e` 保留原始异常链；服务层不捕获、不吞掉下层异常，一律向调用方传播。

## 8. 公共 API（`__init__.py`）

导出：`MusicDLConfig`、`SyncMusicClient`、`PlaylistService`、`SongService`、`DownloadService`、`Playlist`、`PlaylistTrack`、`SongInfo`、`SongUrl`、`QualityLevel`、`MusicDLException` 及其子类。

## 9. 依赖

- 运行时：`requests`、`pydantic >= 2`
- 开发：`pytest`、`pytest-cov`、`responses`（或 `pytest-mock`，用于 HTTP mock）
- 构建：`pyproject.toml`（src 布局），Python `>= 3.10`

## 10. 测试策略

- 全部网络交互使用 mock（`responses`/`mocker`），**测试不发真实请求**。
- 覆盖点：
  - `config`：默认值、手动 IP、TTL 缓存、禁用自动获取时缺 IP 报错
  - `models`：camelCase → snake_case 映射、宽容解析（未知 copyright、非法 time）
  - `client`：timestamp/ip 注入、headers、非 200 → APIError、网络异常 → NetworkError、重试逻辑
  - `playlist service`：单页、自动分页终止条件（空页 / songCount 上限 / 短页）
  - `song service`：info/url 正常路径 + 错误路径
  - `download`：命名模板渲染、非法字符替换、进度回调调用、download_playlist 跳过已存在文件（显式 `skip_existing` 行为）、单曲失败抛 `DownloadError`（含上下文）
- 运行方式：`pytest`（README 中记录）。

## 11. 文档要求

- 所有公共类/函数带 docstring（Google style）、完整类型注解、必要注释。
- `README.md`：安装、快速开始（含代码示例）、API 参考概览、测试运行方式。

## 12. 非目标

- 无 CLI
- 无异步支持
- 无断点续传、无 MD5 校验
- 无并发下载
- 无环境变量 / 配置文件读取
- 不实现文档未提及的接口（搜索、歌词等）
