"""Cross-platform user data / cache / logs directory resolution.

Why a dedicated module:
- Settings (gui_settings.json) used to live in the install directory. On
  Windows, that's ``C:\\Program Files\\TRPG_Converter_Pro\\`` after the
  installer lands the app there, which is read-only for non-admin users.
  The settings save would silently fail or trigger a UAC prompt.
- Real desktop apps put user data in the OS-standard location:
    Windows : %APPDATA%\\TRPG_Converter_Pro\\
    macOS   : ~/Library/Application Support/TRPG_Converter_Pro/
    Linux   : ~/.config/TRPG_Converter_Pro/
- Cache (downloads, thumbnails) goes to a separate cache root:
    Windows : %LOCALAPPDATA%\\TRPG_Converter_Pro\\Cache\\
    macOS   : ~/Library/Caches/TRPG_Converter_Pro/
    Linux   : ~/.cache/TRPG_Converter_Pro/

We deliberately avoid the ``platformdirs`` dependency — these paths are
stable and well-documented; one small module costs less than another
runtime dep in the bundle.

Migration policy:
- On first run after upgrade, if ``<install_dir>/gui_settings.json`` exists
  and ``<user_data>/gui_settings.json`` does not, copy the legacy file over.
  This preserves all the user's settings across the move.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_FOLDER_NAME = "TRPG_Converter_Pro"


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

# Indirected platform check so mypy doesn't strict-narrow ``sys.platform``
# branches as unreachable on the current build host. The runtime value can
# differ from the typing assumption (e.g. PyInstaller cross-build, frozen exe
# from a different OS), so all three branches must compile on every platform.
_PLATFORM: str = sys.platform


def user_data_dir() -> Path:
    """Per-user writable directory for settings, presets, history."""
    if _PLATFORM == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_FOLDER_NAME
        return Path.home() / "AppData" / "Roaming" / APP_FOLDER_NAME
    if _PLATFORM == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_FOLDER_NAME
    # Linux / *BSD — follow XDG Base Directory Specification.
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / APP_FOLDER_NAME
    return Path.home() / ".config" / APP_FOLDER_NAME


def user_cache_dir() -> Path:
    """Per-user discardable cache (downloads, optimised images, etc.)."""
    if _PLATFORM == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_FOLDER_NAME / "Cache"
        return Path.home() / "AppData" / "Local" / APP_FOLDER_NAME / "Cache"
    if _PLATFORM == "darwin":
        return Path.home() / "Library" / "Caches" / APP_FOLDER_NAME
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / APP_FOLDER_NAME
    return Path.home() / ".cache" / APP_FOLDER_NAME


def user_logs_dir() -> Path:
    """Per-user log directory. On macOS this is platform-conventional separate."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_FOLDER_NAME
    # Windows + Linux: keep logs adjacent to settings for easy support extraction.
    return user_data_dir() / "logs"


# ---------------------------------------------------------------------------
# Files within the user data dir
# ---------------------------------------------------------------------------


def gui_settings_path() -> Path:
    return user_data_dir() / "gui_settings.json"


def history_path() -> Path:
    return user_data_dir() / "history.json"


def profiles_dir() -> Path:
    return user_data_dir() / "profiles"


def ensure_dirs() -> None:
    """Make sure every directory we'll write to exists. Cheap, idempotent."""
    for d in (user_data_dir(), user_cache_dir(), user_logs_dir(), profiles_dir()):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("Failed to create %s: %s", d, exc)


# ---------------------------------------------------------------------------
# Migration from legacy install-dir location
# ---------------------------------------------------------------------------


def migrate_from_install_dir(install_dir: Path) -> None:
    """If the legacy install-dir gui_settings.json exists, copy it to %APPDATA%.

    Idempotent — once the user_data file exists this becomes a no-op.
    The legacy file is left in place (read-only or removed on uninstall)
    so a rollback would still find the user's settings.
    """
    ensure_dirs()
    legacy = Path(install_dir) / "gui_settings.json"
    target = gui_settings_path()
    if target.exists():
        return
    if not legacy.exists():
        return
    try:
        shutil.copy2(legacy, target)
        logger.info("Migrated settings: %s -> %s", legacy, target)
    except OSError as exc:
        logger.warning("Settings migration failed: %s", exc)


__all__ = [
    "APP_FOLDER_NAME",
    "ensure_dirs",
    "gui_settings_path",
    "history_path",
    "migrate_from_install_dir",
    "profiles_dir",
    "user_cache_dir",
    "user_data_dir",
    "user_logs_dir",
]
