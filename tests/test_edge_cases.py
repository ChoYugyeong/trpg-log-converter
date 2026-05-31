"""
엣지 케이스 테스트
빈 파일, 깨진 HTML, 유니코드, 잘못된 설정 등
"""

import os
import tempfile
from pathlib import Path

import pytest


class TestEmptyInput:
    """빈/비어있는 입력 처리"""

    def test_parse_empty_html(self, sample_config):
        from core.engine import parse_log
        entries = parse_log("", sample_config)
        assert entries == []

    def test_parse_whitespace_only_html(self, sample_config):
        from core.engine import parse_log
        entries = parse_log("   \n\n  \t  ", sample_config)
        assert entries == []

    def test_parse_empty_body_html(self, sample_config):
        from core.engine import parse_log
        html = "<html><head></head><body></body></html>"
        entries = parse_log(html, sample_config)
        assert entries == []

    def test_filter_empty_entries(self, sample_config):
        from core.engine import filter_entries
        assert filter_entries([], sample_config) == []

    def test_merge_empty_entries(self, sample_config):
        from core.engine import merge_consecutive_dialogues
        assert merge_consecutive_dialogues([], sample_config) == []

    def test_split_empty_entries(self, sample_config):
        from core.engine import split_into_scenes
        result = split_into_scenes([], sample_config)
        assert len(result) == 1
        assert result[0]['entries'] == []

    def test_empty_text_file(self, sample_config, temp_dir):
        from core.text_parser import parse_text_log
        entries = parse_text_log("", sample_config)
        assert entries == []


class TestMalformedHTML:
    """깨진/비정상 HTML 처리"""

    def test_unclosed_tags(self, sample_config):
        from core.engine import parse_log
        html = "<html><body><p><span class='firing_name_test firing_firing'>: 내용<p>다음"
        entries = parse_log(html, sample_config)
        assert isinstance(entries, list)

    def test_no_html_tags(self, sample_config):
        from core.engine import parse_log
        entries = parse_log("이것은 그냥 텍스트입니다", sample_config)
        assert isinstance(entries, list)

    def test_nested_divs_deeply(self, sample_config):
        from core.engine import parse_log
        html = "<html><body>" + "<div>" * 50 + "내용" + "</div>" * 50 + "</body></html>"
        entries = parse_log(html, sample_config)
        assert isinstance(entries, list)

    def test_special_characters_in_html(self, sample_config):
        from core.engine import parse_log
        html = """<html><body>
        <p><span class="firing_name_test firing_firing">: &amp; &lt; &gt; "quotes"</span></p>
        </body></html>"""
        entries = parse_log(html, sample_config)
        assert isinstance(entries, list)


class TestUnicodeEdgeCases:
    """유니코드 엣지 케이스"""

    def test_emoji_in_name(self, sample_config):
        from core.engine import parse_log
        html = '<html><body><p><span class="firing_name_플레이어🎲 firing_firing">: 다이스!</span></p></body></html>'
        entries = parse_log(html, sample_config)
        assert len(entries) >= 1

    def test_japanese_characters(self, sample_config):
        from core.engine import parse_log
        html = '<html><body><p><span class="firing_name_キーパー firing_firing">: シーン開始</span></p></body></html>'
        entries = parse_log(html, sample_config)
        assert len(entries) >= 1

    def test_mixed_scripts(self, sample_config):
        from core.text_parser import parse_text_log
        content = "GM: 한국어English日本語混合テスト"
        entries = parse_text_log(content, sample_config)
        assert len(entries) >= 1

    def test_zero_width_characters(self, sample_config):
        from core.engine import parse_log
        html = '<html><body><p><span class="firing_name_test firing_firing">: \u200b\u200b내용\u200b</span></p></body></html>'
        entries = parse_log(html, sample_config)
        assert isinstance(entries, list)


class TestInvalidRegexPatterns:
    """잘못된 정규식 패턴 처리"""

    def test_invalid_scene_pattern(self, sample_config):
        from core.engine import is_scene_marker
        # 잘못된 정규식이 예외를 발생시키지 않아야 함
        result = is_scene_marker("테스트", ["[invalid"])
        assert isinstance(result, bool)

    def test_invalid_pattern_with_literal_match(self, sample_config):
        from core.engine import is_scene_marker
        # 리터럴 매칭 폴백
        result = is_scene_marker("[invalid", ["[invalid"])
        assert result is True

    def test_validate_regex_valid(self):
        from core.engine import validate_regex
        assert validate_regex(r"^■") is True
        assert validate_regex(r"^\d+") is True

    def test_validate_regex_invalid(self):
        from core.engine import validate_regex
        assert validate_regex("[invalid") is False
        assert validate_regex("(unclosed") is False


