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

    # 줄간격/들여쓰기 — UI(서식/파싱 탭)에서 조절. 과거엔 하드코딩(1.5/1.7/1.5em)되어
    # 슬라이더가 출력에 반영되지 않았다.
    def _num(value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    dialogue_lh = _num(style.get("dialogue_line_height", 1.5), 1.5)
    narration_lh = _num(style.get("narration_line_height", 1.7), 1.7)
    narration_indent = _num(style.get("narration_indent", 1.5), 1.5)

    # 전역 글자 배율 — 본문/나레이션/대사가 모두 em 기반이라 body 크기만 곱하면
    # 문서 전체가 비례 확대/축소된다. 기본 1.0 이면 변화 없음.
    base_font_scale = _num(style.get("base_font_size", 1.0), 1.0)
    if base_font_scale <= 0:
        base_font_scale = 1.0
    body_font_size = round(_num(body_font_size, 14) * base_font_scale, 2)

    # 이미지 정렬/최대 너비 — UI(파싱/고급 탭)에서 조절. 과거엔 가운데/100% 고정.
    images_cfg = config.get("images", {}) if config else {}
    _align_raw = str(images_cfg.get("alignment", "center") or "center").lower()
    img_align = _align_raw if _align_raw in ("left", "right", "center") else "center"
    img_max_width = max(1, min(100, int(_num(images_cfg.get("max_width", 100), 100))))

    # 챕터 헤더 — DOCX/PDF 와 공유되는 ``config['header']``.
    header_cfg = config.get("header", {}) if config else {}
    try:
        header_size_em = max(1.2, float(header_cfg.get("size", 24)) / max(body_font_size, 1))
    except (TypeError, ValueError):
        header_size_em = 1.7
    header_color = header_cfg.get("color", body_text)
    header_weight = "700" if header_cfg.get("bold", True) else "400"
    header_decoration = "text-decoration: underline;" if header_cfg.get("underline") else ""
    # 헤더 박스 — UI 체크박스 'header_box'. 켜면 제목에 배경 박스를 두른다.
    if header_cfg.get("box"):
        _box_color = header_cfg.get("box_color", "#f5f5f5")
        header_box_style = (
            f"background: {_box_color}; padding: 0.5em 0.9em; border-radius: 6px;"
        )
    else:
        header_box_style = ""

    # 인용/효과 박스 스타일(quote_style) — .effect 박스의 테두리/배경 처리.
    quote_style = str(style.get("quote_style", "왼쪽 테두리") or "").strip()
    if quote_style == "없음":
        effect_box = "background: transparent;"
    elif quote_style == "둥근 박스":
        effect_box = f"background: {effect_bg}; border: 1px solid {effect_border}; border-radius: 8px;"
    elif quote_style == "그림자 박스":
        effect_box = (
            f"background: {effect_bg}; border: 1px solid {effect_border}; "
            f"border-radius: 6px; box-shadow: 2px 2px 6px rgba(0,0,0,0.12);"
        )
    elif quote_style == "인용 기호":
        effect_box = f"background: {effect_bg}; border-left: 3px solid {effect_border}; font-style: italic;"
    else:  # 왼쪽 테두리 (기본)
        effect_box = f"background: {effect_bg}; border-left: 3px solid {effect_border};"

    # 주사위 표시 스타일(dice_style) — '하이라이트' 면 .dice 에 배경 강조.
    dice_style = str(style.get("dice_style", "인라인") or "").strip()
    dice_highlight = (
        "background: #fffbe6; border-radius: 4px; padding-right: 0.4em;"
        if dice_style == "하이라이트"
        else ""
    )

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
.dialogue {{ margin: 0.3em 0; line-height: {dialogue_lh}; }}
.dialogue .name {{ font-family: {name_font}; font-weight: {name_bold}; color: {name_color}; font-size: 1em; margin-right: 0.8em; }}
.narration {{ font-size: 0.95em; line-height: {narration_lh}; margin: 0.8em 0; padding-left: {narration_indent}em; }}
.narration.dropcap-para {{ padding-left: 0; }}
.dropcap {{ float: left; font-family: {name_font}; font-size: 3.2em; line-height: 0.72; padding: 0.02em 0.1em 0 0; font-weight: 700; color: {header_color}; }}
.dice {{ font-family: {name_font}; font-size: 0.75em; color: {dice_color}; margin: 0.2em 0; padding-left: 1em; {dice_highlight} }}
.system {{ font-family: {name_font}; font-size: 0.85em; color: {system_color}; margin: 1em 0; padding-left: 0.5em; }}
.effect {{ font-family: {name_font}; font-size: 0.85em; color: #444; {effect_box} padding: 0.6em 1em; margin: 0.3em 0 0.3em 1em; }}
.whisper {{ font-size: 0.92em; font-style: italic; color: #666; padding-left: 1.5em; }}
.highlight {{ background: #fffde7; padding: 0.3em 0.5em; }}
.scene-title, h1.scene-title {{ font-family: {name_font}; font-weight: {header_weight}; font-size: {header_size_em}em; color: {header_color}; text-align: center; margin: 3em 0 2em 0; letter-spacing: 0.06em; page-break-after: avoid; {header_decoration} {header_box_style} }}
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
.illustration {{ text-align: {img_align}; margin: 1.5em 0; }}
.illustration img {{ max-width: {img_max_width}%; }}
.caption {{ font-size: 0.8em; color: #666; margin-top: 0.5em; }}
""")

    custom_css = config.get("custom_css", "")
    if custom_css and custom_css.strip():
        css_parts.append("\n/* Custom CSS */\n" + custom_css)

    return "\n".join(css_parts)
