"""Open About dialog and screenshot it."""
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

from gui.dialogs import AboutDialog
from gui.styles.theme import Theme
app.setStyleSheet(Theme.get_stylesheet())

dlg = AboutDialog()
dlg.show()


def grab():
    pm = dlg.grab()
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/about.png"
    pm.save(out)
    print(f"saved: {out} {pm.size().width()}x{pm.size().height()}")
    app.quit()


QTimer.singleShot(800, grab)
sys.exit(app.exec())
