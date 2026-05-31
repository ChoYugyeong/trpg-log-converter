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
from typing import Any

from core.parsers.helpers import (
    is_dice_roll,
    is_narration_user,
    is_scene_marker,
    normalize_punctuation,
)

logger = logging.getLogger(__name__)


def parse_roll20(soup, config: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    parsing_config = config.get("parsing", {})
    normalize = parsing_config.get("normalize_punctuation", True)
    scene_patterns = config.get("chapter", {}).get("scene_patterns", [])

    messages = soup.find_all("div", class_=lambda x: x and "message" in x)
    last_speaker = None

    for msg in messages:
        class_list = msg.get("class", [])
        class_str = " ".join(class_list) if isinstance(class_list, list) else str(class_list)

        if "hidden-message" in class_str:
            continue

        # 이름 추출: <span class="by"> 또는 <strong>
        by_span = msg.find("span", class_="by")
        name_tag = None
        name = None
        if by_span:
            name_tag = by_span
            name_text = by_span.get_text(strip=True)
            name = name_text.rstrip(":").strip()
            if name in (":", "::"):
                name = "System"
            last_speaker = name
        else:
            strong_tag = msg.find("strong")
            if strong_tag:
                name_tag = strong_tag
                name_text = strong_tag.get_text(strip=True)
                name = name_text.rstrip(":").strip()
                if name in (":", "::"):
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

        if is_scene_marker(content, scene_patterns):
            entry_type = "scene"

        if name in ("System", "::"):
            if entry_type != "scene":
                entry_type = "system"
            name = ""

        if entry_type != "scene" and is_dice_roll(content):
            entry_type = "dice"

        if entry_type not in ("scene", "system") and name and is_narration_user(name, config):
            entry_type = "narration"

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
