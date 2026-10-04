"""Shared pytest fixtures for musicdl tests."""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_error_log(tmp_path, monkeypatch):
    """Keep ErrorLog away from the real user directory.

    ErrorLog uses module-level path constants and a process-wide singleton,
    and it replaces ``sys.excepthook`` on first use. Without this fixture
    tests would write into the real ``~/.config/musicdl-gui/error.log`` and
    leak hook state between tests.
    """
    import musicdl_gui.error_log as error_log_module

    monkeypatch.setattr(error_log_module, "LOG_DIR", tmp_path)
    monkeypatch.setattr(error_log_module, "LOG_FILE", tmp_path / "error.log")
    monkeypatch.setattr(error_log_module, "_instance", None, raising=False)
    old_hook = sys.excepthook
    yield
    sys.excepthook = old_hook
    error_log_module._instance = None


@pytest.fixture
def load_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a loader that reads a JSON fixture by file name."""

    def _load(name: str) -> dict[str, Any]:
        return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def mock_config():
    """Return a mock MusicDLConfig for testing."""
    from musicdl import MusicDLConfig
    return MusicDLConfig(
        base_url="https://test.example.com",
        ip="127.0.0.1",
        timeout=5.0,
        max_retries=1,
    )
