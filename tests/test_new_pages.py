"""
새로운 4-탭 페이지 구조 테스트 (pytest-qt)

HomePage, FormatStylePage, ParsingContentPage, AdvancedSettingsPage
각 페이지의 생성, 시그널, 메서드, 설정 라운드트립을 검증합니다.
"""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Signal

# ---------------------------------------------------------------------------
# 공통 fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def app_state(tmp_path):
    """AppState + ConfigManager를 생성하고 BasePage에 주입한다."""
    from core.config_manager import ConfigManager
    from gui.pages.base_page import BasePage
    from gui.state import AppState

    cm = ConfigManager(app_dir=tmp_path)
    state = AppState(cm)
    BasePage.set_app_state(state)
    return state, cm


@pytest.fixture
def home_page(qtbot, app_state):
    """HomePage 인스턴스를 생성하고 반환한다."""
    state, cm = app_state
    from gui.pages.home_page import HomePage
    page = HomePage(cm)
    qtbot.addWidget(page)
    return page, state, cm


# ===================================================================
# 1. HomePage 생성
# ===================================================================

class TestHomePageCreation:
    """HomePage 인스턴스 생성 및 기본 구조 검증"""

    def test_home_page_creation(self, qtbot, app_state):
        """HomePage가 에러 없이 생성된다."""
        _state, cm = app_state

        # WHEN: HomePage를 생성한다
        from gui.pages.home_page import HomePage
        page = HomePage(cm)
        qtbot.addWidget(page)

        # THEN: 위젯이 정상적으로 존재한다
        assert page is not None
        assert page.objectName() == "HomePage"


# ===================================================================
# 2. HomePage 시그널 존재 확인
# ===================================================================

class TestHomePageSignals:
    """HomePage에 필수 시그널이 정의되어 있는지 검증"""

    def test_home_page_has_required_signals(self, home_page):
        """HomePage에 conversion_started, files_updated, entries_parsed 시그널이 있다."""
        page, _, _ = home_page

        # THEN: 각 시그널이 존재한다
        # PySide6에서는 Signal이 SignalInstance로 바인딩된다
        assert hasattr(page, "conversion_started")
        assert hasattr(page, "files_updated")
        assert hasattr(page, "entries_parsed")

    def test_conversion_requested_signal_exists(self, home_page):
        """HomePage에 conversion_requested 시그널이 있다."""
        page, _, _ = home_page
        assert hasattr(page, "conversion_requested")

    def test_conversion_finished_signal_exists(self, home_page):
        """HomePage에 conversion_finished 시그널이 있다."""
        page, _, _ = home_page
        assert hasattr(page, "conversion_finished")

    def test_files_updated_signal_emits(self, qtbot, home_page, tmp_path):
        """파일 추가 시 files_updated 시그널이 방출된다."""
        page, _, _ = home_page

        # GIVEN: 테스트용 파일 생성
        test_file = tmp_path / "test.html"
        test_file.write_text("<html><body>test</body></html>", encoding="utf-8")

        # WHEN/THEN: 파일 추가 시 시그널 방출
        with qtbot.waitSignal(page.files_updated, timeout=1000):
            page._on_files_dropped([str(test_file)])


# ===================================================================
# 3. HomePage 필수 메서드 존재 확인
# ===================================================================

