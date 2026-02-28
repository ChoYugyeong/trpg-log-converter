"""
TRPG Log Converter Pro - 카드 컴포넌트
QFluentWidgets 기반 Fluent Design
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QButtonGroup
)
from PySide6.QtCore import Qt, QSize

from qfluentwidgets import (
    CardWidget, BodyLabel, LineEdit, ComboBox,
    CheckBox, RadioButton, ToolTipFilter, ToolTipPosition,
    TransparentToolButton, FluentIcon, Flyout, FlyoutView
)


class HelpButton(TransparentToolButton):
    """? 도움말 버튼 - 원형 디자인, 클릭 시 설명 팝업"""

    def __init__(self, help_text: str, parent=None):
        super().__init__(parent)
        self.help_text = help_text
        self.setIcon(FluentIcon.QUESTION)
        self.setFixedSize(20, 20)
        self.setIconSize(QSize(12, 12))
        self.clicked.connect(self._show_help)

        # 원형 스타일 적용
        self.setStyleSheet("""
            TransparentToolButton {
                background: rgba(128, 128, 128, 0.15);
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 10px;
                padding: 0px;
                margin: 0px;
            }
            TransparentToolButton:hover {
                background: #0A84FF;
                border-color: #0A84FF;
            }
        """)

    def _show_help(self):
        """도움말 팝업 표시"""
        view = FlyoutView(
            title="도움말",
            content=self.help_text,
            isClosable=True
        )
        Flyout.make(view, self, self.window(), isDeleteOnClose=True)


class ContentCard(CardWidget):
    """Fluent 스타일 설정 카드"""

    def __init__(self, title: str = None, subtitle: str = None, parent=None):
        super().__init__(parent)
        self._fields = {}

        # 메인 레이아웃 - 컴팩트 마진
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

        # ? 도움말 버튼 추가
        if help_text:
            row.addSpacing(4)
            help_btn = HelpButton(help_text)
            row.addWidget(help_btn)
            # 툴팁도 함께 설정
            widget.setToolTip(help_text)
            widget.installEventFilter(ToolTipFilter(widget, showDelay=500))

        if key:
            self._fields[key] = widget

        self._content_layout.addLayout(row)
        return widget

    def add_text_field(self, label: str, key: str, placeholder: str = "",
                       default: str = "", help_text: str = None,
                       clear_button: bool = True) -> LineEdit:
        """텍스트 입력 필드 추가"""
        entry = LineEdit()
        entry.setPlaceholderText(placeholder)
        entry.setClearButtonEnabled(clear_button)
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
        combo.setMinimumWidth(120)
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
            # 체크박스 + 도움말 버튼을 한 행에
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 4, 0, 4)
            row.addWidget(checkbox)
            row.addSpacing(4)
            help_btn = HelpButton(help_text)
            row.addWidget(help_btn)
            row.addStretch()
            self._content_layout.addLayout(row)

            checkbox.setToolTip(help_text)
            checkbox.installEventFilter(ToolTipFilter(checkbox, showDelay=500))
        else:
            self._content_layout.addWidget(checkbox)

        return checkbox

    def add_radio_group(self, options: list, key: str, default: str = None) -> QButtonGroup:
        """라디오 버튼 그룹 추가"""
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

    def get_value(self, key: str):
        """필드 값 가져오기"""
        widget = self._fields.get(key)
        if widget is None:
            return None

        if isinstance(widget, LineEdit):
            return widget.text()
        elif isinstance(widget, ComboBox):
            return widget.currentText()
        elif isinstance(widget, CheckBox):
            return widget.isChecked()
        elif isinstance(widget, QButtonGroup):
            checked = widget.checkedButton()
            return checked.property("value") if checked else None

        return None

    def set_value(self, key: str, value):
        """필드 값 설정"""
        widget = self._fields.get(key)
        if widget is None:
            return

        if isinstance(widget, LineEdit):
            widget.setText(str(value) if value else "")
        elif isinstance(widget, ComboBox):
            widget.setCurrentText(str(value) if value else "")
        elif isinstance(widget, CheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QButtonGroup):
            for button in widget.buttons():
                if button.property("value") == value:
                    button.setChecked(True)
                    break
