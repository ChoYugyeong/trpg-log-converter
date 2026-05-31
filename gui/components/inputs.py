"""
TRPG Log Converter Pro - 입력 컴포넌트
ColorPicker, TagInput, FileDropArea 등
"""

from typing import ClassVar

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..theme import Colors, Sizes, Spacing, Typography


class ColorPicker(QWidget):
    """macOS 스타일 컬러 피커"""

    color_changed = Signal(str)

    def __init__(self, initial_color: str | None = None, parent=None):
        super().__init__(parent)
        self._color = initial_color or Colors.ACCENT
        self.setFixedHeight(Sizes.BUTTON_LG_H)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # 색상 스와치
        self.swatch = QPushButton()
        self.swatch.setObjectName("ColorSwatch")
        self.swatch.setFixedSize(Sizes.COLOR_SWATCH, Sizes.COLOR_SWATCH)
        self.swatch.setCursor(Qt.PointingHandCursor)
        self.swatch.setToolTip("클릭하여 색상 선택")
        self.swatch.clicked.connect(self._open_picker)
        self._update_swatch()
        layout.addWidget(self.swatch)

        # Hex 입력
        self.hex_input = QLineEdit(self._color)
        self.hex_input.setMinimumWidth(Sizes.COLOR_HEX_MIN_W)
        self.hex_input.setMaximumWidth(Sizes.COLOR_HEX_MAX_W)
        self.hex_input.setFixedHeight(Sizes.COLOR_SWATCH)
        self.hex_input.setPlaceholderText("#RRGGBB")
        self.hex_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid rgba(128, 128, 128, 0.3);
                border-radius: 6px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                font-family: {Typography.FONT_MONO};
                font-size: {Typography.SIZE_SM}px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.ACCENT};
            }}
        """)
        self.hex_input.textChanged.connect(self._on_hex_change)
        layout.addWidget(self.hex_input)

        layout.addStretch()

    def _open_picker(self):
        """시스템 컬러 피커 열기"""
        color = QColorDialog.getColor(
            QColor(self._color), self, "색상 선택", QColorDialog.ShowAlphaChannel
        )
        if color.isValid():
            self.set_color(color.name())

    def _on_hex_change(self, text: str):
        """Hex 입력 변경 시"""
        if len(text) == 7 and text.startswith("#"):
            color = QColor(text)
            if color.isValid():
                self._color = text
                self._update_swatch()
                self.color_changed.emit(text)

    def set_color(self, color: str):
        """색상 설정"""
        self._color = color
        self.hex_input.blockSignals(True)
        self.hex_input.setText(color)
        self.hex_input.blockSignals(False)
        self._update_swatch()
        self.color_changed.emit(color)

    def get_color(self) -> str:
        """현재 색상 반환"""
        return self._color

    def _update_swatch(self):
        """스와치 색상 업데이트"""
        self.swatch.setStyleSheet(f"""
            QPushButton {{
                background: {self._color};
                border: 2px solid rgba(0, 0, 0, 0.12);
                border-radius: 6px;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                border: 2px solid {Colors.ACCENT};
            }}
            QPushButton:pressed {{
                border: 2px solid {Colors.ACCENT_PRESSED};
            }}
        """)


class TagInput(QWidget):
    """태그 입력 컴포넌트 (키워드 추가/삭제)"""

    tags_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        # 입력 영역
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.input = QLineEdit()
        self.input.setPlaceholderText("새 항목 입력...")
        self.input.setMinimumHeight(38)
        self.input.returnPressed.connect(self._add_tag)
        input_row.addWidget(self.input, 1)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(Sizes.BUTTON_LG_H, Sizes.BUTTON_LG_H)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {Typography.SIZE_XXL}px;
                font-weight: bold;
                background: {Colors.ACCENT_BG};
                border: 1px solid {Colors.BORDER_ACCENT};
                border-radius: 8px;
                color: {Colors.ACCENT};
            }}
            QPushButton:hover {{
                background: {Colors.ACCENT_BG_HOVER};
            }}
            QPushButton:pressed {{
                background: {Colors.ACCENT_BG_PRESSED};
            }}
        """)
        add_btn.clicked.connect(self._add_tag)
        input_row.addWidget(add_btn)

        layout.addLayout(input_row)

        # 태그 목록 영역
        self.tags_container = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 4, 0, 4)
        self.tags_layout.setSpacing(8)
        self.tags_layout.addStretch()

        layout.addWidget(self.tags_container)

    def _add_tag(self):
        """태그 추가"""
        text = self.input.text().strip()
        if text and text not in self._tags:
            self._tags.append(text)
            self.input.clear()
            self._refresh_tags()
            self.tags_changed.emit(self._tags.copy())

    def _remove_tag(self, tag: str):
        """태그 제거"""
        if tag in self._tags:
            self._tags.remove(tag)
            self._refresh_tags()
            self.tags_changed.emit(self._tags.copy())

    def _refresh_tags(self):
        """태그 UI 새로고침"""
        # 기존 태그 위젯 제거
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 태그 칩 생성
        for tag in self._tags:
            chip = self._create_chip(tag)
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, chip)

    def _create_chip(self, text: str) -> QFrame:
        """태그 칩 생성"""
        chip = QFrame()
        chip.setObjectName("TagChip")
        chip.setMinimumHeight(32)

        layout = QHBoxLayout(chip)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(6)

        label = QLabel(text)
        label.setMinimumHeight(20)
        label.setStyleSheet(f"font-size: {Typography.SIZE_MD}px;")
        layout.addWidget(label)

        delete_btn = QPushButton("×")
        delete_btn.setObjectName("TagChipDelete")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.ERROR_BG_SOFT};
                border: none;
                border-radius: 12px;
                font-size: {Typography.SIZE_LG}px;
                font-weight: bold;
                color: {Colors.ERROR};
            }}
            QPushButton:hover {{
                background: {Colors.ERROR_BG_HOVER};
            }}
            QPushButton:pressed {{
                background: {Colors.ERROR_BG_PRESSED};
            }}
        """)
        delete_btn.clicked.connect(lambda: self._remove_tag(text))
        layout.addWidget(delete_btn)

        return chip

    def set_tags(self, tags: list):
        """태그 목록 설정"""
        self._tags = list(tags)
        self._refresh_tags()

    def get_tags(self) -> list:
        """태그 목록 반환"""
        return self._tags.copy()

    def clear(self):
        """모든 태그 제거"""
        self._tags.clear()
        self._refresh_tags()
        self.tags_changed.emit([])


class FileDropArea(QFrame):
    """파일 드래그 앤 드롭 영역 - 유효성 검사 포함"""

    files_dropped = Signal(list)
    invalid_files_dropped = Signal(list)  # 잘못된 파일 드롭 시

    SUPPORTED_EXTENSIONS: ClassVar[dict] = {".html", ".htm", ".txt", ".log"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileDropArea")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(100)
        self.setMaximumHeight(140)
        self.setProperty("dragging", False)
        self.setProperty("invalid", False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(4)

        self.icon = QLabel("+")
        self.icon.setObjectName("DropIcon")
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setStyleSheet(
            f"font-size: 24px; font-weight: 300; color: {Colors.ACCENT}; padding: 0; margin: 0;"
        )
        layout.addWidget(self.icon)

        self.text = QLabel("파일을 드래그하거나 클릭하여 추가")
        self.text.setObjectName("HintLabel")
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setWordWrap(True)
        self.text.setStyleSheet(
            f"font-size: {Typography.SIZE_MD}px; color: {Colors.ACCENT}; font-weight: 500; padding: 0; margin: 0;"
        )
        layout.addWidget(self.text)

        self._files = []
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_feedback)

    def _is_valid_file(self, path: str) -> bool:
        """파일 확장자 유효성 검사"""
        import os

        _, ext = os.path.splitext(path.lower())
        return ext in self.SUPPORTED_EXTENSIONS

    def _update_style(self, dragging: bool):
        """드래그 상태에 따른 스타일 업데이트"""
        self.setProperty("dragging", dragging)
        self.style().unpolish(self)
        self.style().polish(self)

    def _show_invalid_feedback(self, rejected_names: list):
        """잘못된 파일 드롭 시 빨간 테두리 + 메시지"""
        self.setProperty("invalid", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setStyleSheet(f"""
            #FileDropArea[invalid="true"] {{
                background: {Colors.ERROR_BG};
                border: 2px solid {Colors.ERROR_BORDER};
                border-radius: 14px;
            }}
        """)
        names = ", ".join(rejected_names[:3])
        suffix = f" 외 {len(rejected_names) - 3}개" if len(rejected_names) > 3 else ""
        self.text.setText(f"지원하지 않는 파일: {names}{suffix}")
        self.text.setStyleSheet(
            f"font-size: {Typography.SIZE_SM}px; color: {Colors.ERROR}; font-weight: 500; padding: 0; margin: 0;"
        )
        self.icon.setStyleSheet(
            f"font-size: 24px; font-weight: 300; color: {Colors.ERROR}; padding: 0; margin: 0;"
        )
        self.icon.setText("!")
        # 2초 후 원래 상태로 복원
        self._reset_timer.start(2500)

    def _show_success_feedback(self, count: int):
        """성공적으로 파일 추가 시 시각 피드백"""
        self.text.setText(f"{count}개 파일 추가됨")
        self.text.setStyleSheet(
            f"font-size: {Typography.SIZE_MD}px; color: {Colors.SUCCESS}; font-weight: 600; padding: 0; margin: 0;"
        )
        self.icon.setStyleSheet(
            f"font-size: 24px; font-weight: 300; color: {Colors.SUCCESS}; padding: 0; margin: 0;"
        )
        self.icon.setText("✓")
        self._reset_timer.start(2000)

    def _reset_feedback(self):
        """원래 상태로 복원"""
        self.setProperty("invalid", False)
        self.setStyleSheet("")  # 인라인 스타일 제거 → qss가 적용됨
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon.setText("+")
        self.icon.setStyleSheet(
            f"font-size: 24px; font-weight: 300; color: {Colors.ACCENT}; padding: 0; margin: 0;"
        )
        self.text.setText("파일을 드래그하거나 클릭하여 추가")
        self.text.setStyleSheet(
            f"font-size: {Typography.SIZE_MD}px; color: {Colors.ACCENT}; font-weight: 500; padding: 0; margin: 0;"
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # 드래그 중 파일 유효성 미리 표시
            has_valid = any(
                self._is_valid_file(url.toLocalFile())
                for url in event.mimeData().urls()
                if url.toLocalFile()
            )
            if has_valid:
                event.acceptProposedAction()
                self._update_style(True)
            else:
                event.acceptProposedAction()
                self.setStyleSheet(f"""
                    #FileDropArea {{
                        background: {Colors.ERROR_BG};
                        border: 2px dashed {Colors.ERROR_BORDER};
                        border-radius: 14px;
                    }}
                """)

    def dragLeaveEvent(self, event):
        self._update_style(False)
        self.setStyleSheet("")  # 인라인 제거

    def dropEvent(self, event: QDropEvent):
        import os

        valid_files = []
        invalid_names = []

        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path:
                continue
            if self._is_valid_file(path) and path not in self._files:
                valid_files.append(path)
            elif not self._is_valid_file(path):
                invalid_names.append(os.path.basename(path))

        if valid_files:
            self._files.extend(valid_files)
            self.files_dropped.emit(valid_files)
            self._show_success_feedback(len(valid_files))

        if invalid_names and not valid_files:
            self._show_invalid_feedback(invalid_names)
            self.invalid_files_dropped.emit(invalid_names)
        elif invalid_names:
            # 일부만 유효한 경우 - 성공 피드백 후 경고
            self._reset_timer.stop()
            self.text.setText(f"{len(valid_files)}개 추가 / {len(invalid_names)}개 지원 안 됨")
            self.text.setStyleSheet(
                f"font-size: {Typography.SIZE_MD}px; color: {Colors.WARNING}; font-weight: 500;"
            )
            self._reset_timer.start(3000)

        self._update_style(False)

    def mousePressEvent(self, event):
        """클릭 시 파일 대화상자"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "파일 선택",
            "",
            "지원 파일 (*.html *.htm *.txt *.log);;HTML (*.html *.htm);;텍스트 (*.txt *.log);;모든 파일 (*.*)",
        )
        new_files = [f for f in files if f not in self._files]
        if new_files:
            self._files.extend(new_files)
            self.files_dropped.emit(new_files)

    def get_files(self) -> list:
        return self._files.copy()

    def clear_files(self):
        self._files.clear()
