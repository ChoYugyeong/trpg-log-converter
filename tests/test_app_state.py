"""
AppState(반응형 상태 관리자) 테스트

AppState는 Pydantic V2 모델 기반 설정을 관리하며,
값 변경 시 Qt Signal을 방출하여 UI가 자동 업데이트됩니다.
"""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QObject

# ---------------------------------------------------------------------------
# 공통 fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def app_state(tmp_path, qapp):
    """AppState + ConfigManager 를 생성하고 BasePage에 주입한다.

    ``qapp`` 의존성: AppState 는 QObject 라서 QApplication 이 먼저 존재해야
    한다. 일부 test 만 qtbot 을 받아서 뒤늦게 QApplication 이 생기면 이전에
    parent 없이 만들어진 QObject 와 충돌해 Linux 에서 SIGABRT (exit 134)
    가 났던 회귀 방지.
    """
    from core.config_manager import ConfigManager
    from gui.pages.base_page import BasePage
    from gui.state import AppState

    cm = ConfigManager(app_dir=tmp_path)
    state = AppState(cm)
    BasePage.set_app_state(state)
    return state, cm


# ===================================================================
# 1. get / set 기본 동작
# ===================================================================


class TestGetSet:
    """AppState.get / set 기본 동작 검증"""

    def test_get_set(self, app_state):
        """set()으로 저장한 값을 get()으로 그대로 읽어올 수 있다."""
        # GIVEN: 초기화된 AppState
        state, _ = app_state

        # WHEN: 키에 값을 설정한다
        state.set("style_font_size", 18)

        # THEN: 같은 키로 동일한 값을 읽을 수 있다
        assert state.get("style_font_size") == 18

    def test_get_default(self, app_state):
        """존재하지 않는 키에 대해 default를 반환한다."""
        state, _ = app_state

        # WHEN/THEN: 알 수 없는 키에 기본값 지정
        assert state.get("nonexistent_key", "fallback") == "fallback"

    def test_set_same_value_no_change(self, app_state, qtbot):
        """동일한 값을 다시 설정하면 changed Signal이 방출되지 않는다."""
        state, _ = app_state

        # GIVEN: 현재 값을 확인
        current = state.get("style_font_size")

        # WHEN: 동일한 값을 다시 설정
        # THEN: changed Signal이 방출되지 않아야 한다
        signals_received = []
        state.changed.connect(lambda k, v: signals_received.append((k, v)))
        state.set("style_font_size", current)
        assert len(signals_received) == 0


# ===================================================================
# 2. Signal 방출
# ===================================================================


class TestSignalEmission:
    """changed / group_changed Signal 방출 검증"""

    def test_signal_emission(self, app_state, qtbot):
        """값 변경 시 changed(key, value) Signal이 방출된다."""
        state, _ = app_state

        # GIVEN: Signal을 수신할 준비
        received = []
        state.changed.connect(lambda k, v: received.append((k, v)))

        # WHEN: 새로운 값을 설정
        state.set("style_font_size", 20)

        # THEN: changed Signal이 (key, value) 쌍으로 방출된다
        assert ("style_font_size", 20) in received

    def test_group_changed(self, app_state, qtbot):
        """style 그룹 키 변경 시 group_changed('style')이 방출된다."""
        state, _ = app_state

        # GIVEN: group_changed Signal 수신 준비
        groups = []
        state.group_changed.connect(lambda g: groups.append(g))

        # WHEN: style 그룹에 속한 키를 변경
        state.set("style_font_size", 22)

        # THEN: 'style' 그룹 변경 Signal이 방출된다
        assert "style" in groups


# ===================================================================
# 3. 배치 업데이트
# ===================================================================


class TestBatchUpdate:
    """batch_update 컨텍스트 매니저 검증"""

    def test_batch_update(self, app_state, qtbot):
        """batch_update 내에서 같은 그룹의 여러 set()은 group_changed를 1회만 방출한다."""
        state, _ = app_state

        # GIVEN: group_changed 수신 카운터
        group_counts = {}

        def on_group(g):
            group_counts[g] = group_counts.get(g, 0) + 1

        state.group_changed.connect(on_group)

        # WHEN: batch 내에서 style 그룹 키 2개를 변경
        with state.batch_update():
            state.set("style_font_size", 16)
            state.set("style_line_height", 1.8)

        # THEN: group_changed('style')는 정확히 1회만 방출
        assert group_counts.get("style", 0) == 1

    def test_batch_update_multiple_groups(self, app_state, qtbot):
        """batch_update 내에서 서로 다른 그룹 키 변경 시 각 그룹당 1회씩 방출된다."""
        state, _ = app_state

        groups = []
        state.group_changed.connect(lambda g: groups.append(g))

        # WHEN: style 그룹과 font 그룹 키를 동시에 변경
        with state.batch_update():
            state.set("style_font_size", 15)
            state.set("epub_body_font", "'Noto Serif KR', serif")

        # THEN: 'style'과 'font' 각 1회씩 방출
        assert groups.count("style") == 1
        assert groups.count("font") == 1

    def test_batch_changed_signals_emitted(self, app_state, qtbot):
        """batch_update 종료 시 개별 changed Signal도 모두 방출된다."""
        state, _ = app_state

        received = []
        state.changed.connect(lambda k, v: received.append(k))

        with state.batch_update():
            state.set("style_font_size", 13)
            state.set("style_line_height", 2.0)

        # THEN: 두 키 모두 changed로 방출
        assert "style_font_size" in received
        assert "style_line_height" in received


