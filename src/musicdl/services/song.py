"""Song metadata and playback URL retrieval."""

from __future__ import annotations

from musicdl.api import endpoints
from musicdl.client import SyncMusicClient
from musicdl.models import QualityLevel, SongInfo, SongUrl


class SongService:
    """Fetch song details and signed playback URLs.

    Args:
        client: Configured HTTP client (kept as the public ``client``
            attribute so other services can read its configuration).
    """

    def __init__(self, client: SyncMusicClient) -> None:
        self.client = client

    def get_info(self, song_id: str | int) -> SongInfo:
        """Fetch metadata for a single song.

        Args:
            song_id: Song ID.

        Returns:
            Validated song metadata.

        Raises:
            APIError / NetworkError / ValidationError: Propagated from the client.
        """
        body = self.client.post_json(endpoints.GET_SONG_INFO, {"id": str(song_id)})
        return SongInfo.model_validate(body["data"])

    def get_url(self, song_id: str | int, *, level: QualityLevel | str | None = None) -> SongUrl:
        """Fetch a signed MP3 playback URL for a song.

        Args:
            song_id: Song ID.
            level: Quality level; ``None`` uses ``client.config.default_level``.
                Enums are sent as their value, arbitrary strings pass through.

        Returns:
            Validated playback URL data (the URL itself is time-limited).

        Raises:
            APIError / NetworkError / ValidationError: Propagated from the client.
        """
        chosen = self.client.config.default_level if level is None else level
        level_value = chosen.value if isinstance(chosen, QualityLevel) else chosen
        body = self.client.post_json(
            endpoints.GET_SONG_URL,
            {"id": str(song_id), "level": level_value},
        )
        return SongUrl.model_validate(body["data"])
