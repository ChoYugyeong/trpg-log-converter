"""Cocofolia (코코포리아) HTML log parser.

Cocofolia exports messages as ``<p>`` / ``<div>`` blocks where each speaker is
identified by ``class="firing_name_<name>"`` and the content by
``class="firing_firing"`` (often on the same span).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from core.parsers.helpers import (
    is_dice_roll,
    is_narration_user,
    is_scene_marker,
    match_custom_style,
    normalize_punctuation,
    smart_split_name_content,
    strip_channel_prefix,
)
from core.parsers.images import extract_image_markers

logger = logging.getLogger(__name__)


def parse_cocofolia(soup, config: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    parsing_config = config.get("parsing", {})
    skip_channels = parsing_config.get("skip_channels", [])
    name_max_length = parsing_config.get("name_max_length", 50)
    normalize = parsing_config.get("normalize_punctuation", True)
    scene_patterns = config.get("chapter", {}).get("scene_patterns", [])

    for element in soup.find_all(["p", "div"]):
        if element.find(["p", "div"]):
            continue

        # firing_name_XXX / firing_firing 스팬에서 이름/내용 추출
        name_from_class = None
        content_from_spans = None
        for span in element.find_all("span"):
            class_attr = span.get("class", [])
            class_str = " ".join(class_attr) if isinstance(class_attr, list) else str(class_attr)

            name_match = re.search(r"firing_name_(\S+)", class_str)
            if name_match:
                name_from_class = name_match.group(1)
                if "firing_firing" in class_str:
                    content_from_spans = span.get_text(strip=True)
            elif "firing_firing" in class_str:
                content_from_spans = span.get_text(strip=True)

        if name_from_class:
            name = name_from_class.replace("_", " ")
            if content_from_spans is not None:
                text = content_from_spans.lstrip(":").strip()
            else:
                text = element.get_text(separator=" ", strip=True).lstrip(":").strip()
        else:
            text = element.get_text(separator=" ", strip=True)
            name = None
            # firing_name_ 도 콜론도 없는 실제 ccfolia 변형:
            #   <p><span style="color:..">이름</span><span>대사</span></p>
            # 첫 스팬이 색상/굵기 스타일을 가진 '이름 스팬' 이고 뒤에 본문이 더
            # 있으면 이를 화자/본문으로 분리한다(콜론이 있으면 기존 콜론 경로 사용).
            if ":" not in text:
                spans = element.find_all("span")
                if spans:
                    first_text = spans[0].get_text(strip=True)
                    style = (spans[0].get("style") or "").lower()
                    styled = ("color" in style) or ("font-weight" in style) or ("bold" in style)
                    if (
                        first_text
                        and styled
                        and text.startswith(first_text)
                        and len(text) > len(first_text)
                    ):
                        rest = text[len(first_text) :].strip()
                        if rest:
                            name = first_text
                            text = rest

        # 채널 접두사 분리 — text 변형 *전* 에 수행해야 [잡담] 매칭 가능
        text = text.strip()
        text, channel = strip_channel_prefix(text)

        if channel and channel in skip_channels:
            continue

        for ch in skip_channels:
            text = re.sub(re.escape(ch) + r"\s*", "", text)
        text = text.strip()

        if not text:
            continue

        text = text.replace("＞", "→")
        if normalize:
            text = normalize_punctuation(text)

        img_filename, text = extract_image_markers(text, config)
        entry: dict[str, Any] = {
            "type": "dialogue",
            "name": name or "",
            "content": text,
            "raw": text,
            "image": img_filename,
            "channel": channel,
        }

        if img_filename and not text.strip():
            entry["type"] = "image"
            entry["content"] = img_filename
            entries.append(entry)
            continue

        if not text:
            continue

        if is_scene_marker(text, scene_patterns):
            entry["type"] = "scene"
            entry["content"] = text
            if name:
                entry["name"] = name
            entries.append(entry)
            continue

        if text.lower().startswith("system :") or text.lower().startswith("system:"):
            content = re.sub(r"^system\s*:\s*", "", text, flags=re.IGNORECASE)
            entry["type"] = "system"
            entry["content"] = content.strip()
        elif name:
            if is_narration_user(name, config):
                entry["type"] = "narration"
                entry["name"] = name
            elif is_dice_roll(text):
                entry["type"] = "dice"
                entry["name"] = name
            elif text.startswith("《") or text.count("|") >= 2:
                entry["type"] = "effect"
                entry["name"] = name
            else:
                entry["type"] = "dialogue"
                entry["name"] = name
        elif ":" in text:
            parsed_name, content = smart_split_name_content(text, name_max_length)
            if parsed_name and parsed_name.lower() != "system":
                entry["name"] = parsed_name
                entry["content"] = content

                if is_narration_user(parsed_name, config):
                    entry["type"] = "narration"
                else:
                    custom_type = match_custom_style(content, config)
                    if custom_type:
                        entry["type"] = custom_type
                    elif is_dice_roll(content):
                        entry["type"] = "dice"
                    elif content.startswith("《") or content.count("|") >= 2:
                        entry["type"] = "effect"
                    else:
                        entry["type"] = "dialogue"

        entries.append(entry)

    return entries
