"""Tests for DownloadService."""

from pathlib import Path
from unittest.mock import Mock

import pytest
import responses

from musicdl.exceptions import APIError, ConfigError, DownloadError, NetworkError
from musicdl.models import Playlist, QualityLevel, SongInfo, SongUrl
from musicdl.services.download import DownloadService

AUDIO = b"ID3 fake mp3 audio bytes " * 10  # 270 bytes
MP3_URL = "https://cdn.example.com/signed/audio.mp3?vuutv=sig"


def make_song_info(song_id: int = 1, name: str = "曲名", singer: str = "歌手A", album: str = "专辑") -> SongInfo:
    return SongInfo.model_validate(
        {
            "id": song_id,
            "name": name,
            "free": True,
            "album": album,
            "singer": singer,
            "picimg": "https://example.com/c.jpg",
            "duration": "3:00",
            "copyright": 1,
            "time": "2026/09/12 17:25:27",
        }
    )


def make_song_url(song_id: int = 1, size: int = len(AUDIO)) -> SongUrl:
    return SongUrl.model_validate(
        {
            "id": song_id,
            "url": MP3_URL,
            "br": 128000,
            "level": "standard",
            "size": size,
            "md5": "x" * 32,
            "channelLayout": None,
            "effects": None,
            "cookie": {"id": "netease-2", "label": "backup", "index": 1},
            "time": "2026/09/12 17:27:44",
        }
    )


def make_song_service(info: SongInfo | None = None) -> Mock:
    service = Mock()
    service.get_info.return_value = info or make_song_info()
    service.get_url.return_value = make_song_url()
    service.client.config.timeout = 5.0
    return service


def make_playlist(songs: list[SongInfo]) -> Playlist:
    return Playlist.model_validate(
        {
            "id": 99,
            "name": "我的歌单",
            "coverImage": "https://example.com/cover.jpg",
            "songCount": len(songs),
            "playCount": 0,
            "description": None,
            "tags": [],
            "creator": {"uid": 1, "avatar": "https://example.com/a.jpg", "name": "n"},
            "songs": [s.model_dump() for s in songs],
        }
    )


@responses.activate
def test_download_song_with_explicit_output(tmp_path: Path) -> None:
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    svc = make_song_service()
    downloader = DownloadService(svc, output_dir=tmp_path)
    target = tmp_path / "explicit.mp3"
    result = downloader.download_song(1, output=target)
    assert result == target
    assert target.read_bytes() == AUDIO
    svc.get_url.assert_called_once_with(1, level=None)


@responses.activate
def test_download_song_without_output_uses_template(tmp_path: Path) -> None:
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    svc = make_song_service(make_song_info(singer="皮卡丘多多", name="想想念念"))
    downloader = DownloadService(svc, output_dir=tmp_path)
    result = downloader.download_song(1)
    assert result == tmp_path / "皮卡丘多多 - 想想念念.mp3"
    assert result.exists()


@responses.activate
def test_illegal_characters_sanitized(tmp_path: Path) -> None:
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    svc = make_song_service(make_song_info(singer="AC/DC", name='a:b*c?"d'))
    downloader = DownloadService(svc, output_dir=tmp_path)
    result = downloader.download_song(1)
    assert "/" not in result.name and ":" not in result.name
    assert result.name == "AC_DC - a_b_c__d.mp3"


@responses.activate
def test_progress_callback_invoked(tmp_path: Path) -> None:
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    calls: list[tuple[int, int]] = []
    svc = make_song_service()
    downloader = DownloadService(
        svc,
        output_dir=tmp_path,
        progress_callback=lambda done, total: calls.append((done, total)),
    )
    downloader.download_song(1)
    assert calls, "progress callback was never called"
    assert calls[-1] == (len(AUDIO), len(AUDIO))


@responses.activate
def test_download_song_failure_raises_download_error(tmp_path: Path) -> None:
    svc = make_song_service()
    svc.get_url.side_effect = APIError(code=500, message="url service down")
    downloader = DownloadService(svc, output_dir=tmp_path)
    with pytest.raises(DownloadError) as exc_info:
        downloader.download_song(1, output=tmp_path / "x.mp3")
    assert isinstance(exc_info.value.original, APIError)
    assert not (tmp_path / "x.mp3").exists()


