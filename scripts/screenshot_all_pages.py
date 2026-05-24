"""Launch app, switch through all pages, screenshot each.

Saves <prefix>_<page>.png for each tab. Used to visually audit UI consistency.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from main import load_embedded_fonts, setup_app_logging

setup_app_logging()
app = QApplication(sys.argv)
load_embedded_fonts()

from core.config_manager import ConfigManager
from gui.main_window import MainWindow
from gui.styles.theme import Theme

app.setStyleSheet(Theme.get_stylesheet())

cm = ConfigManager(ROOT)
win = MainWindow(cm)
win.show()
win.resize(1300, 800)


OUTPUT_PREFIX = sys.argv[1] if len(sys.argv) > 1 else "/tmp/page"

PAGE_KEYS = ["home", "format_style", "parsing_content", "advanced"]


def _shoot_page(idx: int):
    if idx >= len(PAGE_KEYS):
        app.quit()
        return
    key = PAGE_KEYS[idx]
    page = win.pages.get(key)
    if page is None:
        QTimer.singleShot(50, lambda: _shoot_page(idx + 1))
        return
    win.stackedWidget.setCurrentWidget(page)
    QTimer.singleShot(900, lambda: _grab_and_continue(idx))


def _grab_and_continue(idx: int):
    key = PAGE_KEYS[idx]
    pm = win.grab()
    out = f"{OUTPUT_PREFIX}_{key}.png"
    pm.save(out)
    print(f"saved {out}: {pm.size().width()}x{pm.size().height()}", flush=True)
    QTimer.singleShot(150, lambda: _shoot_page(idx + 1))


QTimer.singleShot(1500, lambda: _shoot_page(0))
sys.exit(app.exec())
