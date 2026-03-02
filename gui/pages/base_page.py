"""
TRPG Log Converter Pro - 기본 페이지 클래스
QFluentWidgets 기반
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Signal, Qt

from qfluentwidgets import (
    ScrollArea, TitleLabel, SubtitleLabel, BodyLabel,
    CardWidget, LineEdit, ComboBox, CheckBox, RadioButton,
    PushButton, PrimaryPushButton, Slider, ProgressBar
)


class BasePage(ScrollArea):
    """모든 페이지의 기본 클래스 - Fluent Design"""
    settings_changed = Signal()

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
        self.main_layout.setContentsMargins(24, 20, 24, 24)  # 마진 축소
        self.main_layout.setSpacing(12)  # 간격 축소
        self.main_layout.setAlignment(Qt.AlignTop)

        # 콘텐츠 레이아웃 (서브클래스에서 사용)
        self.content_layout = self.main_layout

    def add_header(self, title: str, subtitle: str = None):
        """페이지 헤더 추가"""
        title_label = TitleLabel(title)
        title_label.setMinimumHeight(36)
        self.main_layout.addWidget(title_label)

        if subtitle:
            subtitle_label = SubtitleLabel(subtitle)
            subtitle_label.setTextColor("#6e6e73", "#98989d")
            subtitle_label.setMinimumHeight(28)
            subtitle_label.setWordWrap(True)
            self.main_layout.addWidget(subtitle_label)

        self.main_layout.addSpacing(8)

    def add_section_title(self, title: str):
        """섹션 제목 추가"""
        label = BodyLabel(title)
        label.setStyleSheet("font-weight: 600; color: palette(dark);")
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
        pass

    def on_page_leave(self):
        """페이지 이탈 시 호출"""
        self.save_settings()

    def save_settings(self):
        """설정 저장 (서브클래스에서 오버라이드)"""
        pass

    def load_settings(self):
        """설정 로드 (서브클래스에서 오버라이드)"""
        pass


class FluentCard(CardWidget):
    """Fluent 스타일 설정 카드"""

    def __init__(self, title: str = None, subtitle: str = None, parent=None):
        super().__init__(parent)
        self._fields = {}

        # 메인 레이아웃 - 컴팩트한 마진
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 16)  # 마진 축소
        self._layout.setSpacing(6)  # 간격 축소

        # 헤더
        if title:
            header = BodyLabel(title)
            header.setMinimumHeight(26)
            header.setStyleSheet("font-size: 16px; font-weight: 600; padding: 2px 0;")
            self._layout.addWidget(header)

        if subtitle:
            sub = BodyLabel(subtitle)
            sub.setMinimumHeight(22)
            sub.setWordWrap(True)
            sub.setStyleSheet("font-size: 13px; color: palette(mid); padding: 2px 0;")
            self._layout.addWidget(sub)

        # 콘텐츠 영역
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(10)
        self._content_layout.setContentsMargins(0, 8, 0, 0)
        self._layout.addLayout(self._content_layout)

    def add_field(self, label: str, widget: QWidget, key: str = None,
                  stretch: int = 1, help_text: str = None) -> QWidget:
        """라벨 + 위젯 행 추가"""
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 4, 0, 4)

        if label:
            lbl = BodyLabel(label)
            lbl.setMinimumWidth(100)
            lbl.setMinimumHeight(28)
            row.addWidget(lbl, 0)

        row.addWidget(widget, stretch)

        if help_text:
            widget.setToolTip(help_text)

        if key:
            self._fields[key] = widget

        self._content_layout.addLayout(row)
        return widget

    def add_text_field(self, label: str, key: str, placeholder: str = "",
                       default: str = "", help_text: str = None) -> LineEdit:
        """텍스트 입력 필드 추가"""
        entry = LineEdit()
        entry.setPlaceholderText(placeholder)
        entry.setMinimumHeight(38)
        if default:
            entry.setText(default)
        return self.add_field(label, entry, key, help_text=help_text)

    def add_dropdown(self, label: str, key: str, options: list,
                     default: str = None, help_text: str = None) -> ComboBox:
        """드롭다운 추가"""
        combo = ComboBox()
        combo.addItems(options)
        combo.setMinimumHeight(38)
        combo.setMinimumWidth(180)
        if default and default in options:
            combo.setCurrentText(default)
        return self.add_field(label, combo, key, help_text=help_text)

    def add_checkbox(self, label: str, key: str, checked: bool = False,
                     help_text: str = None) -> CheckBox:
        """체크박스 추가"""
        checkbox = CheckBox(label)
        checkbox.setChecked(checked)
        checkbox.setMinimumHeight(32)
        self._fields[key] = checkbox

        if help_text:
            checkbox.setToolTip(help_text)

        self._content_layout.addWidget(checkbox)
        return checkbox

    def add_radio_group(self, options: list, key: str, default: str = None):
        """라디오 버튼 그룹 추가"""
        from PySide6.QtWidgets import QButtonGroup

        group = QButtonGroup(self)
        row = QHBoxLayout()
        row.setSpacing(20)
        row.setContentsMargins(0, 4, 0, 4)

        for text, value in options:
            radio = RadioButton(text)
            radio.setProperty("value", value)
            radio.setMinimumHeight(32)
            group.addButton(radio)
            row.addWidget(radio)

            if value == default:
                radio.setChecked(True)

        row.addStretch()
        self._content_layout.addLayout(row)
        self._fields[key] = group
        return group

    def add_widget(self, widget: QWidget, stretch: int = 0):
        """커스텀 위젯 직접 추가"""
        self._content_layout.addWidget(widget, stretch)

    def add_layout(self, layout):
        """커스텀 레이아웃 직접 추가"""
        self._content_layout.addLayout(layout)

    def add_spacing(self, height: int = 8):
        """여백 추가"""
        self._content_layout.addSpacing(height)

    def get_field(self, key: str):
        """필드 위젯 가져오기"""
        return self._fields.get(key)
