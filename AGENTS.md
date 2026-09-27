# musicdl — Agent Instructions

## Quick Start
```bash
cd /Users/macos/musicdl
.venv/bin/pip install -e ".[dev]"  # install with dev deps
.venv/bin/python -m pytest --cov=musicdl  # run tests with coverage
```

## Project Structure
```
src/musicdl/          # library source (src layout)
├── __init__.py       # public exports: SyncMusicClient, PlaylistService, SongService, DownloadService, models, exceptions
├── api/              # endpoint constants
├── client/           # SyncMusicClient (HTTP: timestamp/ip injection, retries, 429/404 handling)
├── config.py         # MusicDLConfig (code-only, no env vars)
├── models/           # Pydantic v2: Playlist, SongInfo, SongUrl, QualityLevel, CopyrightType
├── services/         # PlaylistService (auto-pagination), SongService, DownloadService
└── exceptions/       # MusicDLException hierarchy (never swallowed)
tests/                # pytest + responses mocks (no real network)
download_playlist_*.py  # example scripts for bulk downloads
```

## Key Commands
| Task | Command |
|------|---------|
| Run all tests | `.venv/bin/python -m pytest` |
| Run with coverage | `.venv/bin/python -m pytest --cov=musicdl` |
| Run single test file | `.venv/bin/python -m pytest tests/unit/test_models.py -v` |
| Install editable | `.venv/bin/pip install -e ".[dev]"` |

## Architecture Notes
- **Sync only** — `requests`-based `SyncMusicClient`, no async
- **Layered**: models → api → client → services → exceptions
- **No CLI** — library only, import and use
- **IP handling**: auto-fetches public IP via ipify (cached 1h), or manual via `MusicDLConfig(ip="...")`
- **Retry logic**: client handles 5xx + connection errors; download scripts add 429/404 retry (10s wait, 10 max)
- **Pagination**: `PlaylistService.get_all_tracks()` auto-pages until `song_count` reached

## Common Patterns
```python
from musicdl import MusicDLConfig, SyncMusicClient, PlaylistService

config = MusicDLConfig(ip="1.2.3.4")  # or None for auto
with SyncMusicClient(config) as client:
    svc = PlaylistService(client)
    playlist = svc.get_all_tracks("2249180720")
    for track in playlist.songs:
        print(track.name, track.singer)
```

## Testing Quirks
- All tests use `responses` / `Mock` — **no real network calls allowed**
- Fixtures in `tests/fixtures/` (JSON responses from real API)
- `load_fixture` fixture in `tests/conftest.py`

## Gotchas
- **No env vars / config files** — config is code-only (`MusicDLConfig` dataclass)
- **Exceptions never swallowed** — always propagate; callers handle
- **SongUrl fields may be None** — `url`, `level`, `md5` optional (API returns null on failure)
- **File naming**: download scripts sanitize `/` `\` → `;`
- **Python ≥3.10** required (uses `|` union syntax)

## Development Workflow
1. Make changes in `src/musicdl/`
2. Run tests: `.venv/bin/python -m pytest`
3. Add tests for new behavior in `tests/unit/`
4. Run full suite with coverage before committing