"""
TRPG Log Converter Pro - Fluent Design 네이티브 세팅 카드 컴포넌트

qfluentwidgets의 SettingCard 생태계를 기반으로 한 커스텀 카드 컴포넌트.
각 카드는 도움말 아이콘(FluentIcon.QUESTION)을 포함하며,
클릭 시 TeachingTip으로 설명을 표시한다.
OS 네이티브 툴팁(setToolTip)은 사용하지 않는다.
"""


from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor, QIcon
from PySide6.QtWidgets import QColorDialog, QHBoxLayout, QWidget
from qfluentwidgets import (
    ComboBox,
    FluentIcon,
    IconWidget,
    LineEdit,
    SettingCard,
    SettingCardGroup,
    SpinBox,
    StrongBodyLabel,
    SwitchButton,
    TeachingTip,
    TeachingTipTailPosition,
    TeachingTipView,
    ToolTipFilter,
    setFont,
)
from qfluentwidgets.common.icon import FluentIconBase

from ..theme import Sizes, Spacing

# ---------------------------------------------------------------------------
# 기본 클래스: 도움말 아이콘이 포함된 SettingCard
# ---------------------------------------------------------------------------

class HelpableSettingCard(SettingCard):
    """도움말 아이콘(?)을 지원하는 SettingCard 기본 클래스.

    help_text가 주어지면 카드 우측에 FluentIcon.QUESTION 아이콘을 배치하고,
    클릭 시 TeachingTip으로 도움말을 표시한다.
    ToolTipFilter를 설치하여 호버 시에도 미리보기를 제공한다.

    서브클래스는 _add_right_widget()을 호출하여 조작 위젯을 우측에 배치하고,
    그 뒤에 도움말 아이콘이 자동으로 추가된다.
    """

    # 값 변경 시그널 — 서브클래스에서 emit
    value_changed = Signal(object)

    def __init__(
        self,
        icon: str | QIcon | FluentIconBase,
        title: str,
        content: str = "",
        help_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(icon, title, content, parent)
        self._help_text = help_text
        self._help_icon: IconWidget | None = None

        if help_text:
            self._setup_help(help_text)

    # ── 도움말 아이콘 설정 ──────────────────────────────────────
    def _setup_help(self, help_text: str):
        """도움말 아이콘을 hBoxLayout 맨 오른쪽에 추가한다."""
        self._help_icon = IconWidget(FluentIcon.QUESTION, self)
        self._help_icon.setFixedSize(16, 16)
        self._help_icon.setCursor(QCursor(Qt.PointingHandCursor))

        # 클릭 이벤트 — TeachingTip 표시
        self._help_icon.mousePressEvent = lambda e: self._show_teaching_tip()

        # ToolTipFilter로 호버 시 Fluent 스타일 미리보기 제공
        # 내부적으로 widget.toolTip()을 읽지만, OS 네이티브 이벤트는 필터가 차단
        self._help_icon.setProperty("toolTip_text", help_text)
        self._help_icon_filter = _HelpToolTipFilter(
            self._help_icon, help_text, showDelay=400
        )
        self._help_icon.installEventFilter(self._help_icon_filter)

        # 레이아웃에 추가 (맨 오른쪽)
        self.hBoxLayout.addWidget(self._help_icon, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

    def _show_teaching_tip(self):
        """클릭 시 TeachingTip을 표시한다."""
        if not self._help_text or self._help_icon is None:
            return

        view = TeachingTipView(
            title="도움말",
            content=self._help_text,
            icon=FluentIcon.INFO,
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
        )
        # duration=-1: 사용자가 닫을 때까지 유지
        TeachingTip.make(
            view,
            target=self._help_icon,
            duration=-1,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            parent=self.window(),
            isDeleteOnClose=True,
        )

    # ── 우측 위젯 배치 유틸리티 ─────────────────────────────────
    def _add_right_widget(self, widget: QWidget):
        """조작 위젯을 카드 우측에 추가한다.

        도움말 아이콘이 있으면 그 *앞*에 삽입하여
        [위젯] [?아이콘] [16px] 순서가 되도록 한다.
        """
        if self._help_icon is not None:
            # 도움말 아이콘 위치 찾기 — 아이콘 바로 앞에 삽입
            idx = self.hBoxLayout.indexOf(self._help_icon)
            self.hBoxLayout.insertWidget(idx, widget, 0, Qt.AlignRight)
            self.hBoxLayout.insertSpacing(idx + 1, 12)
        else:
            self.hBoxLayout.addWidget(widget, 0, Qt.AlignRight)
            self.hBoxLayout.addSpacing(16)

    # ── 값 접근 인터페이스 (서브클래스에서 오버라이드) ────────────
    def get_value(self):
        """현재 값을 반환한다. 서브클래스에서 구현."""
        return None

    def set_value(self, value):
        """값을 설정한다. 서브클래스에서 구현."""


# ---------------------------------------------------------------------------
# 내부 헬퍼: ToolTipFilter를 setToolTip() 없이 사용하기 위한 래퍼
# ---------------------------------------------------------------------------

class _HelpToolTipFilter(ToolTipFilter):
    """ToolTipFilter를 setToolTip() 호출 없이 사용하는 래퍼.

    qfluentwidgets의 ToolTipFilter는 내부적으로 parent.toolTip()을 읽어
    Fluent 스타일 ToolTip을 표시한다. 하지만 직접 setToolTip()을 호출하면
    OS 네이티브 툴팁이 트리거될 수 있으므로, 이 래퍼에서 toolTip()을
    오버라이드하여 원하는 텍스트를 반환하도록 한다.
    """

    def __init__(self, parent: QWidget, help_text: str, showDelay: int = 300):
        super().__init__(parent, showDelay=showDelay)
        self._help_text = help_text
        # parent의 toolTip 메서드를 패치하여 텍스트 반환
        parent.toolTip = lambda: self._help_text


# ---------------------------------------------------------------------------
# 콤보박스 세팅 카드
# ---------------------------------------------------------------------------

class HelpableComboBoxCard(HelpableSettingCard):
    """드롭다운(ComboBox)이 포함된 세팅 카드.

    옵션 목록을 받아 ComboBox를 우측에 배치한다.
    사용자가 선택을 변경하면 value_changed 시그널을 emit한다.
    """

    def __init__(
        self,
        icon: str | QIcon | FluentIconBase,
        title: str,
        content: str = "",
        options: list[str] | None = None,
        default: str | None = None,
        help_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(icon, title, content, help_text, parent)
        options = options or []

        # 콤보박스 생성
        self.combo_box = ComboBox(self)
        self.combo_box.addItems(options)
        self.combo_box.setMinimumHeight(Sizes.INPUT_MIN_HEIGHT)

        # 가장 긴 옵션에 맞춰 최소 너비 계산
        if options:
            fm = self.combo_box.fontMetrics()
            max_text_w = max(fm.horizontalAdvance(opt) for opt in options)
            min_w = max(180, max_text_w + 80)
            self.combo_box.setMinimumWidth(min_w)
        else:
            self.combo_box.setMinimumWidth(180)

        # 기본값 설정
        if default and default in options:
            self.combo_box.setCurrentText(default)

        # 레이아웃 배치
        self._add_right_widget(self.combo_box)

        # 시그널 연결
        self.combo_box.currentTextChanged.connect(
            lambda text: self.value_changed.emit(text)
        )

    def get_value(self) -> str:
        """현재 선택된 텍스트를 반환한다."""
        return self.combo_box.currentText()

    def set_value(self, value: str):
        """콤보박스 선택을 변경한다."""
        self.combo_box.setCurrentText(str(value) if value else "")


# ---------------------------------------------------------------------------
# 스위치(토글) 세팅 카드
# ---------------------------------------------------------------------------

class HelpableSwitchCard(HelpableSettingCard):
    """토글 스위치(SwitchButton)가 포함된 세팅 카드.

    ON/OFF 상태를 전환하며, value_changed(bool)를 emit한다.
    """

    def __init__(
        self,
        icon: str | QIcon | FluentIconBase,
        title: str,
        content: str = "",
        default: bool = False,
        on_text: str = "켜짐",
        off_text: str = "꺼짐",
        help_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(icon, title, content, help_text, parent)

        # 스위치 버튼 생성
        self.switch_button = SwitchButton(self)
        self.switch_button.setOnText(on_text)
        self.switch_button.setOffText(off_text)
        self.switch_button.setChecked(default)

        # 레이아웃 배치
        self._add_right_widget(self.switch_button)

        # 시그널 연결
        self.switch_button.checkedChanged.connect(
            lambda checked: self.value_changed.emit(checked)
        )

    def get_value(self) -> bool:
        """현재 체크 상태를 반환한다."""
        return self.switch_button.isChecked()

    def set_value(self, value: bool):
        """체크 상태를 설정한다."""
        self.switch_button.setChecked(bool(value))


# ---------------------------------------------------------------------------
# 스핀박스 세팅 카드
# ---------------------------------------------------------------------------

class HelpableSpinBoxCard(HelpableSettingCard):
    """숫자 입력(SpinBox)이 포함된 세팅 카드.

    최솟값, 최댓값, 스텝을 지정할 수 있으며
    value_changed(int)를 emit한다.
    """

    def __init__(
        self,
        icon: str | QIcon | FluentIconBase,
        title: str,
        content: str = "",
        minimum: int = 0,
        maximum: int = 9999,
        step: int = 1,
        default: int = 0,
        suffix: str = "",
        help_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(icon, title, content, help_text, parent)

        # 스핀박스 생성
        self.spin_box = SpinBox(self)
        self.spin_box.setRange(minimum, maximum)
        self.spin_box.setSingleStep(step)
        self.spin_box.setValue(default)
        self.spin_box.setMinimumHeight(Sizes.INPUT_MIN_HEIGHT)
        self.spin_box.setMaximumWidth(Sizes.INPUT_NUMERIC_MAX_W)

        if suffix:
            self.spin_box.setSuffix(f" {suffix}")

        # 레이아웃 배치
        self._add_right_widget(self.spin_box)

        # 시그널 연결
        self.spin_box.valueChanged.connect(
            lambda val: self.value_changed.emit(val)
        )

    def get_value(self) -> int:
        """현재 스핀박스 값을 반환한다."""
        return self.spin_box.value()

    def set_value(self, value: int):
        """스핀박스 값을 설정한다."""
        self.spin_box.setValue(int(value))


# ---------------------------------------------------------------------------
# 텍스트 입력 세팅 카드
# ---------------------------------------------------------------------------

class HelpableLineEditCard(HelpableSettingCard):
    """텍스트 입력(LineEdit)이 포함된 세팅 카드.

    사용자가 텍스트를 편집하면 value_changed(str)를 emit한다.
    """

    def __init__(
        self,
        icon: str | QIcon | FluentIconBase,
        title: str,
        content: str = "",
        placeholder: str = "",
        default: str = "",
        clear_button: bool = True,
        help_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(icon, title, content, help_text, parent)

        # 텍스트 입력 생성
        self.line_edit = LineEdit(self)
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setClearButtonEnabled(clear_button)
        self.line_edit.setMinimumHeight(Sizes.INPUT_MIN_HEIGHT)
        self.line_edit.setMinimumWidth(200)

        if default:
            self.line_edit.setText(default)

        # 레이아웃 배치
        self._add_right_widget(self.line_edit)

        # 시그널 연결 — textChanged로 실시간 값 반영
        self.line_edit.textChanged.connect(
            lambda text: self.value_changed.emit(text)
        )

    def get_value(self) -> str:
        """현재 텍스트를 반환한다."""
        return self.line_edit.text()

    def set_value(self, value: str):
        """텍스트를 설정한다."""
        self.line_edit.setText(str(value) if value else "")


# ---------------------------------------------------------------------------
# 색상 선택 세팅 카드
# ---------------------------------------------------------------------------

class HelpableColorCard(HelpableSettingCard):
    """색상 선택기(스와치 + Hex 입력)가 포함된 세팅 카드.

    색상 스와치 클릭 시 QColorDialog를 열고,
    Hex 입력으로 직접 색상 코드를 입력할 수 있다.
    value_changed(str)로 "#RRGGBB" 형식의 색상을 emit한다.
    """

    def __init__(
        self,
        icon: str | QIcon | FluentIconBase,
        title: str,
        content: str = "",
        default_color: str = "#007AFF",
        help_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(icon, title, content, help_text, parent)
        self._color = default_color

        # 색상 위젯 컨테이너
        color_container = QWidget(self)
        color_layout = QHBoxLayout(color_container)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(Spacing.SM)

        # Hex 입력 필드
        self.hex_input = LineEdit(color_container)
        self.hex_input.setText(default_color)
        self.hex_input.setPlaceholderText("#RRGGBB")
        self.hex_input.setFixedWidth(Sizes.COLOR_HEX_MAX_W)
        self.hex_input.setMinimumHeight(Sizes.COLOR_SWATCH)
        self.hex_input.setClearButtonEnabled(False)
        color_layout.addWidget(self.hex_input)

        # 색상 스와치 버튼
        self._swatch = _ColorSwatchButton(default_color, color_container)
        self._swatch.setFixedSize(Sizes.COLOR_SWATCH, Sizes.COLOR_SWATCH)
        self._swatch.setCursor(QCursor(Qt.PointingHandCursor))
        self._swatch.clicked.connect(self._open_color_dialog)
        color_layout.addWidget(self._swatch)

        # 레이아웃 배치
        self._add_right_widget(color_container)

        # Hex 입력 변경 시그널
        self.hex_input.textChanged.connect(self._on_hex_changed)

    def _on_hex_changed(self, text: str):
        """Hex 입력 값이 변경될 때 호출된다."""
        if len(text) == 7 and text.startswith("#"):
            color = QColor(text)
            if color.isValid():
                self._color = text
                self._swatch.set_color(text)
                self.value_changed.emit(text)

    def _open_color_dialog(self):
        """시스템 색상 대화상자를 연다."""
        color = QColorDialog.getColor(
            QColor(self._color),
            self.window(),
            "색상 선택",
        )
        if color.isValid():
            hex_color = color.name()
            self._color = hex_color
            self._swatch.set_color(hex_color)
            # blockSignals로 중복 emit 방지
            self.hex_input.blockSignals(True)
            self.hex_input.setText(hex_color)
            self.hex_input.blockSignals(False)
            self.value_changed.emit(hex_color)

    def get_value(self) -> str:
        """현재 색상을 '#RRGGBB' 형식으로 반환한다."""
        return self._color

    def set_value(self, value: str):
        """색상을 설정한다."""
        if not value:
            return
        color = QColor(value)
        if color.isValid():
            self._color = value
            self._swatch.set_color(value)
            self.hex_input.blockSignals(True)
            self.hex_input.setText(value)
            self.hex_input.blockSignals(False)


class _ColorSwatchButton(QWidget):
    """색상 스와치 미리보기 위젯.

    setStyleSheet() 대신 paintEvent로 직접 그려서
    다크/라이트 모드에 모두 대응한다.
    """

    clicked = Signal()

    def __init__(self, color: str = "#007AFF", parent: QWidget | None = None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setObjectName("ColorSwatch")

    def set_color(self, color: str):
        """표시 색상을 변경한다."""
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        """색상 스와치를 직접 그린다."""
        from PySide6.QtGui import QBrush, QPainter, QPen
        from qfluentwidgets.common.style_sheet import isDarkTheme

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 테두리 색상 — 테마에 따라 다름
        if isDarkTheme():
            border_color = QColor(255, 255, 255, 40)
        else:
            border_color = QColor(0, 0, 0, 30)

        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.setBrush(QBrush(self._color))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        painter.end()

    def mousePressEvent(self, event):
        """클릭 이벤트를 시그널로 전달한다."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# 세팅 카드 그룹
# ---------------------------------------------------------------------------

class FluentSettingGroup(SettingCardGroup):
    """세팅 카드들을 묶는 섹션 그룹.

    StrongBodyLabel을 사용하여 섹션 제목을 표시하며,
    인라인 CSS 없이 qfluentwidgets 테마를 따른다.
    """

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(title, parent)

        # 기본 QLabel 대신 StrongBodyLabel로 교체
        self.vBoxLayout.removeWidget(self.titleLabel)
        self.titleLabel.deleteLater()

        self.titleLabel = StrongBodyLabel(title, self)
        setFont(self.titleLabel, 18)
        self.titleLabel.adjustSize()

        # 레이아웃 맨 위에 다시 삽입
        self.vBoxLayout.insertWidget(0, self.titleLabel)

    def add_card(self, card: QWidget):
        """카드를 그룹에 추가한다.

        addSettingCard()의 한국어 별칭.
        """
        self.addSettingCard(card)

    def add_cards(self, cards: list[QWidget]):
        """여러 카드를 한번에 추가한다.

        addSettingCards()의 한국어 별칭.
        """
        self.addSettingCards(cards)
