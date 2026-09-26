"""Playlist-related data models (playlist_trackall)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from musicdl.models.song import SongInfo


class PlaylistCreator(BaseModel):
    """Creator of a playlist."""

    model_config = ConfigDict(populate_by_name=True)

    uid: int
    avatar: str
    name: str


class PlaylistTrack(SongInfo):
    """A single track inside a playlist (same shape as SongInfo)."""


class Playlist(BaseModel):
    """Playlist metadata with its tracks.

    Attributes:
        id: Playlist ID.
        name: Playlist name.
        cover_image: Cover image URL.
        song_count: Total number of songs.
        play_count: Play count.
        description: Description, may be ``None``.
        tags: Tag list.
        creator: Playlist creator.
        songs: Tracks fetched so far (may be partial).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    cover_image: str = Field(alias="coverImage")
    song_count: int = Field(alias="songCount")
    play_count: int = Field(alias="playCount")
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    creator: PlaylistCreator
    songs: list[PlaylistTrack] = Field(default_factory=list)