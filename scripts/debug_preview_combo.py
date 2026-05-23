"""Print runtime geometry of the preview-panel format combo.

Helps diagnose why the combo appears truncated despite setMinimumWidth.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from main import setup_app_logging, load_embedded_fonts  # noqa: E402

setup_app_logging()
app = QApplication(sys.argv)
load_embedded_fonts()

from core.config_manager import ConfigManager  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402

cm = ConfigManager(ROOT)
win = MainWindow(cm)
win.show()


def inspect():
    combo = win.document_preview.format_combo
    print(
        f"combo.size = {combo.size().width()}x{combo.size().height()}"
        f"  minimumWidth = {combo.minimumWidth()}"
        f"  minimumSizeHint = {combo.minimumSizeHint().width()}"
        f"  sizeHint = {combo.sizeHint().width()}"
    )
    parent = combo.parentWidget()
    while parent and parent.objectName() not in (
        "PreviewToolbar", "GlobalPreviewContainer", "MainSplitter"
    ):
        parent = parent.parentWidget()
    if parent:
        print(f"parent {parent.objectName()} = {parent.size().width()}x{parent.size().height()}")
    container = win.preview_container
    print(
        f"preview_container = {container.size().width()}x{container.size().height()}"
        f"  minWidth = {container.minimumWidth()}  maxWidth = {container.maximumWidth()}"
    )
    print(
        f"main_splitter sizes = {win.main_splitter.sizes()}"
    )
    app.quit()


QTimer.singleShot(2000, inspect)
sys.exit(app.exec())
