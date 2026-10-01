"""Shared test fixtures."""

import pytest


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