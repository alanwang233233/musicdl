"""Single-song and playlist downloading (sequential, no resume)."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Callable

import requests

from musicdl.exceptions import ConfigError, DownloadError, MusicDLException
from musicdl.models import Playlist, QualityLevel, SongInfo
from musicdl.services.playlist import PlaylistService
from musicdl.services.song import SongService

logger = logging.getLogger(__name__)

_ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _sanitize(value: object) -> str:
    """Replace characters that are illegal in file names with ``_``."""
    return _ILLEGAL_CHARS.sub("_", str(value)).strip()


class DownloadService:
    """Download songs as MP3 files.

    Downloads are sequential (no concurrency), stream to a ``.part``
    file and are atomically renamed on success. Failures are raised as
    exceptions — the library never swallows them unless the caller
    explicitly opts in via ``skip_failed=True``.

    Args:
        song_service: Service used to resolve playback URLs (and metadata
            when rendering output names).
        playlist_service: Required only when ``download_playlist`` is
            called with a playlist ID instead of a ``Playlist`` object.
        output_dir: Base output directory.
        naming_template: Relative path template (without extension).
            Placeholders: ``{id}``, ``{singer}``, ``{title}``, ``{album}``,
            ``{track_number}``, ``{playlist}``. Literal ``/`` in the
            template creates subdirectories.
        progress_callback: Called after each written chunk with
            ``(downloaded_bytes, total_bytes)``; ``total_bytes`` is ``-1``
            when unknown.

    Raises:
        ConfigError: Missing playlist service or invalid template.
        DownloadError: A download failed (carries song_id/output/completed).
    """

    def __init__(
        self,
        song_service: SongService,
        playlist_service: PlaylistService | None = None,
        *,
        output_dir: Path = Path("."),
        naming_template: str = "{singer} - {title}",
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        self._songs = song_service
        self._playlists = playlist_service
        self.output_dir = Path(output_dir)
        self.naming_template = naming_template
        self._progress = progress_callback

    def _values(self, info: SongInfo, *, track_number: str, playlist: str) -> dict[str, str]:
        return {
            "id": str(info.id),
            "singer": _sanitize(info.singer),
            "title": _sanitize(info.name),
            "album": _sanitize(info.album),
            "track_number": track_number,
            "playlist": _sanitize(playlist),
        }

    def _render(self, values: dict[str, str]) -> Path:
        try:
            return Path(self.naming_template.format_map(values) + ".mp3")
        except KeyError as exc:
            raise ConfigError(f"unknown placeholder {exc} in naming_template") from exc

    def download_song(
        self,
        song_id: str | int,
        *,
        level: QualityLevel | str | None = None,
        output: Path | None = None,
    ) -> Path:
        """Download a single song.

        Args:
            song_id: Song ID.
            level: Quality level passed to ``SongService.get_url``.
            output: Explicit target file. When ``None``, the file name is
                rendered from ``naming_template`` using ``get_info`` data.

        Returns:
            The path of the downloaded file.

        Raises:
            APIError: Resolving song metadata failed.
            ConfigError: The naming template is invalid.
            DownloadError: The stream download failed.
        """
        if output is None:
            info = self._songs.get_info(song_id)
            target = self.output_dir / self._render(self._values(info, track_number="", playlist=""))
        else:
            target = Path(output)
        self._download_one(song_id, target, level)
        return target

    def download_playlist(
        self,
        playlist: Playlist | str | int,
        *,
        level: QualityLevel | str | None = None,
        output_dir: Path | None = None,
        skip_existing: bool = True,
        skip_failed: bool = False,
    ) -> list[Path]:
        """Download every track of a playlist sequentially.

        Args:
            playlist: A ``Playlist`` object or a playlist ID (the latter
                requires ``playlist_service``).
            level: Quality level passed to ``SongService.get_url``.
            output_dir: Overrides the configured ``output_dir``.
            skip_existing: Skip tracks whose target file already exists
                (counted as completed).
            skip_failed: When ``True``, a failed track is logged and
                skipped instead of raising — an explicit opt-in.

        Returns:
            Paths of the files that exist after the run (including skips).

        Raises:
            ConfigError: Playlist ID given without ``playlist_service``,
                or the naming template is invalid.
            DownloadError: A track failed and ``skip_failed=False``
                (carries ``song_id``, ``output_path``, ``completed``).
        """
        if not isinstance(playlist, Playlist):
            if self._playlists is None:
                raise ConfigError(
                    "playlist_service is required to resolve a playlist ID; "
                    "pass a Playlist object instead"
                )
            playlist = self._playlists.get_all_tracks(playlist)
        base = Path(output_dir) if output_dir is not None else self.output_dir
        completed: list[Path] = []
        for index, track in enumerate(playlist.songs, start=1):
            values = self._values(track, track_number=str(index), playlist=playlist.name)
            target = base / self._render(values)
            if skip_existing and target.exists():
                completed.append(target)
                continue
            try:
                self._download_one(track.id, target, level)
            except Exception as exc:
                if skip_failed:
                    logger.warning("skipping song %s (%s): %s", track.id, track.name, exc)
                    continue
                if isinstance(exc, DownloadError):
                    # _download_one already attached song_id/output_path/original;
                    # just add batch context and re-raise without double-wrapping.
                    exc.completed = list(completed)
                    raise
                raise DownloadError(
                    f"failed to download track {track.id} ({track.name})",
                    song_id=track.id,
                    output_path=target,
                    completed=list(completed),
                    original=exc,
                ) from exc
            completed.append(target)
        return completed

    def _download_one(
        self,
        song_id: str | int,
        target: Path,
        level: QualityLevel | str | None,
    ) -> None:
        part_path = target.with_name(target.name + ".part")
        try:
            url = self._songs.get_url(song_id, level=level)
            target.parent.mkdir(parents=True, exist_ok=True)
            timeout = float(self._songs.client.config.timeout)
            with requests.get(url.url, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                total = url.size if url.size > 0 else -1
                downloaded = 0
                with open(part_path, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if self._progress is not None:
                            self._progress(downloaded, total)
            os.replace(part_path, target)
        except DownloadError:
            raise
        except (requests.RequestException, OSError, MusicDLException) as exc:
            part_path.unlink(missing_ok=True)
            raise DownloadError(
                f"failed to download song {song_id}",
                song_id=song_id,
                output_path=target,
                original=exc,
            ) from exc