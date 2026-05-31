"""Font-file discovery for EPUB embedding."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def get_font_files(config: dict[str, Any]) -> dict[str, Any]:
    fonts_dir = Path(config.get("paths", {}).get("fonts_dir", "./fonts"))
    fonts: dict[str, Any] = {"body": None, "name": None, "all": []}
    if not fonts_dir.exists():
        return fonts
    embed_config = config.get("fonts", {}).get("embed", {})
    for font_type in ("body", "name"):
        filename = embed_config.get(font_type)
        if filename:
            font_path = fonts_dir / filename
            if font_path.exists():
                fonts[font_type] = font_path
                fonts["all"].append(font_path)
    return fonts


def get_font_family_name(font_path: Path) -> str:
    name = font_path.stem
    for suffix in ("-Regular", "-Bold", "-Light", "-Medium", "-SemiBold"):
        name = name.replace(suffix, "")
    return name
