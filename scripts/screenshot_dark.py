"""Force dark theme and capture every page + key dialog.

Theme.AUTO follows the system, so manual override is needed to audit dark mode
in isolation. Saves resources/screenshots/dark_*.png — committed alongside
light variants so PR reviewers can spot regressions.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from qfluentwidgets import Theme, setTheme

from main import load_embedded_fonts, setup_app_logging

setup_app_logging()
app = QApplication(sys.argv)
load_embedded_fonts()

# Force dark before any window is constructed.
setTheme(Theme.DARK)

from core.config_manager import ConfigManager
from gui.main_window import MainWindow
from gui.styles.theme import Theme as StyleTheme

app.setStyleSheet(StyleTheme.get_stylesheet())

out_dir = ROOT / "resources" / "screenshots"
out_dir.mkdir(parents=True, exist_ok=True)

cm = ConfigManager(ROOT)
settings = cm.get_gui_settings()
settings["_welcome_seen"] = True  # avoid welcome dialog stealing focus
cm.save_gui_settings(settings)

win = MainWindow(cm)
win.resize(1280, 800)
win.show()

PAGES = ["home", "format_style", "parsing_content", "advanced"]


def _shoot(idx: int):
    if idx >= len(PAGES):
        _shoot_dialogs()
        return
    key = PAGES[idx]
    page = win.pages.get(key)
    if page is None:
        QTimer.singleShot(50, lambda: _shoot(idx + 1))
        return
    win.stackedWidget.setCurrentWidget(page)
    QTimer.singleShot(700, lambda: _grab_page(idx))


def _grab_page(idx: int):
    key = PAGES[idx]
    pm = win.grab()
    out = out_dir / f"dark_{key}.png"
    pm.save(str(out))
    print(f"saved {out}: {pm.size().width()}x{pm.size().height()}", flush=True)
    QTimer.singleShot(120, lambda: _shoot(idx + 1))


def _shoot_dialogs():
    """Capture About and Welcome on top of dark home, then quit."""
    from gui.dialogs import AboutDialog, WelcomeDialog

    win.stackedWidget.setCurrentWidget(win.pages["home"])

    def grab_welcome():
        dlg = WelcomeDialog(win)
        dlg.show()
        QTimer.singleShot(700, lambda: _grab_dialog(dlg, "welcome"))

    def grab_about():
        dlg = AboutDialog(win)
        dlg.show()
        QTimer.singleShot(700, lambda: _grab_dialog(dlg, "about", final=True))

    def _grab_dialog(dlg, name, *, final=False):
        pm = dlg.grab()
        out = out_dir / f"dark_{name}.png"
        pm.save(str(out))
        print(f"saved {out}: {pm.size().width()}x{pm.size().height()}", flush=True)
        dlg.close()
        if final:
            QTimer.singleShot(200, app.quit)
        else:
            QTimer.singleShot(200, grab_about)

    QTimer.singleShot(400, grab_welcome)


QTimer.singleShot(1500, lambda: _shoot(0))
sys.exit(app.exec())
