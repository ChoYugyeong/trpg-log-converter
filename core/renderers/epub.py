"""EPUB renderer.

The public entry point is :func:`create_epub`. ``entries_to_html`` /
``create_cover_html`` / ``create_toc_html`` are exported for tests and for
callers that need to assemble custom EPUB structures.
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from collections.abc import Callable
from typing import Any

from ebooklib import epub

from core.parsers.fonts import get_font_files
from core.parsers.helpers import escape_html
from core.parsers.images import find_image_file, optimize_image
from core.parsers.pipeline import split_into_scenes
from core.renderers.css import generate_css

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]


def _b64_image_mime(b64: str) -> str:
    """base64 문자열 선두로 이미지 MIME 추정 (data URI 용)."""
    if b64.startswith("iVBOR"):
        return "image/png"
    if b64.startswith("/9j/"):
        return "image/jpeg"
    if b64.startswith("R0lGOD"):
        return "image/gif"
    if b64.startswith(("PHN2Zy", "PD94bWw")):
        return "image/svg+xml"
    return "image/png"


def _render_divider_html(config: dict[str, Any]) -> str:
    """장면 구분선(장식)을 챕터 제목 아래 HTML 로 렌더. 빈 문자열이면 표시 안 함."""
    d = config.get("divider", {}) or {}
    dtype = d.get("type", "텍스트/기호")
    if dtype == "사용 안 함":
        return ""
    if dtype == "이미지":
        img = d.get("image", "")
        if not img:
            return ""
        h = d.get("img_height", 40)
        mime = _b64_image_mime(img)
        return (
            '<div class="chapter-divider" style="text-align:center;margin:1em 0">'
            f'<img src="data:{mime};base64,{img}" alt="divider" '
            f'style="height:{h}px;max-width:60%"/></div>'
        )
    if dtype == "선 스타일":
        style_map = {
            "실선": "solid",
            "점선": "dashed",
            "파선": "dashed",
            "점선(촘촘)": "dotted",
            "이중선": "double",
        }
        css_style = style_map.get(d.get("line_style", "실선"), "solid")
        t = d.get("line_thickness", 1)
        w = d.get("line_width", 60)
        c = d.get("line_color", "#cccccc")
        return (
            '<hr class="chapter-divider" style="border:none;'
            f'border-top:{t}px {css_style} {c};width:{w}%;margin:1.2em auto"/>'
        )
    # 텍스트/기호 (기본)
    text = d.get("text", "")
    if not text.strip():
        return ""
    c = d.get("color", "#888888")
    return (
        f'<p class="chapter-divider" style="text-align:center;color:{c};'
        f'margin:0.8em 0;letter-spacing:0.2em">{escape_html(text)}</p>'
    )


def entries_to_html(
    entries: list[dict[str, Any]],
    chapter_title: str | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    style = (config or {}).get("style", {})
    narration_prefix = style.get("narration_prefix", "＿")
    images_config = (config or {}).get("images", {})
    # 드롭캡: 이 챕터의 첫 나레이션 문단 첫 글자만 크게. 한 번 적용하면 끈다.
    dropcap_pending = bool(style.get("first_letter", False))

    html_parts: list[str] = []

    if chapter_title:
        clean_title = chapter_title.lstrip("■▶ ").strip() or chapter_title
        # 헤더 prefix/suffix — DOCX/PDF 와 일관되게 EPUB 에도 적용.
        header_cfg = (config or {}).get("header", {}) or {}
        h_prefix = str(header_cfg.get("prefix", "") or "")
        h_suffix = str(header_cfg.get("suffix", "") or "")
        display_title = f"{h_prefix}{clean_title}{h_suffix}"
        html_parts.append(
            f'<h1 class="scene-title chapter">{escape_html(display_title)}</h1>'
        )
        divider_html = _render_divider_html(config or {})
        if divider_html:
            html_parts.append(divider_html)
        else:
            # 장면 구분선을 '사용 안 함' 으로 둔 경우의 폴백 — 구버전 chapter_ornament
            # 설정이 있으면 제목 아래에 장식선으로 렌더(.chapter-ornament CSS 재사용).
            ornament = str(style.get("chapter_ornament", "") or "").strip()
            if ornament:
                html_parts.append(
                    f'<p class="chapter-ornament">{escape_html(ornament)}</p>'
                )

    for entry in entries:
        t = entry["type"]
        content = entry.get("content", "")
        name = entry.get("name", "")
        img = entry.get("image")

        if img:
            img_path = find_image_file(img, config or {})
            if img_path:
                convert_webp = images_config.get("convert_webp", True)
                ref_name = img_path.name
                if convert_webp and str(img_path).lower().endswith(".webp"):
                    ref_name = img_path.stem + ".jpg"
                html_parts.append(
                    f'<div class="illustration"><img src="images/{ref_name}" '
                    f'alt="{escape_html(img)}"/>'
                )
                if images_config.get("show_caption", True):
                    html_parts.append(f'<p class="caption">{escape_html(img)}</p>')
                html_parts.append("</div>")

        if t == "image" or not content or not content.strip():
            continue

        content_escaped = escape_html(content).replace("\n", "<br/>")
        name_escaped = escape_html(name) if name else ""

        if t == "dialogue":
            if name_escaped:
                html_parts.append(
                    f'<p class="dialogue"><span class="name">{name_escaped}</span>'
                    f'<span class="content">{content_escaped}</span></p>'
                )
            else:
                html_parts.append(f'<p class="dialogue">{content_escaped}</p>')
        elif t == "effect":
            if name_escaped:
                html_parts.append(
                    f'<p class="dialogue"><span class="name">{name_escaped}</span></p>'
                )
            html_parts.append(f'<div class="effect">{content_escaped}</div>')
        elif t == "narration":
            prefix = narration_prefix if narration_prefix else ""
            if dropcap_pending:
                from core.utils import split_first_grapheme

                first, rest = split_first_grapheme(content.lstrip())
                first_html = escape_html(first)
                rest_html = escape_html(rest).replace("\n", "<br/>")
                html_parts.append(
                    f'<p class="narration dropcap-para">'
                    f'<span class="dropcap">{first_html}</span>{rest_html}</p>'
                )
                dropcap_pending = False
            else:
                html_parts.append(f'<p class="narration">{prefix}{content_escaped}</p>')
        elif t == "dice":
            if name_escaped:
                html_parts.append(f'<p class="dice">{name_escaped} : {content_escaped}</p>')
            else:
                html_parts.append(f'<p class="dice">{content_escaped}</p>')
        elif t == "system":
            html_parts.append(f'<p class="system">{content_escaped}</p>')
        elif t == "scene_end":
            html_parts.append(f'<p class="scene-end">{content_escaped}</p>')
        elif t == "whisper":
            html_parts.append(f'<p class="whisper">{content_escaped}</p>')
        elif t == "highlight":
            html_parts.append(f'<p class="highlight">{content_escaped}</p>')
        else:
            html_parts.append(f'<p class="dialogue">{content_escaped}</p>')

    return "\n".join(html_parts)


def create_cover_html(config: dict[str, Any], title: str, author: str) -> str:
    cover_config = config.get("cover", {})
    bg_color = cover_config.get("background_color", "#1a1a1a")
    title_color = cover_config.get("title_color", "#ffffff")
    subtitle = cover_config.get("subtitle", "")

    html = (
        f'<div class="cover" style="background-color: {bg_color}; '
        f'color: {title_color}; min-height: 100vh;">'
    )
    if cover_config.get("title_on_cover", True):
        html += f'<h1 style="color: {title_color};">{escape_html(title)}</h1>'
    if subtitle:
        html += f'<p class="subtitle">{escape_html(subtitle)}</p>'
    if cover_config.get("author_on_cover", True):
        html += f'<p class="author">{escape_html(author)}</p>'
    html += "</div>"
    return html


def create_toc_html(scenes: list[dict[str, Any]], config: dict[str, Any]) -> str:
    from core.renderers.toc_filter import filter_toc_scenes

    toc_title = config.get("toc", {}).get("title", "목차")
    html = f'<div class="toc"><h2>{escape_html(toc_title)}</h2><ul>'
    # 챕터 파일명은 원본 인덱스 기준 (filter 후에도 chapter_3.xhtml 식별 유지).
    for original_idx, scene in filter_toc_scenes(scenes, config):
        title = scene.get("title") or f"장면 {original_idx + 1}"
        html += f'<li><a href="chapter_{original_idx + 1}.xhtml">{escape_html(title)}</a></li>'
    html += "</ul></div>"
    return html


def create_epub(
    entries: list[dict[str, Any]],
    output_path: str,
    config: dict[str, Any],
    title: str = "TRPG 리플레이",
    author: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> str:
    """Render entries into an EPUB file at ``output_path`` (atomic write)."""
    if progress_callback:
        progress_callback(0, 100, "EPUB 생성 준비 중...")

    book = epub.EpubBook()

    if author is None:
        author = config.get("metadata", {}).get("author", "GM")
    language = config.get("metadata", {}).get("language", "ko")

    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language(language)
    book.add_author(author)

    embedded_fonts = get_font_files(config)

    for font_path in embedded_fonts.get("all", []):
        mime_type = "font/ttf" if font_path.suffix == ".ttf" else "font/otf"
        with open(font_path, "rb") as f:
            book.add_item(
                epub.EpubItem(
                    uid=f"font_{font_path.stem}",
                    file_name=f"fonts/{font_path.name}",
                    media_type=mime_type,
                    content=f.read(),
                )
            )

    css_content = generate_css(config, embedded_fonts)
    css = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content=css_content,
    )
    book.add_item(css)

    epub_chapters: list[epub.EpubHtml] = []

    cover_config = config.get("cover", {})
    if cover_config.get("include", True):
        cover_image = cover_config.get("image", "")
        if cover_image:
            img_path = find_image_file(cover_image, config)
            if img_path:
                with open(img_path, "rb") as f:
                    book.set_cover(img_path.name, f.read())

        cover_html = create_cover_html(config, title, author)
        cover_chapter = epub.EpubHtml(title="표지", file_name="cover.xhtml", lang=language)
        cover_chapter.set_content(
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            "<head><title>표지</title>"
            '<link rel="stylesheet" type="text/css" href="style/main.css"/></head>'
            f"<body>{cover_html}</body></html>"
        )
        cover_chapter.add_item(css)
        book.add_item(cover_chapter)
        epub_chapters.append(cover_chapter)

    if progress_callback:
        progress_callback(10, 100, "이미지 처리 중...")

    images_added: set[str] = set()
    for entry in entries:
        img = entry.get("image")
        if img:
            img_path = find_image_file(img, config)
            if img_path and str(img_path) not in images_added:
                img_data, mime_type, opt_name = optimize_image(img_path, config)
                book.add_item(
                    epub.EpubItem(
                        uid=f"img_{img_path.stem}",
                        file_name=f"images/{opt_name}",
                        media_type=mime_type,
                        content=img_data,
                    )
                )
                images_added.add(str(img_path))

    if progress_callback:
        progress_callback(20, 100, "장면 분할 중...")
    scenes = split_into_scenes(entries, config)
    logger.info("Split into %d scenes", len(scenes))

    toc_config = config.get("toc", {})
    if toc_config.get("include", True) and len(scenes) > 1:
        toc_html = create_toc_html(scenes, config)
        toc_chapter = epub.EpubHtml(
            title=toc_config.get("title", "목차"),
            file_name="toc_page.xhtml",
            lang=language,
        )
        toc_chapter.set_content(
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            "<head><title>목차</title>"
            '<link rel="stylesheet" type="text/css" href="style/main.css"/></head>'
            f"<body>{toc_html}</body></html>"
        )
        toc_chapter.add_item(css)
        book.add_item(toc_chapter)
        epub_chapters.append(toc_chapter)

    for idx, scene in enumerate(scenes):
        scene_title = scene.get("title")
        scene_entries = scene.get("entries", [])
        if progress_callback:
            pct = 30 + int(60 * idx / max(len(scenes), 1))
            progress_callback(pct, 100, f"장면 {idx + 1}/{len(scenes)} 생성 중...")

        content_html = entries_to_html(scene_entries, scene_title, config)
        chapter = epub.EpubHtml(
            title=scene_title or f"장면 {idx + 1}",
            file_name=f"chapter_{idx + 1}.xhtml",
            lang=language,
        )
        chapter.set_content(
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            f"<head><title>{escape_html(scene_title or title)}</title>"
            '<link rel="stylesheet" type="text/css" href="style/main.css"/></head>'
            f"<body>{content_html}</body></html>"
        )
        chapter.add_item(css)
        book.add_item(chapter)
        epub_chapters.append(chapter)

    book.toc = epub_chapters
    book.spine = ["nav", *epub_chapters]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    if progress_callback:
        progress_callback(90, 100, "EPUB 저장 중...")

    # 원자적 쓰기: 임시 파일에 작성 후 rename
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".epub", dir=os.path.dirname(output_path) or ".")
    os.close(tmp_fd)
    try:
        epub.write_epub(tmp_path, book)
        if os.path.exists(output_path):
            os.replace(tmp_path, output_path)
        else:
            os.rename(tmp_path, output_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    if progress_callback:
        progress_callback(100, 100, "EPUB 생성 완료")
    logger.info("EPUB created: %s", output_path)
    return output_path
