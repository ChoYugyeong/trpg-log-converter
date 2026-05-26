"""Screenshot the HistoryDialog with a few sample records."""
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

from gui.dialogs import HistoryDialog
from gui.styles.theme import Theme
from core.services.history import HistoryManager

app.setStyleSheet(Theme.get_stylesheet())

# 임시 dir 에 sample records 넣기.
import tempfile
tmp = Path(tempfile.mkdtemp())
hm = HistoryManager(tmp)

samples = [
    dict(input_file="C:/logs/embargo_area_1부.html",
         output_files=["C:/export/Embargo_Area_1.epub", "C:/export/Embargo_Area_1.docx"],
         output_format="both", title="Embargo Area · 1부",
         author="GM", entry_count=487, scene_count=12, success=True, duration_ms=8500),
    dict(input_file="C:/logs/embargo_area_2부.html",
         output_files=["C:/export/Embargo_Area_2.epub"],
         output_format="epub", title="Embargo Area · 2부",
         author="GM", entry_count=512, scene_count=9, success=True, duration_ms=6200),
    dict(input_file="C:/logs/dx3_session_5.html",
         output_files=["C:/export/dx3_5.pdf"],
         output_format="pdf", title="DX3 캠페인 #5",
         author="KP", entry_count=320, scene_count=7, success=True, duration_ms=4100),
    dict(input_file="C:/logs/broken_log.html",
         output_files=[], output_format="both", title="(실패)",
         author="GM", entry_count=0, scene_count=0, success=False,
         error_message="HTML 파싱 실패", duration_ms=200),
    dict(input_file="C:/logs/test.txt",
         output_files=["C:/export/test.epub", "C:/export/test.docx", "C:/export/test.pdf"],
         output_format="all", title="테스트 변환",
         author="GM", entry_count=15, scene_count=2, success=True, duration_ms=900),
]
for s in samples:
    hm.add_record(**s)

dlg = HistoryDialog(hm)
dlg.show()


def grab():
    pm = dlg.grab()
    out = ROOT / "resources" / "screenshots" / "history.png"
    pm.save(str(out))
    print(f"saved: {out} {pm.size().width()}x{pm.size().height()}")
    app.quit()


QTimer.singleShot(800, grab)
sys.exit(app.exec())
