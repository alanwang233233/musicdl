"""Shared pytest fixtures for musicdl tests."""

import json
from pathlib import Path
from typing import Any, Callable

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