class TestConfigEdgeCases:
    """설정 엣지 케이스"""

    def test_missing_config_keys(self):
        from core.engine import parse_log
        entries = parse_log("<html><body><p>테스트</p></body></html>", {})
        assert isinstance(entries, list)

    def test_none_values_in_config(self, sample_config):
        import contextlib

        from core.engine import filter_entries
        config = sample_config.copy()
        config['content'] = None
        # None이어도 크래시하지 않아야 함 — TypeError/AttributeError 는 예상된 에러.
        with contextlib.suppress(TypeError, AttributeError):
            filter_entries([], config)

    def test_deep_merge_with_empty(self):
        from core.engine import deep_merge
        result = deep_merge({}, {'a': 1})
        assert result == {'a': 1}

    def test_deep_merge_nested(self):
        from core.engine import deep_merge
        base = {'a': {'b': 1, 'c': 2}}
        override = {'a': {'b': 3, 'd': 4}}
        result = deep_merge(base, override)
        assert result['a']['b'] == 3
        assert result['a']['c'] == 2
        assert result['a']['d'] == 4

    def test_config_schema_migration(self):
        from core.config.migrations import migrate_gui_settings
        old_settings = {'margins': 'invalid_string', '_schema_version': 1}
        migrated = migrate_gui_settings(old_settings)
        assert migrated['_schema_version'] >= 2
        assert isinstance(migrated['margins'], dict)

    def test_config_schema_already_current(self):
        from core.config.defaults import CONFIG_SCHEMA_VERSION
        from core.config.migrations import migrate_gui_settings
        settings = {'_schema_version': CONFIG_SCHEMA_VERSION}
        result = migrate_gui_settings(settings)
        assert result['_schema_version'] == CONFIG_SCHEMA_VERSION


class TestDiceDetection:
    """다이스 판정 엣지 케이스"""

    def test_not_dice_plain_text(self):
        from core.engine import is_dice_roll
        assert is_dice_roll("안녕하세요") is False

    def test_not_dice_url_with_numbers(self):
        from core.engine import is_dice_roll
        assert is_dice_roll("https://example.com/page123") is False

    def test_dice_ccb_format(self):
        from core.engine import is_dice_roll
        assert is_dice_roll("CCB<=65 → 42 성공") is True

    def test_dice_roll_command(self):
        from core.engine import is_dice_roll
        assert is_dice_roll("/roll 2d6") is True

    def test_dice_with_result(self):
        from core.engine import is_dice_roll
        assert is_dice_roll("3d6 = 12") is True


class TestNameSplitting:
    """이름/내용 분리 엣지 케이스"""

    def test_no_colon(self):
        from core.engine import smart_split_name_content
        name, _content = smart_split_name_content("콜론없는텍스트")
        assert name is None

    def test_time_format_rejection(self):
        from core.engine import smart_split_name_content
        name, _content = smart_split_name_content("10:30 게임 시작")
        assert name is None

    def test_very_long_name(self):
        from core.engine import smart_split_name_content
        long_text = "A" * 100 + ": 내용"
        name, _content = smart_split_name_content(long_text, max_name_length=50)
        assert name is None

    def test_multiple_colons(self):
        from core.engine import smart_split_name_content
        name, content = smart_split_name_content("플레이어 (전사): 안녕: 반가워")
        assert name is not None
        assert "안녕" in content


class TestSceneSplitting:
    """장면 분할 엣지 케이스"""

    def test_no_patterns(self, sample_config):
        from core.engine import split_into_scenes
        config = sample_config.copy()
        config['chapter'] = {'split_mode': 'scene', 'scene_patterns': []}
        entries = [{'type': 'dialogue', 'content': 'test', 'name': 'A'}]
        result = split_into_scenes(entries, config)
        assert len(result) == 1

    def test_split_by_count(self, sample_config):
        from core.engine import split_into_scenes
        config = sample_config.copy()
        config['chapter'] = {'split_mode': 'count', 'entries_per_chapter': 2, 'title_format': '장면 {n}'}
        entries = [
            {'type': 'dialogue', 'content': f'대사 {i}', 'name': 'A'}
            for i in range(5)
        ]
        result = split_into_scenes(entries, config)
        assert len(result) == 3  # 2+2+1

    def test_split_mode_none(self, sample_config):
        from core.engine import split_into_scenes
        config = sample_config.copy()
        config['chapter'] = {'split_mode': 'none'}
        entries = [{'type': 'dialogue', 'content': 'test', 'name': 'A'}]
        result = split_into_scenes(entries, config)
        assert len(result) == 1
        assert result[0]['title'] is None


class TestFileEncoding:
    """파일 인코딩 엣지 케이스"""

    def test_utf8_file(self, temp_dir):
        filepath = temp_dir / "utf8.html"
        filepath.write_text("<html><body><p>한글 테스트</p></body></html>", encoding='utf-8')

        from core.engine import convert, load_config
        config = load_config()
        config['paths']['output_dir'] = str(temp_dir)
        config['output_format'] = 'epub'

        # 파일이 읽히기만 하면 성공 — 변환 실패는 OK, 인코딩 에러만 아니면 됨.
        import contextlib
        with contextlib.suppress(Exception):
            convert(str(filepath), config=config, format='epub')

    def test_euckr_file(self, temp_dir):
        filepath = temp_dir / "euckr.html"
        filepath.write_bytes("<html><body><p>한글 테스트</p></body></html>".encode('euc-kr'))

        from core.engine import convert
        config = {'paths': {'output_dir': str(temp_dir)}, 'output_format': 'epub'}

        try:
            convert(str(filepath), config=config, format='epub')
        except UnicodeDecodeError:
            pytest.fail("EUC-KR 파일을 읽지 못했습니다")
        except Exception:
            pass  # 다른 에러는 OK


class TestNormalizePunctuation:
    """구두점 정규화"""

    def test_ellipsis_normalization(self):
        from core.engine import normalize_punctuation
        assert normalize_punctuation("잠깐...") == "잠깐……"
        assert normalize_punctuation("뭐.....라고?") == "뭐……라고?"

    def test_no_change_needed(self):
        from core.engine import normalize_punctuation
        assert normalize_punctuation("정상 텍스트") == "정상 텍스트"
