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
from musicdl.filename import sanitize_filename
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
    "APIError",
    "ConfigError",
    "CookieInfo",
    "CopyrightType",
    "DownloadError",
    "DownloadService",
    "IPFetchError",
    "MusicDLConfig",
    "MusicDLException",
    "NetworkError",
    "Playlist",
    "PlaylistCreator",
    "PlaylistService",
    "PlaylistTrack",
    "QualityLevel",
    "SongInfo",
    "SongService",
    "SongUrl",
    "SyncMusicClient",
    "ValidationError",
    "__version__",
    "sanitize_filename",
]
