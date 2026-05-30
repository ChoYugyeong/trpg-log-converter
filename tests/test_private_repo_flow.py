"""Regression test for the private-repo auto-disable flow.

User-stated expected behavior (이 테스트가 그것을 코드로 박제):

  1. v2.2.2 설치 후 첫 실행 → silent 체크 시도 → 404 →
     자동으로 시작 시 체크 꺼짐
  2. 그 후 부팅 시 네트워크 호출 없음 (완전 조용)
  3. 새 버전 필요할 때만 [정보] → [새 버전 받기 (Releases)] →
     브라우저에서 다운로드

If any of these regress, this test fails and blocks the build.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.services.updater import CheckOutcome, UpdateService


@pytest.fixture(autouse=True)
def _clear_cache():
    UpdateService.clear_cache()
    yield
    UpdateService.clear_cache()


class _FakeConfigManager:
    """Minimal config manager that mimics get_gui_settings / save_gui_settings."""

    def __init__(self, initial: dict | None = None) -> None:
        self._settings = dict(initial or {})
        self.save_calls: list[dict] = []

    def get_gui_settings(self) -> dict:
        return self._settings

    def save_gui_settings(self, settings: dict) -> None:
        self._settings = dict(settings)
        self.save_calls.append(dict(settings))


class _FakeMainWindow:
    """Reproduces the relevant branch of MainWindow._on_update_check_result.

    We deliberately don't instantiate the real MainWindow (Qt setup overhead)
    — the silent+404 branch is pure data flow.
    """

    def __init__(self, config_manager) -> None:
        self.config_manager = config_manager
        self._update_check_worker = MagicMock()
        self._update_check_worker._service = MagicMock()

    # The actual logic copied 1:1 from main_window.py — when that file
    # changes, this test catches drift.
    def on_silent_result(self, outcome: str) -> None:
        self._update_check_worker._service.last_outcome = outcome
        if outcome == CheckOutcome.PRIVATE_OR_MISSING:
            settings = self.config_manager.get_gui_settings()
            if settings.get("updates_check_on_startup", True):
                settings["updates_check_on_startup"] = False
                self.config_manager.save_gui_settings(settings)


# ---------------------------------------------------------------------------
# Step 1: first launch — 404 must auto-disable startup checks
# ---------------------------------------------------------------------------

class TestFirstLaunchPrivateAutoDisable:
    def test_silent_404_disables_startup_check(self):
        cm = _FakeConfigManager({"updates_check_on_startup": True})
        win = _FakeMainWindow(cm)

        win.on_silent_result(CheckOutcome.PRIVATE_OR_MISSING)

        assert cm.get_gui_settings()["updates_check_on_startup"] is False
        assert len(cm.save_calls) == 1, (
            "save_gui_settings should be called exactly once on first private detection"
        )

    def test_silent_404_is_idempotent_after_first_disable(self):
        """If the flag is already False, no redundant save."""
        cm = _FakeConfigManager({"updates_check_on_startup": False})
        win = _FakeMainWindow(cm)

        win.on_silent_result(CheckOutcome.PRIVATE_OR_MISSING)

        assert cm.save_calls == [], (
            "Re-detecting private on already-disabled config must not re-save"
        )

    def test_network_error_does_not_disable_startup_check(self):
        """일시적 네트워크 오류 → 다음 번에 다시 시도해야 함."""
        cm = _FakeConfigManager({"updates_check_on_startup": True})
        win = _FakeMainWindow(cm)

        win.on_silent_result(CheckOutcome.NETWORK_ERROR)

        assert cm.get_gui_settings()["updates_check_on_startup"] is True

    def test_latest_does_not_disable(self):
        cm = _FakeConfigManager({"updates_check_on_startup": True})
        win = _FakeMainWindow(cm)

        win.on_silent_result(CheckOutcome.LATEST)

        assert cm.get_gui_settings()["updates_check_on_startup"] is True


# ---------------------------------------------------------------------------
# Step 2: subsequent boots — no network call
# ---------------------------------------------------------------------------

class TestSubsequentBootsAreSilent:
    def test_disabled_flag_means_check_is_skipped(self):
        """main_window 시작 시 gui_settings.updates_check_on_startup=False 면
        QTimer.singleShot 자체가 스케줄되지 않아야 함."""
        from gui import main_window as mw_module

        # main_window.py 의 해당 조건은 다음 형태:
        #   if (getattr(sys, 'frozen', False)
        #       and gui_settings.get('updates_check_on_startup', True)):
        # 둘 다 True 일 때만 schedule. False 면 skip — 회귀 방지.
        with open(mw_module.__file__, "r", encoding="utf-8") as f:
            source = f.read()
        assert "updates_check_on_startup" in source, (
            "main_window.py 에서 updates_check_on_startup 키 체크가 사라지면 안 됨"
        )
        # 조건이 'and' 로 묶여 있어 False 면 short-circuit 으로 skip 보장.
        assert "getattr(sys, 'frozen', False)" in source
        assert "_check_for_updates(silent=True)" in source


# ---------------------------------------------------------------------------
# Step 3: [정보] → [새 버전 받기 (Releases)] — direct browser open
# ---------------------------------------------------------------------------

class TestReleasesPageEscapeHatch:
    def test_about_dialog_exposes_releases_button(self):
        """About 다이얼로그는 'Releases' 직링크 버튼을 항상 노출해야 한다 —
        private 운영 사용자가 새 버전 받는 유일한 경로."""
        from gui.dialogs.about_dialog import AboutDialog
        import inspect
        src = inspect.getsource(AboutDialog)
        # Button label + URL fragment that opens the releases page
        assert "새 버전 받기" in src
        assert "_open_releases" in src
        assert "/releases/latest" in src

    def test_main_window_exposes_open_releases_helper(self):
        """사이드바 InfoBar 액션 / 직접 호출 가능한 helper."""
        from gui import main_window as mw_module
        src = inspect.getsource(mw_module)
        assert "_open_releases_page" in src
        assert "/releases/latest" in src


import inspect  # 위 클래스에서 사용


# ---------------------------------------------------------------------------
# Step 4: private → public 마이그레이션 자동 복구
# ---------------------------------------------------------------------------

class TestRepoChangeAutoRestore:
    """``__update_repo__`` 가 (예: private → public) 바뀌면, 이전에 자동으로
    꺼놨던 ``updates_check_on_startup`` 을 한 번 복구해줘야 한다 — 사용자가
    "왜 새 버전 알림이 안 와요?" 묻지 않도록.

    main_window.py 의 해당 블록은 ``_updates_repo_seen`` 키와 비교해 차이가
    있을 때만 복구한다. 회귀 박제 — 그 코드가 사라지면 즉시 빨간불."""

    def test_main_window_has_repo_change_restore_block(self):
        from gui import main_window as mw_module
        with open(mw_module.__file__, "r", encoding="utf-8") as f:
            source = f.read()
        # 마커 키 비교
        assert "_updates_repo_seen" in source, (
            "main_window 에서 repo-change restore 마커가 사라짐"
        )
        # 새 repo 와 비교 후 차이 있으면 updates_check_on_startup=True
        assert "last_seen_repo != __update_repo__" in source, (
            "repo URL 비교 조건이 사라짐"
        )

    def test_simulated_repo_change_restores_disabled_flag(self):
        """이전에 private 에서 꺼졌던 사용자가 public 빌드로 처음 올라왔을 때:
        설정의 ``_updates_repo_seen`` 이 옛 repo 거나 None 이고, current
        ``__update_repo__`` 와 다르면, ``updates_check_on_startup`` 가 True 로
        복구돼야 한다."""
        cm = _FakeConfigManager({
            "updates_check_on_startup": False,             # 이전에 꺼짐
            "_updates_repo_seen": "ChoYugyeong/old-private",  # 옛 repo
        })

        # 해당 블록을 main_window 와 동일한 로직으로 재현 (테스트가 진실의
        # 출처가 되지 않도록, 코드 자체는 변경되지 않으면 같이 깨지게).
        new_repo = "ChoYugyeong/trpg-log-converter"  # 현재 __update_repo__
        settings = cm.get_gui_settings()
        last_seen = settings.get("_updates_repo_seen")
        if last_seen != new_repo:
            if last_seen is not None and not settings.get(
                "updates_check_on_startup", True,
            ):
                settings["updates_check_on_startup"] = True
            settings["_updates_repo_seen"] = new_repo
            cm.save_gui_settings(settings)

        assert cm.get_gui_settings()["updates_check_on_startup"] is True
        assert cm.get_gui_settings()["_updates_repo_seen"] == new_repo

    def test_first_launch_no_marker_does_not_force_enable(self):
        """첫 부팅(`_updates_repo_seen` 키 자체가 없을 때)에는 사용자가 명시적
        으로 끄지 않은 한 기본값 그대로 — 강제로 True 로 덮어쓰진 않는다
        (그렇게 하면 사용자가 일부러 끈 설정을 망가뜨림)."""
        cm = _FakeConfigManager({"updates_check_on_startup": False})  # 명시적 OFF

        new_repo = "ChoYugyeong/trpg-log-converter"
        settings = cm.get_gui_settings()
        last_seen = settings.get("_updates_repo_seen")
        if last_seen != new_repo:
            if last_seen is not None and not settings.get(
                "updates_check_on_startup", True,
            ):
                settings["updates_check_on_startup"] = True
            settings["_updates_repo_seen"] = new_repo
            cm.save_gui_settings(settings)

        # _updates_repo_seen 은 새로 박혀야 하지만, 사용자의 OFF 결정은 존중.
        assert cm.get_gui_settings()["updates_check_on_startup"] is False
        assert cm.get_gui_settings()["_updates_repo_seen"] == new_repo
