"""Open the Roll20 help dialog programmatically and screenshot it.

This bypasses GUI clicks — we directly call ``_show_log_help_dialog`` on the
loaded MainWindow.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap

# Replicate main.py initialisation order.
from main import load_embedded_fonts, setup_app_logging  # noqa: E402

setup_app_logging()
app = QApplication(sys.argv)
load_embedded_fonts()

from core.config_manager import ConfigManager  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402
from gui.styles.theme import Theme  # noqa: E402

app.setStyleSheet(Theme.get_stylesheet())

cm = ConfigManager(ROOT)
win = MainWindow(cm)
win.show()
win.resize(1300, 800)


def open_and_shoot():
    # 1. ensure home_page exists
    home = win.home_page
    # 2. open Roll20 help (non-blocking — modal would block exec())
    #    We'll grab the topmost widget instead. Trick: schedule shoot after dialog opens.
    QTimer.singleShot(900, _grab_dialog)
    home._show_log_help_dialog("roll20")


def _grab_dialog():
    # Find any visible QDialog as a child of the app.
    from PySide6.QtWidgets import QDialog
    dialogs = [w for w in app.topLevelWidgets() if isinstance(w, QDialog) and w.isVisible()]
    if dialogs:
        dlg = dialogs[0]
        pm = dlg.grab()
        pm.save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dlg.png")
        print(f"saved dialog: {pm.size().width()}x{pm.size().height()}")
    else:
        print("no visible dialog found")
    app.quit()


QTimer.singleShot(1500, open_and_shoot)
sys.exit(app.exec())
