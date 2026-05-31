"""Pure text utilities shared by every parser path.

No I/O, no third-party deps beyond ``python-docx`` (only for :class:`RGBColor`).
This file should stay leaf — no imports from other ``core.parsers.*`` siblings.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from docx.shared import RGBColor

logger = logging.getLogger(__name__)


def normalize_punctuation(text: str) -> str:
    text = re.sub(r"\.{3,}", "……", text)
    text = text.replace("...", "……")
    return text


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hex_to_rgb(hex_color: str) -> RGBColor:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def is_narration_user(name: str, config: dict[str, Any]) -> bool:
    default_users = [
        "GM", "KP", "DM", "System", "시스템", "나레이션",
        "Narrator", "진행자", "Storyteller", "Keeper",
    ]
    config_users = config.get("narration", {}).get("users", [])
    narration_users = list(set(default_users + config_users))
    return name.lower().strip() in [u.lower() for u in narration_users]


def match_custom_style(content: str, config: dict[str, Any]) -> str | None:
    for _, style_config in config.get("custom_styles", {}).items():
        pattern = style_config.get("pattern", "")
        if pattern:
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    result: str = style_config.get("type", "dialogue")
                    return result
            except re.error as e:
                logger.warning("커스텀 스타일 패턴 오류 '%s': %s", pattern, e)
    return None


def is_dice_roll(text: str) -> bool:
    """주사위 굴림 판정 — 다양한 형식 지원."""
    text_upper = text.upper()

    if re.search(r"(CCB|1D100|2D6|\d+D\d+)", text_upper) and (
        "→" in text or "=" in text or ">" in text or "＞" in text
    ):
        return True
    if re.search(r"/roll\s+\d*d\d+", text, re.IGNORECASE):
        return True
    if re.search(r"rolling\s+\d*d\d+", text, re.IGNORECASE):
        return True
    if re.search(r"\d+d\d+.*vs\s*(ac|dc)", text, re.IGNORECASE):
        return True
    if re.search(r"(attack|damage|hit|save|check)\s*:?\s*\d*d\d+", text, re.IGNORECASE):
        return True
    if re.search(r"\d+d\d+", text, re.IGNORECASE) and re.search(
        r"(성공|실패|critical|crit|fumble|대성공|대실패)", text, re.IGNORECASE
    ):
        return True
    return bool(re.search(r"\d+d\d+\s*[+\-]?\s*\d*\s*=\s*\d+", text, re.IGNORECASE))


def validate_regex(pattern: str) -> bool:
    try:
        re.compile(pattern)
        return True
    except re.error as e:
        logger.warning("잘못된 정규식 패턴 '%s': %s", pattern, e)
        return False


def is_scene_marker(text: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error as e:
            logger.warning("씬 마커 패턴 오류 '%s': %s (리터럴 매칭 시도)", pattern, e)
            if pattern in text:
                return True
    return False


def extract_scene_title(text: str) -> str | None:
    text = text.strip()
    text = re.sub(r"^[─━\-=\*]+\s*", "", text)
    text = re.sub(r"\s*[─━\-=\*]+$", "", text)
    return text.strip() if text else None


# 씬 종료 마커 — 새 챕터 시작이 아니라 직전 챕터의 마지막 줄로 출력된다.
_DEFAULT_SCENE_END_PATTERNS = (
    r"^[ㅡ─━\-—]+\s*씬?\s*[\d일차\s]*\s*종료",
    r"^[ㅡ─━\-—]+\s*Scene\s*end",
    r"^[ㅡ─━\-—]+\s*end\s*[ㅡ─━\-—]+",
)


def is_scene_end(text: str, patterns: list[str] | None = None) -> bool:
    """씬 종료 마커 여부. 본문 중에 '종료' 가 들어가는 일반 문장은 제외하기 위해
    줄 시작에 ㅡ/─/대시 같은 구분 기호가 와야 매칭된다.
    """
    if not text:
        return False
    sample = text.strip()
    if len(sample) > 30:
        return False
    targets = patterns if patterns else list(_DEFAULT_SCENE_END_PATTERNS)
    for p in targets:
        try:
            if re.search(p, sample, re.IGNORECASE):
                return True
        except re.error:
            if p in sample:
                return True
    return False


def strip_channel_prefix(text: str) -> tuple[str, str | None]:
    """채널 접두사 제거 (예: [메인], [잡담], [정보] 등).

    이미지 마커(``[IMG: x.png]``, ``[삽화: y.jpg]``)는 콜론을 포함하므로
    채널 토큰으로 잘못 매칭되지 않도록 콜론이 들어간 토큰은 제외한다.
    """
    match = re.match(r"^\s*(\[[^\]:]+\])\s*", text)
    if match:
        return text[match.end():].strip(), match.group(1)
    return text, None


def smart_split_name_content(text: str, max_name_length: int = 50) -> tuple[str | None, str]:
    """이름과 내용을 지능적으로 분리 (복잡한 이름 처리)."""
    if ":" not in text:
        return None, text

    colon_positions = [i for i, c in enumerate(text) if c == ":"]

    if len(colon_positions) == 1:
        pos = colon_positions[0]
        if 0 < pos <= max_name_length:
            name_part = text[:pos].strip()
            if re.match(r"^\d{1,2}$", name_part):
                return None, text
            return name_part, text[pos + 1:].strip()
        return None, text

    best_pos: int | None = None
    best_score = -1

    for pos in colon_positions:
        if pos == 0 or pos > max_name_length:
            continue

        name_part = text[:pos].strip()
        content_part = text[pos + 1:].strip()

        score = 0
        if 1 <= len(name_part) <= 30:
            score += 10
        if "(" in name_part and ")" in name_part:
            score += 5
        if pos + 1 < len(text) and text[pos + 1] == " ":
            score += 3
        if pos > 0 and text[pos - 1] == " ":
            score += 2
        if content_part and content_part[0] in '「『"\'""「':
            score += 5
        if re.match(r"^[\d\W]+$", name_part):
            score -= 10
        if re.match(r"^\d{1,2}:\d{2}", name_part) or re.match(r"^\d{1,2}:\d{2}", text[:pos]):
            score -= 20
        if ":" in name_part:
            score -= 15

        if score > best_score:
            best_score = score
            best_pos = pos

    if best_pos is not None and best_score >= 0:
        return text[:best_pos].strip(), text[best_pos + 1:].strip()

    pos = colon_positions[0]
    if 0 < pos <= max_name_length:
        return text[:pos].strip(), text[pos + 1:].strip()

    return None, text
