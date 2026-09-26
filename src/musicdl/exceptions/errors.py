"""Custom exceptions for musicdl.

The library never swallows exceptions: every failure is raised as a
``MusicDLException`` subclass and handled by the caller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence


class MusicDLException(Exception):
    """Base class for all musicdl errors."""


class ConfigError(MusicDLException):
    """Raised when the library is misconfigured (e.g. missing IP)."""


class IPFetchError(MusicDLException):
    """Raised when the public IP could not be fetched automatically."""


class APIError(MusicDLException):
    """Raised when the API returns a non-200 business code or HTTP 4xx.

    Attributes:
        code: Status code returned by the API (or the HTTP status).
        message: Human readable error message.
        payload: Raw response body, when available.
    """

    def __init__(self, code: int, message: str, payload: Any = None) -> None:
        self.code = code
        self.message = message
        self.payload = payload
        super().__init__(f"API error {code}: {message}")


class NetworkError(MusicDLException):
    """Raised when a request fails at transport level (after retries).

    Attributes:
        original: The underlying ``requests`` exception, if any.
    """

    def __init__(self, message: str, original: BaseException | None = None) -> None:
        self.original = original
        super().__init__(message)


class ValidationError(MusicDLException):
    """Raised when a response body cannot be parsed or validated.

    Attributes:
        original: The underlying parsing/validation exception.
    """

    def __init__(self, message: str, original: BaseException | None = None) -> None:
        self.original = original
        super().__init__(message)


class DownloadError(MusicDLException):
    """Raised when downloading a song fails.

    Attributes:
        song_id: ID of the song that failed, when known.
        output_path: Target path the download was writing to.
        completed: Paths already downloaded in this batch (playlist mode).
        original: The underlying exception, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        song_id: int | str | None = None,
        output_path: Path | None = None,
        completed: Sequence[Path] = (),
        original: BaseException | None = None,
    ) -> None:
        self.song_id = song_id
        self.output_path = output_path
        self.completed = list(completed)
        self.original = original
        super().__init__(message)
