# musicdl-gui Design Specification

## Overview

A cross-platform desktop GUI for the musicdl library, built with Python + Flet. Single-window tabbed interface aligning with CLI behavior (auto IP fetching, exception handling, rate limiting).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      musicdl-gui (Flet App)                  │
├─────────────────────────────────────────────────────────────┤
│  Tab 1: Playlist Browser    Tab 2: Song Downloader         │
│  Tab 3: Download Queue      Tab 4: Settings                │
│  Tab 5: Error Log                                                  │
├─────────────────────────────────────────────────────────────┤
│                    Core Services Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ConfigManager│  │DownloadQueue│  │  ApiClient  │         │
│  │  (persist)  │  │  (async)    │  │  (wrapper)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐                                              │
│  │  ErrorLog   │  (global exception capture & persistence)   │
│  └─────────────┘                                              │
├─────────────────────────────────────────────────────────────┤
│                    musicdl Library                           │
│  SyncMusicClient → PlaylistService → SongService → DownloadService
└─────────────────────────────────────────────────────────────┘
```

## Tab Details

### Tab 1: Playlist Browser
- **Input**: Playlist ID field + "Fetch" button
- **Output**: Playlist info card (name, cover, song count, creator)
- **Track List**: Virtualized list showing tracks (singer - title, duration)
- **Actions**: "Download All", "Select Tracks", "Add to Queue"
- **Loading**: Progress indicator during fetch (pagination handled by library)

### Tab 2: Song Downloader
- **Input**: Song ID field + "Preview" button
- **Preview**: Shows song info (title, singer, album, cover, duration)
- **Quality Selector**: Dropdown (standard/hires/lossless + custom)
- **Output Path**: Auto-generated from template, editable
- **Action**: "Download" button with progress bar

### Tab 3: Download Queue
- **Queue Table**: Columns: #, Title, Singer, Playlist, Quality, Progress, Status, Actions
- **Status States**: Pending → Downloading → Completed / Failed / Skipped
- **Controls**: Retry Failed, Clear Completed, Remove Selected, Move Up/Down
- **Global Progress**: Current item progress bar + speed/ETA (no overall - serial only)
- **Persistence**: Queue survives app restart (JSON file)
- **Serial Processing**: Only one download at a time. Playlist downloads process track-by-track sequentially. Next queued item starts only after current fully completes.

### Tab 4: Settings
- **API Settings**: Base URL, IP (auto/manual), timeout, retries, backoff
- **Download Settings**: Output directory, naming template, default quality
- **Advanced**: User-Agent, IP fetch URL, cache TTL
- **Actions**: Save, Reset to Defaults, Test Connection

### Tab 5: Error Log
- **Log Table**: Columns: Timestamp, Level (ERROR/WARNING), Source, Message, Exception Type, Stack Trace (expandable)
- **Sources**: API Client, Download Queue, Config, UI, Network
- **Filters**: By level, source, date range, search text
- **Actions**: Clear Log, Export to File, Copy Selected, Show Details Modal
- **Persistence**: Survives app restart (rotating file, max 10MB / 1000 entries)
- **Real-time**: New errors appear instantly (event-driven from ErrorLog service)
- **Global Exception Handler**: Catches unhandled exceptions in async tasks, logs automatically

## Core Services

### ConfigManager
- Persists settings to `~/.config/musicdl-gui/config.json`
- Loads on startup, validates against MusicDLConfig schema
- Provides default values matching library defaults

### DownloadQueue (Serial)
- Single background task processes queue sequentially
- Uses `asyncio.to_thread()` for each download (library is sync)
- No thread pool - one download at a time, fully blocking until done
- Emits events: `on_progress`, `on_complete`, `on_error`, `on_status_change`, `on_queue_empty`
- Persists queue state to `~/.config/musicdl-gui/queue.json`
- Playlist download = multiple QueueItems added sequentially, processed one-by-one

### ApiClient Wrapper
- Wraps `SyncMusicClient` with GUI-friendly error handling
- Implements retry logic matching CLI (`download_with_retry` pattern)
- Exposes async methods: `fetch_playlist()`, `fetch_song_info()`, `get_song_url()`

### ErrorLog
- Global singleton capturing all exceptions across the application
- Integrates with Python's `logging` module + custom `sys.excepthook` for unhandled exceptions
- Async-safe: thread-safe queue + background writer to rotating log file (`~/.config/musicdl-gui/error.log`)
- In-memory ring buffer (last 1000 entries) for instant UI display
- Structured log entries: timestamp, level, source, message, exception_type, traceback, context dict
- Emits `on_new_entry` event for real-time UI updates
- Methods: `log_exception(exc, source, context)`, `log_message(level, source, message, context)`, `get_entries(filters)`, `clear()`, `export(path)`

## Error Handling (CLI-Aligned)

| Error Type | GUI Behavior |
|------------|--------------|
| `NetworkError` | Auto-retry with exponential backoff, show toast "Retrying... (attempt N)" |
| `APIError` (429) | Parse `retryAfter`, wait, retry silently |
| `APIError` (other) | Show error dialog with code/message, log details |
| `DownloadError` | Mark item failed, show in queue with "Retry" button, include completed count |
| `ConfigError` | Highlight invalid field in Settings, prevent save |
| `IPFetchError` | Fallback to manual IP entry, show warning banner |

## Data Models (Flet-specific)

```python
# QueueItem - extends library models with GUI state
class QueueItem:
    song_id: int
    title: str
    singer: str
    playlist: str
    quality: str
    output_path: Path
    status: Enum[Pending, Downloading, Completed, Failed, Skipped]
    progress: float  # 0-1
    downloaded_bytes: int
    total_bytes: int
    error: str | None
    retry_count: int