class TestHomePageMethods:
    """HomePage에 필수 메서드가 정의되어 있는지 검증"""

    def test_home_page_has_required_methods(self, home_page):
        """HomePage에 get_files, get_title, update_progress 등 메서드가 있다."""
        page, _, _ = home_page

        # THEN: 각 메서드가 호출 가능하다
        assert callable(getattr(page, "get_files", None))
        assert callable(getattr(page, "get_title", None))
        assert callable(getattr(page, "update_progress", None))
        assert callable(getattr(page, "get_author", None))
        assert callable(getattr(page, "get_convert_mode", None))
        assert callable(getattr(page, "get_output_format", None))
        assert callable(getattr(page, "save_settings", None))
        assert callable(getattr(page, "load_settings", None))
        assert callable(getattr(page, "conversion_complete", None))

    def test_get_files_returns_empty_initially(self, home_page):
        """초기 상태에서 get_files()는 빈 리스트를 반환한다."""
        page, _, _ = home_page

        # THEN: 초기 파일 목록은 비어있다
        assert page.get_files() == []

    def test_get_title_default(self, home_page):
        """title_entry가 비어있거나 존재하지 않으면 기본값 'TRPG 리플레이'를 반환한다.
        get_title() 메서드는 내부적으로 hasattr 가드를 사용한다.
        """
        page, _, _ = home_page

        # GIVEN: title_entry가 있으면 비우고, 없으면 그대로
        if hasattr(page, "title_entry"):
            page.title_entry.setText("")

        # THEN: get_title()은 항상 기본값 또는 설정된 값을 반환한다
        title = page.get_title()
        assert isinstance(title, str)
        assert len(title) > 0
        # title_entry가 비어있거나 없으면 기본값
        if not hasattr(page, "title_entry") or not page.title_entry.text():
            assert title == "TRPG 리플레이"

    def test_get_convert_mode_default(self, home_page):
        """기본 변환 모드는 'single'이다."""
        page, _, _ = home_page

        assert page.get_convert_mode() == "single"

    def test_get_output_format_default(self, home_page):
        """기본 출력 형식은 'both'이다."""
        page, _, _ = home_page

        assert page.get_output_format() == "both"

    def test_update_progress(self, home_page):
        """update_progress()가 진행률 바와 라벨을 갱신한다."""
        page, _, _ = home_page

        # WHEN: 진행 상태 업데이트
        page.progress_frame.setVisible(True)
        page.update_progress(50, "변환 중...")

        # THEN: 위젯이 올바르게 갱신된다
        assert page.progress_bar.value() == 50
        assert page.progress_label.text() == "변환 중..."

    def test_conversion_complete_success(self, home_page):
        """변환 완료 시 진행 프레임이 숨겨지고 버튼이 활성화된다."""
        page, _, _ = home_page

        # GIVEN: 변환 중 상태
        page.progress_frame.setVisible(True)
        page.convert_btn.setEnabled(False)

        # WHEN: 변환 완료
        page.conversion_complete(True, "완료!")

        # THEN: 프레임 숨김, 버튼 활성화
        assert page.progress_frame.isVisible() is False
        assert page.convert_btn.isEnabled() is True


# ===================================================================
# 4. HomePage save/load 라운드트립 - AppState 경유
# ===================================================================

class TestHomePageSaveLoadRoundTrip:
    """AppState를 통한 save → load 라운드트립 검증.

    HomePage의 내부 위젯(title_entry 등)은 qfluentwidgets 환경에 따라
    CI에서 완전히 초기화되지 않을 수 있으므로, AppState를 직접 조작하여
    라운드트립을 검증한다.
    """

    def test_home_page_save_load_round_trip(self, home_page):
        """AppState를 통해 narrators를 설정·저장·로드하면 문자열로 보존된다."""
        _page, state, _cm = home_page

        # GIVEN: AppState를 통해 narrators 설정
        test_narrators = "GM, KP, DM, Narrator"
        state.set("narrators", test_narrators)

        # WHEN: 저장 후 로드
        state.save()
        state.load()

        # THEN: narrators가 문자열로 보존된다
        loaded = state.get("narrators")
        assert isinstance(loaded, str)
        assert "GM" in loaded
        assert "KP" in loaded

    def test_narrators_never_becomes_list(self, home_page):
        """AppState를 거쳐도 narrators가 리스트로 바뀌지 않는다."""
        _page, state, _ = home_page

        # GIVEN: narrators를 문자열로 설정하고 저장
        state.set("narrators", "GM, KP")
        state.save()

        # WHEN: 다시 로드
        state.load()

        # THEN: 여전히 문자열이다
        narrators = state.get("narrators")
        assert isinstance(narrators, str), f"narrators가 {type(narrators)}로 저장되었다"

    def test_save_load_preserves_title(self, home_page):
        """AppState를 통한 제목 라운드트립 검증."""
        _page, state, _ = home_page

        # GIVEN: 제목 설정
        state.set("title", "마이 세션")
        state.save()

        # WHEN: 다시 로드
        state.load()

        # THEN: 제목이 보존된다
        assert state.get("title") == "마이 세션"


