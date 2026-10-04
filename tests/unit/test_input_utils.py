"""Tests for input_utils.extract_id."""

from musicdl_gui.input_utils import extract_id


def test_plain_id_passthrough():
    assert extract_id("2249180720") == "2249180720"


def test_extracts_id_param_from_url():
    assert extract_id("https://music.xxx.com/xxx?id=2249180720&xxx=xxx") == "2249180720"


def test_extracts_id_with_whitespace_around_url():
    assert extract_id("  https://music.xxx.com/play?id=42  ") == "42"


def test_url_without_id_param_falls_back_to_raw():
    raw = "https://music.xxx.com/xxx?foo=1"
    assert extract_id(raw) == raw


def test_plain_non_numeric_falls_back_to_raw():
    assert extract_id("abc") == "abc"


def test_query_only_value():
    assert extract_id("?id=42") == "42"


def test_empty_input():
    assert extract_id("") == ""
    assert extract_id(None) == ""
