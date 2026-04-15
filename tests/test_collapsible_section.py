"""
CollapsibleSection 위젯 테스트 (pytest-qt)

아코디언 스타일의 접을 수 있는 섹션 위젯을 검증합니다.
헤더 클릭으로 본문 영역의 펼침/접힘을 토글하며,
toggled(bool) 시그널을 방출합니다.

NOTE: Qt에서 isVisible()은 위젯 자신 + 모든 부모가 show()된 경우에만 True를 반환한다.
테스트에서는 위젯을 화면에 표시하지 않으므로, 위젯이 명시적으로 숨겨졌는지를
확인하는 isHidden()을 사용한다. isHidden()은 setVisible(False)가 호출된 경우에만
True를 반환한다 (부모의 show 여부와 무관).
"""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel


# ---------------------------------------------------------------------------
# 공통 fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def section_collapsed(qtbot):
    """접힌 상태의 CollapsibleSection을 생성한다."""
    from gui.components.cards import CollapsibleSection

    section = CollapsibleSection("테스트 섹션", expanded=False)
    qtbot.addWidget(section)
    return section


@pytest.fixture
def section_expanded(qtbot):
    """펼쳐진 상태의 CollapsibleSection을 생성한다."""
    from gui.components.cards import CollapsibleSection

    section = CollapsibleSection("펼침 섹션", expanded=True)
    qtbot.addWidget(section)
    return section


# ===================================================================
# 1. 기본 접힌 상태
# ===================================================================

class TestDefaultCollapsed:
    """expanded=False로 생성된 CollapsibleSection 검증"""

    def test_default_collapsed(self, section_collapsed):
        """expanded=False로 생성하면 본문이 숨겨져 있다."""
        # GIVEN: expanded=False로 생성된 섹션

        # THEN: 본문(body)이 명시적으로 숨겨져 있다
        assert section_collapsed._body.isHidden() is True
        assert section_collapsed.is_expanded() is False

    def test_header_shows_collapsed_arrow(self, section_collapsed):
        """접힌 상태에서 헤더에 '▶' 화살표가 표시된다."""
        header_text = section_collapsed._header.text()
        assert "▶" in header_text


# ===================================================================
# 2. 기본 펼쳐진 상태
# ===================================================================

class TestDefaultExpanded:
    """expanded=True로 생성된 CollapsibleSection 검증"""

    def test_default_expanded(self, section_expanded):
        """expanded=True로 생성하면 본문이 숨겨지지 않는다 (보임 의도)."""
        # GIVEN: expanded=True로 생성된 섹션

        # THEN: 본문(body)이 명시적으로 숨겨지지 않았다 (보임 상태)
        assert section_expanded._body.isHidden() is False
        assert section_expanded.is_expanded() is True

    def test_header_shows_expanded_arrow(self, section_expanded):
        """펼쳐진 상태에서 헤더에 '▼' 화살표가 표시된다."""
        header_text = section_expanded._header.text()
        assert "▼" in header_text


# ===================================================================
# 3. 토글 동작
# ===================================================================

class TestToggle:
    """헤더 클릭으로 펼침/접힘 토글 검증"""

    def test_toggle_from_collapsed(self, qtbot, section_collapsed):
        """접힌 상태에서 헤더 클릭 시 펼쳐진다."""
        # GIVEN: 접힌 상태
        assert section_collapsed.is_expanded() is False

        # WHEN: 헤더를 클릭한다
        qtbot.mouseClick(section_collapsed._header, Qt.LeftButton)

        # THEN: 본문이 숨겨지지 않은 상태가 되고 펼쳐진 상태가 된다
        assert section_collapsed._body.isHidden() is False
        assert section_collapsed.is_expanded() is True

    def test_toggle_from_expanded(self, qtbot, section_expanded):
        """펼쳐진 상태에서 헤더 클릭 시 접힌다."""
        # GIVEN: 펼쳐진 상태
        assert section_expanded.is_expanded() is True

        # WHEN: 헤더를 클릭한다
        qtbot.mouseClick(section_expanded._header, Qt.LeftButton)

        # THEN: 본문이 숨겨지고 접힌 상태가 된다
        assert section_expanded._body.isHidden() is True
        assert section_expanded.is_expanded() is False

    def test_double_toggle_restores_state(self, qtbot, section_collapsed):
        """두 번 토글하면 원래 상태로 돌아온다."""
        # GIVEN: 접힌 상태
        original_expanded = section_collapsed.is_expanded()

        # WHEN: 두 번 클릭 (토글 -> 토글)
        qtbot.mouseClick(section_collapsed._header, Qt.LeftButton)
        qtbot.mouseClick(section_collapsed._header, Qt.LeftButton)

        # THEN: 원래 상태로 복원
        assert section_collapsed.is_expanded() == original_expanded

    def test_toggle_updates_arrow(self, qtbot, section_collapsed):
        """토글 시 헤더 화살표가 갱신된다."""
        # GIVEN: 접힌 상태 (▶)
        assert "▶" in section_collapsed._header.text()

        # WHEN: 클릭하여 펼침
        qtbot.mouseClick(section_collapsed._header, Qt.LeftButton)

        # THEN: 화살표가 ▼ 으로 바뀐다
        assert "▼" in section_collapsed._header.text()

    def test_set_expanded_programmatic(self, section_collapsed):
        """set_expanded()로 프로그래밍 방식으로 토글할 수 있다."""
        # WHEN: 프로그래밍 방식으로 펼침
        section_collapsed.set_expanded(True)

        # THEN: 펼쳐진 상태
        assert section_collapsed.is_expanded() is True
        assert section_collapsed._body.isHidden() is False

    def test_set_expanded_same_state_no_change(self, section_collapsed):
        """이미 같은 상태로 set_expanded()하면 토글되지 않는다."""
        # GIVEN: 접힌 상태
        assert section_collapsed.is_expanded() is False

        # WHEN: 같은 상태(False)로 설정
        section_collapsed.set_expanded(False)

        # THEN: 여전히 접힌 상태
        assert section_collapsed.is_expanded() is False


