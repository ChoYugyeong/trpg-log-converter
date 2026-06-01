"""
TRPG Log Converter Pro - 카드 컴포넌트
QFluentWidgets 기반 Fluent Design
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    Flyout,
    FlyoutView,
    LineEdit,
    RadioButton,
    StrongBodyLabel,
    ToolTipFilter,
)

from ..theme import Sizes, Spacing


class CollapsibleSection(QWidget):
    """접을 수 있는 아코디언 섹션 위젯.

    헤더 클릭으로 본문을 펼치거나 접을 수 있다.
    QSS: #CollapsibleHeader, #CollapsibleBody
    """

    toggled = Signal(bool)

    def __init__(self, title: str, expanded: bool = False, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, Spacing.SM)
        layout.setSpacing(0)

        # 헤더 버튼 (QSS #CollapsibleHeader로 스타일링)
        arrow = "▼" if expanded else "▶"
        self._header = QPushButton(f"{arrow}  {title}")
        self._header.setObjectName("CollapsibleHeader")
        self._header.setProperty("expanded", expanded)
        self._header.setCursor(Qt.PointingHandCursor)
        self._header.clicked.connect(self._toggle)
        layout.addWidget(self._header)

        # 본문 (QSS #CollapsibleBody로 스타일링)
        self._body = QWidget()
        self._body.setObjectName("CollapsibleBody")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        self._body_layout.setSpacing(Spacing.MD)
        self._body.setVisible(expanded)
        layout.addWidget(self._body)

        self._expanded = expanded
        self._title = title

    def _toggle(self):
        """펼침/접힘 토글"""
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        arrow = "▼" if self._expanded else "▶"
        self._header.setText(f"{arrow}  {self._title}")
        self._header.setProperty("expanded", self._expanded)
        # QSS 동적 속성 갱신
        self._header.style().unpolish(self._header)
        self._header.style().polish(self._header)
        self.toggled.emit(self._expanded)

    def add_card(self, card):
        """ContentCard 또는 CardWidget을 본문에 추가"""
        self._body_layout.addWidget(card)

    def add_widget(self, widget):
        """일반 위젯을 본문에 추가"""
        self._body_layout.addWidget(widget)

    def add_layout(self, layout):
        """레이아웃을 본문에 추가"""
        self._body_layout.addLayout(layout)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool):
        if self._expanded != expanded:
            self._toggle()


class HelpButton(QPushButton):
    """도움말 버튼 - 원형 ? 아이콘, 클릭 시 설명 팝업 (Notion/Figma 스타일)"""

    # 앱 전체에서 도움말 팝업은 한 번에 하나만. (flyout, 그걸 연 버튼)을 클래스
    # 레벨로 추적해 중복 누적을 막고, 같은 버튼 재클릭은 토글로 닫는다.
    _open_flyout = None
    _open_owner = None

    def __init__(self, help_text: str, parent=None):
        super().__init__("?", parent)
        self.help_text = help_text
        self.setObjectName("HelpButton")
        self.setFixedSize(Sizes.HELP_BUTTON, Sizes.HELP_BUTTON)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._show_help)

    def _show_help(self):
        """도움말 팝업 표시.

        - 다른 도움말이 떠 있으면 닫고 이걸 연다.
        - 같은 버튼을 눌렀고 그 도움말이 '실제로 떠 있던' 경우에만 토글로 닫는다.
          (X/바깥클릭으로 이미 닫힌 경우엔 다시 열어준다 — 이전 구현은 stale 상태
          때문에 닫은 뒤 다시 눌러도 안 열리는 문제가 있었다.)
        """
        prev = HelpButton._open_flyout
        owner = HelpButton._open_owner
        HelpButton._open_flyout = None
        HelpButton._open_owner = None

        was_showing = False
        if prev is not None:
            try:
                was_showing = prev.isVisible()
                prev.close()
            except Exception:
                was_showing = False

        if owner is self and was_showing:
            return  # 같은 버튼 토글 → 닫기만

        view = FlyoutView(title="도움말", content=self.help_text, isClosable=True)
        flyout = Flyout.make(view, self, self.window(), isDeleteOnClose=True)
        # qfluentwidgets 버그 우회: Flyout 은 FlyoutView 의 X 버튼(closed 시그널)을
        # 자동으로 닫기에 연결하지 않는다 → X 를 눌러도 안 닫힘. 직접 연결한다.
        view.closed.connect(flyout.close)
        HelpButton._open_flyout = flyout
        HelpButton._open_owner = self


class ContentCard(CardWidget):
    """Fluent 스타일 설정 카드"""

    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        help_text: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._fields = {}
        # key -> 그 필드가 들어있는 행(라벨+위젯) 컨테이너 위젯.
        # 행 단위 표시/숨김에 사용. widget.parent() 에 의존하면 카드 전체가
        # 숨겨지는 버그가 생기므로, 항상 이 컨테이너로 토글한다.
        self._field_rows = {}

        # 메인 레이아웃
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            Sizes.CARD_PADDING_H,
            Sizes.CARD_PADDING_V_TOP,
            Sizes.CARD_PADDING_H,
            Sizes.CARD_PADDING_V_BOTTOM,
        )
        self._layout.setSpacing(Sizes.CARD_SPACING)

        # 헤더 (제목 + 도움말 버튼)
        if title:
            header_row = QHBoxLayout()
            header_row.setSpacing(8)
            header_row.setContentsMargins(0, 0, 0, 0)

            header = StrongBodyLabel(title)
            header.setObjectName("CardTitle")
            header.setMinimumHeight(26)
            header_row.addWidget(header)
            header_row.addStretch()

            if help_text:
                help_btn = HelpButton(help_text)
                header_row.addWidget(help_btn)

            self._layout.addLayout(header_row)

        if subtitle:
            sub = CaptionLabel(subtitle)
            sub.setObjectName("CardSubtitle")
            sub.setMinimumHeight(22)
            sub.setWordWrap(True)
            self._layout.addWidget(sub)

        # 콘텐츠 영역
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(Sizes.CARD_CONTENT_SPACING)
        self._content_layout.setContentsMargins(0, 10, 0, 0)
        self._layout.addLayout(self._content_layout)

    def add_field(
        self,
        label: str,
        widget: QWidget,
        key: str | None = None,
        stretch: int = 1,
        help_text: str | None = None,
    ) -> QWidget:
        """라벨 + 위젯 행 추가"""
        row = QHBoxLayout()
        row.setSpacing(Sizes.FIELD_SPACING)
        row.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)

        if label:
            lbl = BodyLabel(label)
            lbl.setMinimumWidth(Sizes.FIELD_LABEL_MIN_WIDTH)
            lbl.setMinimumHeight(Sizes.FIELD_MIN_HEIGHT)
            row.addWidget(lbl, 0)

        row.addWidget(widget, stretch)

        # ? 도움말 버튼 추가
        if help_text:
            row.addSpacing(Spacing.XS)
            help_btn = HelpButton(help_text)
            row.addWidget(help_btn)
            # 툴팁도 함께 설정
            widget.setToolTip(help_text)
            widget.installEventFilter(ToolTipFilter(widget, showDelay=300))

        if key:
            self._fields[key] = widget

        container = self._wrap_row(row)
        # 호출 측이 위젯만 들고 있어도 행 전체를 토글할 수 있도록 참조를 부착.
        widget._field_row = container
        if key:
            self._field_rows[key] = container
        return widget

    def _wrap_row(self, row: QHBoxLayout) -> QWidget:
        """행(QHBoxLayout)을 독립 QWidget 컨테이너로 감싸 콘텐츠 영역에 추가.

        레이아웃을 직접 addLayout 하면 그 안의 위젯들의 parent() 가 카드 전체가
        되어, 한 위젯의 parent().setVisible(False) 호출이 카드를 통째로 숨기는
        버그를 유발한다. 행마다 별도 컨테이너를 두면 행 단위로 안전하게 숨길 수
        있고, 위젯의 parent() 도 해당 행 컨테이너로 한정된다.
        """
        container = QWidget()
        container.setLayout(row)
        self._content_layout.addWidget(container)
        return container

    def row_of(self, key: str) -> QWidget | None:
        """key 로 추가된 필드가 속한 행 컨테이너 위젯을 반환."""
        return self._field_rows.get(key)

    def add_text_field(
        self,
        label: str,
        key: str,
        placeholder: str = "",
        default: str = "",
        help_text: str | None = None,
        clear_button: bool = True,
    ) -> LineEdit:
        """텍스트 입력 필드 추가"""
        entry = LineEdit()
        entry.setPlaceholderText(placeholder)
        entry.setClearButtonEnabled(clear_button)
        entry.setMinimumHeight(Sizes.INPUT_MIN_HEIGHT)
        if default:
            entry.setText(default)
        return self.add_field(label, entry, key, help_text=help_text)

    def add_dropdown(
        self,
        label: str,
        key: str,
        options: list,
        default: str | None = None,
        help_text: str | None = None,
    ) -> ComboBox:
        """드롭다운 추가"""
        combo = ComboBox()
        combo.addItems(options)
        combo.setMinimumHeight(Sizes.INPUT_MIN_HEIGHT)
        # 가장 긴 옵션 텍스트에 맞춰 최소 너비 설정
        if options:
            fm = combo.fontMetrics()
            max_text_width = max(fm.horizontalAdvance(opt) for opt in options)
            min_w = max(180, max_text_width + 80)  # 80px = 화살표+패딩+여백
            combo.setMinimumWidth(min_w)
            # 팝업 리스트도 충분한 너비 확보
            if hasattr(combo, "view") and callable(combo.view):
                combo.view().setMinimumWidth(max(min_w, max_text_width + 40))
        else:
            combo.setMinimumWidth(180)
        if default and default in options:
            combo.setCurrentText(default)
        return self.add_field(label, combo, key, help_text=help_text)

    def add_checkbox(
        self, label: str, key: str, checked: bool = False, help_text: str | None = None
    ) -> CheckBox:
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
            container = self._wrap_row(row)
            checkbox._field_row = container
            self._field_rows[key] = container

            checkbox.setToolTip(help_text)
            checkbox.installEventFilter(ToolTipFilter(checkbox, showDelay=300))
        else:
            self._content_layout.addWidget(checkbox)
            checkbox._field_row = checkbox
            self._field_rows[key] = checkbox

        return checkbox

    def add_radio_group(self, options: list, key: str, default: str | None = None) -> QButtonGroup:
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
        container = self._wrap_row(row)
        self._field_rows[key] = container
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
