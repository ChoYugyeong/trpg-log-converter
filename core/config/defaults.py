"""Default engine configuration — the single source of truth.

This module has **no internal imports** so it can be safely loaded by both the
engine and the config manager without circular import gymnastics.

Anything outside this file that hardcodes engine defaults is a bug; import from
here instead. To change a default, edit this file (and bump
``CONFIG_SCHEMA_VERSION`` if the change is breaking).
"""

from __future__ import annotations

import copy
from typing import Any

CONFIG_SCHEMA_VERSION: int = 3

DEFAULT_ENGINE_CONFIG: dict[str, Any] = {
    "paths": {
        "input_dir": "./input",
        "output_dir": "./export",
        "fonts_dir": "./fonts",
        "images_dir": "./images",
    },
    "output_format": "both",
    "log_source": "auto",
    "cover": {
        "image": "",
        "include": True,
        "title_on_cover": True,
        "author_on_cover": True,
        "background_color": "#1a1a1a",
        "title_color": "#ffffff",
        "subtitle": "",
    },
    "toc": {
        "include": True,
        "title": "목차",
        "mode": "auto",
        "entries": [],
        "style": "simple",
    },
    "fonts": {
        "name_font": "'Pretendard', sans-serif",
        "body_font": "'Nanum Myeongjo', serif",
        "pretendard_cdn": (
            "https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css"
        ),
        "embed": {},
        "docx_fallback": {"body": "맑은 고딕", "name": "맑은 고딕"},
    },
    "style": {
        "narration_prefix": "＿",
        "scene_marker": "■",
        "dialogue_margin": 0.12,
        "narration_margin": 0.8,
        "narration_indent": 1.5,
        "dice_color": "#888",
    },
    "narration": {
        "users": ["GM", "KP", "DM", "Keeper", "Narrator"],
        "style": "indent",
    },
    "content": {
        "include_dice": True,
        "include_system": True,
        "include_effects": True,
    },
    "dialogue": {
        "merge_consecutive": False,
        "merge_separator": "\n",
        "merge_max": 5,
    },
    "images": {
        "enable": True,
        "markers": [r"\[IMG:\s*(.+?)\]", r"\[삽화:\s*(.+?)\]"],
        "show_caption": True,
        "jpeg_quality": 85,
        "max_resolution": 1600,
        "convert_webp": True,
    },
    "custom_styles": {},
    "chapter": {
        "split_mode": "scene",
        "entries_per_chapter": 300,
        "extract_scene_title": True,
        "title_format": "장면 {n}",
        "min_scene_entries": 10,
        "scene_patterns": ["^■", r"^씬\s*\d+", r"^장면\s*\d+"],
    },
    "parsing": {
        "name_max_length": 50,
        "skip_channels": [],
        "normalize_punctuation": True,
    },
    "performance": {
        "parse_max_workers": 4,
        "max_html_bytes": 50 * 1024 * 1024,  # 50 MiB hard cap on input HTML
    },
}


def default_engine_config() -> dict[str, Any]:
    """Return a deep copy of the defaults so callers can freely mutate."""
    return copy.deepcopy(DEFAULT_ENGINE_CONFIG)
