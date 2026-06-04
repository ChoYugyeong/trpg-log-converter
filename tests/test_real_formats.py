"""실제 export 양식(Roll20/Discord/Cocofolia) 더미 파일이 올바로 파싱되는지 검증.

각 플랫폼의 실제 HTML/텍스트 양식을 조사해 만든 sample_logs/realformat/* 더미를
파서에 통과시켜 분류(scene/dialogue/dice/narration/system)가 맞는지 확인한다.
"""

from pathlib import Path

from core.config import default_engine_config
from core.engine import ConversionEngine

FIX = Path(__file__).resolve().parent.parent / "sample_logs" / "realformat"


def _engine():
    cfg = default_engine_config()
    cfg["narration"]["users"] = ["-", "GM", "KP", "DM", "Keeper", "키퍼", "나레이터"]
    return ConversionEngine(cfg)


def _types(entries):
    return [e.get("type") for e in entries]


class TestRoll20RealFormat:
    def test_parses(self):
        ents = _engine().parse_file(str(FIX / "roll20_real.html"))
        assert ents, "엔트리가 비어있으면 안 됨"
        types = _types(ents)
        assert "scene" in types
        assert "dialogue" in types
        assert "dice" in types
        # '::' 시스템 행이 system 으로 분류돼야 한다(과거엔 dialogue 로 오분류)
        assert "system" in types
        # 기본(include_whisper=False)에선 hidden-message 귓속말은 제외된다
        joined = " ".join(e.get("content", "") for e in ents)
        assert "함정이 있다" not in joined

    def test_dialogue_speaker_extracted(self):
        ents = _engine().parse_file(str(FIX / "roll20_real.html"))
        dlg = [e for e in ents if e.get("type") == "dialogue"]
        assert any(e.get("name") == "아라곤" for e in dlg)


class TestDiscordRealFormat:
    def test_multiline_parsed(self):
        ents = _engine().parse_file(str(FIX / "discord_real.txt"))
        assert ents
        # 헤더/구분선/메타가 엔트리로 새지 않아야 한다
        joined = " ".join(e.get("content", "") for e in ents)
        assert "====" not in joined
        assert "Guild:" not in joined
        assert "Exported" not in joined
        # 타임스탬프가 이름으로 잘못 들어가지 않아야 한다
        for e in ents:
            assert "PM]" not in (e.get("name") or "")
            assert not (e.get("name") or "").startswith("[2024")

    def test_speaker_and_multiline_content(self):
        ents = _engine().parse_file(str(FIX / "discord_real.txt"))
        jake = [e for e in ents if e.get("name") == "제이크"]
        assert jake, "제이크 발언이 파싱돼야 함"
        # 멀티라인 본문이 합쳐졌는지
        assert any("둘러본다" in e.get("content", "") for e in jake)

    def test_scene_marker(self):
        ents = _engine().parse_file(str(FIX / "discord_real.txt"))
        assert any(e.get("type") == "scene" for e in ents)

    def test_ooc_filtered_by_default(self):
        ents = _engine().parse_file(str(FIX / "discord_real.txt"))
        joined = " ".join(e.get("content", "") for e in ents)
        assert "화장실" not in joined  # ((...)) OOC 는 기본 제외


class TestCocofoliaRealFormat:
    def test_inline_style_format_parsed(self):
        """firing_name_ 클래스가 없는 실제 inline-style 양식도 콜론 폴백으로 처리."""
        ents = _engine().parse_file(str(FIX / "cocofolia_real.html"))
        assert ents
        types = _types(ents)
        assert "scene" in types
        assert "dialogue" in types
        assert "dice" in types
        names = {e.get("name") for e in ents}
        assert "제이크" in names
        assert "미아" in names

    def test_channel_skip(self):
        ents = _engine().parse_file(str(FIX / "cocofolia_real.html"))
        joined = " ".join(e.get("content", "") for e in ents)
        assert "음료수" not in joined  # [잡담] 채널은 기본 skip

    def test_no_colon_span_format(self):
        """콜론 없이 이름 스팬 + 본문 스팬으로 나뉜 실제 변형도 화자/본문 분리."""
        ents = _engine().parse_file(str(FIX / "cocofolia_real.html"))
        doyun = [e for e in ents if e.get("name") == "도윤"]
        assert doyun, "콜론 없는 스팬 양식의 화자가 인식돼야 함"
        assert "콜론 없이" in doyun[0].get("content", "")
        # 이름이 본문에 합쳐지지 않아야 한다
        assert "도윤" not in doyun[0].get("content", "")
