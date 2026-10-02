# AGENTS.md - musicdl-gui

## Project Overview
Cross-platform GUI for the musicdl library (self-hosted NextMusic API), built with **Python + Flet**.
- **App entrypoint**: `src/musicdl_gui/main.py` → `musicdl_gui.main:main`
- **CLI entrypoint**: `src/musicdl_cli/main.py` → `musicdl_cli.main:app`
- **Library**: `src/musicdl/` — core musicdl library (API client, services, models)

## Quick Commands

| Action | Command |
|--------|---------|
| Install (dev) | `pip install -e ".[dev]"` |
| Run GUI | `flet run src/musicdl_gui/main.py` or `python -m musicdl_gui.main` |
| Run CLI | `musicdl` or `python -m musicdl_cli.main` |
| Run tests | `pytest` |
| Coverage | `pytest --cov=musicdl_gui --cov-report=html` |
| Build macOS | `pyinstaller musicdl_gui.spec --clean` |
| Lint | `ruff check src/` |
| Typecheck | `pyright src/musicdl_gui/` |

## Architecture Notes

- **src layout**: `src/musicdl`, `src/musicdl_cli`, `src/musicdl_gui`
- **Tests**: `tests/` (unit + integration), pytest with `responses` for HTTP mocking
- **Config**: `~/.config/musicdl-gui/config.json` (auto-created)
- **Queue/Downloads**: persisted to `~/.config/musicdl-gui/queue.json`
- **Error log**: `~/.config/musicdl-gui/error.log` (rotating, 10MB/1000 entries)
- **Temp files**: `~/tmp/musicdl-gui-playback/` (auto-cleared on startup/exit)

## Key Dependencies
- **flet>=1.0.0** + **flet-audio>=0.1.0** (GUI + audio playback)
- **musicdl** (internal library — same repo)
- **pydantic>=2**, **requests**, **typer**, **rich**

## Developer Workflow

```bash
# 1. Install deps
pip install -e ".[dev]"

# 2. Run tests (all 100 pass)
pytest

# 2a. Run GUI-specific tests only
pytest src/musicdl_gui/

# 3. Lint + typecheck
ruff check src/
pyright src/musicdl_gui/

# 4. Run GUI
flet run src/musicdl_gui/main.py
```

## Typeguard Setup
- `install_import_hook("musicdl_gui")` + `install_import_hook("musicdl")` in `main.py`
- **Do not** install hook for `flet` (typeguard 4.x conflicts with flet's TypeVars)

## Flet 1.0 Compatibility (Critical)

| Flet 0.x | Flet 1.0 |
|----------|----------|
| `ft.Tab(text="...")` | `ft.Tab(label="...")` |
| `ft.Button(text="...")` | `ft.Button(content=ft.Text("..."))` |
| `ft.padding.symmetric(...)` | `ft.Padding(left=..., top=..., right=..., bottom=...)` |
| `ft.padding.only(...)` | `ft.Padding(left=..., top=..., right=..., bottom=...)` |
| `ft.border.all(...)` | `ft.Border(top=..., right=..., bottom=..., left=...)` |
| `ft.border.only(...)` | `ft.Border(top=..., right=..., bottom=..., left=...)` |
| `page.show_snack_bar(...)` | `page.overlay.append(SnackBar(..., open=True))` |
| `ft.ElevatedButton` | `ft.FilledButton` / `ft.OutlinedButton` |
| `ft.UserControl` | `ft.Column` / `ft.Container` |
| `ft.ImageFit` | `ft.BoxFit` |
| `ft.padding.symmetric` | `ft.Padding(left=..., top=..., right=..., bottom=...)` |
| `ft.border.all` | `ft.Border(top=..., right=..., bottom=..., left=...)` |
| `ft.ImageFit.COVER` | `ft.BoxFit.COVER` |
| `ft.padding.symmetric` | `ft.Padding(left=..., top=..., right=..., bottom=...)` |
| `ft.border.all` | `ft.Border(top=..., right=..., bottom=..., left=...)` |
| `ft.ImageFit.COVER` | `ft.BoxFit.COVER` |
| `PopupMenuItem(text="...")` | `PopupMenuItem(content=ft.Text("..."))` |
| `PopupMenuItem(leading=...)` | Removed — use `content=ft.Row([Icon, Text])` |
| `ft.padding.symmetric(...)` | `ft.Padding(left=..., top=..., right=..., bottom=...)` |
| `ft.border.all(...)` | `ft.Border(top=..., right=..., bottom=..., left=...)` |
| `ft.ImageFit.COVER` | `ft.BoxFit.COVER` |
| `ft.padding.symmetric(...)` | `ft.Padding(left=..., top=..., right=..., bottom=...)` |
| `ft.border.all(...)` | `ft.Border(top=..., right=..., bottom=..., left=...)` |
| `ft.ImageFit.COVER` | `ft.BoxFit.COVER` |
| `ft.padding.symmetric(...)` | `ft.Padding(left=..., top=..., right=..., bottom=...)` |
| `ft.border.all(...)` | `ft.Border(top=..., right=..., bottom=..., left=...)` |
| `ft.ImageFit.COVER` | `ft.BoxFit.COVER` |
| `page.run_interval()` | `asyncio.create_task()` with `asyncio.sleep()` |

## Common Gotchas

1. **Page.on_window_event** doesn't exist in Flet 1.0 — use `page.on_window_event = ...` only works in 0.x
2. **PopupMenuItem** in Flet 1.0 uses `content=ft.Text("...")` not `text="..."`, no `leading` param
3. **Padding/Border** must use explicit `ft.Padding` / `ft.Border` constructors
4. **Audio playback** uses `flet_audio` — `fta.Audio` with `src=str(file_path)`, not `ft.Audio`
5. **Duration/position** from flet-audio are `Duration` objects — use `.total_seconds()` or `.in_milliseconds / 1000.0`
6. **ft.Duration** has `.in_milliseconds` as property, not method
7. **ft.padding.only/symmetric** and **ft.border.all/only** don't exist

## Testing Notes
- Run `pytest` (all 100 tests pass)
- Coverage: `pytest --cov=musicdl_gui --cov-report=term-missing`
- Integration tests use `responses` for HTTP mocking
- Coverage targets: api(94%), config(95%), error_log(91%), queue(86%), models(100%)

## Build Notes
- **macOS**: `pyinstaller musicdl_gui.spec --clean` → `dist/musicdl-gui.app`
- **Spec file**: `musicdl_gui.spec` (includes flet client, assets, hidden imports)
- Flet client bundles Python — no system Python needed on target

## Config Files (auto-created)
- `~/.config/musicdl-gui/config.json` — API URL, IP, timeout, output dir, quality
- `~/.config/musicdl-gui/queue.json` — download queue persistence
- `~/.config/musicdl-gui/error.log` — rotating error log (10MB/1000 entries)