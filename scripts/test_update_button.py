"""Programmatically trigger _check_for_updates and verify UI stays responsive.

This is a smoke test for the user-reported "press update, app freezes" bug.
After clicking, we measure how long the UI stays unresponsive. If urlopen
truly blocks the main thread the elapsed time will exceed the timeout.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from main import load_embedded_fonts, setup_app_logging
setup_app_logging()
app = QApplication(sys.argv)
load_embedded_fonts()

from core.config_manager import ConfigManager
from gui.main_window import MainWindow
from gui.styles.theme import Theme

app.setStyleSheet(Theme.get_stylesheet())

cm = ConfigManager(ROOT)
settings = cm.get_gui_settings()
settings["_welcome_seen"] = True
cm.save_gui_settings(settings)

win = MainWindow(cm)
win.show()

results = {"started": False, "result_seen": False, "ui_ticks": 0}


def tick_ui():
    """Fires every 50ms while the check is running. If the main thread is
    blocked, this would stop being called → ui_ticks won't grow."""
    if results["started"] and not results["result_seen"]:
        results["ui_ticks"] += 1


def click_update_button():
    results["started"] = True
    results["t_click"] = time.monotonic()
    print(f"[t=0.00s] Clicking _check_for_updates(silent=False)...", flush=True)
    win._check_for_updates(silent=False)


def on_result_arrived(info, silent):
    results["result_seen"] = True
    elapsed = time.monotonic() - results["t_click"]
    print(
        f"[t={elapsed:.2f}s] Result received: info={info}, "
        f"ui_ticks_during_check={results['ui_ticks']}",
        flush=True,
    )
    if results["ui_ticks"] >= 10:
        print("  ✓ UI remained responsive (ticks > 10)", flush=True)
    else:
        print("  ✗ UI was BLOCKED during the check", flush=True)
    QTimer.singleShot(500, app.quit)


# Patch the result handler to also notify us.
orig_handler = win._on_update_check_result
def patched_handler(info, silent):
    orig_handler(info, silent)
    on_result_arrived(info, silent)
win._on_update_check_result = patched_handler

# Sample UI thread responsiveness every 50ms.
ticker = QTimer()
ticker.timeout.connect(tick_ui)
ticker.start(50)

QTimer.singleShot(800, click_update_button)
QTimer.singleShot(8000, app.quit)  # hard timeout 8s
sys.exit(app.exec())
