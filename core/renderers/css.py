"""CSS stylesheet generation for EPUB / HTML output."""
from __future__ import annotations

from typing import Any

from core.parsers.fonts import get_font_family_name


def generate_css(config: dict[str, Any], embedded_fonts: dict[str, Any] | None = None) -> str:
    fonts = config.get("fonts", {})
    style = config.get("style", {})

    body_font = fonts.get("body_font", "serif")
    name_font = fonts.get("name_font", "sans-serif")

    body_bg = style.get("body_bg", "#ffffff")
    body_text = style.get("body_text", "#1a1a1a")
    body_font_size = style.get("body_font_size", 14)
    name_color = style.get("name_color", "#2d2d2d")
    name_bold = "bold" if style.get("name_bold", True) else "normal"
    line_height = style.get("visual_line_height", 1.6)

    dice_color = style.get("dice_color", "#888")
    system_color = style.get("system_color", "#666")
    effect_bg = style.get("effect_bg", "#f5f5f5")
    effect_border = style.get("effect_border", "#ccc")

    # 챕터 헤더 — DOCX/PDF 와 공유되는 ``config['header']``.
    header_cfg = config.get("header", {}) if config else {}
    try:
        header_size_em = max(1.2, float(header_cfg.get("size", 24)) / max(body_font_size, 1))
    except (TypeError, ValueError):
        header_size_em = 1.7
    header_color = header_cfg.get("color", body_text)
    header_weight = "700" if header_cfg.get("bold", True) else "400"
    header_decoration = "text-decoration: underline;" if header_cfg.get("underline") else ""

    css_parts = [f"@import url('{fonts.get('pretendard_cdn', '')}');"]

    if embedded_fonts:
        for font_path in embedded_fonts.get("all", []):
            family_name = get_font_family_name(font_path)
            css_parts.append(
                f"@font-face {{ font-family: '{family_name}'; "
                f"src: url('fonts/{font_path.name}'); }}"
            )
        if embedded_fonts.get("body"):
            body_font = f"'{get_font_family_name(embedded_fonts['body'])}', {body_font}"
        if embedded_fonts.get("name"):
            name_font = f"'{get_font_family_name(embedded_fonts['name'])}', {name_font}"

    css_parts.append(f"""
body {{ font-family: {body_font}; font-size: {body_font_size}px; line-height: {line_height}; color: {body_text}; background-color: {body_bg}; margin: 1em; text-align: justify; }}
.dialogue {{ margin: 0.3em 0; line-height: 1.5; }}
.dialogue .name {{ font-family: {name_font}; font-weight: {name_bold}; color: {name_color}; font-size: 1em; margin-right: 0.8em; }}
.narration {{ font-size: 0.95em; line-height: 1.7; margin: 0.8em 0; padding-left: 1.5em; }}
.dice {{ font-family: {name_font}; font-size: 0.75em; color: {dice_color}; margin: 0.2em 0; padding-left: 1em; }}
.system {{ font-family: {name_font}; font-size: 0.85em; color: {system_color}; margin: 1em 0; padding-left: 0.5em; }}
.effect {{ font-family: {name_font}; font-size: 0.85em; color: #444; background: {effect_bg}; border-left: 3px solid {effect_border}; padding: 0.6em 1em; margin: 0.3em 0 0.3em 1em; }}
.whisper {{ font-size: 0.92em; font-style: italic; color: #666; padding-left: 1.5em; }}
.highlight {{ background: #fffde7; padding: 0.3em 0.5em; }}
.scene-title, h1.scene-title {{ font-family: {name_font}; font-weight: {header_weight}; font-size: {header_size_em}em; color: {header_color}; text-align: center; margin: 3em 0 2em 0; letter-spacing: 0.06em; page-break-after: avoid; {header_decoration} }}
h1 {{ font-family: {name_font}; font-size: 1.8em; font-weight: 700; text-align: center; margin: 2em 0 1em 0; }}
.scene-end {{ font-family: {name_font}; font-size: 0.85em; color: #999; text-align: center; margin: 1.5em 0 0.5em 0; letter-spacing: 0.1em; }}
.chapter-ornament {{ text-align: center; color: #bbb; margin: 0.5em 0 1.5em 0; font-size: 0.85em; }}
.cover {{ text-align: center; padding: 20% 10%; }}
.cover h1 {{ font-size: 2em; margin-bottom: 0.5em; }}
.toc {{ margin: 2em 0; }}
.toc h2 {{ text-align: center; margin-bottom: 1em; }}
.toc ul {{ list-style: none; padding: 0; }}
.toc li {{ margin: 0.5em 0; }}
.toc a {{ color: inherit; text-decoration: none; }}
.illustration {{ text-align: center; margin: 1.5em 0; }}
.illustration img {{ max-width: 100%; }}
.caption {{ font-size: 0.8em; color: #666; margin-top: 0.5em; }}
""")

    custom_css = config.get("custom_css", "")
    if custom_css and custom_css.strip():
        css_parts.append("\n/* Custom CSS */\n" + custom_css)

    return "\n".join(css_parts)
