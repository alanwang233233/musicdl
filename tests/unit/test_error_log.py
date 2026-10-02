import pytest
from musicdl_gui.error_log import ErrorLog, ErrorLogEntry


def test_log_exception_creates_entry():
    log = ErrorLog()
    log.clear()
    try:
        raise ValueError("test error")
    except ValueError as e:
        log.log_exception(e, "test_source", {"key": "value"})
    entries = log.get_entries()
    assert len(entries) == 1
    assert entries[0].exception_type == "ValueError"
    assert entries[0].message == "test error"
    assert entries[0].source == "test_source"


def test_log_message_creates_entry():
    log = ErrorLog()
    log.clear()
    log.log_message("WARNING", "test", "test message")
    entries = log.get_entries()
    assert len(entries) == 1
    assert entries[0].level == "WARNING"
    assert entries[0].message == "test message"


def test_get_entries_with_limit():
    log = ErrorLog()
    log.clear()
    for i in range(10):
        log.log_message("INFO", "test", f"message {i}")
    entries = log.get_entries(limit=5)
    assert len(entries) == 5


def test_clear_removes_all_entries():
    log = ErrorLog()
    log.log_message("INFO", "test", "message")
    log.clear()
    assert len(log.get_entries()) == 0


def test_export_writes_file(tmp_path):
    log = ErrorLog()
    log.clear()
    log.log_message("ERROR", "test", "error message")
    export_path = tmp_path / "export.log"
    log.export(export_path)
    assert export_path.exists()
    content = export_path.read_text()
    assert "error message" in content