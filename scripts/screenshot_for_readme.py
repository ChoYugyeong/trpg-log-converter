"""Render screenshots for the README at a fixed 1280×800 window size.

Why a dedicated script: ``screenshot_app.py`` grabs whatever the user's last
window size was, which can be smaller than ideal for marketing screenshots.
We launch the app inline, force a known size, then ``QWidget.grab()``.

Usage: python scripts/screenshot_for_readme.py <out_dir>
"""
from __future__ import annotations

import sys
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

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "resources/screenshots")
out_dir.mkdir(parents=True, exist_ok=True)

cm = ConfigManager(ROOT)
# Mark welcome dialog as seen so it doesn't pop up over the home shot.
settings = cm.get_gui_settings()
settings["_welcome_seen"] = True
cm.save_gui_settings(settings)

win = MainWindow(cm)
win.resize(1280, 800)
win.show()


def grab_home():
    pm = win.grab()
    out = out_dir / "home.png"
    pm.save(str(out))
    print(f"saved {out}: {pm.size().width()}x{pm.size().height()}")
    app.quit()


QTimer.singleShot(1500, grab_home)
sys.exit(app.exec())
