"""Roll20 Chat Archive parser.

Recognises ``id="textchat"`` containers and ``div.message`` rows that Roll20
exports use, including:

  * ``<span class="by">Name:</span>`` speaker tags
  * ``<strong>Name:</strong>`` alternative speaker tags
  * ``message desc`` for narration / descriptions
  * ``hidden-message`` rows (skipped)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from core.parsers.helpers import (
    is_dice_roll,
    is_narration_user,
    is_scene_marker,
    normalize_punctuation,
)

logger = logging.getLogger(__name__)

# Roll20 timestamp formats vary between exports. We try each format in turn.
# All formats are STATIC patterns fed to ``datetime.strptime`` — we never call
# ``datetime.now()`` so behaviour stays deterministic.
_TSTAMP_FORMATS = (
    # 초(%S)를 포함하는 변형 — 실제 Roll20 export 가 HH:MM:SS 를 많이 쓴다.
    "%B %d, %Y %I:%M:%S%p",  # "January 1, 2024 3:04:05PM"
    "%B %d, %Y %I:%M:%S %p",
    "%b %d, %Y %I:%M:%S%p",
    "%m/%d/%y %I:%M:%S%p",
    "%m/%d/%Y %I:%M:%S%p",
    "%Y-%m-%d %H:%M:%S",  # "2024-01-01 15:04:05"
    "%I:%M:%S%p",  # "3:04:05PM"
    "%I:%M:%S %p",
    "%H:%M:%S",  # "15:04:05"
    # 분(%M)까지만 있는 변형
    "%B %d, %Y %I:%M%p",  # "January 1, 2024 3:04PM"
    "%B %d, %Y %I:%M %p",  # "January 1, 2024 3:04 PM"
    "%b %d, %Y %I:%M%p",  # "Jan 1, 2024 3:04PM"
    "%m/%d/%y %I:%M%p",  # "12/24/24 7:32PM"
    "%m/%d/%Y %I:%M%p",  # "12/24/2024 7:32PM"
    "%Y-%m-%d %H:%M",  # "2024-01-01 15:04"
    "%I:%M%p",  # "3:04PM" (clock only)
    "%I:%M %p",  # "3:04 PM"
    "%H:%M",  # "15:04" (clock only)
)


def _parse_tstamp(text: str) -> datetime | None:
    """Best-effort parse of a Roll20 timestamp string.

    Returns a ``datetime`` or ``None`` if no known format matches. Never raises.
    Clock-only formats parse onto a fixed reference date (1900-01-01 via
    ``strptime`` default), which is fine for gap comparison within a session.
    """
    if not text:
        return None
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return None
    for fmt in _TSTAMP_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def parse_roll20(soup, config: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    parsing_config = config.get("parsing", {})
    normalize = parsing_config.get("normalize_punctuation", True)
    scene_patterns = config.get("chapter", {}).get("scene_patterns", [])

    roll20_config = config.get("roll20", {}) or {}
    include_whisper = bool(roll20_config.get("include_whisper", False))
    emote_style = str(roll20_config.get("emote_style", "italic")).strip().lower()
    session_gap_minutes = _safe_int(roll20_config.get("session_gap_minutes", 60), 60)

    messages = soup.find_all("div", class_=lambda x: x and "message" in x)
    last_speaker = None
    prev_time: datetime | None = None
    session_counter = 1

    for msg in messages:
        class_list = msg.get("class", [])
        class_str = " ".join(class_list) if isinstance(class_list, list) else str(class_list)

        is_hidden = "hidden-message" in class_str
        is_emote = "emote" in class_str

        # Whispers / GM-rolls are exported as ``hidden-message`` rows. By default
        # we skip them entirely (no regression). When include_whisper is on we
        # let them flow through extraction and tag them as "whisper" later.
        if is_hidden and not include_whisper:
            continue

        # 이름 추출: <span class="by"> 또는 <strong>
        by_span = msg.find("span", class_="by")
        name_tag = None
        name = None
        if by_span:
            name_tag = by_span
            name_text = by_span.get_text(strip=True)
            name = name_text.rstrip(":").strip()
            # 콜론만 있는 화자(":"/"::" 등 Roll20 시스템 행)는 rstrip 후 빈 문자열이
            # 되므로, 원본이 비어있지 않았다면 System 으로 정규화한다.
            if not name and name_text:
                name = "System"
            last_speaker = name
        else:
            strong_tag = msg.find("strong")
            if strong_tag:
                name_tag = strong_tag
                name_text = strong_tag.get_text(strip=True)
                name = name_text.rstrip(":").strip()
                if not name and name_text:
                    name = "System"
                last_speaker = name

        # 내용 추출
        content = ""
        if name_tag:
            for sibling in name_tag.next_siblings:
                if hasattr(sibling, "get_text"):
                    content += sibling.get_text(separator=" ", strip=True) + " "
                elif isinstance(sibling, str):
                    content += sibling.strip() + " "
            content = content.strip()
            if not content and name_tag.parent:
                parent_text = name_tag.parent.get_text(strip=True)
                name_with_colon = name_tag.get_text(strip=True)
                if parent_text.startswith(name_with_colon):
                    content = parent_text[len(name_with_colon) :].lstrip(":").strip()
        else:
            # avatar/tstamp/spacer 등은 제외
            for child in msg.children:
                child_class = child.get("class", []) if hasattr(child, "get") else []
                child_class_str = (
                    " ".join(child_class) if isinstance(child_class, list) else str(child_class)
                )
                if any(skip in child_class_str for skip in ("avatar", "tstamp", "spacer")):
                    continue
                if hasattr(child, "get_text"):
                    content += child.get_text(separator=" ", strip=True) + " "
                elif isinstance(child, str):
                    content += child.strip() + " "
            content = content.strip()

        if not content:
            continue

        content = re.sub(r"^:\s*", "", content)
        if normalize:
            content = normalize_punctuation(content)
        content = content.replace("＞", "→")

        entry_type = "dialogue"

        if "desc" in class_str:
            entry_type = "narration"
            if not name:
                name = ""

        if not name and "general" in class_str and last_speaker:
            name = last_speaker

        is_scene = is_scene_marker(content, scene_patterns)
        if is_scene:
            entry_type = "scene"

        if name in ("System", "::"):
            if entry_type != "scene":
                entry_type = "system"
            name = ""

        if entry_type != "scene" and is_dice_roll(content):
            entry_type = "dice"

        if entry_type not in ("scene", "system") and name and is_narration_user(name, config):
            entry_type = "narration"

        # Emote (/me) rows: map to a descriptive entry. A scene marker still wins.
        # emote_style == "italic" → "whisper" (renders italic in all renderers);
        # anything else (e.g. "normal"/"plain") → "narration".
        if is_emote and not is_scene:
            entry_type = "whisper" if emote_style == "italic" else "narration"

        # Whisper (hidden-message) rows always win over dialogue/dice — except a
        # genuine scene marker is still allowed to be a scene.
        if is_hidden and not is_scene:
            entry_type = "whisper"

        # session_gap: insert a synthetic scene before this entry when the time
        # gap from the previous message exceeds the configured threshold.
        if session_gap_minutes > 0:
            tstamp_tag = msg.find("span", class_="tstamp")
            cur_time = None
            if tstamp_tag is not None:
                # 실제 Roll20 채팅 아카이브는 타임스탬프를 보통 ``title`` 속성에 둔다.
                # ``aria-label`` / 텍스트도 폴백으로 시도한다.
                cur_time = (
                    _parse_tstamp(tstamp_tag.get("title", ""))
                    or _parse_tstamp(tstamp_tag.get("aria-label", ""))
                    or _parse_tstamp(tstamp_tag.get_text(strip=True))
                )
            if cur_time is not None:
                if prev_time is not None:
                    gap_minutes = (cur_time - prev_time).total_seconds() / 60.0
                    if gap_minutes > session_gap_minutes:
                        session_counter += 1
                        label = f"세션 {session_counter}"
                        entries.append(
                            {
                                "type": "scene",
                                "name": "",
                                "content": label,
                                "raw": label,
                                "image": None,
                                "channel": None,
                            }
                        )
                prev_time = cur_time

        entries.append(
            {
                "type": entry_type,
                "name": name or "",
                "content": content,
                "raw": content,
                "image": None,
                "channel": None,
            }
        )

    return entries