# ===================================================================
# 4. 미리보기 설정
# ===================================================================


class TestPreviewSettings:
    """get_preview_settings() 반환값 검증"""

    def test_get_preview_settings(self, app_state):
        """get_preview_settings()는 DocumentPreview에 필요한 키를 포함한 dict를 반환한다."""
        state, _ = app_state

        # WHEN: 미리보기 설정을 요청
        preview = state.get_preview_settings()

        # THEN: 필수 키가 모두 존재한다
        expected_keys = {
            "dialogue_color",
            "narration_color",
            "font_family",
            "font_size",
            "line_height",
            "scene_marker",
            "narration_prefix",
            "narrators",
            "body_bg",
            "name_color",
            "name_bold",
            "separator",
        }
        assert expected_keys.issubset(set(preview.keys())), (
            f"누락된 키: {expected_keys - set(preview.keys())}"
        )

    def test_preview_settings_types(self, app_state):
        """미리보기 설정 값의 타입이 올바른지 확인한다."""
        state, _ = app_state
        preview = state.get_preview_settings()

        # THEN: 주요 값 타입 검증
        assert isinstance(preview["font_size"], (int, float))
        assert isinstance(preview["line_height"], (int, float))
        assert isinstance(preview["name_bold"], bool)
        assert isinstance(preview["narrators"], str)


# ===================================================================
# 5. save / load 영속화
# ===================================================================


class TestSaveLoad:
    """save() → load() 영속화 검증"""

    def test_save_load(self, app_state):
        """save() 후 load() 시 변경된 값이 유지된다."""
        state, _cm = app_state

        # GIVEN: 값을 변경
        state.set("style_font_size", 20)
        state.set("title", "테스트 제목")

        # WHEN: 저장 후 다시 로드
        state.save()
        state.load()

        # THEN: 변경된 값이 보존된다
        assert state.get("style_font_size") == 20
        assert state.get("title") == "테스트 제목"

    def test_save_persists_to_file(self, app_state, tmp_path):
        """save()가 gui_settings.json 파일에 기록한다."""
        state, _cm = app_state

        # WHEN: 값 설정 후 저장
        state.set("author", "테스트 저자")
        state.save()

        # THEN: JSON 파일이 존재하고 올바른 값을 포함한다
        import json

        settings_path = tmp_path / "gui_settings.json"
        assert settings_path.exists()
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("author") == "테스트 저자"


# ===================================================================
# 6. reset_to_defaults
# ===================================================================


class TestResetToDefaults:
    """reset_to_defaults() 검증"""

    def test_reset_to_defaults(self, app_state, qtbot):
        """reset_to_defaults()는 모든 값을 기본값으로 초기화하고 reset Signal을 방출한다."""
        state, _ = app_state

        # GIVEN: 기본값과 다른 값으로 변경
        state.set("style_font_size", 22)
        state.set("title", "커스텀 제목")

        # WHEN: 기본값으로 초기화
        with qtbot.waitSignal(state.reset, timeout=1000):
            state.reset_to_defaults()

        # THEN: 기본값으로 복원된다
        assert state.get("style_font_size") == 14  # Pydantic 모델 기본값
        assert state.get("title") == "TRPG 리플레이"  # HomeSettings 기본값


# ===================================================================
# 7. is_preview_group
# ===================================================================


class TestIsPreviewGroup:
    """is_preview_group() 그룹 분류 검증"""

    @pytest.mark.parametrize("group", ["style", "font", "decoration", "cover", "basic"])
    def test_preview_groups_return_true(self, group):
        """미리보기 갱신이 필요한 그룹은 True를 반환한다."""
        from gui.state import AppState

        # WHEN/THEN: 미리보기 관련 그룹
        assert AppState.is_preview_group(group) is True

    @pytest.mark.parametrize("group", ["output", "advanced", "scene", "parsing", "content"])
    def test_non_preview_groups_return_false(self, group):
        """미리보기 갱신이 불필요한 그룹은 False를 반환한다."""
        from gui.state import AppState

        # WHEN/THEN: 미리보기와 무관한 그룹
        assert AppState.is_preview_group(group) is False


# ===================================================================
# 8. get_group_for_key
# ===================================================================


class TestGetGroupForKey:
    """get_group_for_key() 키-그룹 매핑 검증"""

    @pytest.mark.parametrize(
        "key,expected_group",
        [
            ("style_font_size", "style"),
            ("style_line_height", "style"),
            ("epub_body_font", "font"),
            ("include_cover", "cover"),
            ("divider_type", "decoration"),
            ("include_dice", "content"),
            ("split_mode", "scene"),
            ("name_max_length", "advanced"),
            ("platform", "basic"),
            ("title", "basic"),
            ("epub_page_format", "output"),
            ("custom_separator_type", "parsing"),
        ],
    )
    def test_get_group_for_key(self, key, expected_group):
        """각 키가 올바른 그룹에 매핑된다."""
        from gui.state import AppState

        # WHEN: 키에 대한 그룹을 조회
        group = AppState.get_group_for_key(key)

        # THEN: 기대하는 그룹과 일치한다
        assert group == expected_group

    def test_unknown_key_returns_unknown(self):
        """알 수 없는 키는 'unknown' 그룹을 반환한다."""
        from gui.state import AppState

        assert AppState.get_group_for_key("nonexistent_key_xyz") == "unknown"
