"""Shared filename sanitization for downloads."""

from __future__ import annotations

import re

_ILLEGAL_CHARS = re.compile(r'[\\:*?"<>|\x00-\x1f]')


def sanitize_filename(value: object) -> str:
    """Sanitize a single filename segment.

    ``/`` becomes ``;`` (readability), other illegal characters (including
    ``\\`` and glob metacharacters) become ``_``. Trailing dots and spaces
    are stripped (Windows). Empty results become ``_``.
    """
    sanitized = _ILLEGAL_CHARS.sub("_", str(value).replace("/", ";")).strip()
    sanitized = sanitized.rstrip(" .")
    return sanitized or "_"


def sanitize_path_segments(parts: list[str]) -> list[str]:
    """Sanitize each segment of a relative path, blocking traversal segments.

    API-controlled values must never be able to escape the output directory,
    so a segment that is exactly ``.`` or ``..`` is replaced with ``_``.
    """
    return ["_" if part in (".", "..") else sanitize_filename(part) for part in parts]