# ===================================================================
# 5. 언어 드롭다운 표시명 검증
# ===================================================================

class TestHomePageLanguage:
    """언어 매핑이 전체 이름을 사용하는지 검증.

    LANGUAGE_MAP / LANGUAGE_REVERSE_MAP이 올바르게 정의되어 있으면
    HomePage의 드롭다운도 올바르게 표시된다.
    """

    def test_home_page_language_full_name(self, home_page):
        """LANGUAGE_MAP에 '한국어 (Korean)' 키가 존재하고 'ko' 코드로 매핑된다."""
        from gui.theme import LANGUAGE_MAP, LANGUAGE_REVERSE_MAP

        # THEN: 전체 이름이 키로 존재한다
        assert "한국어 (Korean)" in LANGUAGE_MAP
        assert LANGUAGE_MAP["한국어 (Korean)"] == "ko"

        # THEN: 역매핑도 올바르다
        assert LANGUAGE_REVERSE_MAP.get("ko") == "한국어 (Korean)"

    def test_language_map_has_no_bare_codes_as_keys(self):
        """LANGUAGE_MAP의 키에 'ko', 'en', 'ja' 같은 짧은 코드가 없다."""
        from gui.theme import LANGUAGE_MAP

        for key in LANGUAGE_MAP:
            assert len(key) > 3, f"키가 너무 짧음 (코드 직접 사용 의심): {key}"

    def test_language_includes_english_and_japanese(self):
        """LANGUAGE_MAP에 영어와 일본어도 포함된다."""
        from gui.theme import LANGUAGE_MAP

        assert "English" in LANGUAGE_MAP
        assert "日本語 (Japanese)" in LANGUAGE_MAP

    def test_language_combo_items_if_available(self, home_page):
        """HomePage에 language_combo가 있으면 전체 이름으로 표시되는지 확인한다."""
        page, _, _ = home_page

        if not hasattr(page, "language_combo"):
            pytest.skip("language_combo가 생성되지 않음 (qfluentwidgets 환경 제한)")

        items = [page.language_combo.itemText(i) for i in range(page.language_combo.count())]

        assert "한국어 (Korean)" in items, f"드롭다운 항목: {items}"
        assert "ko" not in items, "언어 코드가 직접 표시되어서는 안 된다"
        assert "English" in items
        assert "日本語 (Japanese)" in items


# ===================================================================
# 6. FormatStylePage 생성
# ===================================================================

class TestFormatStylePageCreation:
    """FormatStylePage 인스턴스 생성 검증"""

    def test_format_style_page_creation(self, qtbot, app_state):
        """FormatStylePage가 에러 없이 생성된다."""
        _state, cm = app_state

        # WHEN: FormatStylePage를 생성한다
        from gui.pages.format_style_page import FormatStylePage
        page = FormatStylePage(cm)
        qtbot.addWidget(page)

        # THEN: 위젯이 정상적으로 존재한다
        assert page is not None

    def test_format_style_page_is_base_page(self, qtbot, app_state):
        """FormatStylePage는 BasePage의 서브클래스이다."""
        _state, cm = app_state
        from gui.pages.base_page import BasePage
        from gui.pages.format_style_page import FormatStylePage

        page = FormatStylePage(cm)
        qtbot.addWidget(page)

        assert isinstance(page, BasePage)


