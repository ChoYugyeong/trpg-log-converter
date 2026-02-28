"""
TRPG Log Converter Pro - 엔터프라이즈급 파일 리스트 컴포넌트
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QListWidget, QListWidgetItem, QMenu, QAbstractItemView,
    QStyledItemDelegate, QStyle, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen, QBrush,
    QLinearGradient, QPainterPath, QAction, QCursor
)
from pathlib import Path
import os


class FileItemDelegate(QStyledItemDelegate):
    """현대적인 파일 아이템 커스텀 렌더러"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_row = -1

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect.adjusted(4, 2, -4, -2)
        is_selected = option.state & QStyle.State_Selected
        is_hover = option.state & QStyle.State_MouseOver

        # 배경
        if is_selected:
            bg_color = QColor("#007AFF")
            bg_color.setAlpha(200)
        elif is_hover:
            bg_color = QColor("#007AFF")
            bg_color.setAlpha(30)
        else:
            bg_color = QColor(128, 128, 128, 15)

        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 10, 10)
        painter.fillPath(path, bg_color)

        # 데이터 가져오기
        file_path = index.data(Qt.UserRole)
        file_name = index.data(Qt.DisplayRole) or ""
        status = index.data(Qt.UserRole + 1) or "ready"  # ready, parsing, error
        file_size = index.data(Qt.UserRole + 2) or ""

        # 왼쪽 아이콘 영역
        icon_rect = QRect(rect.x() + 12, rect.y() + 10, 36, 36)
        self._draw_file_icon(painter, icon_rect, file_path, status, is_selected)

        # 텍스트 영역
        text_x = icon_rect.right() + 12
        text_color = QColor("white") if is_selected else QColor(Qt.black if not self._is_dark_mode() else Qt.white)

        # 파일명
        painter.setPen(text_color)
        name_font = QFont()
        name_font.setPointSize(13)
        name_font.setWeight(QFont.Medium)
        painter.setFont(name_font)

        name_rect = QRect(text_x, rect.y() + 8, rect.width() - text_x - 80, 22)
        fm = QFontMetrics(name_font)
        elided_name = fm.elidedText(file_name, Qt.ElideMiddle, name_rect.width())
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_name)

        # 파일 경로 (서브텍스트)
        if file_path:
            sub_color = QColor(180, 180, 180) if is_selected else QColor(128, 128, 128)
            painter.setPen(sub_color)
            sub_font = QFont()
            sub_font.setPointSize(11)
            painter.setFont(sub_font)

            dir_path = str(Path(file_path).parent)
            sub_rect = QRect(text_x, rect.y() + 30, rect.width() - text_x - 80, 18)
            fm_sub = QFontMetrics(sub_font)
            elided_path = fm_sub.elidedText(dir_path, Qt.ElideMiddle, sub_rect.width())
            painter.drawText(sub_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_path)

        # 오른쪽 상태/크기 영역
        right_x = rect.right() - 70

        # 파일 크기
        if file_size:
            size_color = QColor(180, 180, 180) if is_selected else QColor(128, 128, 128)
            painter.setPen(size_color)
            size_font = QFont()
            size_font.setPointSize(11)
            painter.setFont(size_font)
            size_rect = QRect(right_x, rect.y() + 8, 60, 18)
            painter.drawText(size_rect, Qt.AlignRight | Qt.AlignVCenter, file_size)

        # 상태 배지
        badge_rect = QRect(right_x + 10, rect.y() + 30, 50, 18)
        self._draw_status_badge(painter, badge_rect, status, is_selected)

        painter.restore()

    def _draw_file_icon(self, painter, rect, file_path, status, is_selected):
        """파일 아이콘 그리기"""
        # 아이콘 배경
        if status == "error":
            icon_bg = QColor("#FF3B30")
        elif status == "parsing":
            icon_bg = QColor("#FF9500")
        else:
            icon_bg = QColor("#007AFF") if is_selected else QColor("#E8E8E8")

        icon_bg.setAlpha(230 if is_selected or status != "ready" else 180)

        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 8, 8)
        painter.fillPath(path, icon_bg)

        # 파일 확장자 또는 아이콘
        ext = Path(file_path).suffix.lower() if file_path else ""
        icon_text = ext[1:3].upper() if ext else "FL"

        if ext in ['.html', '.htm']:
            icon_text = "HT"
        elif ext == '.txt':
            icon_text = "TX"

        painter.setPen(QColor("white") if (is_selected or status != "ready") else QColor("#666"))
        icon_font = QFont()
        icon_font.setPointSize(14 if len(icon_text) <= 2 else 16)
        painter.setFont(icon_font)
        painter.drawText(rect, Qt.AlignCenter, icon_text)

    def _draw_status_badge(self, painter, rect, status, is_selected):
        """상태 배지 그리기"""
        if status == "ready":
            return

        if status == "parsing":
            badge_color = QColor("#FF9500")
            badge_text = "처리중"
        elif status == "error":
            badge_color = QColor("#FF3B30")
            badge_text = "오류"
        else:
            return

        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 9, 9)
        painter.fillPath(path, badge_color)

        painter.setPen(QColor("white"))
        badge_font = QFont()
        badge_font.setPointSize(9)
        badge_font.setWeight(QFont.Medium)
        painter.setFont(badge_font)
        painter.drawText(rect, Qt.AlignCenter, badge_text)

    def _is_dark_mode(self):
        """다크 모드 여부 확인"""
        palette = QApplication.palette()
        return palette.color(palette.ColorRole.Window).lightness() < 128

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 60)


