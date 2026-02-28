"""
TRPG Log Converter Pro - 버튼 컴포넌트
macOS 스타일 액션 버튼
"""

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QWidget
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor


class ActionButton(QPushButton):
    """macOS 스타일 액션 버튼"""

    def __init__(self, text: str, style: str = "default", parent=None):
        """
        Args:
            text: 버튼 텍스트
            style: "default", "primary", "danger", "success"
        """
        super().__init__(text, parent)
        self._style = style

        self.setMinimumHeight(40)
        self.setMinimumWidth(100)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        if style != "default":
            self.setObjectName(style)

    def set_loading(self, loading: bool):
        """로딩 상태 설정"""
        if loading:
            self._original_text = self.text()
            self.setText("처리 중...")
            self.setEnabled(False)
        else:
            if hasattr(self, '_original_text'):
                self.setText(self._original_text)
            self.setEnabled(True)


class SidebarButton(QPushButton):
    """사이드바 네비게이션 버튼"""

    def __init__(self, text: str, icon: str = "", parent=None):
        """
        Args:
            text: 버튼 텍스트
            icon: 이모지 아이콘 (예: "⚡", "🎨")
        """
        display_text = f"  {icon}  {text}" if icon else f"  {text}"
        super().__init__(display_text, parent)

        self.setObjectName("SidebarButton")
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))


class ButtonGroup(QWidget):
    """버튼 그룹 (수평 배치)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = []

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.addStretch()

    def add_button(self, button: QPushButton, stretch: bool = False):
        """버튼 추가"""
        # stretch 앞에 삽입
        insert_pos = self._layout.count() - 1
        if stretch:
            self._layout.insertWidget(insert_pos, button, 1)
        else:
            self._layout.insertWidget(insert_pos, button)
        self._buttons.append(button)
        return button

    def add_spacer(self):
        """여백 추가"""
        self._layout.insertStretch(self._layout.count() - 1)

    def get_buttons(self) -> list:
        """모든 버튼 반환"""
        return self._buttons.copy()
