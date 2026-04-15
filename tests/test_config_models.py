"""
Pydantic V2 기반 GUI 설정 모델 테스트

AppSettings, flatten_settings, unflatten_settings 등
계층형 모델과 플랫 dict 간 양방향 변환을 검증합니다.
"""

import pytest

from gui.config_models import (
    AppSettings,
    HomeSettings,
    CoverSettings,
    ColorPalette,
    StyleSettings,
    FontSettings,
    DecorationSettings,
    ContentFilterSettings,
    SceneSplitSettings,
    ParsingRulesSettings,
    OutputSettings,
    AdvancedOptions,
    flatten_settings,
    unflatten_settings,
)


# ===================================================================
# 1. 기본값 유효성
# ===================================================================

class TestDefaultValues:
    """AppSettings() 기본 생성 시 유효한 기본값을 갖는지 검증"""

    def test_default_values(self):
        """AppSettings()는 아무 인자 없이 유효한 기본값 인스턴스를 생성한다."""
        # GIVEN/WHEN: 기본 인스턴스 생성
        settings = AppSettings()

        # THEN: 최상위 그룹이 모두 존재한다
        assert settings.home is not None
        assert settings.format_style is not None
        assert settings.parsing_content is not None
        assert settings.advanced_group is not None

    def test_home_defaults(self):
        """HomeSettings의 기본값이 올바르다."""
        # WHEN: HomeSettings 기본 생성
        home = HomeSettings()

        # THEN: 핵심 기본값 검증
        assert home.platform == "cocofolia"
        assert home.title == "TRPG 리플레이"
        assert home.author == "GM"
        assert home.output_format == "both"
        assert home.language == "ko"

    def test_style_defaults(self):
        """StyleSettings의 기본값이 올바르다."""
        style = StyleSettings()

        assert style.style_font_size == 14
        assert style.style_line_height == 1.6
        assert style.style_name_bold is True
        assert style.style_body_bg == "#ffffff"

    def test_cover_defaults(self):
        """CoverSettings의 기본값이 올바르다."""
        cover = CoverSettings()

        assert cover.include_cover is True
        assert cover.cover_bg == "#1a1a1a"
        assert cover.cover_title_color == "#ffffff"
        assert cover.include_toc is True
        assert cover.toc_title == "목차"

    def test_decoration_defaults(self):
        """DecorationSettings의 기본값이 올바르다."""
        deco = DecorationSettings()

        assert deco.scene_marker == "■"
        assert deco.narration_prefix == "＿"
        assert deco.divider_type == "텍스트/기호"


# ===================================================================
# 2. flatten / unflatten 라운드트립
# ===================================================================

class TestFlattenRoundTrip:
    """flatten → unflatten → flatten 이 동일한 결과를 산출하는지 검증"""

    def test_flatten_round_trip(self):
        """flatten → unflatten → flatten 결과가 동일하다."""
        # GIVEN: 기본 AppSettings
        original = AppSettings()

        # WHEN: flatten → unflatten → flatten
        flat_1 = flatten_settings(original)
        model_2 = unflatten_settings(flat_1)
        flat_2 = flatten_settings(model_2)

        # THEN: 두 번의 flatten 결과가 동일하다
        assert flat_1 == flat_2

    def test_flatten_round_trip_with_custom_values(self):
        """사용자 지정 값이 포함된 경우에도 라운드트립이 보존된다."""
        # GIVEN: 커스텀 값이 포함된 플랫 dict
        custom_flat = {
            "platform": "roll20",
            "title": "커스텀 세션",
            "author": "테스트 GM",
            "style_font_size": 18,
            "style_line_height": 2.0,
            "cover_bg": "#333333",
            "cover_title_color": "#00ff00",
            "narrators": "GM, KP",
            "language": "ja",
        }

        # WHEN: unflatten → flatten
        model = unflatten_settings(custom_flat)
        result = flatten_settings(model)

        # THEN: 설정한 값이 보존된다
        assert result["platform"] == "roll20"
        assert result["title"] == "커스텀 세션"
        assert result["style_font_size"] == 18
        assert result["cover_bg"] == "#333333"

    def test_unflatten_from_empty_dict(self):
        """빈 dict에서 unflatten 시 기본값 모델이 생성된다."""
        # WHEN: 빈 dict로 unflatten
        model = unflatten_settings({})

        # THEN: 기본값이 적용된 유효한 모델
        assert model.home.platform == "cocofolia"
        assert model.format_style.style.style_font_size == 14


# ===================================================================
# 3. narrators 필드 타입 검증
# ===================================================================