class EnterpriseFileList(QFrame):
    """엔터프라이즈급 파일 리스트"""

    files_changed = Signal(list)
    file_selected = Signal(str)
    file_removed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EnterpriseFileList")
        self._files = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 헤더
        header = QFrame()
        header.setObjectName("FileListHeader")
        header.setStyleSheet("""
            #FileListHeader {
                background: rgba(128, 128, 128, 0.05);
                border-bottom: 1px solid rgba(128, 128, 128, 0.1);
                padding: 8px 12px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        self.count_label = QLabel("0개 파일")
        self.count_label.setStyleSheet("font-size: 12px; color: palette(mid); font-weight: 500;")
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        self.size_label = QLabel("")
        self.size_label.setStyleSheet("font-size: 12px; color: palette(mid);")
        header_layout.addWidget(self.size_label)

        layout.addWidget(header)

        # 파일 리스트
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("EnterpriseFileListWidget")
        self.list_widget.setItemDelegate(FileItemDelegate(self))
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)

        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 0;
                margin: 2px 4px;
                border: none;
                background: transparent;
            }
        """)

        layout.addWidget(self.list_widget)

        # 빈 상태 표시
        self.empty_widget = self._create_empty_state()
        layout.addWidget(self.empty_widget)

        self._update_empty_state()

    def _create_empty_state(self) -> QWidget:
        """빈 상태 위젯 생성"""
        widget = QFrame()
        widget.setObjectName("EmptyState")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(16)

        icon = QLabel("+")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 36px; font-weight: 300; color: #22C55E;")
        layout.addWidget(icon)

        title = QLabel("파일을 추가하세요")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: palette(text);")
        layout.addWidget(title)

        desc = QLabel("드래그 앤 드롭하거나\n상단의 버튼으로 파일을 추가할 수 있습니다")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: palette(mid); line-height: 1.5;")
        layout.addWidget(desc)

        return widget

    def _update_empty_state(self):
        """빈 상태 표시 업데이트"""
        has_files = len(self._files) > 0
        self.list_widget.setVisible(has_files)
        self.empty_widget.setVisible(not has_files)

        # 파일 수 업데이트
        self.count_label.setText(f"{len(self._files)}개 파일")

        # 총 크기 계산
        total_size = sum(os.path.getsize(f) for f in self._files if os.path.exists(f))
        self.size_label.setText(self._format_size(total_size))

    def _format_size(self, size: int) -> str:
        """파일 크기 포맷"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def add_files(self, files: list):
        """파일 추가"""
        for file_path in files:
            if file_path not in self._files and os.path.exists(file_path):
                self._files.append(file_path)

                item = QListWidgetItem()
                item.setData(Qt.DisplayRole, Path(file_path).name)
                item.setData(Qt.UserRole, file_path)
                item.setData(Qt.UserRole + 1, "ready")  # status
                item.setData(Qt.UserRole + 2, self._format_size(os.path.getsize(file_path)))
                item.setSizeHint(QSize(0, 60))

                self.list_widget.addItem(item)

        self._update_empty_state()
        self.files_changed.emit(self._files.copy())

    def remove_selected(self):
        """선택된 파일 제거"""
        for item in self.list_widget.selectedItems():
            file_path = item.data(Qt.UserRole)
            if file_path in self._files:
                self._files.remove(file_path)
                self.file_removed.emit(file_path)
            self.list_widget.takeItem(self.list_widget.row(item))

        self._update_empty_state()
        self.files_changed.emit(self._files.copy())

    def clear_files(self):
        """모든 파일 제거"""
        self._files.clear()
        self.list_widget.clear()
        self._update_empty_state()
        self.files_changed.emit([])

    def get_files(self) -> list:
        """현재 순서대로 파일 목록 반환"""
        files = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(Qt.UserRole)
            if path:
                files.append(path)
        return files

    def set_file_status(self, file_path: str, status: str):
        """파일 상태 설정 (ready, parsing, error)"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == file_path:
                item.setData(Qt.UserRole + 1, status)
                self.list_widget.update()
                break

    def _show_context_menu(self, pos):
        """컨텍스트 메뉴 표시"""
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: palette(base);
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #007AFF;
                color: white;
            }
        """)

        # 메뉴 항목
        open_action = QAction("폴더에서 보기", self)
        open_action.triggered.connect(lambda: self._open_in_folder(item.data(Qt.UserRole)))
        menu.addAction(open_action)

        menu.addSeparator()

        move_up = QAction("위로 이동", self)
        move_up.triggered.connect(lambda: self._move_item(item, -1))
        menu.addAction(move_up)

        move_down = QAction("아래로 이동", self)
        move_down.triggered.connect(lambda: self._move_item(item, 1))
        menu.addAction(move_down)

        menu.addSeparator()

        remove_action = QAction("제거", self)
        remove_action.triggered.connect(self.remove_selected)
        menu.addAction(remove_action)

        menu.exec(self.list_widget.mapToGlobal(pos))

    def _open_in_folder(self, file_path: str):
        """폴더에서 파일 열기"""
        import subprocess
        import sys

        if sys.platform == 'darwin':
            subprocess.run(['open', '-R', file_path])
        elif sys.platform == 'win32':
            subprocess.run(['explorer', '/select,', file_path])
        else:
            subprocess.run(['xdg-open', str(Path(file_path).parent)])

    def _move_item(self, item, direction):
        """아이템 이동"""
        row = self.list_widget.row(item)
        new_row = row + direction

        if 0 <= new_row < self.list_widget.count():
            taken = self.list_widget.takeItem(row)
            self.list_widget.insertItem(new_row, taken)
            self.list_widget.setCurrentItem(taken)
            self._sync_files_order()

    def _on_selection_changed(self):
        """선택 변경 시"""
        items = self.list_widget.selectedItems()
        if items:
            self.file_selected.emit(items[0].data(Qt.UserRole))

    def _on_rows_moved(self):
        """드래그로 순서 변경 시"""
        self._sync_files_order()

    def _sync_files_order(self):
        """내부 파일 순서 동기화"""
        self._files = self.get_files()
        self.files_changed.emit(self._files.copy())
