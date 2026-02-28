"""
캐릭터 색상 서비스 테스트
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.services.character_colors import CharacterColorService, get_contrasting_text_color


class TestCharacterColorService:
    """CharacterColorService 테스트"""

    def test_get_color_returns_unique_colors(self):
        """각 캐릭터에 고유한 색상이 할당되는지 확인"""
        service = CharacterColorService()

        color1 = service.get_color("캐릭터A")
        color2 = service.get_color("캐릭터B")
        color3 = service.get_color("캐릭터C")

        assert color1 != color2
        assert color2 != color3
        assert color1 != color3

    def test_get_color_returns_same_color_for_same_character(self):
        """같은 캐릭터는 같은 색상을 반환하는지 확인"""
        service = CharacterColorService()

        color1 = service.get_color("테스트캐릭터")
        color2 = service.get_color("테스트캐릭터")

        assert color1 == color2

    def test_get_color_case_insensitive(self):
        """캐릭터 이름이 대소문자 구분 없이 같은 색상을 반환하는지 확인"""
        service = CharacterColorService()

        color_lower = service.get_color("test")
        color_upper = service.get_color("TEST")

        assert color_lower == color_upper

    def test_narration_users_get_gray_color(self):
        """나레이션 사용자는 회색 계열 색상을 받는지 확인"""
        service = CharacterColorService()

        gm_color = service.get_color("GM")
        kp_color = service.get_color("KP")
        dm_color = service.get_color("DM")

        assert gm_color == "#666666"
        assert kp_color == "#666666"
        assert dm_color == "#666666"

    def test_custom_colors_override(self):
        """사용자 정의 색상이 기본 색상을 덮어쓰는지 확인"""
        custom = {"테스트": "#FF0000"}
        service = CharacterColorService(custom_colors=custom)

        color = service.get_color("테스트")
        assert color == "#FF0000"

    def test_set_custom_color(self):
        """set_custom_color가 올바르게 작동하는지 확인"""
        service = CharacterColorService()

        service.set_custom_color("캐릭터X", "#00FF00")
        color = service.get_color("캐릭터X")

        assert color == "#00FF00"

    def test_reset_clears_assigned_colors(self):
        """reset이 할당된 색상을 지우는지 확인"""
        service = CharacterColorService()

        color1 = service.get_color("테스트1")
        service.reset()
        color2 = service.get_color("테스트1")

        # 리셋 후에도 같은 인덱스에서 시작하므로 같은 색상
        assert color1 == color2

    def test_extract_characters_from_entries(self):
        """엔트리에서 캐릭터를 올바르게 추출하는지 확인"""
        service = CharacterColorService()

        entries = [
            {"type": "dialogue", "name": "캐릭터A", "content": "대사1"},
            {"type": "dialogue", "name": "캐릭터B", "content": "대사2"},
            {"type": "dialogue", "name": "캐릭터A", "content": "대사3"},
            {"type": "narration", "name": "GM", "content": "나레이션"},
            {"type": "system", "name": "", "content": "시스템 메시지"},
        ]

        characters = service.extract_characters(entries)

        assert "캐릭터A" in characters
        assert "캐릭터B" in characters
        assert "GM" not in characters  # 나레이션 사용자 제외
        assert len(characters) == 2

    def test_auto_assign_returns_color_dict(self):
        """auto_assign이 색상 딕셔너리를 반환하는지 확인"""
        service = CharacterColorService()

        entries = [
            {"type": "dialogue", "name": "A", "content": "대사1"},
            {"type": "dialogue", "name": "B", "content": "대사2"},
        ]

        colors = service.auto_assign(entries)

        assert isinstance(colors, dict)
        assert "a" in colors or "A" in [k for k in colors.keys()]

    def test_apply_to_entries_adds_color_field(self):
        """apply_to_entries가 color 필드를 추가하는지 확인"""
        service = CharacterColorService()

        entries = [
            {"type": "dialogue", "name": "테스트", "content": "대사"},
        ]

        result = service.apply_to_entries(entries)

        assert "color" in result[0]
        assert result[0]["color"].startswith("#")

    def test_empty_name_gets_default_color(self):
        """빈 이름은 기본 색상을 받는지 확인"""
        service = CharacterColorService()

        color = service.get_color("")
        assert color == "#333333"

    def test_palette_cycling(self):
        """팔레트 소진 후 해시 기반 색상 생성되는지 확인"""
        service = CharacterColorService()

        # 팔레트 크기보다 많은 캐릭터 생성
        colors = set()
        for i in range(20):
            color = service.get_color(f"캐릭터{i}")
            colors.add(color)

        # 모든 색상이 고유한지 확인
        assert len(colors) == 20


class TestContrastingTextColor:
    """대비 텍스트 색상 함수 테스트"""

    def test_dark_background_returns_white_text(self):
        """어두운 배경에서 흰색 텍스트를 반환하는지 확인"""
        result = get_contrasting_text_color("#000000")
        assert result == "#ffffff"

        result = get_contrasting_text_color("#333333")
        assert result == "#ffffff"

    def test_light_background_returns_black_text(self):
        """밝은 배경에서 검은색 텍스트를 반환하는지 확인"""
        result = get_contrasting_text_color("#ffffff")
        assert result == "#000000"

        result = get_contrasting_text_color("#f0f0f0")
        assert result == "#000000"

    def test_handles_short_hex_format(self):
        """짧은 형식의 16진수 색상도 처리하는지 확인"""
        result = get_contrasting_text_color("#fff")
        assert result == "#000000"

        result = get_contrasting_text_color("#000")
        assert result == "#ffffff"
