"""Enumerations used across musicdl models."""

from __future__ import annotations

from enum import Enum


class QualityLevel(str, Enum):
    """Audio quality levels accepted by the getSongUrl endpoint."""

    STANDARD = "standard"


class CopyrightType(int, Enum):
    """Copyright flags returned in song data.

    Unknown values are tolerated and mapped to ``OTHER`` during parsing.
    """

    NO_COPYRIGHT = 0
    COPYRIGHT = 1
    OTHER = 2
