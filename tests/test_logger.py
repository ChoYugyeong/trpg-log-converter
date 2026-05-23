"""Coverage tests for the application logger."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from core.services.logger import AppLogger, get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_singleton():
    """Logger is a singleton; reset between tests so each gets a clean root."""
    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:  # noqa: BLE001
            pass


def test_setup_logging_creates_log_dir(tmp_path: Path):
    setup_logging(tmp_path, debug=False)
    assert (tmp_path / "logs").exists()


def test_setup_logging_writes_to_rotating_file(tmp_path: Path):
    setup_logging(tmp_path, debug=True)
    logging.getLogger(__name__).info("hello from test")

    # Force flush handlers so the file is written.
    for handler in logging.getLogger().handlers:
        handler.flush()

    log_file = tmp_path / "logs" / "app.log"
    assert log_file.exists()
    assert "hello from test" in log_file.read_text(encoding="utf-8")


def test_setup_is_idempotent(tmp_path: Path):
    """Calling setup twice must not duplicate handlers."""
    setup_logging(tmp_path)
    before = len(logging.getLogger().handlers)
    setup_logging(tmp_path)
    after = len(logging.getLogger().handlers)
    assert before == after


def test_json_output_mode_emits_one_object_per_line(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOG_JSON", "1")
    AppLogger().setup(tmp_path, log_level=logging.INFO, console_output=False, file_output=True)

    logging.getLogger(__name__).info("structured event", extra={"event": "test.fire", "value": 42})
    for handler in logging.getLogger().handlers:
        handler.flush()

    log_file = tmp_path / "logs" / "app.log"
    lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if line]
    assert lines, "no log lines written"

    # Find our event line and verify it's parseable JSON.
    parsed = [json.loads(line) for line in lines if "test.fire" in line]
    assert parsed, "structured event missing from JSON log"
    assert parsed[0]["event"] == "test.fire"
    assert parsed[0]["value"] == 42
    assert parsed[0]["level"] == "INFO"


def test_third_party_loggers_dampened(tmp_path: Path):
    setup_logging(tmp_path)
    # PIL should be at WARNING, not DEBUG/INFO.
    assert logging.getLogger("PIL").level >= logging.WARNING
    assert logging.getLogger("urllib3").level >= logging.WARNING


def test_get_logger_returns_named_instance():
    assert get_logger("foo.bar").name == "foo.bar"


def test_set_level_updates_root_and_handlers(tmp_path: Path):
    AppLogger().setup(tmp_path, log_level=logging.WARNING)
    AppLogger().set_level(logging.DEBUG)
    assert logging.getLogger().level == logging.DEBUG
