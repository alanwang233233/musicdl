"""Tests for the download playlist CLI command."""

from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from musicdl_cli.main import app

runner = CliRunner()


def test_download_playlist_requires_playlist_id():
    result = runner.invoke(app, ["download", "playlist"])
    assert result.exit_code != 0


def test_download_playlist_help():
    result = runner.invoke(app, ["download", "playlist", "--help"])
    assert result.exit_code == 0
    assert "--output-dir" in result.output
    assert "--quality" in result.output
    assert "--ip" in result.output
    assert "--max-retries" in result.output
    assert "--retry-wait" in result.output
    assert "--skip-existing" in result.output
    assert "--skip-failed" in result.output


def test_download_playlist_invokes_services(tmp_path: Path):
    mock_playlist = Mock()
    mock_playlist.name = "测试歌单"
    mock_playlist.songs = []
    mock_playlist.tags = []
    mock_playlist.description = None
    mock_playlist.cover_image = ""
    mock_playlist.play_count = 0
    mock_playlist.creator = Mock()
    mock_playlist.creator.name = "创建者"
    mock_playlist.creator.uid = 1
    mock_playlist.creator.avatar = ""
    mock_playlist.id = 123

    mock_playlist_service = Mock()
    mock_playlist_service.get_all_tracks.return_value = mock_playlist

    mock_downloader = Mock()
    mock_downloader.download_song.return_value = tmp_path / "test.mp3"

    with (
        patch("musicdl_cli.commands.download.SyncMusicClient") as MockSyncClient,
        patch("musicdl_cli.commands.download.PlaylistService") as MockPlaylistService,
        patch("musicdl_cli.commands.download.SongService") as MockSongService,
        patch("musicdl_cli.commands.download.DownloadService") as MockDownloadService,
    ):
        # Setup context manager for SyncMusicClient
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        MockSyncClient.return_value = mock_client

        MockPlaylistService.return_value = mock_playlist_service
        MockSongService.return_value = Mock()
        MockDownloadService.return_value = mock_downloader

        result = runner.invoke(app, ["download", "playlist", "123", "--output-dir", str(tmp_path), "--skip-failed"])

    assert result.exit_code == 0
    mock_playlist_service.get_all_tracks.assert_called_once_with("123")
    # Verify downloader was instantiated
    MockDownloadService.assert_called()