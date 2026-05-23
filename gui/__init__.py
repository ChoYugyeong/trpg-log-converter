"""TRPG Log Converter Pro — GUI package.

The package is intentionally side-effect free at import time so that headless
contexts (CLI, tests, config-only code paths) can load ``gui.config_models``
without dragging in PySide6.

``from gui import MainWindow`` still works via PEP 562 ``__getattr__``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .main_window import MainWindow

__all__ = ["MainWindow"]


def __getattr__(name: str):
    if name == "MainWindow":
        from .main_window import MainWindow as _MainWindow
        return _MainWindow
    raise AttributeError(f"module 'gui' has no attribute {name!r}")
