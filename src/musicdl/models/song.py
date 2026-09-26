"""Song-related data models (getSongInfo / getSongUrl)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from musicdl.models.enums import CopyrightType


def _parse_time(value: Any) -> Any:
    """Parse ``%Y/%m/%d %H:%M:%S`` strings leniently, keep raw value otherwise."""
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            return value
    return value


class SongInfo(BaseModel):
    """Song metadata returned by getSongInfo and playlist_trackall.

    Attributes:
        id: Unique song ID.
        name: Song title.
        free: Whether the song is free to play.
        album: Album name.
        singer: Artist(s), slash-separated when multiple.
        picimg: Cover image URL.
        duration: Duration as ``mm:ss``.
        copyright: Copyright flag.
        time: Data timestamp (parsed when well-formed).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    free: bool
    album: str
    singer: str
    picimg: str
    duration: str
    copyright: CopyrightType
    time: datetime | str

    @field_validator("copyright", mode="before")
    @classmethod
    def _copyright_lenient(cls, value: Any) -> Any:
        try:
            return CopyrightType(int(value))
        except (TypeError, ValueError):
            return CopyrightType.OTHER

    @field_validator("time", mode="before")
    @classmethod
    def _time_lenient(cls, value: Any) -> Any:
        return _parse_time(value)


class CookieInfo(BaseModel):
    """Account cookie used to obtain a stream URL."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    index: int


class SongUrl(BaseModel):
    """Playback URL returned by getSongUrl.

    Attributes:
        id: Song ID.
        url: Signed MP3 direct link (time-limited).
        br: Bitrate in bps.
        level: Quality level actually returned.
        size: File size in bytes.
        md5: Audio file MD5.
        channel_layout: Channel layout, if reported.
        effects: Effects metadata, if reported.
        cookie: Account info used for streaming.
        time: Data timestamp (parsed when well-formed).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    url: str
    br: int
    level: str
    size: int
    md5: str
    channel_layout: str | None = None
    effects: Any = None
    cookie: CookieInfo
    time: datetime | str

    @field_validator("time", mode="before")
    @classmethod
    def _time_lenient(cls, value: Any) -> Any:
        return _parse_time(value)