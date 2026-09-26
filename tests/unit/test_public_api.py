"""Tests for the public top-level API surface."""

import musicdl


def test_public_names_exported() -> None:
    expected = [
        "MusicDLConfig",
        "SyncMusicClient",
        "PlaylistService",
        "SongService",
        "DownloadService",
        "Playlist",
        "PlaylistTrack",
        "PlaylistCreator",
        "SongInfo",
        "SongUrl",
        "CookieInfo",
        "QualityLevel",
        "CopyrightType",
        "MusicDLException",
        "APIError",
        "NetworkError",
        "ValidationError",
        "DownloadError",
        "ConfigError",
        "IPFetchError",
    ]
    for name in expected:
        assert hasattr(musicdl, name), f"missing public export: {name}"
        assert name in musicdl.__all__


def test_version() -> None:
    assert musicdl.__version__ == "0.1.0"