# ErrorLogEntry - structured error record
class ErrorLogEntry:
    timestamp: datetime
    level: Enum[ERROR, WARNING, INFO]
    source: str           # "api_client", "download_queue", "config", "ui", "network"
    message: str
    exception_type: str | None    # e.g., "APIError", "DownloadError", "NetworkError"
    traceback: str | None
    context: dict         # additional context (song_id, playlist_id, url, etc.)
```

## Testing Strategy

- **Unit Tests**: Core services (ConfigManager, DownloadQueue, ApiClient) with mocks
- **Integration Tests**: Full download flows using `responses` HTTP mocking (like library tests)
- **UI Tests**: Flet's headless testing for critical user flows
- **Coverage Target**: ≥80% for core services, ≥60% overall

## Cross-Platform Build

**Primary Target (Desktop - macOS only for deliverable artifacts)**:
| Platform | Build Tool | Output |
|----------|------------|--------|
| macOS | PyInstaller + flet build | `.app` / universal binary (DMG, notarized) |

**Development Targets** (code runs on these platforms but no deliverable artifact required):
- **Windows**: Runs via `flet run` / `python -m musicdl_gui` - native file dialogs, keyboard shortcuts
- **Linux**: Runs via `flet run` / `python -m musicdl_gui` - native file dialogs, keyboard shortcuts
- **Android**: Functional availability via `flet run --android` - touch-friendly layouts, responsive UI

**Platform-Specific Adaptations**:
- **macOS (Deliverable)**: `.app` bundle, DMG installer, notarization, universal binary (arm64 + x86_64)
- **Desktop (Windows/Linux)**: Multi-window support, keyboard shortcuts, native file dialogs
- **Android**: Single-window, touch gestures, storage access framework (SAF) for output dir, adaptive column layouts (stack on mobile)
- **Shared**: Responsive Flet layouts using `ResponsiveRow`/`Column`, configurable breakpoints

## File Structure

```
musicdl_gui/
├── src/musicdl_gui/
│   ├── __init__.py
│   ├── main.py              # App entry, routing
│   ├── config.py            # ConfigManager
│   ├── queue.py             # DownloadQueue
│   ├── api.py               # ApiClient wrapper
│   ├── error_log.py         # ErrorLog service
│   ├── models.py            # QueueItem, ErrorLogEntry, enums
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── playlist_browser.py
│   │   ├── song_downloader.py
│   │   ├── download_queue.py
│   │   ├── settings.py
│   │   └── error_log.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── playlist_card.py
│   │   ├── track_list.py
│   │   ├── queue_table.py
│   │   ├── progress_bar.py
│   │   ├── dialogs.py
│   │   └── error_log_table.py
│   └── utils/
│       ├── __init__.py
│       ├── threading.py     # run_in_executor helpers
│       └── formatting.py    # bytes, duration, etc.
├── tests/
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_queue.py
│   │   └── test_api.py
│   ├── integration/
│   │   └── test_download_flow.py
│   └── conftest.py
├── assets/                  # Icons, images
├── pyproject.toml
├── README.md
└── musicdl_gui.spec         # PyInstaller spec
```

## Acceptance Criteria

1. ✅ Fetch playlist by ID, display all tracks with pagination
2. ✅ Download single song with quality selection and preview
3. ✅ Batch download playlist with progress per track + overall
4. ✅ Queue persists across restarts, supports retry (serial - no pause/resume)
5. ✅ Settings saved to config file, validated on save
6. ✅ All CLI error behaviors replicated (retry, rate limit, IP fetch)
7. ✅ Error Log tab displays all runtime exceptions with timestamp, level, source, message, traceback
8. ✅ Error log persists across restarts (rotating file, max 10MB/1000 entries)
9. ✅ Real-time error capture: unhandled exceptions auto-logged, appear instantly in UI
10. ✅ Builds to native macOS `.app` bundle (DMG, notarized, universal binary)
11. ✅ Unit tests pass with ≥80% coverage on core services
12. ✅ Flet hot-reload works during development