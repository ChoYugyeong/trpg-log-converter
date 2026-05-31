"""Global crash handler — writes a diagnostic dump on unhandled exceptions.

Production-grade safety net:
- Catches anything that escapes the Qt event loop or main thread.
- Writes a timestamped ``crashes/<iso-ts>.txt`` with: app version, OS,
  Python version, exception traceback, last 200 log lines.
- Logs to the regular logger so JSON ingest works.
- Never blocks the original exception propagation — re-raises so Qt's
  default ``abort`` still fires (so the OS reports it).

No PII collected, no network call. Pure local file write.
"""
from __future__ import annotations

import contextlib
import logging
import platform
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

from core.version import __app_name__, __version__

logger = logging.getLogger(__name__)


_INSTALLED = False
_CRASH_DIR: Path | None = None


def install(app_dir: Path) -> None:
    """Install global excepthook + threading.excepthook.

    Crash dumps go to ``<user_data_dir>/crashes/`` (writable by non-admin
    users even when installed to Program Files). ``app_dir`` is ignored but
    kept for backwards compatible callers.
    """
    global _INSTALLED, _CRASH_DIR
    if _INSTALLED:
        return
    try:
        from core.paths import user_data_dir
        _CRASH_DIR = user_data_dir() / "crashes"
    except ImportError:
        _CRASH_DIR = Path(app_dir) / "crashes"
    try:
        _CRASH_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Last-resort fallback.
        _CRASH_DIR = Path(app_dir) / "crashes"
        _CRASH_DIR.mkdir(parents=True, exist_ok=True)

    sys.excepthook = _excepthook
    # Threads spawned by Qt and concurrent.futures need their own hook.
    # AttributeError defense is just in case (we target 3.10+ where this exists).
    with contextlib.suppress(AttributeError):
        threading.excepthook = _thread_excepthook

    _INSTALLED = True
    logger.info("Crash handler installed (dumps -> %s)", _CRASH_DIR)


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        # Let Ctrl+C through cleanly.
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    _write_dump(exc_type, exc_value, exc_tb, source="excepthook")
    # Defer to the default handler so the OS still sees the crash.
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def _thread_excepthook(args) -> None:  # ``threading.ExceptHookArgs``
    if args.exc_type is None or issubclass(args.exc_type, SystemExit):
        return
    _write_dump(
        args.exc_type,
        args.exc_value,
        args.exc_traceback,
        source=f"thread:{args.thread.name if args.thread else '?'}",
    )


def _write_dump(exc_type, exc_value, exc_tb, *, source: str) -> None:
    if _CRASH_DIR is None:
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _CRASH_DIR / f"crash_{ts}.txt"

    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

    header = (
        f"{__app_name__} crash report\n"
        f"app_version: {__version__}\n"
        f"timestamp:   {datetime.now().isoformat()}\n"
        f"source:      {source}\n"
        f"os:          {platform.platform()}\n"
        f"python:      {sys.version.splitlines()[0]}\n"
        f"frozen:      {getattr(sys, 'frozen', False)}\n"
        f"executable:  {sys.executable}\n"
        f"---\n"
    )

    log_tail = _read_log_tail(200)

    try:
        path.write_text(
            header + "TRACEBACK\n---\n" + tb_text + "\n\nRECENT LOG\n---\n" + log_tail,
            encoding="utf-8",
        )
        logger.error(
            "Crash dump written: %s (%s)", path.name, exc_type.__name__,
            exc_info=(exc_type, exc_value, exc_tb),
        )
    except OSError as write_err:
        # Last resort — at least try to log it.
        logger.exception("Failed to write crash dump: %s", write_err)


def _read_log_tail(lines: int) -> str:
    """Read last N lines of the app log for the dump. Cheap & best-effort."""
    if _CRASH_DIR is None:
        return ""
    log_file = _CRASH_DIR.parent / "logs" / "app.log"
    if not log_file.exists():
        return "(no log file)"
    try:
        with open(log_file, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    except OSError:
        return "(failed to read log)"