@responses.activate
def test_http_failure_cleans_partial_file(tmp_path: Path) -> None:
    responses.add(responses.GET, MP3_URL, body="boom", status=500)
    svc = make_song_service()
    downloader = DownloadService(svc, output_dir=tmp_path)
    with pytest.raises(DownloadError):
        downloader.download_song(1, output=tmp_path / "x.mp3")
    assert not (tmp_path / "x.mp3").exists()
    assert not (tmp_path / "x.mp3.part").exists()


@responses.activate
def test_playlist_skips_existing_files(tmp_path: Path) -> None:
    playlist = make_playlist([make_song_info(song_id=1), make_song_info(song_id=2, name="第二首")])
    existing = tmp_path / "歌手A - 曲名.mp3"
    existing.write_bytes(b"already here")
    svc = make_song_service()
    downloader = DownloadService(svc, output_dir=tmp_path)
    # Track 1 pre-exists; track 2 must still be downloaded.
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    svc.get_url.side_effect = None
    svc.get_url.return_value = make_song_url(song_id=2)
    result = downloader.download_playlist(playlist, skip_existing=True)
    assert existing.read_bytes() == b"already here"
    assert len(result) == 2
    assert svc.get_url.call_count == 1  # only the missing track


@responses.activate
def test_playlist_default_failure_raises_with_context(tmp_path: Path) -> None:
    playlist = make_playlist([make_song_info(song_id=1), make_song_info(song_id=2, name="第二首")])
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    svc = make_song_service()
    svc.get_url.side_effect = [make_song_url(song_id=1), NetworkError("boom")]
    downloader = DownloadService(svc, output_dir=tmp_path)
    with pytest.raises(DownloadError) as exc_info:
        downloader.download_playlist(playlist, skip_failed=False)
    err = exc_info.value
    assert err.song_id == 2
    assert err.output_path == tmp_path / "歌手A - 第二首.mp3"
    assert err.completed == [tmp_path / "歌手A - 曲名.mp3"]
    assert isinstance(err.original, NetworkError)


@responses.activate
def test_playlist_skip_failed_continues(tmp_path: Path) -> None:
    playlist = make_playlist([make_song_info(song_id=1), make_song_info(song_id=2, name="第二首")])
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    svc = make_song_service()
    svc.get_url.side_effect = [NetworkError("boom"), make_song_url(song_id=2)]
    downloader = DownloadService(svc, output_dir=tmp_path)
    result = downloader.download_playlist(playlist, skip_failed=True)
    assert result == [tmp_path / "歌手A - 第二首.mp3"]


def test_playlist_id_without_service_raises_config_error(tmp_path: Path) -> None:
    svc = make_song_service()
    downloader = DownloadService(svc, output_dir=tmp_path)
    with pytest.raises(ConfigError):
        downloader.download_playlist("18120707017")


def test_unknown_placeholder_raises_config_error(tmp_path: Path) -> None:
    svc = make_song_service()
    downloader = DownloadService(svc, output_dir=tmp_path, naming_template="{nope}")
    with pytest.raises(ConfigError):
        downloader.download_song(1, output=None)


@responses.activate
def test_subdirectory_template(tmp_path: Path) -> None:
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    svc = make_song_service(make_song_info(singer="歌手A", name="曲名", album="专辑X"))
    downloader = DownloadService(
        svc,
        output_dir=tmp_path,
        naming_template="{singer}/{album} - {title}",
    )
    result = downloader.download_song(1)
    assert result == tmp_path / "歌手A" / "专辑X - 曲名.mp3"
    assert result.exists()


@responses.activate
def test_level_forwarded_to_get_url(tmp_path: Path) -> None:
    responses.add(responses.GET, MP3_URL, body=AUDIO, status=200, content_type="audio/mpeg")
    svc = make_song_service()
    downloader = DownloadService(svc, output_dir=tmp_path)
    downloader.download_song(1, level=QualityLevel.STANDARD, output=tmp_path / "a.mp3")
    svc.get_url.assert_called_once_with(1, level=QualityLevel.STANDARD)
