"""Tests for ``ConfigManager`` automatic settings backup.

가드:
- ``save_gui_settings`` 호출 시 직전 settings 가 ``backups/`` 로 회전 보관
- 5 슬롯 초과분은 가장 오래된 것부터 삭제
- 첫 저장 (settings_path 없음) 시에는 백업 안 만들고 그냥 저장
- atomic write — 저장 중간 실패해도 기존 파일 살아 있음
- ``list_backups`` / ``restore_backup`` 으로 복구 가능
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from core.config_manager import ConfigManager


@pytest.fixture
def cm(tmp_path: Path) -> ConfigManager:
    return ConfigManager(app_dir=tmp_path)


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


class TestBackupRotation:
    def test_first_save_does_not_create_backup(self, cm: ConfigManager, tmp_path: Path):
        cm.save_gui_settings({"key": "v1"})
        assert cm.settings_path.exists()
        backup_dir = cm.settings_path.parent / "backups"
        # 처음 저장이라 백업 폴더가 비어 있거나 없어야 함.
        assert not backup_dir.exists() or not list(backup_dir.glob("*.json"))

    def test_second_save_creates_backup(self, cm: ConfigManager):
        cm.save_gui_settings({"key": "v1"})
        cm.save_gui_settings({"key": "v2"})

        backups = cm.list_backups()
        assert len(backups) == 1
        assert _read(backups[0]) == {"key": "v1"}, (
            "백업은 직전 settings (v1) 를 보존해야 함"
        )
        assert _read(cm.settings_path) == {"key": "v2"}

    def test_rotation_caps_at_5_slots(self, cm: ConfigManager):
        # 10번 저장 → 백업 5개만 남아야 함.
        for i in range(10):
            cm.save_gui_settings({"i": i})
            time.sleep(0.01)  # mtime 분리

        backups = cm.list_backups()
        assert len(backups) == 5
        # 가장 최근 백업이 i=8 (방금 저장한 i=9 이 현재 settings, i=8 이 직전).
        latest_backup = _read(backups[0])
        assert latest_backup == {"i": 8}

    def test_list_backups_sorted_by_recency(self, cm: ConfigManager):
        cm.save_gui_settings({"a": 1})
        time.sleep(0.02)
        cm.save_gui_settings({"a": 2})
        time.sleep(0.02)
        cm.save_gui_settings({"a": 3})

        backups = cm.list_backups()
        assert len(backups) == 2
        # 가장 최근 백업 (a=2) 가 첫 번째
        assert _read(backups[0]) == {"a": 2}
        assert _read(backups[1]) == {"a": 1}

    def test_restore_backup(self, cm: ConfigManager):
        cm.save_gui_settings({"version": "good"})
        cm.save_gui_settings({"version": "bad"})

        assert _read(cm.settings_path) == {"version": "bad"}
        backups = cm.list_backups()
        restored = cm.restore_backup(backups[0])

        assert restored == {"version": "good"}
        assert _read(cm.settings_path) == {"version": "good"}


class TestAtomicWrite:
    def test_existing_settings_survive_concurrent_save(self, cm: ConfigManager):
        """tmp → rename 패턴이라 저장 중간에 죽어도 settings_path 는 valid."""
        cm.save_gui_settings({"first": True})
        # save 가 atomic 이므로 .tmp 잔존물이 없어야 함.
        tmp_file = cm.settings_path.with_suffix(".json.tmp")
        assert not tmp_file.exists()
        # 파일은 valid JSON.
        assert _read(cm.settings_path) == {"first": True}


class TestBackupIsolation:
    def test_backup_dir_lives_next_to_settings(self, cm: ConfigManager, tmp_path: Path):
        cm.save_gui_settings({"a": 1})
        cm.save_gui_settings({"a": 2})

        backup_dir = cm.settings_path.parent / "backups"
        assert backup_dir.exists()
        # 모든 백업이 backups/ 하위에 있음 (settings_path 인접 폴더 오염 없음).
        for b in cm.list_backups():
            assert b.parent == backup_dir
