"""
TRPG Log Converter Pro - 엔터프라이즈급 액션 바
하단 고정 액션 버튼 및 상태 표시
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class ActionButton(QPushButton):
    """현대적인 액션 버튼"""

    def __init__(self, text: str, primary: bool = False, parent=None):
        super().__init__(text, parent)
        self._primary = primary
        self._loading = False
        self._original_text = text
        self._loading_dots = 0

        self.setMinimumHeight(48)
        self.setMinimumWidth(140)
        self.setCursor(Qt.PointingHandCursor)

        self._loading_timer = QTimer(self)
        self._loading_timer.timeout.connect(self._update_loading_animation)

        self._apply_style()

    def _apply_style(self):
        if self._primary:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0A84FF, stop:1 #0066CC);
                    border: none;
                    border-radius: 10px;
                    color: white;
                    font-size: 15px;
                    font-weight: 600;
                    padding: 12px 28px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3399FF, stop:1 #0077DD);
                }
                QPushButton:pressed {
                    background: #0055BB;
                }
                QPushButton:disabled {
                    background: rgba(128, 128, 128, 0.3);
                    color: rgba(255, 255, 255, 0.5);
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(128, 128, 128, 0.1);
                    border: 1px solid rgba(128, 128, 128, 0.2);
                    border-radius: 10px;
                    color: palette(text);
                    font-size: 14px;
                    font-weight: 500;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: rgba(128, 128, 128, 0.2);
                    border-color: rgba(128, 128, 128, 0.3);
                }
                QPushButton:pressed {
                    background: rgba(128, 128, 128, 0.25);
                }
                QPushButton:disabled {
                    color: rgba(128, 128, 128, 0.5);
                }
            """)

    def set_loading(self, loading: bool):
        """로딩 상태 설정"""
        self._loading = loading
        self.setEnabled(not loading)

        if loading:
            self._loading_timer.start(400)
        else:
            self._loading_timer.stop()
            self.setText(self._original_text)

    def _update_loading_animation(self):
        """로딩 애니메이션 업데이트"""
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        self.setText(f"처리 중{dots}")


