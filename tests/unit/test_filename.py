"""Tests for the shared filename sanitizer."""

import pytest

from musicdl import sanitize_filename
from musicdl.filename import sanitize_path_segments


def test_replaces_slash_with_semicolon():
    assert sanitize_filename("AC/DC") == "AC;DC"


def test_replaces_backslash_and_glob_metacharacters():
    # `*` `?` 会破坏路径/glob 语义,必须替换;`[` `]` 不在替换范围,
    # 由"精确路径比较"(存在性检查不再用 glob)保证安全
    assert sanitize_filename("Love [Remix]") == "Love [Remix]"
    assert sanitize_filename("Why?") == "Why_"
    assert sanitize_filename("a*b\\c") == "a_b_c"


def test_replaces_illegal_and_control_characters():
    assert sanitize_filename('a:b*c?"<>|d') == "a_b_c_____d"
    assert sanitize_filename("a\x00b") == "a_b"


def test_strips_trailing_dots_and_spaces():
    assert sanitize_filename("name. .") == "name"
    assert sanitize_filename("  name  ") == "name"


def test_empty_becomes_underscore():
    assert sanitize_filename("") == "_"
    assert sanitize_filename("///") == ";;;"


def test_path_segments_block_traversal():
    # API 返回的数据不得通过 ".." 段逃逸输出目录
    assert sanitize_path_segments(["..", "title"]) == ["_", "title"]
    assert sanitize_path_segments([".", "x"]) == ["_", "x"]


def test_path_segments_normalizes_each_segment():
    # 段内的 "/" 会被替换为 ";";各段独立净化
    assert sanitize_path_segments(["a/b"]) == ["a;b"]


@pytest.mark.parametrize("value", [123, None, 4.5])
def test_accepts_non_string_values(value):
    assert isinstance(sanitize_filename(value), str)
