"""Top-level parsing pipeline.

* ``parse_log`` — autodetect Roll20 vs Cocofolia and route accordingly.
* ``filter_entries`` — drop entry types per ``content.*`` config flags.
* ``merge_consecutive_dialogues`` — collapse same-speaker runs.
* ``split_into_scenes`` — produce chapter-shaped scene list for renderers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from core.parsers.cocofolia import parse_cocofolia
from core.parsers.helpers import (
    extract_scene_title,
    is_scene_end,
    is_scene_marker,
)
from core.parsers.roll20 import parse_roll20

logger = logging.getLogger(__name__)

# 후처리에서 덮어쓰면 안 되는 확정형 type 들.
_PROTECTED_TYPES = frozenset({"image", "system"})


def parse_log(html_content: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "html.parser")

    # Roll20 형식 감지
    is_roll20 = (
        soup.find(id="textchat") is not None
        or soup.find(class_="message") is not None
    )
    if is_roll20:
        return parse_roll20(soup, config)

    entries = parse_cocofolia(soup, config)

    # 이름/콜론 분리 후의 content 를 기준으로 scene 마커 재검사.
    # (원본 파서 경로에서는 "- : ▶Scene 1" 같은 줄이 ^▶Scene 패턴을 통과하지 못했음)
    scene_patterns = config.get("chapter", {}).get("scene_patterns", [])
    scene_end_patterns = config.get("chapter", {}).get("scene_end_patterns")

    for e in entries:
        if e.get("type") in _PROTECTED_TYPES:
            continue
        content_check = e.get("content", "")
        if not content_check:
            continue
        if e.get("type") != "scene_end" and is_scene_end(content_check, scene_end_patterns):
            e["type"] = "scene_end"
            continue
        if e.get("type") != "scene" and is_scene_marker(content_check, scene_patterns):
            e["type"] = "scene"

    return entries


def filter_entries(entries: List[Dict], config: Dict[str, Any]) -> List[Dict]:
    content_config = config.get("content", {})
    filtered: List[Dict] = []
    for entry in entries:
        t = entry["type"]
        if t == "dice" and not content_config.get("include_dice", True):
            continue
        if t == "system" and not content_config.get("include_system", True):
            patterns = config.get("chapter", {}).get("scene_patterns", [])
            if not is_scene_marker(entry.get("content", ""), patterns):
                continue
        if t == "effect" and not content_config.get("include_effects", True):
            continue
        filtered.append(entry)
    return filtered


def merge_consecutive_dialogues(entries: List[Dict], config: Dict[str, Any]) -> List[Dict]:
    dialogue_config = config.get("dialogue", {})
    if not dialogue_config.get("merge_consecutive", False):
        return entries

    separator = dialogue_config.get("merge_separator", "\n")
    max_merge = dialogue_config.get("merge_max", 5)

    merged: List[Dict] = []
    i = 0
    while i < len(entries):
        entry = entries[i].copy()
        if entry["type"] == "dialogue" and entry.get("name"):
            same_speaker = [entry["content"]]
            j = i + 1
            merge_count = 1
            while j < len(entries) and (max_merge == 0 or merge_count < max_merge):
                next_entry = entries[j]
                if (
                    next_entry["type"] == "dialogue"
                    and next_entry.get("name", "").lower() == entry["name"].lower()
                ):
                    same_speaker.append(next_entry["content"])
                    j += 1
                    merge_count += 1
                else:
                    break
            if len(same_speaker) > 1:
                entry["content"] = separator.join(same_speaker)
                i = j
            else:
                i += 1
        else:
            i += 1
        merged.append(entry)
    return merged


def split_into_scenes(entries: List[Dict], config: Dict[str, Any]) -> List[Dict]:
    chapter_config = config.get("chapter", {})
    split_mode = chapter_config.get("split_mode", "scene")
    if split_mode == "none":
        return [{"title": None, "entries": entries}]
    if split_mode == "count":
        return split_by_count(entries, chapter_config)
    return split_by_scene(entries, chapter_config)


def split_by_count(entries, chapter_config) -> List[Dict]:
    per_chapter = chapter_config.get("entries_per_chapter", 300)
    title_format = chapter_config.get("title_format", "장면 {n}")
    scenes: List[Dict] = []
    for i in range(0, len(entries), per_chapter):
        chunk = entries[i:i + per_chapter]
        scenes.append({"title": title_format.format(n=len(scenes) + 1), "entries": chunk})
    return scenes


def split_by_scene(entries, chapter_config) -> List[Dict]:
    patterns = chapter_config.get("scene_patterns", [])
    min_entries = chapter_config.get("min_scene_entries", 10)
    title_format = chapter_config.get("title_format", "장면 {n}")
    extract_title = chapter_config.get("extract_scene_title", True)

    if not patterns:
        return [{"title": None, "entries": entries}]

    scenes: List[Dict] = []
    current_scene: Dict[str, Any] = {"title": None, "entries": []}
    scene_count = 0

    for entry in entries:
        content = entry.get("content", "")
        entry_type = entry["type"]

        is_scene = False
        if entry_type == "scene":
            is_scene = True
        elif entry_type in ("system", "narration") and is_scene_marker(content, patterns):
            is_scene = True

        if is_scene:
            if current_scene["entries"]:
                if len(current_scene["entries"]) >= min_entries or not scenes:
                    scenes.append(current_scene)
                elif scenes:
                    scenes[-1]["entries"].extend(current_scene["entries"])

            scene_count += 1
            scene_title = extract_scene_title(content) if extract_title else None
            if not scene_title:
                scene_title = title_format.format(n=scene_count)

            current_scene = {"title": scene_title, "entries": []}
        else:
            current_scene["entries"].append(entry)

    if current_scene["entries"]:
        if not current_scene["title"]:
            current_scene["title"] = (
                title_format.format(n=scene_count + 1) if scene_count else None
            )
        scenes.append(current_scene)

    return scenes if scenes else [{"title": None, "entries": entries}]
