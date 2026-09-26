"""Tests for the musicdl exception hierarchy."""

from pathlib import Path

from musicdl.exceptions import (
    APIError,
    ConfigError,
    DownloadError,
    IPFetchError,
    MusicDLException,
    NetworkError,
    ValidationError,
)


def test_all_exceptions_subclass_base() -> None:
    for exc_cls in (ConfigError, IPFetchError, APIError, NetworkError, ValidationError, DownloadError):
        assert issubclass(exc_cls, MusicDLException)
        assert issubclass(exc_cls, Exception)


def test_api_error_carries_code_and_payload() -> None:
    err = APIError(code=404, message="playlist not found", payload={"code": 404})
    assert err.code == 404
    assert err.message == "playlist not found"
    assert err.payload == {"code": 404}
    assert "404" in str(err)


def test_network_error_keeps_original_exception() -> None:
    cause = OSError("connection reset")
    err = NetworkError("request failed", original=cause)
    assert err.original is cause


def test_validation_error_keeps_original_exception() -> None:
    cause = ValueError("bad json")
    err = ValidationError("invalid response", original=cause)
    assert err.original is cause


def test_download_error_carries_context() -> None:
    cause = OSError("disk full")
    done = [Path("a.mp3"), Path("b.mp3")]
    err = DownloadError(
        "failed",
        song_id=1432544572,
        output_path=Path("c.mp3"),
        completed=done,
        original=cause,
    )
    assert err.song_id == 1432544572
    assert err.output_path == Path("c.mp3")
    assert err.completed == done
    assert err.original is cause


def test_download_error_defaults() -> None:
    err = DownloadError("failed")
    assert err.song_id is None
    assert err.output_path is None
    assert err.completed == []
    assert err.original is None