class TestNarratorsField:
    """narrators 필드가 항상 문자열 타입인지 검증"""

    def test_narrators_is_string(self):
        """HomeSettings.narrators는 문자열 타입이다."""
        # GIVEN: 기본 HomeSettings
        home = HomeSettings()

        # THEN: narrators는 str 타입
        assert isinstance(home.narrators, str)
        assert "GM" in home.narrators

    def test_narrators_preserved_in_flatten(self):
        """flatten 후에도 narrators가 문자열로 유지된다."""
        # GIVEN: 기본 AppSettings
        settings = AppSettings()

        # WHEN: flatten
        flat = flatten_settings(settings)

        # THEN: narrators는 str
        assert isinstance(flat["narrators"], str)
        assert "," in flat["narrators"]  # 쉼표 구분 문자열

    def test_narrators_round_trip_stays_string(self):
        """narrators가 unflatten → flatten 거쳐도 문자열을 유지한다."""
        flat_in = {"narrators": "GM, KP, DM"}
        model = unflatten_settings(flat_in)
        flat_out = flatten_settings(model)

        assert isinstance(flat_out["narrators"], str)
        assert flat_out["narrators"] == "GM, KP, DM"


# ===================================================================
# 4. CoverSettings 색상 검증
# ===================================================================

class TestColorValidation:
    """CoverSettings의 hex 색상 검증 (field_validator)"""

    def test_valid_hex_color(self):
        """유효한 7자리 hex 색상은 그대로 통과한다."""
        # WHEN: 유효한 색상으로 생성
        cover = CoverSettings(cover_bg="#ff0000", cover_title_color="#00ff00")

        # THEN: 값이 그대로 유지
        assert cover.cover_bg == "#ff0000"
        assert cover.cover_title_color == "#00ff00"

    def test_valid_short_hex_color(self):
        """유효한 4자리 짧은 hex 색상도 통과한다."""
        cover = CoverSettings(cover_bg="#f00")
        assert cover.cover_bg == "#f00"

    def test_invalid_color_falls_back(self):
        """유효하지 않은 색상은 기본값(#1a1a1a)으로 대체된다."""
        # WHEN: 잘못된 형식의 색상
        cover = CoverSettings(cover_bg="not-a-color", cover_title_color="rgb(0,0,0)")

        # THEN: 기본값으로 대체
        assert cover.cover_bg == "#1a1a1a"
        assert cover.cover_title_color == "#1a1a1a"

    def test_empty_color_falls_back(self):
        """빈 문자열 색상도 기본값으로 대체된다."""
        cover = CoverSettings(cover_bg="", cover_title_color="")
        assert cover.cover_bg == "#1a1a1a"
        assert cover.cover_title_color == "#1a1a1a"


# ===================================================================
# 5. extra 필드 보존
# ===================================================================

class TestExtraFieldsPreserved:
    """AppSettings(extra="allow")로 알려지지 않은 필드가 보존되는지 검증"""

    def test_extra_fields_preserved(self):
        """AppSettings에 정의되지 않은 필드도 유지된다."""
        # GIVEN: 알 수 없는 필드를 포함한 dict
        data = {"home": {}, "my_custom_field": "custom_value", "another_extra": 42}

        # WHEN: AppSettings 생성
        settings = AppSettings(**data)

        # THEN: extra 필드가 model_extra에 보존된다
        assert settings.model_extra is not None
        assert settings.model_extra.get("my_custom_field") == "custom_value"
        assert settings.model_extra.get("another_extra") == 42

    def test_extra_fields_survive_flatten_round_trip(self):
        """extra 필드가 flatten → unflatten 라운드트립에서 보존된다."""
        # GIVEN: 알 수 없는 키가 포함된 플랫 dict
        flat_in = {
            "platform": "cocofolia",
            "unknown_plugin_setting": "hello",
        }

        # WHEN: unflatten → flatten
        model = unflatten_settings(flat_in)
        flat_out = flatten_settings(model)

        # THEN: 알 수 없는 키가 보존된다
        assert flat_out.get("unknown_plugin_setting") == "hello"


# ===================================================================
# 6. flatten 키 개수
# ===================================================================

class TestFlattenKeyCount:
    """flatten된 dict의 키 개수가 기대 범위에 있는지 검증"""

    def test_flatten_key_count(self):
        """기본 AppSettings를 flatten하면 최소 50개 이상의 키가 생성된다."""
        # GIVEN: 기본 AppSettings
        settings = AppSettings()

        # WHEN: flatten
        flat = flatten_settings(settings)

        # THEN: 충분한 수의 키가 존재한다
        # _FIELD_MAP에 약 80+ 항목 + colors, margins, _schema_version
        assert len(flat) >= 50, f"키 개수가 너무 적습니다: {len(flat)}"

    def test_flatten_includes_colors_dict(self):
        """flatten 결과에 colors가 dict로 포함된다."""
        flat = flatten_settings(AppSettings())

        assert "colors" in flat
        assert isinstance(flat["colors"], dict)
        assert "text_color" in flat["colors"]
        assert "name_color" in flat["colors"]

    def test_flatten_includes_margins_dict(self):
        """flatten 결과에 margins가 dict로 포함된다."""
        flat = flatten_settings(AppSettings())

        assert "margins" in flat
        assert isinstance(flat["margins"], dict)
        assert "top" in flat["margins"]
        assert "left" in flat["margins"]

    def test_flatten_includes_schema_version(self):
        """flatten 결과에 _schema_version이 포함된다."""
        flat = flatten_settings(AppSettings())
        assert flat.get("_schema_version") == 2
