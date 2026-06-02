"""
캐릭터 색상 자동 할당 서비스
각 캐릭터에 고유한 색상을 자동으로 지정
"""

import colorsys
import hashlib
from typing import ClassVar


class CharacterColorService:
    """캐릭터별 색상 자동 할당 서비스"""

    # 미리 정의된 가독성 좋은 색상 팔레트
    DEFAULT_PALETTE: ClassVar[list[str]] = [
        "#E53935",  # Red
        "#1E88E5",  # Blue
        "#43A047",  # Green
        "#FB8C00",  # Orange
        "#8E24AA",  # Purple
        "#00ACC1",  # Cyan
        "#F4511E",  # Deep Orange
        "#3949AB",  # Indigo
        "#7CB342",  # Light Green
        "#C0CA33",  # Lime
        "#FFB300",  # Amber
        "#6D4C41",  # Brown
        "#546E7A",  # Blue Grey
        "#D81B60",  # Pink
        "#00897B",  # Teal
        "#5E35B1",  # Deep Purple
    ]

    # 나레이션/시스템 사용자용 색상
    NARRATION_COLORS: ClassVar[dict[str, str]] = {
        "gm": "#666666",
        "kp": "#666666",
        "dm": "#666666",
        "keeper": "#666666",
        "narrator": "#666666",
        "system": "#888888",
    }

    def __init__(self, custom_colors: dict[str, str] | None = None):
        """
        Args:
            custom_colors: 사용자 정의 색상 맵핑 {캐릭터명: 색상코드}
        """
        self._custom_colors = custom_colors or {}
        self._assigned_colors: dict[str, str] = {}
        self._palette_index = 0

    def get_color(self, character_name: str) -> str:
        """
        캐릭터 이름에 해당하는 색상 반환

        Args:
            character_name: 캐릭터 이름

        Returns:
            색상 코드 (예: "#E53935")
        """
        if not character_name:
            return "#333333"

        name_lower = character_name.lower().strip()

        # 1. 사용자 정의 색상 확인
        if character_name in self._custom_colors:
            return self._custom_colors[character_name]
        if name_lower in self._custom_colors:
            return self._custom_colors[name_lower]

        # 2. 나레이션/시스템 사용자 확인
        if name_lower in self.NARRATION_COLORS:
            return self.NARRATION_COLORS[name_lower]

        # 3. 이미 할당된 색상 확인
        if name_lower in self._assigned_colors:
            return self._assigned_colors[name_lower]

        # 4. 새 색상 할당
        color = self._assign_new_color(name_lower)
        self._assigned_colors[name_lower] = color
        return color

    def _assign_new_color(self, name: str) -> str:
        """새 색상 할당 (팔레트 순환 + 해시 기반 혼합)"""
        if self._palette_index < len(self.DEFAULT_PALETTE):
            color = self.DEFAULT_PALETTE[self._palette_index]
            self._palette_index += 1
            return color

        # 팔레트 소진 시 해시 기반 색상 생성
        return self._generate_hash_color(name)

    def _generate_hash_color(self, name: str) -> str:
        """이름 해시 기반 고유 색상 생성"""
        # MD5 는 색상 분산용 hash — security 가 아닌 단순 fingerprint 목적.
        # usedforsecurity=False 로 명시해 bandit B324 false positive 차단.
        hash_val = int(
            hashlib.md5(name.encode(), usedforsecurity=False).hexdigest()[:8],
            16,
        )

        # HSV 색상 공간 사용 (채도/명도 고정으로 가독성 유지)
        hue = (hash_val % 360) / 360.0
        saturation = 0.65 + (hash_val % 20) / 100.0  # 0.65-0.85
        value = 0.70 + (hash_val % 15) / 100.0  # 0.70-0.85

        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    def set_custom_color(self, character_name: str, color: str) -> None:
        """사용자 정의 색상 설정"""
        self._custom_colors[character_name] = color

    def remove_color(self, character_name: str) -> None:
        """특정 캐릭터의 색상 매핑을 제거한다(대소문자 키 모두)."""
        for key in {character_name, character_name.lower().strip()}:
            self._custom_colors.pop(key, None)
            self._assigned_colors.pop(key, None)

    def get_all_colors(self) -> dict[str, str]:
        """모든 할당된 색상 반환"""
        result = {}
        result.update(self._assigned_colors)
        result.update(self._custom_colors)
        return result

    def reset(self) -> None:
        """색상 할당 초기화"""
        self._assigned_colors.clear()
        self._palette_index = 0

    def extract_characters(self, entries: list[dict]) -> list[str]:
        """
        파싱된 엔트리에서 캐릭터 목록 추출

        Args:
            entries: 파싱된 로그 엔트리 리스트

        Returns:
            고유 캐릭터 이름 리스트 (등장 순서)
        """
        seen = set()
        characters = []

        for entry in entries:
            name = entry.get("name", "").strip()
            if not name:
                continue

            name_lower = name.lower()
            if name_lower in seen:
                continue
            if name_lower in self.NARRATION_COLORS:
                continue

            seen.add(name_lower)
            characters.append(name)

        return characters

    def auto_assign(self, entries: list[dict]) -> dict[str, str]:
        """
        엔트리에서 캐릭터를 추출하고 자동으로 색상 할당

        Args:
            entries: 파싱된 로그 엔트리 리스트

        Returns:
            캐릭터별 색상 맵핑
        """
        self.reset()
        characters = self.extract_characters(entries)

        for char in characters:
            self.get_color(char)

        return self.get_all_colors()

    def apply_to_entries(self, entries: list[dict]) -> list[dict]:
        """
        엔트리에 색상 정보 추가

        Args:
            entries: 파싱된 로그 엔트리 리스트

        Returns:
            색상 정보가 추가된 엔트리 리스트
        """
        for entry in entries:
            name = entry.get("name", "").strip()
            if name:
                entry["color"] = self.get_color(name)
            else:
                entry["color"] = "#333333"

        return entries


def get_contrasting_text_color(bg_color: str) -> str:
    """
    배경색에 맞는 대비 텍스트 색상 반환

    Args:
        bg_color: 배경 색상 코드 (예: "#E53935")

    Returns:
        "#ffffff" 또는 "#000000"
    """
    hex_color = bg_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # 상대 휘도 계산
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    return "#000000" if luminance > 0.5 else "#ffffff"
