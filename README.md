# MusicDL GUI

Cross-platform GUI for the [musicdl](https://github.com/musicdl/musicdl) library, built with Python + Flet.

## Features

- **Playlist Browser**: Fetch and browse playlists by ID
- **Song Downloader**: Preview and download individual songs
- **Download Queue**: Serial download management with persistence
- **Settings**: Configure API, download, and quality options
- **Error Log**: Real-time error tracking and export

## Installation

### From Source

```bash
git clone https://github.com/musicdl/musicdl-gui.git
cd musicdl-gui
pip install -e ".[dev]"
```

### Run

```bash
flet run src/musicdl_gui/main.py
```

Or:

```bash
python -m musicdl_gui.main
```

## Build

### macOS

```bash
pyinstaller musicdl_gui.spec --clean
```

Output: `dist/musicdl-gui.app`

## Development

### Run Tests

```bash
pytest
```

### Code Coverage

```bash
pytest --cov=musicdl_gui --cov-report=html
```

## Configuration

Configuration is stored in `~/.config/musicdl-gui/config.json`.

## License

MIT