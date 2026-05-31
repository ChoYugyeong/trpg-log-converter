"""Regression tests for ``core.renderers.toc_filter``.

User-stated behavior we are protecting:

* By default (no toc options), filter returns all scenes — zero regression to
  existing books.
* ``toc.scene_only=True`` hides auto-titled scenes (those created from
  ``split_by_count``, fallback ``장면 N`` 명칭, 또는 system noise 매치).
* ``toc.exclude_patterns`` 의 각 정규식이 매칭되는 씬 제목을 숨김.
* 빈 정규식이나 잘못된 정규식은 경고만 찍고 통과해야 함 (사용자 입력 보호).
* 원본 인덱스가 유지돼 ``chapter_{N}.xhtml`` 파일명이 깨지지 않음.

이 박제가 깨지면 빌드 차단.
"""

from __future__ import annotations

import pytest

from core.parsers.pipeline import split_by_count, split_by_scene
from core.renderers.toc_filter import filter_toc_scenes


def _scene(title: str, auto: bool, n: int = 50):
    return {
        "title": title,
        "entries": [{"content": f"line {i}"} for i in range(n)],
        "auto_title": auto,
    }


class TestDefaults:
    def test_no_options_returns_all(self):
        scenes = [
            _scene("Scene 1 — 숲의 입구", auto=False),
            _scene("장면 2", auto=True),
            _scene("Main Process Started", auto=False),
        ]
        result = filter_toc_scenes(scenes, {})
        assert [idx for idx, _ in result] == [0, 1, 2], "default should keep all scenes"


class TestSceneOnlyFlag:
    def test_scene_only_drops_auto(self):
        scenes = [
            _scene("Scene 1 — 숲의 입구", auto=False),
            _scene("장면 2", auto=True),
            _scene("Scene 3 — 동굴", auto=False),
        ]
        result = filter_toc_scenes(scenes, {"toc": {"scene_only": True}})
        kept = [scene["title"] for _, scene in result]
        assert kept == ["Scene 1 — 숲의 입구", "Scene 3 — 동굴"]

    def test_scene_only_preserves_original_index(self):
        scenes = [
            _scene("장면 1", auto=True),  # idx 0 — drop
            _scene("정찰", auto=False),  # idx 1 — keep
            _scene("장면 3", auto=True),  # idx 2 — drop
            _scene("결투", auto=False),  # idx 3 — keep
        ]
        result = filter_toc_scenes(scenes, {"toc": {"scene_only": True}})
        # chapter_2.xhtml 과 chapter_4.xhtml 로 링크 가야 함.
        assert [idx for idx, _ in result] == [1, 3]


class TestExcludePatterns:
    def test_pattern_blacklist_drops_system_noise(self):
        scenes = [
            _scene("Scene 1 — 숲의 입구", auto=False),
            _scene("Main Process Started", auto=False),
            _scene("System Load", auto=False),
            _scene("Scene 2 — 동굴", auto=False),
        ]
        result = filter_toc_scenes(
            scenes,
            {
                "toc": {
                    "exclude_patterns": [r"main\s*process", r"^system"],
                }
            },
        )
        kept = [scene["title"] for _, scene in result]
        assert kept == ["Scene 1 — 숲의 입구", "Scene 2 — 동굴"]

    def test_case_insensitive(self):
        scenes = [_scene("MAIN PROCESS", auto=False)]
        result = filter_toc_scenes(
            scenes,
            {
                "toc": {
                    "exclude_patterns": ["main process"],
                }
            },
        )
        assert result == []

    def test_invalid_regex_logged_but_not_fatal(self, caplog):
        scenes = [_scene("normal title", auto=False)]
        with caplog.at_level("WARNING"):
            result = filter_toc_scenes(
                scenes,
                {
                    "toc": {
                        "exclude_patterns": ["[unclosed", "valid"],
                    }
                },
            )
        # invalid 는 무시, valid 는 매치 안 됨 → 원본 유지.
        assert len(result) == 1
        assert any("정규식 오류" in r.message for r in caplog.records)

    def test_empty_pattern_strings_ignored(self):
        scenes = [_scene("kept", auto=False)]
        result = filter_toc_scenes(
            scenes,
            {
                "toc": {
                    "exclude_patterns": ["", None, "  "],
                }
            },
        )
        assert len(result) == 1


class TestMinEntries:
    def test_short_scene_dropped(self):
        scenes = [
            _scene("substantive", auto=False, n=20),
            _scene("one-liner", auto=False, n=2),
            _scene("medium", auto=False, n=10),
        ]
        result = filter_toc_scenes(scenes, {"toc": {"min_entries": 5}})
        kept = [scene["title"] for _, scene in result]
        assert kept == ["substantive", "medium"]


class TestCombinedRules:
    def test_all_filters_compose(self):
        scenes = [
            _scene("Scene 1 — real", auto=False, n=100),
            _scene("장면 2", auto=True, n=100),  # drop: auto
            _scene("System Init", auto=False, n=100),  # drop: pattern
            _scene("Tiny Scene", auto=False, n=2),  # drop: min_entries
            _scene("Scene 5 — long real", auto=False, n=100),
        ]
        result = filter_toc_scenes(
            scenes,
            {
                "toc": {
                    "scene_only": True,
                    "exclude_patterns": ["^system"],
                    "min_entries": 10,
                }
            },
        )
        kept = [scene["title"] for _, scene in result]
        assert kept == ["Scene 1 — real", "Scene 5 — long real"]


# ---------------------------------------------------------------------------
# Pipeline integration — make sure split_by_scene / split_by_count set
# the auto_title field so toc_filter can act on it.
# ---------------------------------------------------------------------------


class TestPipelineMarksAutoTitle:
    def test_split_by_count_marks_all_auto(self):
        entries = [{"type": "say", "content": f"l{i}"} for i in range(20)]
        scenes = split_by_count(entries, {"entries_per_chapter": 5})
        assert all(s.get("auto_title") is True for s in scenes)

    def test_split_by_scene_marks_extracted_as_not_auto(self):
        entries = [
            {"type": "scene", "content": "Scene 1 — 진짜 제목"},
            {"type": "say", "content": "안녕"},
            {"type": "scene", "content": "─" * 5},  # 비어있는 제목 → auto fallback
            {"type": "say", "content": "후속"},
        ]
        scenes = split_by_scene(
            entries,
            {
                "scene_patterns": [r"^Scene", r"^─"],
                "min_entries": 1,
                "title_format": "장면 {n}",
                "extract_scene_title": True,
            },
        )
        # 첫 씬: explicit, 두번째: auto fallback ("장면 2").
        assert scenes[0]["auto_title"] is False
        assert scenes[1]["auto_title"] is True
