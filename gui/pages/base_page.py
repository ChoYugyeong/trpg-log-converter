"""
TRPG Log Converter Pro - 기본 페이지 클래스
QFluentWidgets 기반
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import ScrollArea, SubtitleLabel, TitleLabel

from ..theme import Colors, Sizes


class BasePage(ScrollArea):
    """모든 페이지의 기본 클래스 - Fluent Design

    서브클래스는 설정 읽기/쓰기 시 self.app_state를 사용할 수 있다.
    app_state가 없으면 self.settings (flat dict) 폴백.
    """
    settings_changed = Signal()

    # MainWindow에서 주입하는 공유 AppState (클래스 변수)
    _shared_app_state = None

    @classmethod
    def set_app_state(cls, app_state):
        """MainWindow에서 호출하여 모든 페이지가 공유하는 AppState를 설정"""
        cls._shared_app_state = app_state

    @property
    def app_state(self):
        """반응형 상태 관리자 접근 (없으면 None)"""
        return self._shared_app_state

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.inspector = inspector
        self.settings = config_manager.get_gui_settings() if config_manager else {}

        # 스크롤 영역 설정
        self.setWidgetResizable(True)
        self.setObjectName(self.__class__.__name__)

        # 메인 위젯
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName('scrollWidget')
        self.setWidget(self.scroll_widget)

        # 메인 레이아웃 - 반응형 마진
        self.main_layout = QVBoxLayout(self.scroll_widget)
        self.main_layout.setContentsMargins(
            Sizes.PAGE_MARGIN_H, Sizes.PAGE_MARGIN_V_TOP,
            Sizes.PAGE_MARGIN_H, Sizes.PAGE_MARGIN_V_BOTTOM,
        )
        self.main_layout.setSpacing(Sizes.PAGE_SPACING)
        self.main_layout.setAlignment(Qt.AlignTop)

        # 콘텐츠 레이아웃 (서브클래스에서 사용)
        self.content_layout = self.main_layout

    def add_header(self, title: str, subtitle: str | None = None):
        """페이지 헤더 추가"""
        title_label = TitleLabel(title)
        title_label.setMinimumHeight(Sizes.HEADER_TITLE_H)
        self.main_layout.addWidget(title_label)

        if subtitle:
            subtitle_label = SubtitleLabel(subtitle)
            subtitle_label.setTextColor(Colors.TEXT_MUTED_LIGHT, Colors.TEXT_MUTED_DARK)
            subtitle_label.setMinimumHeight(Sizes.HEADER_SUBTITLE_H)
            subtitle_label.setWordWrap(True)
            self.main_layout.addWidget(subtitle_label)

        self.main_layout.addSpacing(Sizes.HEADER_BOTTOM_SPACE)

    def add_section_title(self, title: str):
        """섹션 제목 추가"""
        from qfluentwidgets import StrongBodyLabel
        label = StrongBodyLabel(title)
        self.content_layout.addWidget(label)

    def add_stretch(self):
        """스트레치 추가"""
        self.content_layout.addStretch()

    def update_inspector(self, **kwargs):
        """인스펙터 바 업데이트"""
        if self.inspector and hasattr(self.inspector, 'update_preview'):
            self.inspector.update_preview(**kwargs)

    def on_page_enter(self):
        """페이지 진입 시 호출"""

    def on_page_leave(self):
        """페이지 이탈 시 호출"""
        self.save_settings()

    def save_settings(self):
        """설정 저장 (서브클래스에서 오버라이드)"""

    def load_settings(self):
        """설정 로드 (서브클래스에서 오버라이드)"""

    @staticmethod
    def safe_set_combo(combo, text: str):
        """콤보박스에 안전하게 값 설정 (존재하지 않는 값이면 첫 항목 유지)"""
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)
