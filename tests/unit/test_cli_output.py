"""Tests for musicdl_cli Rich output helpers."""

from musicdl.models import Playlist, PlaylistTrack
from musicdl_cli.ui.output import print_playlist_info, print_track_list


def make_track(song_id: int, name: str, singer: str) -> PlaylistTrack:
    return PlaylistTrack.model_validate(
        {
            "id": song_id,
            "name": name,
            "free": True,
            "album": "专辑",
            "singer": singer,
            "picimg": "https://example.com/c.jpg",
            "duration": "3:00",
            "copyright": 1,
            "time": "2026/09/12 17:25:27",
        }
    )


def make_playlist() -> Playlist:
    return Playlist.model_validate(
        {
            "id": 18120707017,
            "name": "测试歌单",
            "coverImage": "https://example.com/cover.jpg",
            "songCount": 2,
            "playCount": 100,
            "description": "一个测试歌单",
            "tags": ["流行", "电子"],
            "creator": {"uid": 1, "avatar": "https://example.com/a.jpg", "name": "创建者"},
            "songs": [
                make_track(1, "歌曲A", "歌手X").model_dump(),
                make_track(2, "歌曲B", "歌手Y").model_dump(),
            ],
        }
    )


def test_print_playlist_info_runs_without_error(capsys):
    print_playlist_info(make_playlist())
    captured = capsys.readouterr()
    assert "测试歌单" in captured.out
    assert "18120707017" in captured.out


def test_print_track_list_runs_without_error(capsys):
    tracks = [make_track(1, "歌曲A", "歌手X"), make_track(2, "歌曲B", "歌手Y")]
    print_track_list(tracks)
    captured = capsys.readouterr()
    assert "歌曲A" in captured.out
    assert "歌手X" in captured.out
    assert "歌曲B" in captured.out
