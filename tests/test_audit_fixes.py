"""전체 코드 점검(2026-06)에서 발견된 '작동하지 않던' 항목들의 회귀 방지 테스트."""

import os
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

from core.config import default_engine_config
from core.engine import ConversionEngine, make_session_scene_entry
from core.layout import parse_page_format
from core.parsers.pipeline import filter_entries, split_into_scenes
from core.parsers.roll20 import _parse_tstamp, parse_roll20
from core.services.config_schema import validate_engine_config
from core.utils import safe_int


class TestEpubEmptyDocument:
    def test_empty_entries_no_crash(self):
        eng = ConversionEngine(default_engine_config())
        d = tempfile.mkdtemp()
        out = eng.create_epub([], os.path.join(d, "empty.epub"), "T", "GM")
        assert os.path.exists(out)

    def test_all_filtered_no_crash(self):
        cfg = default_engine_config()
        cfg["content"]["include_dice"] = False
        eng = ConversionEngine(cfg)
        entries = [{"type": "dice", "name": "A", "content": "1d100 → 5"}]
        filtered = filter_entries(entries, cfg)
        d = tempfile.mkdtemp()
        out = eng.create_epub(filtered, os.path.join(d, "f.epub"), "T", "GM")
        assert os.path.exists(out)


class TestMissingTypeKey:
    def test_renderers_tolerate_missing_type(self):
        eng = ConversionEngine(default_engine_config())
        entries = [{"content": "타입 키 없음"}]  # 'type' 누락
        d = tempfile.mkdtemp()
        # 크래시하지 않아야 한다
        eng.create_epub(entries, os.path.join(d, "a.epub"), "T", "GM")
        eng.create_docx(entries, os.path.join(d, "a.docx"), "T", "GM")


class TestRoll20SystemSpeaker:
    def test_colon_only_speaker_is_system(self):
        cfg = default_engine_config()
        soup = BeautifulSoup(
            '<div id="textchat"><div class="message system">'
            '<span class="by">::</span> Session ended</div></div>',
            "html.parser",
        )
        entries = parse_roll20(soup, cfg)
        assert entries
        assert entries[0]["type"] == "system"


class TestRoll20Timestamp:
    def test_parses_seconds(self):
        assert _parse_tstamp("2024-01-01 15:04:05") is not None
        assert _parse_tstamp("January 1, 2024 3:04:05PM") is not None
        assert _parse_tstamp("15:04:05") is not None

    def test_parses_minute_only(self):
        assert _parse_tstamp("2024-01-01 15:04") is not None


class TestCampaignSceneTitle:
    def test_explicit_empty_scene_kept(self):
        cfg = default_engine_config()
        cfg["chapter"]["scene_patterns"] = ["^■"]
        cfg["chapter"]["min_scene_entries"] = 1
        entries = [
            make_session_scene_entry("Session {n}: {filename}", 1, "fileA"),
            {"type": "scene", "content": "■ 장면 1", "name": "", "raw": "■ 장면 1"},
            {"type": "dialogue", "name": "A", "content": "안녕"},
        ]
        scenes = split_into_scenes(entries, cfg)
        titles = [s.get("title") for s in scenes]
        assert any("Session 1" in (t or "") for t in titles)


class TestSafeIntFloat:
    def test_float_value(self):
        assert safe_int(14.0, -1) == 14

    def test_float_string(self):
        assert safe_int("14.0", -1) == 14

    def test_suffixed_string(self):
        assert safe_int("85 (권장)", -1) == 85

    def test_garbage(self):
        assert safe_int("abc", -1) == -1


class TestSchemaFailurePreserves:
    def test_bad_field_preserves_other_user_settings(self):
        cfg = default_engine_config()
        cfg["narration"]["users"] = ["MyCustomGM"]
        cfg["output_format"] = 999  # wrong type → validation fails
        result = validate_engine_config(cfg)
        assert result["narration"]["users"] == ["MyCustomGM"]


class TestHistoryIdUnique:
    def test_rapid_adds_unique_ids(self):
        from core.services.history import HistoryManager

        hm = HistoryManager(Path(tempfile.mkdtemp()))
        ids = {
            hm.add_record("f.html", ["o.epub"], "epub", "T", "GM", 10, 2, True).id
            for _ in range(60)
        }
        assert len(ids) == 60


class TestCacheKeyConfig:
    def test_dialogue_style_change_invalidates(self):
        from core.services.cache import CacheService

        cs = CacheService(Path(tempfile.mkdtemp()))
        h1 = cs._get_config_hash({"dialogue": {"merge_consecutive": False}})
        h2 = cs._get_config_hash({"dialogue": {"merge_consecutive": True}})
        assert h1 != h2
        s1 = cs._get_config_hash({"style": {"dialogue_separator": "없음"}})
        s2 = cs._get_config_hash({"style": {"dialogue_separator": "「 」 (꺾쇠)"}})
        assert s1 != s2


class TestCustomPageFormat:
    def test_custom_size_parses(self):
        w, h = parse_page_format("사용자 정의 (120x180mm)")
        assert (w, h) == (120.0, 180.0)


class TestSceneTitleStripsMarker:
    def test_strips_leading_marker(self):
        from core.parsers.helpers import extract_scene_title

        assert extract_scene_title("■ 장면 1: 폐교") == "장면 1: 폐교"
        assert extract_scene_title("▶ Scene 2") == "Scene 2"

    def test_strips_decorative_dashes(self):
        from core.parsers.helpers import extract_scene_title

        assert extract_scene_title("───  장면 3  ───") == "장면 3"


class TestEpubPrefixEscaped:
    def test_narration_prefix_escaped(self):
        from core.renderers.epub import entries_to_html

        entries = [{"type": "narration", "name": "", "content": "문이 열렸다"}]
        html = entries_to_html(entries, None, {"style": {"narration_prefix": "<b>"}})
        assert "<b>문이" not in html  # 접두사가 마크업으로 해석되지 않아야
        assert "&lt;b&gt;" in html
