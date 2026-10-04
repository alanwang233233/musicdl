"""Song-related data models (getSongInfo / getSongUrl)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from musicdl.models.enums import CopyrightType


def _parse_time(value: Any) -> Any:
    """Parse ``%Y/%m/%d %H:%M:%S`` strings leniently, keep raw value otherwise."""
    if isinstance(value, str):
        try:
            # API 时间戳不带时区信息,按设计保持 naive datetime
            return datetime.strptime(value, "%Y/%m/%d %H:%M:%S")  # noqa: DTZ007
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
        url: Signed MP3 direct link (time-limited). May be None if unavailable.
        br: Bitrate in bps. May be None if unavailable.
        level: Quality level actually returned. May be None if unavailable.
        size: File size in bytes. May be None if unavailable.
        md5: Audio file MD5. May be None if unavailable.
        channel_layout: Channel layout, if reported.
        effects: Effects metadata, if reported.
        cookie: Account info used for streaming. May be None if unavailable.
        time: Data timestamp (parsed when well-formed). May be None if unavailable.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    url: str | None = None
    br: int | None = None
    level: str | None = None
    size: int | None = None
    md5: str | None = None
    channel_layout: str | None = Field(default=None, alias="channelLayout")
    effects: Any = None
    cookie: CookieInfo | None = None
    time: datetime | str | None = None

    @field_validator("time", mode="before")
    @classmethod
    def _time_lenient(cls, value: Any) -> Any:
        return _parse_time(value)
