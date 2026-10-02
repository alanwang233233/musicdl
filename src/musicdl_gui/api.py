"""Async wrapper around musicdl SyncMusicClient."""

from __future__ import annotations

import asyncio
from typing import Any

from musicdl import (
    MusicDLConfig,
    SyncMusicClient,
    PlaylistService,
    SongService,
    Playlist,
    SongInfo,
    SongUrl,
)
from musicdl.exceptions import MusicDLException
from musicdl_gui.error_log import ErrorLog


class ApiClient:
    """Async wrapper for musicdl API calls."""

    def __init__(self, config: MusicDLConfig) -> None:
        self._config = config
        self._client: SyncMusicClient | None = None
        self._playlist_service: PlaylistService | None = None
        self._song_service: SongService | None = None
        self._error_log = ErrorLog()

    def _ensure_client(self) -> SyncMusicClient:
        if self._client is None:
            self._client = SyncMusicClient(self._config)
            self._playlist_service = PlaylistService(self._client)
            self._song_service = SongService(self._client)
        return self._client

    async def fetch_playlist(self, playlist_id: str) -> Playlist:
        """Fetch playlist with all tracks."""
        try:
            client = self._ensure_client()
            return await asyncio.to_thread(
                self._playlist_service.get_all_tracks, playlist_id
            )
        except MusicDLException as e:
            self._error_log.log_exception(e, "api_client", {"playlist_id": playlist_id})
            raise

    async def fetch_song_info(self, song_id: int) -> SongInfo:
        """Fetch song metadata."""
        try:
            client = self._ensure_client()
            return await asyncio.to_thread(self._song_service.get_info, song_id)
        except MusicDLException as e:
            self._error_log.log_exception(e, "api_client", {"song_id": song_id})
            raise

    async def get_song_url(self, song_id: int, level: str | None = None) -> SongUrl:
        """Fetch song playback URL."""
        try:
            client = self._ensure_client()
            return await asyncio.to_thread(
                self._song_service.get_url, song_id, level=level
            )
        except MusicDLException as e:
            self._error_log.log_exception(e, "api_client", {"song_id": song_id, "level": level})
            raise

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None