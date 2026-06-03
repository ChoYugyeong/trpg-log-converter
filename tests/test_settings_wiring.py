"""'설정이 저장되지만 변환 코드가 안 읽는' 죽은 옵션 회귀 방지 테스트.

merge_consecutive 버그와 동일 패턴(프로듀서는 키를 만들지만 소비자가 없던 것)을
재발 방지한다: 타이포그래피 줄간격/들여쓰기, 이미지 정렬/너비, 헤더 박스,
빈 대사 placeholder, 대사 구분자 래핑.
"""

from core.engine import format_session_title
from core.parsers.helpers import (
    _resolve_dialogue_brackets,
    apply_parsing_overrides,
)
from core.parsers.pipeline import filter_entries
from core.renderers.css import generate_css
from core.renderers.epub import entries_to_html


class TestDialogueBracketResolve:
    def test_kkoeswae(self):
        assert _resolve_dialogue_brackets({"dialogue_separator": "「 」 (꺾쇠)"}) == ("「", "」")

    def test_quotes(self):
        assert _resolve_dialogue_brackets({"dialogue_separator": '" " (따옴표)'}) == ('"', '"')

    def test_single_quotes(self):
        assert _resolve_dialogue_brackets({"dialogue_separator": "' ' (작은따옴표)"}) == ("'", "'")

    def test_none(self):
        assert _resolve_dialogue_brackets({"dialogue_separator": "없음"}) is None

    def test_empty(self):
        assert _resolve_dialogue_brackets({}) is None

    def test_custom_space_separated(self):
        result = _resolve_dialogue_brackets(
            {"dialogue_separator": "직접 입력", "dialogue_separator_custom": "[ ]"}
        )
        assert result == ("[", "]")

    def test_custom_two_chars(self):
        result = _resolve_dialogue_brackets(
            {"dialogue_separator": "직접 입력", "dialogue_separator_custom": "<>"}
        )
        assert result == ("<", ">")


class TestEmptyDialoguePlaceholder:
    def test_empty_substituted(self):
        entries = [{"type": "dialogue", "name": "제이크", "content": "   "}]
        config = {"dialogue": {"empty_dialogue": "……"}}
        result = apply_parsing_overrides(entries, config)
        assert result[0]["content"] == "……"

    def test_nonempty_untouched(self):
        entries = [{"type": "dialogue", "name": "제이크", "content": "안녕"}]
        config = {"dialogue": {"empty_dialogue": "……"}}
        result = apply_parsing_overrides(entries, config)
        assert result[0]["content"] == "안녕"

    def test_no_placeholder_no_change(self):
        entries = [{"type": "dialogue", "name": "제이크", "content": "  "}]
        result = apply_parsing_overrides(entries, {"dialogue": {"empty_dialogue": ""}})
        assert result[0]["content"] == "  "


class TestDialogueSeparatorWrapping:
    def test_wraps_unbracketed(self):
        entries = [{"type": "dialogue", "name": "제이크", "content": "안녕"}]
        config = {"style": {"dialogue_separator": "「 」 (꺾쇠)"}}
        result = apply_parsing_overrides(entries, config)
        assert result[0]["content"] == "「안녕」"

    def test_skips_already_bracketed(self):
        entries = [{"type": "dialogue", "name": "제이크", "content": "「안녕」"}]
        config = {"style": {"dialogue_separator": "「 」 (꺾쇠)"}}
        result = apply_parsing_overrides(entries, config)
        assert result[0]["content"] == "「안녕」"  # 중복 래핑 안 함

    def test_none_no_wrap(self):
        entries = [{"type": "dialogue", "name": "제이크", "content": "안녕"}]
        config = {"style": {"dialogue_separator": "없음"}}
        result = apply_parsing_overrides(entries, config)
        assert result[0]["content"] == "안녕"

    def test_narration_not_wrapped(self):
        entries = [{"type": "narration", "name": "", "content": "문이 열렸다"}]
        config = {"style": {"dialogue_separator": "「 」 (꺾쇠)"}}
        result = apply_parsing_overrides(entries, config)
        assert result[0]["content"] == "문이 열렸다"

    def test_custom_brackets(self):
        entries = [{"type": "dialogue", "name": "제이크", "content": "안녕"}]
        config = {
            "style": {
                "dialogue_separator": "직접 입력",
                "dialogue_separator_custom": "( )",
            }
        }
        result = apply_parsing_overrides(entries, config)
        assert result[0]["content"] == "(안녕)"


