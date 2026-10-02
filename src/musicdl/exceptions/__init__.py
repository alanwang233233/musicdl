"""Custom exception hierarchy for musicdl."""

from musicdl.exceptions.errors import (
    APIError,
    ConfigError,
    DownloadError,
    IPFetchError,
    MusicDLException,
    NetworkError,
    ValidationError,
)

__all__ = [
    "APIError",
    "ConfigError",
    "DownloadError",
    "IPFetchError",
    "MusicDLException",
    "NetworkError",
    "ValidationError",
]
