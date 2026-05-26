"""Diagnostic bundle exporter — one-click 'send me the logs' workflow.

When a user reports a bug, support typically needs:
  - the app version + OS / Python
  - the rolling app.log tail
  - any recent crash dumps
  - the user's gui_settings.json (so settings-shaped bugs reproduce)
  - the install dir layout (so missing-file bugs surface)

Bundling these into a single ZIP makes "please send me the logs" a 5-second
task for the user instead of a 5-minute treasure hunt.

Privacy: the bundle stays on disk; it is never uploaded automatically.
``gui_settings.json`` may contain customised paths or character names — the
user controls what to share.
"""
from __future__ import annotations

import io
import json
import logging
import platform
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.paths import user_data_dir, user_logs_dir
from core.version import __app_name__, __version__

logger = logging.getLogger(__name__)


def build_diagnostic_zip(output_path: Optional[Path] = None) -> Path:
    """Collect runtime + log + settings data into a single ZIP.

    Args:
        output_path: Where to write the ZIP. Default = Desktop with a
            timestamped name (or the user data dir if Desktop is unavailable).

    Returns:
        The path the ZIP was written to.
    """
    if output_path is None:
        output_path = _default_output_path()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    user_data = user_data_dir()
    logs = user_logs_dir()

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Runtime info ----------------------------------------------------
        zf.writestr("info.txt", _runtime_info())

        # 2. App log (last 1MB chunk if too large)
        for log in sorted(logs.glob("app.log*")):
            try:
                data = log.read_bytes()
                # Truncate to last 1 MiB to keep the bundle small.
                if len(data) > 1024 * 1024:
                    data = data[-(1024 * 1024):]
                    arcname = f"logs/{log.name}.tail"
                else:
                    arcname = f"logs/{log.name}"
                zf.writestr(arcname, data)
            except OSError as exc:
                logger.warning("Skipped %s: %s", log, exc)

        # 3. Crash dumps
        crashes = user_data / "crashes"
        if crashes.exists():
            for dump in sorted(crashes.glob("crash_*.txt"))[-10:]:  # last 10
                try:
                    zf.writestr(f"crashes/{dump.name}", dump.read_bytes())
                except OSError:
                    pass

        # 4. gui_settings.json (redacted — strip base64 image blobs)
        settings_path = user_data / "gui_settings.json"
        if settings_path.exists():
            try:
                payload = json.loads(settings_path.read_text(encoding="utf-8"))
                payload = _redact_large_blobs(payload)
                zf.writestr(
                    "gui_settings.json",
                    json.dumps(payload, ensure_ascii=False, indent=2),
                )
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipped settings: %s", exc)

        # 5. User data dir listing (filenames only, no content)
        listing = io.StringIO()
        listing.write(f"# {user_data}\n")
        for p in sorted(user_data.rglob("*")):
            try:
                rel = p.relative_to(user_data)
                size = p.stat().st_size if p.is_file() else "-"
                listing.write(f"{size!s:>10}  {rel}\n")
            except OSError:
                continue
        zf.writestr("user_data_listing.txt", listing.getvalue())

    logger.info("Diagnostic bundle written: %s (%d bytes)",
                output_path, output_path.stat().st_size)
    return output_path


def _runtime_info() -> str:
    return (
        f"{__app_name__} diagnostic bundle\n"
        f"version:     {__version__}\n"
        f"generated:   {datetime.now().isoformat()}\n"
        f"os:          {platform.platform()}\n"
        f"python:      {sys.version.splitlines()[0]}\n"
        f"frozen:      {getattr(sys, 'frozen', False)}\n"
        f"executable:  {sys.executable}\n"
        f"user_data:   {user_data_dir()}\n"
        f"user_logs:   {user_logs_dir()}\n"
    )


def _redact_large_blobs(settings: dict) -> dict:
    """Replace base64-looking long strings with a placeholder.

    Cover images and custom assets in settings can be 100KB+ base64 blobs that
    bloat the bundle and may contain user-private images. We strip those.
    """
    THRESHOLD = 4096

    def walk(value):
        if isinstance(value, str) and len(value) > THRESHOLD:
            return f"<redacted: {len(value)} chars>"
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value

    return walk(settings)


def _default_output_path() -> Path:
    """Pick a user-friendly default location for the bundle."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"TRPG_Converter_Pro_diagnostics_{ts}.zip"

    desktop_candidates = [
        Path.home() / "Desktop",
        Path.home() / "바탕 화면",  # Korean Windows
        Path.home() / "デスクトップ",  # Japanese
    ]
    for d in desktop_candidates:
        if d.exists() and d.is_dir():
            return d / fname

    return user_data_dir() / fname


__all__ = ["build_diagnostic_zip"]
