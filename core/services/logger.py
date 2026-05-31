"""Application-wide logging.

Production-grade behaviour:

* **Rotating files** — ``logs/app.log`` rotates at 5 MiB, keeps 5 backups.
* **Optional JSON output** — set ``LOG_JSON=1`` for structured logs (one event per line).
* **Third-party noise dampened** — PIL/urllib3/Pillow drop to WARNING by default.
* **Idempotent setup** — calling ``setup_logging`` more than once does not duplicate
  handlers; existing handlers are torn down first.
* **UTF-8 everywhere** — required for the Korean log messages this app emits.

Style:
  * Korean strings = user-facing messages (e.g. "변환 실패").
  * English strings = internal/debug log lines.
  * Pass structured fields via ``extra={...}`` when emitting events worth grepping
    in production (e.g. ``extra={"event": "conversion.start", "file_count": 3}``).
"""
from __future__ import annotations

import contextlib
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import ClassVar

# Third-party loggers that flood DEBUG/INFO with noise we don't own.
_NOISY_LOGGERS = (
    "PIL",
    "PIL.Image",
    "PIL.PngImagePlugin",
    "urllib3",
    "asyncio",
    "matplotlib",
    "fontTools",
)


class _JsonFormatter(logging.Formatter):
    """One JSON object per line. Suitable for ingest into Loki / Datadog / CloudWatch."""

    _RESERVED: ClassVar[dict] = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.utcfromtimestamp(record.created).isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Extra fields attached via logger.info(..., extra={"event": "..."}).
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


class AppLogger:
    """Singleton wrapper around the root logger.

    Existing call-sites use ``setup_logging`` / ``get_logger`` free functions
    defined at module bottom; this class is kept for backwards compat.
    """

    _instance: AppLogger | None = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if AppLogger._initialized:
            return
        AppLogger._initialized = True
        self._log_dir: Path | None = None
        self._file_handler: logging.Handler | None = None
        self._console_handler: logging.Handler | None = None
        self._log_level: int = logging.INFO

    def setup(
        self,
        app_dir: Path,
        log_level: int = logging.INFO,
        console_output: bool = True,
        file_output: bool = True,
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 5,
        json_output: bool | None = None,
    ) -> None:
        self._log_level = log_level
        # In production: logs go to the OS-standard per-user dir so frozen
        # installs to Program Files don't need admin to write. In dev/tests
        # the caller passes an explicit app_dir (typically a tmp dir) and we
        # keep ``<app_dir>/logs`` so test isolation works.
        from core.paths import user_logs_dir
        if getattr(sys, "frozen", False):
            self._log_dir = user_logs_dir()
        else:
            self._log_dir = Path(app_dir) / "logs"
        if file_output:
            try:
                self._log_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                self._log_dir = Path(app_dir) / "logs"
                self._log_dir.mkdir(parents=True, exist_ok=True)

        if json_output is None:
            json_output = os.environ.get("LOG_JSON", "").lower() in {"1", "true", "yes"}

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Tear down any prior handlers to keep setup idempotent.
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            with contextlib.suppress(Exception):
                handler.close()

        text_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        json_formatter = _JsonFormatter()

        if console_output:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(log_level)
            # Console stays human-readable even when LOG_JSON is set, unless
            # the operator forces JSON via LOG_JSON_CONSOLE=1.
            console_is_json = (
                json_output
                and os.environ.get("LOG_JSON_CONSOLE", "").lower() in {"1", "true", "yes"}
            )
            self._console_handler.setFormatter(json_formatter if console_is_json else text_formatter)
            root_logger.addHandler(self._console_handler)

        if file_output and self._log_dir is not None:
            log_file = self._log_dir / "app.log"
            self._file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            self._file_handler.setLevel(log_level)
            self._file_handler.setFormatter(json_formatter if json_output else text_formatter)
            root_logger.addHandler(self._file_handler)

        # Dampen noisy third-party loggers.
        for noisy in _NOISY_LOGGERS:
            logging.getLogger(noisy).setLevel(logging.WARNING)

        # Drop ancient day-stamped logs from the previous implementation.
        self._purge_legacy_dated_logs()

        logging.getLogger(__name__).info(
            "Logging initialised (level=%s, json=%s, file=%s)",
            logging.getLevelName(log_level),
            json_output,
            file_output,
        )

    def _purge_legacy_dated_logs(self) -> None:
        """The old setup wrote ``app_YYYYMMDD.log``. Remove them to avoid clutter."""
        if not self._log_dir:
            return
        for legacy in self._log_dir.glob("app_*.log"):
            with contextlib.suppress(OSError):
                legacy.unlink()

    def set_level(self, level: int) -> None:
        self._log_level = level
        logging.getLogger().setLevel(level)
        for handler in (self._console_handler, self._file_handler):
            if handler is not None:
                handler.setLevel(level)

    def get_log_dir(self) -> Path | None:
        return self._log_dir

    def get_recent_logs(self, lines: int = 100) -> list[str]:
        if not self._log_dir:
            return []
        candidates = sorted(self._log_dir.glob("app.log*"), reverse=True)
        if not candidates:
            return []
        try:
            with open(candidates[0], encoding="utf-8") as fh:
                return fh.readlines()[-lines:]
        except OSError:
            return []


app_logger = AppLogger()


def setup_logging(app_dir: Path, debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    app_logger.setup(app_dir, log_level=level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
