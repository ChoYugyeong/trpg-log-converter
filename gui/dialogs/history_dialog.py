"""Conversion history dialog.

Surface for ``core.services.history.HistoryManager`` — lets the user:
  - browse past conversions in a sortable table
  - search by filename / title / author
  - open the output folder of any past conversion in the file explorer
  - delete individual rows or clear all
  - see summary stats (total / success / failure / formats)

UI/UX Pro Max:
  - §10 sortable-table     : column headers sort the table
  - §10 contrast-data      : success/failure rows visually distinct
  - §8 empty-states        : helpful placeholder when no records
  - §5 visual-hierarchy    : search → table → stats → actions
"""
from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.services.history import ConversionRecord, HistoryManager

# Columns shown in the table (header label, attribute, width)
_COLUMNS = [
    ("일시",      "_display_time",     150),
    ("입력 파일",   "input_filename",    220),
    ("제목",       "title",             180),
    ("형식",       "output_format",     80),
    ("항목 수",    "entry_count",       70),
    ("장면",       "scene_count",       60),
    ("상태",       "_status_text",      70),
]


class HistoryDialog(QDialog):
    """변환 이력 다이얼로그."""

    def __init__(self, history_manager: HistoryManager, parent=None) -> None:
        super().__init__(parent)
        self._history = history_manager
        self._records: list[ConversionRecord] = []

        self.setWindowTitle("변환 이력")
        self.setMinimumSize(880, 540)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self._build_header(layout)
        self._build_table(layout)
        self._build_stats(layout)
        self._build_actions(layout)

        self.refresh()

    # ── Layout pieces ────────────────────────────────────────

    def _build_header(self, parent_layout: QVBoxLayout) -> None:
        title = QLabel("변환 이력")
        title.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: palette(text); "
            "letter-spacing: -0.4px;"
        )
        parent_layout.addWidget(title)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        search_label = QLabel("검색")
        search_label.setStyleSheet("color: palette(mid); font-size: 12px;")
        search_row.addWidget(search_label)

        self._search = QLineEdit()
        self._search.setPlaceholderText("파일명·제목·저자로 검색...")
        self._search.textChanged.connect(self._on_search_changed)
        self._search.setMinimumHeight(30)
        search_row.addWidget(self._search, 1)
        parent_layout.addLayout(search_row)

    def _build_table(self, parent_layout: QVBoxLayout) -> None:
        self._table = QTableWidget()
        self._table.setObjectName("HistoryTable")
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels([c[0] for c in _COLUMNS])
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.doubleClicked.connect(self._on_row_double_clicked)

        header = self._table.horizontalHeader()
        for i, (_, _, width) in enumerate(_COLUMNS):
            self._table.setColumnWidth(i, width)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 입력 파일 칸이 늘어남

        # Empty-state placeholder — viewport overlay (mirrors home_page pattern).
        self._empty_state = QLabel(
            "아직 변환한 기록이 없어요\n파일을 변환하면 자동으로 여기에 기록됩니다."
        )
        self._empty_state.setAlignment(Qt.AlignCenter)
        self._empty_state.setStyleSheet(
            "color: palette(mid); font-size: 12px; line-height: 1.6; "
            "background: transparent;"
        )
        self._empty_state.setParent(self._table.viewport())
        self._empty_state.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._table.viewport().installEventFilter(self)

        parent_layout.addWidget(self._table, 1)

    def _build_stats(self, parent_layout: QVBoxLayout) -> None:
        self._stats = QLabel("")
        self._stats.setStyleSheet(
            "color: palette(mid); font-size: 11px; padding: 4px 2px;"
        )
        parent_layout.addWidget(self._stats)

    def _build_actions(self, parent_layout: QVBoxLayout) -> None:
        actions = QHBoxLayout()
        actions.setSpacing(8)

        clear_all_btn = QPushButton("모두 지우기")
        clear_all_btn.setProperty("class", "destructive-secondary")
        clear_all_btn.clicked.connect(self._on_clear_all)
        actions.addWidget(clear_all_btn)

        actions.addStretch()

        close_btn = QPushButton("닫기")
        close_btn.setDefault(True)
        close_btn.setMinimumWidth(80)
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)
        parent_layout.addLayout(actions)

    # ── Data → table ────────────────────────────────────────

    def refresh(self) -> None:
        """Reload all records from the manager and repopulate the table."""
        self._records = self._history.get_records()
        self._apply_filter(self._search.text())

    def _apply_filter(self, query: str) -> None:
        if query.strip():
            filtered = self._history.search(query)
        else:
            filtered = self._records

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(filtered))
        for row, record in enumerate(filtered):
            self._populate_row(row, record)
        self._table.setSortingEnabled(True)

        self._refresh_empty_state(empty=len(filtered) == 0)
        self._refresh_stats()

    def _populate_row(self, row: int, record: ConversionRecord) -> None:
        for col, (_, attr, _) in enumerate(_COLUMNS):
            text = self._cell_text(record, attr)
            item = QTableWidgetItem(text)
            item.setData(Qt.UserRole, record.id)
            # 상태 셀은 색 강조
            if attr == "_status_text":
                if record.success:
                    item.setForeground(QColor("#0a7a2e"))
                else:
                    item.setForeground(QColor("#a02030"))
                    item.setToolTip(record.error_message or "")
            # 숫자 열은 우측 정렬
            if attr in ("entry_count", "scene_count"):
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, col, item)

    def _cell_text(self, record: ConversionRecord, attr: str) -> str:
        if attr == "_display_time":
            try:
                dt = datetime.fromisoformat(record.timestamp)
                return dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                return record.timestamp[:16]
        if attr == "_status_text":
            return "성공" if record.success else "실패"
        return str(getattr(record, attr, ""))

    def _refresh_stats(self) -> None:
        stats = self._history.get_stats()
        if stats["total_conversions"] == 0:
            self._stats.setText("")
            return
        formats = " · ".join(
            f"{fmt}({n})" for fmt, n in sorted(stats["formats_used"].items())
        )
        self._stats.setText(
            f"총 {stats['total_conversions']}건 · 성공 {stats['success_count']} · "
            f"실패 {stats['failure_count']} · "
            f"평균 항목 {stats['avg_entries']}  ·  포맷: {formats or '-'}"
        )

    # ── Event handlers ──────────────────────────────────────

    def _on_search_changed(self, query: str) -> None:
        self._apply_filter(query)

    def _on_row_double_clicked(self, index) -> None:
        record = self._record_for_row(index.row())
        if record is None:
            return
        # 출력 파일 중 첫 번째의 폴더를 OS 파일 탐색기로 열기.
        for out in record.output_files:
            p = Path(out)
            if p.exists():
                self._open_in_explorer(p)
                return
            if p.parent.exists():
                self._open_in_explorer(p.parent)
                return

    def _on_context_menu(self, pos) -> None:
        index = self._table.indexAt(pos)
        if not index.isValid():
            return
        record = self._record_for_row(index.row())
        if record is None:
            return

        menu = QMenu(self)
        open_act = QAction("출력 폴더 열기", self)
        open_act.triggered.connect(lambda: self._on_row_double_clicked(index))
        menu.addAction(open_act)

        copy_act = QAction("입력 경로 복사", self)
        copy_act.triggered.connect(lambda: self._copy_to_clipboard(record.input_file))
        menu.addAction(copy_act)

        menu.addSeparator()

        delete_act = QAction("이 기록 삭제", self)
        delete_act.triggered.connect(lambda: self._delete_record(record))
        menu.addAction(delete_act)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _on_clear_all(self) -> None:
        if not self._records:
            return
        reply = QMessageBox.question(
            self, "모든 이력 삭제",
            f"기록 {len(self._records)}건을 모두 삭제할까요?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._history.clear()
            self.refresh()

    def _delete_record(self, record: ConversionRecord) -> None:
        self._history.delete_record(record.id)
        self.refresh()

    # ── Helpers ─────────────────────────────────────────────

    def _record_for_row(self, row: int) -> ConversionRecord | None:
        item = self._table.item(row, 0)
        if item is None:
            return None
        record_id = item.data(Qt.UserRole)
        return self._history.get_record_by_id(record_id)

    def _open_in_explorer(self, path: Path) -> None:
        """크로스 플랫폼으로 파일/폴더 위치를 시스템 탐색기에서 열기."""
        path = Path(path).resolve()
        system = platform.system()
        try:
            if system == "Windows":
                if path.is_file():
                    subprocess.Popen(["explorer", "/select,", str(path)])
                else:
                    os.startfile(str(path))
            elif system == "Darwin":
                subprocess.Popen(["open", "-R" if path.is_file() else "", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path.parent if path.is_file() else path)])
        except Exception:
            pass

    def _copy_to_clipboard(self, text: str) -> None:
        from PySide6.QtWidgets import QApplication
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(text)

    def _refresh_empty_state(self, *, empty: bool) -> None:
        self._empty_state.setVisible(empty)
        if empty:
            self._empty_state.setGeometry(self._table.viewport().rect())

    def eventFilter(self, obj, event) -> bool:
        from PySide6.QtCore import QEvent
        if (
            obj is self._table.viewport()
            and event.type() == QEvent.Resize
            and self._empty_state.isVisible()
        ):
            self._empty_state.setGeometry(self._table.viewport().rect())
        return super().eventFilter(obj, event)