class StatusIndicator(QFrame):
    """상태 표시기"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusIndicator")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # 상태 아이콘
        self.icon = QLabel("●")
        self.icon.setStyleSheet("font-size: 10px; color: palette(mid);")
        layout.addWidget(self.icon)

        # 상태 텍스트
        self.text = QLabel("준비")
        self.text.setStyleSheet("font-size: 12px; color: palette(mid);")
        layout.addWidget(self.text)

        self.setStyleSheet("""
            #StatusIndicator {
                background: rgba(128, 128, 128, 0.08);
                border-radius: 14px;
            }
        """)

    def set_status(self, status: str, icon_color: str = "#888"):
        """상태 설정"""
        self.text.setText(status)
        self.icon.setStyleSheet(f"font-size: 10px; color: {icon_color};")


class EnterpriseActionBar(QFrame):
    """엔터프라이즈급 액션 바"""

    action_clicked = Signal()
    secondary_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EnterpriseActionBar")
        self.setMinimumHeight(80)

        self._setup_ui()
        self._setup_shadow()

    def _setup_ui(self):
        self.setStyleSheet("""
            #EnterpriseActionBar {
                background: palette(base);
                border-top: 1px solid rgba(128, 128, 128, 0.15);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 왼쪽: 상태 표시
        left_section = QVBoxLayout()
        left_section.setSpacing(6)

        self.status_indicator = StatusIndicator()
        left_section.addWidget(self.status_indicator)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(128, 128, 128, 0.15);
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0A84FF, stop:1 #30D158);
                border-radius: 3px;
            }
        """)
        left_section.addWidget(self.progress_bar)

        self.progress_text = QLabel("")
        self.progress_text.setStyleSheet("font-size: 11px; color: palette(mid);")
        self.progress_text.setVisible(False)
        left_section.addWidget(self.progress_text)

        layout.addLayout(left_section, 1)

        # 오른쪽: 액션 버튼
        right_section = QHBoxLayout()
        right_section.setSpacing(12)

        self.secondary_buttons = {}

        # 보조 버튼들
        self.settings_btn = ActionButton("설정", primary=False)
        self.settings_btn.setMinimumWidth(80)
        self.settings_btn.clicked.connect(lambda: self.secondary_clicked.emit("settings"))
        right_section.addWidget(self.settings_btn)

        # 주요 액션 버튼
        self.action_btn = ActionButton("변환 시작", primary=True)
        self.action_btn.setMinimumWidth(160)
        self.action_btn.clicked.connect(self.action_clicked.emit)
        right_section.addWidget(self.action_btn)

        layout.addLayout(right_section)

    def _setup_shadow(self):
        """그림자 효과"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, -2)
        self.setGraphicsEffect(shadow)

    def set_status(self, status: str, icon_color: str = "#888"):
        """상태 설정"""
        self.status_indicator.set_status(status, icon_color)

    def set_ready(self, file_count: int = 0):
        """준비 상태로 설정"""
        if file_count > 0:
            self.set_status(f"{file_count}개 파일 준비됨", "#30D158")
            self.action_btn.setEnabled(True)
        else:
            self.set_status("파일을 추가하세요", "#888")
            self.action_btn.setEnabled(False)

        self.progress_bar.setVisible(False)
        self.progress_text.setVisible(False)
        self.action_btn.set_loading(False)
        self.action_btn.setText("변환 시작")

    def set_processing(self, progress: int = 0, message: str = ""):
        """처리 중 상태로 설정"""
        self.set_status("변환 중...", "#FF9500")
        self.action_btn.set_loading(True)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(progress)

        if message:
            self.progress_text.setVisible(True)
            self.progress_text.setText(message)

    def set_complete(self, success: bool = True, message: str = ""):
        """완료 상태로 설정"""
        if success:
            self.set_status("✓ 변환 완료", "#30D158")
        else:
            self.set_status("✗ 변환 실패", "#FF3B30")

        self.progress_bar.setVisible(False)
        self.action_btn.set_loading(False)
        self.action_btn.setText("변환 시작")

        if message:
            self.progress_text.setVisible(True)
            self.progress_text.setText(message)
        else:
            self.progress_text.setVisible(False)


class WorkflowSteps(QFrame):
    """워크플로우 단계 표시"""

    step_clicked = Signal(int)

    def __init__(self, steps: list, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkflowSteps")
        self._steps = steps
        self._current = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)

        self.step_widgets = []

        for i, step in enumerate(self._steps):
            # 단계 버튼
            btn = QPushButton(f"{i+1}. {step}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self.step_clicked.emit(idx))
            self.step_widgets.append(btn)
            layout.addWidget(btn)

            # 연결선 (마지막 제외)
            if i < len(self._steps) - 1:
                line = QLabel("→")
                line.setStyleSheet("color: palette(mid); font-size: 14px; padding: 0 8px;")
                layout.addWidget(line)

        self._update_style()

    def set_current(self, index: int):
        """현재 단계 설정"""
        self._current = index
        self._update_style()

    def _update_style(self):
        """스타일 업데이트"""
        for i, btn in enumerate(self.step_widgets):
            if i < self._current:
                # 완료됨
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(48, 209, 88, 0.1);
                        border: 1px solid rgba(48, 209, 88, 0.3);
                        border-radius: 16px;
                        color: #30D158;
                        font-size: 12px;
                        font-weight: 500;
                        padding: 6px 14px;
                    }
                """)
            elif i == self._current:
                # 현재
                btn.setStyleSheet("""
                    QPushButton {
                        background: #007AFF;
                        border: none;
                        border-radius: 16px;
                        color: white;
                        font-size: 12px;
                        font-weight: 600;
                        padding: 6px 14px;
                    }
                """)
            else:
                # 미완료
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(128, 128, 128, 0.1);
                        border: 1px solid rgba(128, 128, 128, 0.2);
                        border-radius: 16px;
                        color: palette(mid);
                        font-size: 12px;
                        font-weight: 500;
                        padding: 6px 14px;
                    }
                    QPushButton:hover {
                        background: rgba(128, 128, 128, 0.15);
                    }
                """)
