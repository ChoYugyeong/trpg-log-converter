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
        "GM",
        "KP",
        "DM",
        "System",
        "시스템",
        "나레이션",
        "Narrator",
        "진행자",
        "Storyteller",
        "Keeper",
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


# 대사가 이미 따옴표/괄호로 감싸진 경우 구분자 중복 래핑을 막기 위한 여는 기호 집합.
_OPENING_BRACKETS = "「『\"'“”‘’《〈<([（｢"


def _resolve_dialogue_brackets(
    style: dict[str, Any],
) -> tuple[str, str] | None:
    """'대사 구분자' UI 값(라벨)을 (여는기호, 닫는기호) 튜플로 변환.

    감싸지 않는 경우('없음'/미설정/해석 불가)에는 None 을 반환한다.
    """
    label = str(style.get("dialogue_separator", "") or "").strip()
    if not label or "없음" in label:
        return None
    if "직접" in label:  # 직접 입력
        custom = str(style.get("dialogue_separator_custom", "") or "").strip()
        if not custom:
            return None
        parts = custom.split()
        if len(parts) >= 2:
            return parts[0], parts[1]
        # 공백 구분이 없으면 한 글자씩(예: "[]") 또는 양쪽 동일 기호로 처리
        if len(custom) >= 2:
            return custom[0], custom[-1]
        return custom, custom
    if "작은따옴표" in label:
        return "'", "'"
    if "따옴표" in label:
        return '"', '"'
    if "꺾쇠" in label:
        return "「", "」"
    return None


def apply_parsing_overrides(
    entries: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    """'파싱 규칙' + 대사 표현 UI 설정을 실제 파싱 결과에 반영하는 공통 post-pass.

    HTML(코코포리아/Roll20) 파이프라인과 텍스트 파서 양쪽에서 호출한다.
    기본값이면 아무것도 하지 않고 그대로 반환해 기존 동작을 보존한다.

    1) system_prefix: content 가 이 접두사로 시작하면 system 메시지로 분류.
    2) dice_keywords: dialogue 로 분류된 항목이 사용자 키워드 + 결과 기호(→/=/>)를
       가지면 dice 로 재분류(기본 다이스 감지에 '추가'되는 보강).
    3) narration_no_name: 이름 없는 dialogue 를 narration 으로.
    4) empty_dialogue: 내용이 비어있는 대사를 placeholder(…) 로 치환.
    5) dialogue_separator: 대사 content 를 선택한 기호(「」 등)로 감싼다.
       이미 따옴표/괄호로 시작하는 대사는 중복 래핑하지 않는다.
    """
    parsing = config.get("parsing", {})
    sys_prefix = (parsing.get("system_prefix") or "").strip()
    extra_dice = [k for k in (parsing.get("dice_keywords") or []) if k]
    narr_no_name = bool(parsing.get("narration_no_name", False))

    style = config.get("style", {})
    brackets = _resolve_dialogue_brackets(style)
    empty_placeholder = str(config.get("dialogue", {}).get("empty_dialogue", "") or "").strip()

    reclassify = bool(sys_prefix or extra_dice or narr_no_name)
    if not reclassify and brackets is None and not empty_placeholder:
        return entries  # 기본값 — 무변경

    _skip = {"scene", "scene_end", "image"}
    for entry in entries:
        if entry.get("type") in _skip:
            continue
        content = entry.get("content") or ""
        # system_prefix 는 '원본 줄(raw)' 기준으로 검사한다. 그렇지 않으면
        # "[INFO] 규칙: ..." 처럼 접두사 줄에 콜론이 또 있을 때 이름:대사 분리에서
        # 접두사가 name 으로 빨려들어가 content 검사가 놓친다.
        probe = entry.get("raw") or content

        if reclassify:
            if sys_prefix and probe.lstrip().lower().startswith(sys_prefix.lower()):
                entry["type"] = "system"
                entry["content"] = probe.lstrip()[len(sys_prefix) :].strip()
                entry["name"] = ""
                continue

            if extra_dice and entry.get("type") == "dialogue":
                cu = content.upper()
                has_symbol = any(s in content for s in ("→", "=", ">", "＞"))
                if has_symbol and any(k.upper() in cu for k in extra_dice):
                    entry["type"] = "dice"

            if (
                narr_no_name
                and entry.get("type") == "dialogue"
                and not (entry.get("name") or "").strip()
            ):
                entry["type"] = "narration"

        # 아래 두 처리는 최종 분류가 dialogue 인 항목에만 적용된다.
        if entry.get("type") != "dialogue":
            continue

        # 4) 빈 대사 → placeholder
        if empty_placeholder and not (entry.get("content") or "").strip():
            entry["content"] = empty_placeholder

        # 5) 대사 구분자 래핑 (이미 감싸진 대사는 건너뜀)
        if brackets is not None:
            text = (entry.get("content") or "").strip()
            if text and text[0] not in _OPENING_BRACKETS:
                open_b, close_b = brackets
                entry["content"] = f"{open_b}{text}{close_b}"

    return entries


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
    # 선두 장식/마커(─━-=* 및 ■▶◆●) 를 제거해 제목만 남긴다. 렌더러 본문은
    # 별도로 ■▶ 를 lstrip 하지만 TOC/목차·EPUB nav 는 이 title 을 그대로 쓰므로
    # 여기서 한 번에 정리해 표시 일관성을 맞춘다.
    text = text.strip()
    text = re.sub(r"^[─━\-=\*■▶◆●▷▸\s]+", "", text)
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
        return text[match.end() :].strip(), match.group(1)
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
            return name_part, text[pos + 1 :].strip()
        return None, text

    best_pos: int | None = None
    best_score = -1

    for pos in colon_positions:
        if pos == 0 or pos > max_name_length:
            continue

        name_part = text[:pos].strip()
        content_part = text[pos + 1 :].strip()

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
        return text[:best_pos].strip(), text[best_pos + 1 :].strip()

    pos = colon_positions[0]
    if 0 < pos <= max_name_length:
        return text[:pos].strip(), text[pos + 1 :].strip()

    return None, text