# ===================================================================
# 4. add_card
# ===================================================================

class TestAddCard:
    """add_card()로 위젯을 본문에 추가하는 기능 검증"""

    def test_add_card(self, qtbot, section_expanded):
        """add_card()로 위젯을 본문에 추가할 수 있다."""
        # GIVEN: 펼쳐진 섹션
        initial_count = section_expanded._body_layout.count()

        # WHEN: 위젯을 추가한다
        card = QLabel("테스트 카드")
        section_expanded.add_card(card)

        # THEN: 본문 레이아웃에 위젯이 추가된다
        assert section_expanded._body_layout.count() == initial_count + 1

    def test_add_multiple_cards(self, qtbot, section_expanded):
        """여러 위젯을 순서대로 추가할 수 있다."""
        # WHEN: 3개의 위젯을 추가
        initial_count = section_expanded._body_layout.count()

        for i in range(3):
            section_expanded.add_card(QLabel(f"카드 {i}"))

        # THEN: 3개가 추가된다
        assert section_expanded._body_layout.count() == initial_count + 3

    def test_add_widget_method(self, qtbot, section_expanded):
        """add_widget()으로도 위젯을 추가할 수 있다."""
        initial_count = section_expanded._body_layout.count()

        section_expanded.add_widget(QLabel("위젯"))

        assert section_expanded._body_layout.count() == initial_count + 1


# ===================================================================
# 5. toggled 시그널
# ===================================================================

class TestSignalEmitted:
    """toggled(bool) 시그널 방출 검증"""

    def test_signal_emitted_on_click(self, qtbot, section_collapsed):
        """헤더 클릭 시 toggled(bool) 시그널이 방출된다."""
        # GIVEN: 접힌 상태

        # WHEN/THEN: 클릭 시 toggled 시그널이 방출된다
        with qtbot.waitSignal(section_collapsed.toggled, timeout=1000) as blocker:
            qtbot.mouseClick(section_collapsed._header, Qt.LeftButton)

        # THEN: 방출된 값은 새로운 expanded 상태 (True)
        assert blocker.args == [True]

    def test_signal_emitted_with_false_on_collapse(self, qtbot, section_expanded):
        """펼쳐진 상태에서 클릭하면 toggled(False)가 방출된다."""
        with qtbot.waitSignal(section_expanded.toggled, timeout=1000) as blocker:
            qtbot.mouseClick(section_expanded._header, Qt.LeftButton)

        # THEN: 접힌 상태(False)로 방출
        assert blocker.args == [False]

    def test_signal_emitted_on_set_expanded(self, qtbot, section_collapsed):
        """set_expanded()로 토글해도 시그널이 방출된다."""
        with qtbot.waitSignal(section_collapsed.toggled, timeout=1000) as blocker:
            section_collapsed.set_expanded(True)

        assert blocker.args == [True]

    def test_multiple_toggles_emit_correct_sequence(self, qtbot, section_collapsed):
        """여러 번 토글하면 올바른 순서로 시그널이 방출된다."""
        received = []
        section_collapsed.toggled.connect(lambda v: received.append(v))

        # WHEN: 3번 토글
        qtbot.mouseClick(section_collapsed._header, Qt.LeftButton)  # False -> True
        qtbot.mouseClick(section_collapsed._header, Qt.LeftButton)  # True -> False
        qtbot.mouseClick(section_collapsed._header, Qt.LeftButton)  # False -> True

        # THEN: [True, False, True] 순서로 방출
        assert received == [True, False, True]
