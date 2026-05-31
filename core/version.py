"""Application version metadata — single source of truth.

Why centralised:
- About dialog reads this for "Version 2.2.0 (build 42)"
- Update service compares against GitHub Releases API tag (e.g. "v2.3.0")
- main.py sets QApplication.applicationVersion / aboutToQuit logs
- PyInstaller spec can read this at build time

Convention: semver (MAJOR.MINOR.PATCH) without leading 'v'. GitHub release
tags are prefixed with 'v' and stripped during comparison.
"""

from __future__ import annotations

__version__ = "2.4.0"
__app_name__ = "TRPG Log Converter Pro"
__author__ = "TRPG Tools"
__copyright__ = "© 2026 TRPG Tools"
__license__ = "MIT"
__homepage__ = "https://github.com/ChoYugyeong/trpg-log-converter"
__update_repo__ = "ChoYugyeong/trpg-log-converter"


def version_tuple() -> tuple[int, int, int]:
    """Parse __version__ into a comparable tuple. Used by the updater."""
    parts = __version__.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)


def is_newer_than(remote: str) -> bool:
    """Return True if ``remote`` version string is newer than current.

    Accepts ``v2.3.0`` or ``2.3.0`` form. Returns False for malformed strings.
    """
    try:
        clean = remote.lstrip("v").strip()
        parts = clean.split(".")
        remote_t = (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
        return remote_t > version_tuple()
    except (ValueError, IndexError):
        return False


__all__ = [
    "__app_name__",
    "__author__",
    "__copyright__",
    "__homepage__",
    "__license__",
    "__update_repo__",
    "__version__",
    "is_newer_than",
    "version_tuple",
]
