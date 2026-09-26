"""musicdl — Python client library for the self-hosted NextMusic API.

Quick start::

    from musicdl import MusicDLConfig, SyncMusicClient, PlaylistService

    with SyncMusicClient(MusicDLConfig(ip="1.2.3.4")) as client:
        playlist = PlaylistService(client).get_all_tracks("18120707017")
"""

from musicdl.client import SyncMusicClient
from musicdl.config import MusicDLConfig
from musicdl.exceptions import (
    APIError,
    ConfigError,
    DownloadError,
    IPFetchError,
    MusicDLException,
    NetworkError,
    ValidationError,
)
from musicdl.models import (
    CookieInfo,
    CopyrightType,
    Playlist,
    PlaylistCreator,
    PlaylistTrack,
    QualityLevel,
    SongInfo,
    SongUrl,
)
from musicdl.services import DownloadService, PlaylistService, SongService

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "MusicDLConfig",
    "SyncMusicClient",
    "PlaylistService",
    "SongService",
    "DownloadService",
    "Playlist",
    "PlaylistCreator",
    "PlaylistTrack",
    "SongInfo",
    "SongUrl",
    "CookieInfo",
    "QualityLevel",
    "CopyrightType",
    "MusicDLException",
    "ConfigError",
    "IPFetchError",
    "APIError",
    "NetworkError",
    "ValidationError",
    "DownloadError",
]