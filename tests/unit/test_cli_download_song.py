"""Tests for the download song CLI command."""

from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from musicdl_cli.main import app

runner = CliRunner()


def test_download_song_requires_song_id():
    result = runner.invoke(app, ["download", "song"])
    assert result.exit_code != 0


def test_download_song_help():
    result = runner.invoke(app, ["download", "song", "--help"])
    assert result.exit_code == 0
    assert "--output-dir" in result.output
    assert "--quality" in result.output
    assert "--ip" in result.output
    assert "--max-retries" in result.output
    assert "--retry-wait" in result.output


def test_download_song_invokes_download_service(tmp_path: Path):
    mock_client = Mock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    mock_downloader = Mock()
    mock_downloader.download_song.return_value = tmp_path / "test.mp3"

    with patch("musicdl_cli.commands.download._create_client_and_downloader") as mock_factory:
        mock_factory.return_value = (mock_client, mock_downloader)
        result = runner.invoke(app, ["download", "song", "12345", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    mock_downloader.download_song.assert_called_once()
    call_kwargs = mock_downloader.download_song.call_args
    assert call_kwargs[0][0] == "12345"