# ===================================================================
# 7. ParsingContentPage 생성
# ===================================================================

class TestParsingContentPageCreation:
    """ParsingContentPage 인스턴스 생성 검증"""

    def test_parsing_content_page_creation(self, qtbot, app_state):
        """ParsingContentPage가 에러 없이 생성된다."""
        _state, cm = app_state

        from gui.pages.parsing_content_page import ParsingContentPage
        page = ParsingContentPage(cm)
        qtbot.addWidget(page)

        assert page is not None

    def test_parsing_content_page_has_settings_changed(self, qtbot, app_state):
        """ParsingContentPage에 settings_changed 시그널이 있다."""
        _state, cm = app_state

        from gui.pages.parsing_content_page import ParsingContentPage
        page = ParsingContentPage(cm)
        qtbot.addWidget(page)

        assert hasattr(page, "settings_changed")


# ===================================================================
# 8. AdvancedSettingsPage 생성
# ===================================================================

class TestAdvancedSettingsPageCreation:
    """AdvancedSettingsPage 인스턴스 생성 검증"""

    def test_advanced_settings_page_creation(self, qtbot, app_state):
        """AdvancedSettingsPage가 에러 없이 생성된다."""
        _state, cm = app_state

        from gui.pages.advanced_settings_page import AdvancedSettingsPage
        page = AdvancedSettingsPage(cm)
        qtbot.addWidget(page)

        assert page is not None

    def test_advanced_settings_page_has_settings_changed(self, qtbot, app_state):
        """AdvancedSettingsPage에 settings_changed 시그널이 있다."""
        _state, cm = app_state

        from gui.pages.advanced_settings_page import AdvancedSettingsPage
        page = AdvancedSettingsPage(cm)
        qtbot.addWidget(page)

        assert hasattr(page, "settings_changed")


# ===================================================================
# 9. 모든 페이지가 같은 AppState를 공유
# ===================================================================

class TestAllPagesShareAppState:
    """모든 페이지가 동일한 AppState 참조를 사용하는지 검증"""

    def test_all_pages_share_app_state(self, qtbot, app_state):
        """HomePage, FormatStylePage, ParsingContentPage, AdvancedSettingsPage가
        모두 동일한 app_state 참조를 사용한다."""
        state, cm = app_state

        # GIVEN: 4개 페이지를 모두 생성
        from gui.pages.advanced_settings_page import AdvancedSettingsPage
        from gui.pages.format_style_page import FormatStylePage
        from gui.pages.home_page import HomePage
        from gui.pages.parsing_content_page import ParsingContentPage

        home = HomePage(cm)
        qtbot.addWidget(home)
        format_style = FormatStylePage(cm)
        qtbot.addWidget(format_style)
        parsing = ParsingContentPage(cm)
        qtbot.addWidget(parsing)
        advanced = AdvancedSettingsPage(cm)
        qtbot.addWidget(advanced)

        # THEN: 모든 페이지의 app_state가 동일한 객체이다
        assert home.app_state is state
        assert format_style.app_state is state
        assert parsing.app_state is state
        assert advanced.app_state is state

    def test_state_change_visible_across_pages(self, qtbot, app_state):
        """한 페이지에서 AppState를 변경하면 다른 페이지에서도 보인다."""
        _state, cm = app_state

        from gui.pages.format_style_page import FormatStylePage
        from gui.pages.home_page import HomePage

        home = HomePage(cm)
        qtbot.addWidget(home)
        format_page = FormatStylePage(cm)
        qtbot.addWidget(format_page)

        # WHEN: HomePage의 app_state를 통해 값 변경
        home.app_state.set("style_font_size", 20)

        # THEN: FormatStylePage의 app_state에서도 동일한 값을 읽을 수 있다
        assert format_page.app_state.get("style_font_size") == 20
