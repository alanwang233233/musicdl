"""Playlist retrieval with automatic pagination."""

from __future__ import annotations

from typing import Iterator

from musicdl.api import endpoints
from musicdl.client import SyncMusicClient
from musicdl.models import Playlist, PlaylistTrack


class PlaylistService:
    """Fetch playlist metadata and tracks from playlist_trackall.

    Pagination rule: keep requesting with ``offset += len(songs)`` until
    the returned ``songs`` array is empty, the accumulated count reaches
    ``song_count``, or a page returns fewer than ``limit`` items.

    Args:
        client: Configured HTTP client.
        page_size: Default page size (limit) used by automatic pagination.
    """

    def __init__(self, client: SyncMusicClient, page_size: int = 500) -> None:
        self._client = client
        self.page_size = page_size

    def get_tracks(self, playlist_id: str | int, *, limit: int, offset: int) -> Playlist:
        """Fetch a single page of playlist tracks.

        Args:
            playlist_id: Playlist ID.
            limit: Page size (max songs per response).
            offset: Pagination offset (0-based).

        Returns:
            Playlist with the tracks of this page.

        Raises:
            APIError / NetworkError / ValidationError: Propagated from the client.
        """
        body = self._client.post_json(
            endpoints.PLAYLIST_TRACKALL,
            {"id": str(playlist_id), "limit": limit, "offset": offset},
        )
        return Playlist.model_validate(body["data"])

    def iter_tracks(self, playlist_id: str | int, *, page_size: int | None = None) -> Iterator[PlaylistTrack]:
        """Iterate all tracks of a playlist, fetching pages automatically.

        Args:
            playlist_id: Playlist ID.
            page_size: Overrides the service default page size.

        Yields:
            Each track in playlist order.

        Raises:
            APIError / NetworkError / ValidationError: Propagated from the client.
        """
        size = page_size if page_size is not None else self.page_size
        offset = 0
        expected: int | None = None
        yielded = 0
        while True:
            page = self.get_tracks(playlist_id, limit=size, offset=offset)
            if expected is None:
                expected = page.song_count
            if not page.songs:
                return
            yield from page.songs
            yielded += len(page.songs)
            offset += len(page.songs)
            if yielded >= expected:
                return
            if len(page.songs) < size:
                return

    def get_all_tracks(self, playlist_id: str | int, *, page_size: int | None = None) -> Playlist:
        """Fetch a playlist with its complete track list.

        Args:
            playlist_id: Playlist ID.
            page_size: Overrides the service default page size.

        Returns:
            Playlist metadata from the first page plus all collected songs.

        Raises:
            APIError / NetworkError / ValidationError: Propagated from the client.
        """
        size = page_size if page_size is not None else self.page_size
        offset = 0
        first: Playlist | None = None
        songs: list[PlaylistTrack] = []
        while True:
            page = self.get_tracks(playlist_id, limit=size, offset=offset)
            if first is None:
                first = page
            if not page.songs:
                break
            songs.extend(page.songs)
            offset += len(page.songs)
            if len(songs) >= page.song_count or len(page.songs) < size:
                break
        assert first is not None
        return first.model_copy(update={"songs": songs})