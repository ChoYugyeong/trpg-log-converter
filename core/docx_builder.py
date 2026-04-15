#!/usr/bin/env python3
"""
DOCX 빌더 — TRPG 로그 entries를 .docx 파일로 변환한다.

이 모듈은 core.engine의 파싱/유틸 헬퍼(get_font_files, find_image_file,
split_into_scenes 등)에 의존하지만, engine.py는 모듈 최하단에서
이 모듈을 re-export하므로 순환 import는 발생하지 않는다.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from core.engine import (
    get_font_files,
    get_font_family_name,
    hex_to_rgb,
    find_image_file,
    optimize_image,
    split_into_scenes,
)

logger = logging.getLogger(__name__)


def set_run_font(run, font_name, size_pt=None, bold=False, italic=False, color=None):
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    if size_pt:
        run.font.size = Pt(size_pt)
    if bold:
        run.font.bold = True
    if italic:
        run.font.italic = True
    if color:
        run.font.color.rgb = hex_to_rgb(color) if isinstance(color, str) else color


def add_paragraph_spacing(paragraph, before_pt=0, after_pt=0, line_spacing=1.0):
    pPr = paragraph._p.get_or_add_pPr()
    spacing = OxmlElement('w:spacing')
    spacing.set(qn('w:before'), str(int(before_pt * 20)))
    spacing.set(qn('w:after'), str(int(after_pt * 20)))
    spacing.set(qn('w:line'), str(int(line_spacing * 240)))
    spacing.set(qn('w:lineRule'), 'auto')
    pPr.append(spacing)


def create_docx(entries, output_path, config, title="TRPG 리플레이", author=None, progress_callback=None):
    if progress_callback:
        progress_callback(0, 100, "DOCX 생성 준비 중...")
    doc = Document()

    if author is None:
        author = config.get('metadata', {}).get('author', 'GM')

    fonts = config.get('fonts', {})
    embedded = get_font_files(config)
    fallback = fonts.get('docx_fallback', {})
    style_config = config.get('style', {})
    narration_prefix = style_config.get('narration_prefix', '＿')

    body_font = get_font_family_name(embedded['body']) if embedded.get('body') else fallback.get('body', '맑은 고딕')
    name_font = get_font_family_name(embedded['name']) if embedded.get('name') else fallback.get('name', '맑은 고딕')

    cover_config = config.get('cover', {})
    if cover_config.get('include', True):
        cover_image = cover_config.get('image', '')
        if cover_image:
            img_path = find_image_file(cover_image, config)
            if img_path:
                img_data, _, _ = optimize_image(img_path, config)
                doc.add_picture(io.BytesIO(img_data), width=Inches(5))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

        if cover_config.get('title_on_cover', True):
            title_para = doc.add_paragraph()
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_run = title_para.add_run(title)
            set_run_font(title_run, name_font, size_pt=28, bold=True)
            add_paragraph_spacing(title_para, before_pt=72, after_pt=24)

        if cover_config.get('author_on_cover', True):
            auth_para = doc.add_paragraph()
            auth_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            auth_run = auth_para.add_run(author)
            set_run_font(auth_run, name_font, size_pt=12, color='#888888')

        doc.add_page_break()

    scenes = split_into_scenes(entries, config)

    for scene_idx, scene in enumerate(scenes):
        scene_title = scene.get('title')
        scene_entries = scene.get('entries', [])
        if progress_callback:
            pct = 10 + int(80 * scene_idx / max(len(scenes), 1))
            progress_callback(pct, 100, f"장면 {scene_idx+1}/{len(scenes)} 생성 중...")

        if scene_title:
            if scene_idx > 0:
                doc.add_page_break()

            title_para = doc.add_paragraph()
            title_para.alignment = WD_ALIGN_PARAGRAPH.LEFT

            title_has_marker = scene_title.startswith('■')
            display_title = scene_title if title_has_marker else f"■ {scene_title}"

            title_run = title_para.add_run(display_title)
            set_run_font(title_run, name_font, size_pt=14, bold=True)
            add_paragraph_spacing(title_para, before_pt=24, after_pt=16)

        for entry in scene_entries:
            t = entry['type']
            content = entry.get('content', '')
            name = entry.get('name', '')
            img = entry.get('image')

            if img:
                img_path = find_image_file(img, config)
                if img_path:
                    img_data, _, _ = optimize_image(img_path, config)
                    doc.add_picture(io.BytesIO(img_data), width=Inches(4))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

            if t == 'image' or not content.strip():
                continue

            para = doc.add_paragraph()

            if t == 'dialogue':
                if name:
                    name_run = para.add_run(f"{name}   ")
                    set_run_font(name_run, name_font, size_pt=11, bold=True)
                content_run = para.add_run(content)
                set_run_font(content_run, body_font, size_pt=11)
                add_paragraph_spacing(para, before_pt=2, after_pt=2, line_spacing=1.3)

            elif t == 'narration':
                prefix = narration_prefix if narration_prefix else ''
                content_run = para.add_run(f"{prefix}{content}")
                set_run_font(content_run, body_font, size_pt=10.5)
                para.paragraph_format.left_indent = Inches(0.3)
                add_paragraph_spacing(para, before_pt=8, after_pt=8, line_spacing=1.4)

            elif t == 'dice':
                dice_text = f"{name} : {content}" if name else content
                content_run = para.add_run(dice_text)
                set_run_font(content_run, name_font, size_pt=9, color='#888888')
                para.paragraph_format.left_indent = Inches(0.2)
                add_paragraph_spacing(para, before_pt=1, after_pt=1, line_spacing=1.2)

            elif t == 'system':
                content_run = para.add_run(content)
                set_run_font(content_run, name_font, size_pt=10, color='#666666')
                add_paragraph_spacing(para, before_pt=12, after_pt=12)

            elif t == 'effect':
                if name:
                    name_run = para.add_run(f"{name}\n")
                    set_run_font(name_run, name_font, size_pt=10, bold=True)
                content_run = para.add_run(content)
                set_run_font(content_run, name_font, size_pt=9, color='#444444')
                para.paragraph_format.left_indent = Inches(0.3)
                add_paragraph_spacing(para, before_pt=4, after_pt=4, line_spacing=1.2)

            elif t == 'whisper':
                content_run = para.add_run(content)
                set_run_font(content_run, body_font, size_pt=10, italic=True, color='#666666')
                para.paragraph_format.left_indent = Inches(0.4)

            else:
                content_run = para.add_run(content)
                set_run_font(content_run, body_font, size_pt=11)

    if progress_callback:
        progress_callback(95, 100, "DOCX 저장 중...")

    # 원자적 쓰기: 임시 파일에 작성 후 rename
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.docx', dir=os.path.dirname(output_path) or '.')
    os.close(tmp_fd)
    try:
        doc.save(tmp_path)
        if os.path.exists(output_path):
            os.replace(tmp_path, output_path)
        else:
            os.rename(tmp_path, output_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    if progress_callback:
        progress_callback(100, 100, "DOCX 생성 완료")
    logger.info("DOCX created: %s", output_path)
    return output_path
