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

    mock_playlist_service = Mock()
    mock_playlist_service.get_all_tracks.return_value = mock_playlist

    mock_downloader = Mock()
    mock_downloader.download_playlist.return_value = []

    with (
        patch("musicdl_cli.commands.download.PlaylistService") as MockPlaylistService,
        patch("musicdl_cli.commands.download.DownloadService") as MockDownloadService,
    ):
        MockPlaylistService.return_value = mock_playlist_service
        MockDownloadService.return_value = mock_downloader
        result = runner.invoke(app, ["download", "playlist", "123", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    mock_playlist_service.get_all_tracks.assert_called_once_with("123")
    mock_downloader.download_playlist.assert_called_once()
