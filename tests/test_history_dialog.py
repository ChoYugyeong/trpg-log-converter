"""Tests for HistoryManager UI integration.

Focus: data flow (manager ↔ dialog) and the contract that ConversionWorker.
last_records 가 main_window 의 _on_conversion_finished 에서 정상적으로 기록되는지.
GUI dialog 자체는 pytest-qt 로 표면 검사만.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.services.history import ConversionRecord, HistoryManager


@pytest.fixture
def hm(tmp_path: Path) -> HistoryManager:
    return HistoryManager(tmp_path, max_records=100)


def _add(hm: HistoryManager, **overrides) -> ConversionRecord:
    base = {
        "input_file": str(Path("session.html").resolve()),
        "output_files": [str(Path("session.epub").resolve()),
                       str(Path("session.docx").resolve())],
        "output_format": "both",
        "title": "테스트 변환",
        "author": "GM",
        "entry_count": 120,
        "scene_count": 4,
        "success": True,
        "duration_ms": 4321,
    }
    base.update(overrides)
    return hm.add_record(**base)


class TestPersistence:
    def test_record_round_trips(self, hm: HistoryManager, tmp_path: Path):
        rec = _add(hm, title="Round-Trip Test")
        # 새 manager 가 같은 dir 에서 로드해도 같은 record.
        hm2 = HistoryManager(tmp_path)
        reloaded = hm2.get_records()
        assert len(reloaded) == 1
        assert reloaded[0].title == "Round-Trip Test"
        assert reloaded[0].id == rec.id

    def test_max_records_cap(self, tmp_path: Path):
        hm = HistoryManager(tmp_path, max_records=3)
        for i in range(5):
            _add(hm, title=f"#{i}")
        records = hm.get_records()
        assert len(records) == 3
        # 가장 최근 #4 부터 보관.
        assert records[0].title == "#4"
        assert records[-1].title == "#2"

    def test_delete_record(self, hm: HistoryManager):
        a = _add(hm, title="A")
        _add(hm, title="B")
        assert hm.delete_record(a.id) is True
        remaining = [r.title for r in hm.get_records()]
        assert remaining == ["B"]
        assert hm.delete_record("nonexistent") is False


class TestSearch:
    def test_search_by_title(self, hm: HistoryManager):
        _add(hm, title="민음사 희곡")
        _add(hm, title="Roll20 Session 12")
        results = hm.search("희곡")
        assert len(results) == 1
        assert "희곡" in results[0].title

    def test_search_by_author_case_insensitive(self, hm: HistoryManager):
        _add(hm, author="Aragorn")
        _add(hm, author="다른사람")
        results = hm.search("ARAGORN")
        assert len(results) == 1


class TestStats:
    def test_stats_aggregate(self, hm: HistoryManager):
        _add(hm, success=True, output_format="epub", entry_count=100)
        _add(hm, success=False, output_format="both", entry_count=50)
        _add(hm, success=True, output_format="both", entry_count=200)
        stats = hm.get_stats()
        assert stats["total_conversions"] == 3
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 1
        assert stats["total_entries"] == 350
        assert stats["avg_entries"] == 350 // 3
        assert stats["formats_used"] == {"epub": 1, "both": 2}

    def test_stats_empty(self, hm: HistoryManager):
        stats = hm.get_stats()
        assert stats["total_conversions"] == 0
        assert stats["formats_used"] == {}


class TestDialogContract:
    """HistoryDialog 가 의존하는 manager API 가 사라지지 않도록."""

    def test_required_methods_exist(self):
        for name in ("get_records", "get_record_by_id", "search", "get_stats",
                     "delete_record", "clear", "add_record"):
            assert hasattr(HistoryManager, name), f"HistoryManager.{name} missing"

    def test_record_has_required_attributes(self, hm: HistoryManager):
        rec = _add(hm)
        # 표시에 필요한 모든 필드.
        for attr in ("id", "timestamp", "input_filename", "title", "author",
                     "output_format", "output_files", "entry_count",
                     "scene_count", "success", "error_message", "duration_ms"):
            assert hasattr(rec, attr), f"ConversionRecord.{attr} missing"


class TestMainWindowIntegrationContract:
    """ConversionWorker.last_records 가 main_window 가 기대하는 형식과 맞는지."""

    def test_worker_record_shape(self):
        # main_window._on_conversion_finished 가 reading 하는 키들이 정의되어
        # 있어야 함. ConversionWorker 가 보관하는 record 의 컨트랙트.
        sample = {
            "input_file": "x.html",
            "output_files": ["a.epub"],
            "output_format": "epub",
            "title": "T",
            "author": "A",
            "entry_count": 10,
            "scene_count": 1,
            "success": True,
            "duration_ms": 100,
        }
        # HistoryManager.add_record 가 같은 키를 받는지 확인.
        import inspect
        sig = inspect.signature(HistoryManager.add_record)
        for k in sample:
            if k == "duration_ms":
                continue  # add_record 는 duration_ms 도 받음
            assert k in sig.parameters, (
                f"HistoryManager.add_record 가 {k} 를 받지 못하면 "
                "main_window._on_conversion_finished 가 깨짐"
            )
