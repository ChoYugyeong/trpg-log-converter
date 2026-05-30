"""Probe: how does PySide6 dispatch Signal(bool).emit(True) to a slot with
keyword-only `silent`? This determines whether the nav button click silently
fails (TypeError swallowed by Qt) or somehow succeeds."""
from __future__ import annotations
import sys, traceback
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from PySide6.QtCore import QObject, Signal, QCoreApplication


class Emitter(QObject):
    sig = Signal(bool)


class Receiver(QObject):
    called = 0
    last_silent = None
    def slot(self, *, silent: bool = False):
        Receiver.called += 1
        Receiver.last_silent = silent
        print(f"  slot called: silent={silent}")


app = QCoreApplication([])
e, r = Emitter(), Receiver()
e.sig.connect(r.slot)

print("[1] emit(True) on Signal(bool) → kw-only slot")
try:
    e.sig.emit(True)
except Exception:
    print("  EXCEPTION raised by emit():")
    traceback.print_exc()
print(f"  Receiver.called = {Receiver.called}")
print(f"  Receiver.last_silent = {Receiver.last_silent}")

# Direct call for comparison.
print("\n[2] direct call r.slot(True) — pure Python control")
try:
    r.slot(True)
except TypeError as exc:
    print(f"  TypeError: {exc}")
