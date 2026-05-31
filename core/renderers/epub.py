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
from typing import Any, Callable, Dict, List, Optional

from ebooklib import epub

from core.parsers.fonts import get_font_files
from core.parsers.helpers import escape_html
from core.parsers.images import find_image_file, optimize_image
from core.parsers.pipeline import split_into_scenes
from core.renderers.css import generate_css

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]


def entries_to_html(
    entries: List[Dict[str, Any]],
    chapter_title: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    style = (config or {}).get("style", {})
    narration_prefix = style.get("narration_prefix", "＿")
    images_config = (config or {}).get("images", {})

    html_parts: List[str] = []

    if chapter_title:
        clean_title = chapter_title.lstrip("■▶ ").strip() or chapter_title
        html_parts.append(
            f'<h1 class="scene-title chapter">{escape_html(clean_title)}</h1>'
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
            html_parts.append(f'<p class="narration">{prefix}{content_escaped}</p>')
        elif t == "dice":
            if name_escaped:
                html_parts.append(
                    f'<p class="dice">{name_escaped} : {content_escaped}</p>'
                )
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


def create_cover_html(config: Dict[str, Any], title: str, author: str) -> str:
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


def create_toc_html(scenes: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    from core.renderers.toc_filter import filter_toc_scenes

    toc_title = config.get("toc", {}).get("title", "목차")
    html = f'<div class="toc"><h2>{escape_html(toc_title)}</h2><ul>'
    # 챕터 파일명은 원본 인덱스 기준 (filter 후에도 chapter_3.xhtml 식별 유지).
    for original_idx, scene in filter_toc_scenes(scenes, config):
        title = scene.get("title") or f"장면 {original_idx + 1}"
        html += (
            f'<li><a href="chapter_{original_idx+1}.xhtml">'
            f'{escape_html(title)}</a></li>'
        )
    html += "</ul></div>"
    return html


def create_epub(
    entries: List[Dict[str, Any]],
    output_path: str,
    config: Dict[str, Any],
    title: str = "TRPG 리플레이",
    author: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
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

    epub_chapters: List[epub.EpubHtml] = []

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
            progress_callback(pct, 100, f"장면 {idx+1}/{len(scenes)} 생성 중...")

        content_html = entries_to_html(scene_entries, scene_title, config)
        chapter = epub.EpubHtml(
            title=scene_title or f"장면 {idx+1}",
            file_name=f"chapter_{idx+1}.xhtml",
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
    book.spine = ["nav"] + epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    if progress_callback:
        progress_callback(90, 100, "EPUB 저장 중...")

    # 원자적 쓰기: 임시 파일에 작성 후 rename
    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=".epub", dir=os.path.dirname(output_path) or "."
    )
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
