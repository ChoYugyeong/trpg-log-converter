"""End-to-end repro: drive _check_for_updates(silent=False) the same way
the navigation button does, but bypass the nav widget so we don't fight
qfluentwidgets / standalone QApplication quirks. Writes to ``repro_button_click.log``.

The silent=False path is what the user reports freezing; this script proves
the worker → result handler pipeline returns within a reasonable budget.
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG_FILE = ROOT / "repro_button_click.log"
LOG_FILE.write_text("", encoding="utf-8")


def log(msg: str) -> None:
    print(msg, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
        f.flush()


from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def pump(app: QApplication, ms: int) -> None:
    """Pump the real event loop for ``ms`` milliseconds — equivalent to what
    a running app would do. Plain processEvents() + sleep() loses cross-thread
    queued events that need the real loop to drain."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    log("[setup] importing MainWindow…")
    from gui.main_window import MainWindow
    from core.config_manager import ConfigManager
    from core.services.updater import UpdateService

    log("[setup] constructing MainWindow…")
    config_manager = ConfigManager(ROOT)
    w = MainWindow(config_manager)
    w.show()
    pump(app, 500)
    log("[setup] window shown\n")

    # --- COLD: explicit click semantics (silent=False), no cache
    UpdateService.clear_cache()
    log("[COLD] _check_for_updates(silent=False) — cache cleared")
    t0 = time.monotonic()
    w._check_for_updates(silent=False)
    return_ms = (time.monotonic() - t0) * 1000
    log(f"  call returned in {return_ms:.1f}ms (this is the UI block)")
    if return_ms > 200:
        log(f"  FAIL: UI thread blocked {return_ms:.0f}ms > 200ms")
        return 4

    # Pump real Qt event loop, polling for thread cleanup.
    result_ms = None
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        pump(app, 100)
        if getattr(w, "_update_check_thread", None) is None:
            result_ms = (time.monotonic() - t0) * 1000
            log(f"  result delivered at +{result_ms:.0f}ms")
            break
    if result_ms is None:
        log("  FAIL: thread never cleaned up within 5s — TRUE FREEZE")
        return 3

    # --- WARM: cache hit
    log("\n[WARM] second call — cache hit expected")
    t0 = time.monotonic()
    w._check_for_updates(silent=False)
    return_ms2 = (time.monotonic() - t0) * 1000
    log(f"  call returned in {return_ms2:.1f}ms")

    result_ms2 = None
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        pump(app, 50)
        if getattr(w, "_update_check_thread", None) is None:
            result_ms2 = (time.monotonic() - t0) * 1000
            log(f"  result delivered at +{result_ms2:.0f}ms")
            break
    if result_ms2 is None:
        log("  FAIL: warm path never cleaned up — cache miss bug")
        return 5

    # --- POSITIONAL: the nav button emits clicked(bool) — verify slot accepts it
    log("\n[POSITIONAL] _check_for_updates(True) — mirrors Signal(bool).emit(True)")
    UpdateService.clear_cache()
    t0 = time.monotonic()
    try:
        w._check_for_updates(True)
        log(f"  positional True accepted ({(time.monotonic()-t0)*1000:.1f}ms)")
    except TypeError as exc:
        log(f"  FAIL: TypeError on positional bool — fix regressed: {exc}")
        return 6
    # Drain.
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        pump(app, 100)
        if getattr(w, "_update_check_thread", None) is None:
            break

    log("\n[VERDICT] PASS — no freeze, signature accepts both shapes, results delivered")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        log("EXCEPTION:")
        log(traceback.format_exc())
        code = 99
    log(f"\n[exit] code={code}")
    sys.exit(code)