class TestCssTypographyWiring:
    def test_dialogue_line_height_applied(self):
        css = generate_css({"style": {"dialogue_line_height": 2.0}})
        assert "line-height: 2.0" in css

    def test_narration_indent_applied(self):
        css = generate_css({"style": {"narration_indent": 3.0}})
        assert "padding-left: 3.0em" in css

    def test_narration_line_height_applied(self):
        css = generate_css({"style": {"narration_line_height": 2.2}})
        assert "line-height: 2.2" in css

    def test_image_alignment_applied(self):
        css = generate_css({"images": {"alignment": "left"}})
        assert "text-align: left" in css

    def test_image_max_width_applied(self):
        css = generate_css({"images": {"max_width": 60}})
        assert "max-width: 60%" in css

    def test_header_box_applied(self):
        css = generate_css({"header": {"box": True, "box_color": "#abcdef"}})
        assert "#abcdef" in css

    def test_header_box_off_by_default(self):
        css = generate_css({"header": {"box": False}})
        # 박스 미사용 시 scene-title 에 background 선언이 추가되지 않아야 한다
        assert "border-radius: 6px" not in css

    def test_defaults_unchanged(self):
        """기본값에서는 기존 출력과 동일(줄간격 1.5/1.7, 들여쓰기 1.5em, 가운데, 100%)."""
        css = generate_css({})
        assert "line-height: 1.5" in css
        assert "line-height: 1.7" in css
        assert "padding-left: 1.5em" in css
        assert "text-align: center" in css
        assert "max-width: 100%" in css


class TestBaseFontScale:
    def test_scales_body_font_size(self):
        css = generate_css({"style": {"body_font_size": 10, "base_font_size": 2.0}})
        assert "font-size: 20" in css  # 10 * 2.0

    def test_default_scale_unchanged(self):
        css = generate_css({"style": {"body_font_size": 14, "base_font_size": 1.0}})
        assert "font-size: 14" in css


class TestQuoteAndDiceStyle:
    def test_quote_round_box(self):
        css = generate_css({"style": {"quote_style": "둥근 박스", "effect_bg": "#eeeeee"}})
        assert "border-radius" in css

    def test_quote_none_transparent(self):
        css = generate_css({"style": {"quote_style": "없음"}})
        assert "background: transparent" in css

    def test_dice_highlight(self):
        css = generate_css({"style": {"dice_style": "하이라이트"}})
        assert "#fffbe6" in css

    def test_dice_icon_prefixes(self):
        entries = [{"type": "dice", "name": "제이크", "content": "1d100 → 42"}]
        result = apply_parsing_overrides(entries, {"style": {"dice_icon": True}})
        assert result[0]["content"].startswith("🎲")

    def test_dice_icon_no_double(self):
        entries = [{"type": "dice", "name": "", "content": "🎲 1d100 → 42"}]
        result = apply_parsing_overrides(entries, {"style": {"dice_icon": True}})
        assert result[0]["content"].count("🎲") == 1

    def test_dice_style_hidden_filters(self):
        entries = [
            {"type": "dialogue", "name": "A", "content": "안녕"},
            {"type": "dice", "name": "A", "content": "1d100"},
        ]
        result = filter_entries(entries, {"style": {"dice_style": "숨김"}})
        assert all(e["type"] != "dice" for e in result)


class TestIncludeOOC:
    def test_double_paren_filtered_by_default(self):
        entries = [
            {"type": "dialogue", "name": "A", "content": "((잠깐 화장실))"},
            {"type": "dialogue", "name": "A", "content": "안녕하세요"},
        ]
        result = filter_entries(entries, {"content": {"include_ooc": False}})
        assert len(result) == 1
        assert result[0]["content"] == "안녕하세요"

    def test_ooc_kept_when_enabled(self):
        entries = [{"type": "dialogue", "name": "A", "content": "((메모))"}]
        result = filter_entries(entries, {"content": {"include_ooc": True}})
        assert len(result) == 1

    def test_in_character_paren_not_filtered(self):
        """단일 괄호 인-캐릭터 대사는 OOC 로 오탐하지 않는다."""
        entries = [{"type": "dialogue", "name": "A", "content": "(작게 속삭이며) 안녕"}]
        result = filter_entries(entries, {"content": {"include_ooc": False}})
        assert len(result) == 1


class TestEpubHeaderAndOrnament:
    def test_header_prefix_suffix(self):
        html = entries_to_html([], "장면 1", {"header": {"prefix": "【", "suffix": "】"}})
        assert "【장면 1】" in html

    def test_chapter_ornament_fallback(self):
        html = entries_to_html(
            [],
            "장면 1",
            {"divider": {"type": "사용 안 함"}, "style": {"chapter_ornament": "~~~ ✦ ~~~"}},
        )
        assert "chapter-ornament" in html
        assert "~~~ ✦ ~~~" in html


class TestCampaignSessionTitle:
    def test_format(self):
        assert format_session_title("Session {n}: {filename}", 3, "log3") == "Session 3: log3"

    def test_default_format(self):
        assert format_session_title("", 1, "a") == "Session 1: a"
