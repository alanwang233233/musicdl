"""Tests for pydantic data models."""

from datetime import datetime

from musicdl.models import (
    CookieInfo,
    CopyrightType,
    Playlist,
    PlaylistTrack,
    QualityLevel,
    SongInfo,
    SongUrl,
)


def test_quality_level_value() -> None:
    assert QualityLevel.STANDARD.value == "standard"
    assert isinstance(QualityLevel.STANDARD, str)


def test_copyright_type_values() -> None:
    assert CopyrightType.NO_COPYRIGHT == 0
    assert CopyrightType.COPYRIGHT == 1
    assert CopyrightType.OTHER == 2


def test_song_info_from_fixture(load_fixture) -> None:
    info = SongInfo.model_validate(load_fixture("song_info.json")["data"])
    assert info.id == 1432544572
    assert info.name == "想想念念"
    assert info.free is False
    assert info.copyright == CopyrightType.COPYRIGHT
    assert isinstance(info.time, datetime)
    assert info.time.year == 2026


def test_song_info_unknown_copyright_maps_to_other() -> None:
    data = {
        "id": 1,
        "name": "x",
        "free": True,
        "album": "a",
        "singer": "s",
        "picimg": "http://x/1.jpg",
        "duration": "1:00",
        "copyright": 99,
        "time": "2026/09/12 17:25:27",
    }
    info = SongInfo.model_validate(data)
    assert info.copyright == CopyrightType.OTHER


def test_song_info_invalid_time_kept_as_string() -> None:
    data = {
        "id": 1,
        "name": "x",
        "free": True,
        "album": "a",
        "singer": "s",
        "picimg": "http://x/1.jpg",
        "duration": "1:00",
        "copyright": 1,
        "time": "not-a-date",
    }
    info = SongInfo.model_validate(data)
    assert info.time == "not-a-date"


def test_song_url_from_fixture(load_fixture) -> None:
    url = SongUrl.model_validate(load_fixture("song_url.json")["data"])
    assert url.id == 1432544572
    assert url.url.startswith("https://")
    assert url.br == 128000
    assert url.size == 3209133
    assert url.channel_layout is None
    assert url.effects is None
    assert isinstance(url.cookie, CookieInfo)
    assert url.cookie.index == 1


def test_playlist_aliases_from_fixture(load_fixture) -> None:
    pl = Playlist.model_validate(load_fixture("playlist_page1.json")["data"])
    assert pl.cover_image.startswith("https://")
    assert pl.song_count == 3
    assert pl.play_count == 38
    assert pl.description is None
    assert pl.tags == ["流行"]
    assert pl.creator.name == "Error404-Official"
    assert len(pl.songs) == 2
    assert isinstance(pl.songs[0], PlaylistTrack)


def test_playlist_accepts_snake_case_keys() -> None:
    data = {
        "id": 1,
        "name": "p",
        "cover_image": "http://x/c.jpg",
        "song_count": 0,
        "play_count": 0,
        "description": None,
        "tags": [],
        "creator": {"uid": 1, "avatar": "http://x/a.jpg", "name": "n"},
        "songs": [],
    }
    pl = Playlist.model_validate(data)
    assert pl.song_count == 0


def test_playlist_track_is_song_info_subclass() -> None:
    assert issubclass(PlaylistTrack, SongInfo)
