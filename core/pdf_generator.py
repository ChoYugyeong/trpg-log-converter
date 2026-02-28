#!/usr/bin/env python3
"""
PDF 생성 모듈
reportlab 사용 - 표지, 목차, 이미지 처리 완전 지원
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    from reportlab.lib.pagesizes import A4, A5, B5, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, black, gray, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image,
        Table, TableStyle, KeepTogether, ListFlowable, ListItem
    )
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

logger = logging.getLogger(__name__)

# 페이지 크기 매핑
PAGE_SIZES = {
    'A4': A4,
    'A5': A5,
    'B5': B5,
    'Letter': letter,
    '신국판': (152*mm, 225*mm),
    '국판': (148*mm, 210*mm),
    '46배판': (128*mm, 188*mm),
    '문고판': (105*mm, 148*mm),
}


class NumberedCanvas(canvas.Canvas):
    """페이지 번호가 있는 캔버스"""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self._page_number_start = 1
        self._skip_first_pages = 2  # 표지, 목차 스킵

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for idx, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            # 페이지 번호 (표지, 목차 이후부터)
            if idx >= self._skip_first_pages:
                self.draw_page_number(idx - self._skip_first_pages + 1)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num):
        self.saveState()
        self.setFont('Helvetica', 9)
        self.setFillColor(gray)
        page_width = self._pagesize[0]
        self.drawCentredString(page_width / 2, 15*mm, str(page_num))
        self.restoreState()


def register_fonts(config: Dict) -> tuple:
    """한글 폰트 등록"""
    if not PDF_AVAILABLE:
        return None, None

    fonts_dir = Path(config.get('paths', {}).get('fonts_dir', './fonts'))
    body_font = 'Helvetica'
    name_font = 'Helvetica-Bold'
    registered_fonts = set()

    # 시스템 폰트 경로 동적 탐색
    import sys
    system_fonts = []

    if sys.platform == 'darwin':
        font_dirs = [Path('/System/Library/Fonts'), Path('/Library/Fonts'), Path.home() / 'Library/Fonts']
        font_candidates = [
            {'filename': 'AppleSDGothicNeo.ttc', 'index': 0, 'name': 'AppleSDGothicNeo'},
            {'filename': 'NanumMyeongjo.ttf', 'index': None, 'name': 'NanumMyeongjo'},
            {'filename': 'NanumGothic.ttf', 'index': None, 'name': 'NanumGothic'},
        ]
    elif sys.platform == 'win32':
        win_fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
        local_fonts = Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Windows/Fonts'
        font_dirs = [win_fonts, local_fonts]
        font_candidates = [
            {'filename': 'malgun.ttf', 'index': None, 'name': 'MalgunGothic'},
            {'filename': 'malgunbd.ttf', 'index': None, 'name': 'MalgunGothicBold'},
            {'filename': 'NanumGothic.ttf', 'index': None, 'name': 'NanumGothic'},
            {'filename': 'gulim.ttc', 'index': 0, 'name': 'Gulim'},
        ]
    else:  # Linux
        font_dirs = [
            Path('/usr/share/fonts'), Path('/usr/local/share/fonts'),
            Path.home() / '.local/share/fonts', Path.home() / '.fonts',
        ]
        font_candidates = [
            {'filename': 'NanumGothic.ttf', 'index': None, 'name': 'NanumGothic'},
            {'filename': 'NanumMyeongjo.ttf', 'index': None, 'name': 'NanumMyeongjo'},
        ]

    for candidate in font_candidates:
        for font_dir in font_dirs:
            font_path = font_dir / candidate['filename']
            if font_path.exists():
                system_fonts.append({
                    'path': str(font_path), 'index': candidate['index'], 'name': candidate['name']
                })
                break  # 첫 번째 발견 경로 사용

    # 앱 내장 폰트 우선 등록
    app_fonts_dir = Path(__file__).parent.parent / 'resources' / 'fonts'
    for fonts_path in [fonts_dir, app_fonts_dir]:
        if fonts_path.exists():
            for font_file in fonts_path.glob('*.ttf'):
                try:
                    font_name = font_file.stem
                    if font_name not in registered_fonts:
                        pdfmetrics.registerFont(TTFont(font_name, str(font_file)))
                        registered_fonts.add(font_name)

                        if 'pretendard' in font_name.lower():
                            body_font = font_name
                            name_font = font_name
                        elif 'myeongjo' in font_name.lower() or 'body' in font_name.lower():
                            body_font = font_name
                        elif 'gothic' in font_name.lower() or 'name' in font_name.lower():
                            name_font = font_name

                        logger.debug(f"폰트 로드: {font_name}")
                except Exception as e:
                    logger.warning(f"폰트 로드 실패: {font_file} - {e}")

    # 시스템 폰트 (폴백)
    if body_font == 'Helvetica':
        for font_info in system_fonts:
            font_path = font_info['path']
            if os.path.exists(font_path):
                try:
                    font_name = font_info['name']
                    if font_name not in registered_fonts:
                        if font_info['index'] is not None:
                            pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=font_info['index']))
                        else:
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                        registered_fonts.add(font_name)
                        body_font = font_name
                        name_font = font_name
                        logger.debug(f"시스템 폰트 로드: {font_name}")
                        break
                except Exception as e:
                    logger.warning(f"시스템 폰트 로드 실패: {font_path} - {e}")

    if body_font == 'Helvetica':
        logger.warning("한글 폰트를 찾을 수 없음 - 한글이 깨질 수 있습니다")

    return body_font, name_font


def find_image_file(filename: str, config: Dict) -> Optional[Path]:
    """이미지 파일 찾기 - 에러 처리 강화"""
    if not filename:
        return None

    images_dir = Path(config.get('paths', {}).get('images_dir', './images'))

    # 절대 경로
    if Path(filename).is_absolute():
        path = Path(filename)
        if path.exists():
            return path
        logger.warning(f"이미지 파일 없음: {filename}")
        return None

    # 상대 경로 검색
    search_paths = [
        Path(filename),
        images_dir / filename,
        Path(__file__).parent.parent / 'images' / filename,
    ]

    for path in search_paths:
        if path.exists():
            return path

    logger.warning(f"이미지 파일을 찾을 수 없음: {filename}")
    return None


def get_image_size(img_path: Path, max_width: float, max_height: float) -> tuple:
    """이미지 크기 계산 (비율 유지)"""
    try:
        from PIL import Image as PILImage
        with PILImage.open(img_path) as img:
            width, height = img.size
            ratio = min(max_width / width, max_height / height)
            return width * ratio, height * ratio
    except ImportError:
        # PIL 없으면 기본 크기
        return max_width * 0.8, max_height * 0.5
    except Exception as e:
        logger.warning(f"이미지 크기 계산 실패: {e}")
        return max_width * 0.8, max_height * 0.5


def create_styles(body_font: str, name_font: str, config: Dict) -> Dict[str, ParagraphStyle]:
    """PDF 스타일 정의"""
    styles = getSampleStyleSheet()
    style_config = config.get('style', {})

    custom_styles = {
        'CoverTitle': ParagraphStyle(
            'CoverTitle',
            parent=styles['Title'],
            fontName=name_font,
            fontSize=28,
            leading=36,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=HexColor(style_config.get('cover_title_color', '#ffffff')),
        ),
        'CoverSubtitle': ParagraphStyle(
            'CoverSubtitle',
            parent=styles['Normal'],
            fontName=body_font,
            fontSize=14,
            alignment=TA_CENTER,
            textColor=HexColor('#cccccc'),
            spaceAfter=10,
        ),
        'CoverAuthor': ParagraphStyle(
            'CoverAuthor',
            parent=styles['Normal'],
            fontName=body_font,
            fontSize=12,
            textColor=gray,
            spaceAfter=40,
            alignment=TA_CENTER,
        ),
        'TOCTitle': ParagraphStyle(
            'TOCTitle',
            parent=styles['Heading1'],
            fontName=name_font,
            fontSize=18,
            alignment=TA_CENTER,
            spaceBefore=30,
            spaceAfter=30,
        ),
        'TOCEntry': ParagraphStyle(
            'TOCEntry',
            parent=styles['Normal'],
            fontName=body_font,
            fontSize=11,
            leading=20,
            leftIndent=20,
        ),
        'SceneTitle': ParagraphStyle(
            'SceneTitle',
            parent=styles['Heading2'],
            fontName=name_font,
            fontSize=14,
            spaceBefore=25,
            spaceAfter=15,
            textColor=black,
            keepWithNext=True,
        ),
        'Dialogue': ParagraphStyle(
            'Dialogue',
            parent=styles['Normal'],
            fontName=body_font,
            fontSize=10.5,
            leading=16,
            spaceBefore=3,
            spaceAfter=3,
            alignment=TA_JUSTIFY,
        ),
        'DialogueName': ParagraphStyle(
            'DialogueName',
            parent=styles['Normal'],
            fontName=name_font,
            fontSize=10.5,
            textColor=HexColor('#333333'),
        ),
        'Narration': ParagraphStyle(
            'Narration',
            parent=styles['Normal'],
            fontName=body_font,
            fontSize=10,
            leading=17,
            leftIndent=12*mm,
            spaceBefore=8,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
        ),
        'Dice': ParagraphStyle(
            'Dice',
            parent=styles['Normal'],
            fontName=name_font,
            fontSize=8.5,
            textColor=HexColor(style_config.get('dice_color', '#888888')),
            leftIndent=6*mm,
            spaceBefore=2,
            spaceAfter=2,
        ),
        'System': ParagraphStyle(
            'System',
            parent=styles['Normal'],
            fontName=name_font,
            fontSize=9.5,
            textColor=HexColor('#666666'),
            spaceBefore=12,
            spaceAfter=12,
            alignment=TA_CENTER,
        ),
        'Effect': ParagraphStyle(
            'Effect',
            parent=styles['Normal'],
            fontName=name_font,
            fontSize=9,
            textColor=HexColor('#444444'),
            leftIndent=8*mm,
            spaceBefore=5,
            spaceAfter=5,
            backColor=HexColor('#f5f5f5'),
        ),
        'ImageCaption': ParagraphStyle(
            'ImageCaption',
            parent=styles['Normal'],
            fontName=body_font,
            fontSize=9,
            textColor=gray,
            alignment=TA_CENTER,
            spaceBefore=5,
            spaceAfter=15,
        ),
    }

    return custom_styles


def escape_xml(text: str) -> str:
    """XML 특수문자 이스케이프"""
    if not text:
        return ''
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def create_cover(story: List, config: Dict, title: str, author: str,
                 styles: Dict[str, ParagraphStyle], page_size: tuple):
    """표지 생성"""
    cover_config = config.get('cover', {})
    if not cover_config.get('include', True):
        return

    page_width, page_height = page_size

    # 표지 이미지
    cover_image = cover_config.get('image', '')
    if cover_image:
        img_path = find_image_file(cover_image, config)
        if img_path:
            try:
                img_width, img_height = get_image_size(
                    img_path,
                    page_width - 40*mm,
                    page_height - 100*mm
                )
                story.append(Spacer(1, 20*mm))
                story.append(Image(str(img_path), width=img_width, height=img_height))
                story.append(Spacer(1, 15*mm))
            except Exception as e:
                logger.error(f"표지 이미지 로드 실패: {e}")
    else:
        story.append(Spacer(1, page_height * 0.3))

    # 제목
    if cover_config.get('title_on_cover', True):
        story.append(Paragraph(escape_xml(title), styles['CoverTitle']))

    # 부제
    subtitle = cover_config.get('subtitle', '')
    if subtitle:
        story.append(Paragraph(escape_xml(subtitle), styles['CoverSubtitle']))

    # 저자
    if cover_config.get('author_on_cover', True):
        story.append(Spacer(1, 20*mm))
        story.append(Paragraph(escape_xml(author), styles['CoverAuthor']))

    story.append(PageBreak())


def create_toc(story: List, scenes: List[Dict], config: Dict,
               styles: Dict[str, ParagraphStyle]):
    """목차 생성"""
    toc_config = config.get('toc', {})
    if not toc_config.get('include', True) or len(scenes) <= 1:
        return

    toc_title = toc_config.get('title', '목차')
    story.append(Paragraph(escape_xml(toc_title), styles['TOCTitle']))
    story.append(Spacer(1, 10*mm))

    for idx, scene in enumerate(scenes):
        scene_title = scene.get('title') or f"장면 {idx + 1}"
        # 목차 항목
        toc_entry = f"{idx + 1}. {escape_xml(scene_title)}"
        story.append(Paragraph(toc_entry, styles['TOCEntry']))

    story.append(PageBreak())


def add_image_to_story(story: List, img_path: Path, config: Dict,
                       styles: Dict[str, ParagraphStyle], page_size: tuple,
                       caption: str = None):
    """이미지를 스토리에 추가"""
    page_width, page_height = page_size
    max_width = page_width - 50*mm
    max_height = page_height * 0.5

    try:
        img_width, img_height = get_image_size(img_path, max_width, max_height)
        story.append(Spacer(1, 5*mm))
        story.append(Image(str(img_path), width=img_width, height=img_height))

        if caption and config.get('images', {}).get('show_caption', True):
            story.append(Paragraph(escape_xml(caption), styles['ImageCaption']))
        else:
            story.append(Spacer(1, 5*mm))
    except Exception as e:
        logger.error(f"이미지 추가 실패: {img_path} - {e}")


def create_pdf(entries: List[Dict], output_path: str, config: Dict,
               title: str = "TRPG 리플레이", author: str = None) -> Optional[str]:
    """PDF 생성 - 완전한 기능"""
    if not PDF_AVAILABLE:
        logger.error("PDF 라이브러리 없음 (reportlab 설치 필요)")
        return None

    try:
        if author is None:
            author = config.get('metadata', {}).get('author', 'GM')

        # 폰트 등록
        body_font, name_font = register_fonts(config)

        # 페이지 크기
        page_format = config.get('page', {}).get('format', 'A5')
        page_size = PAGE_SIZES.get(page_format, A5)

        # 여백
        margins = config.get('page', {}).get('margins', {})
        left_margin = margins.get('left', 15) * mm
        right_margin = margins.get('right', 15) * mm
        top_margin = margins.get('top', 20) * mm
        bottom_margin = margins.get('bottom', 20) * mm

        # 문서 생성
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=right_margin,
            leftMargin=left_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
            title=title,
            author=author,
        )

        # 스타일 생성
        pdf_styles = create_styles(body_font, name_font, config)
        style_config = config.get('style', {})
        narration_prefix = style_config.get('narration_prefix', '＿')

        story = []

        # 장면 분할
        from core.engine import split_into_scenes
        scenes = split_into_scenes(entries, config)

        # 표지
        create_cover(story, config, title, author, pdf_styles, page_size)

        # 목차
        create_toc(story, scenes, config, pdf_styles)

        # 본문
        for scene_idx, scene in enumerate(scenes):
            scene_title = scene.get('title')
            scene_entries = scene.get('entries', [])

            if scene_idx > 0:
                story.append(PageBreak())

            # 장면 제목
            if scene_title:
                display_title = scene_title if scene_title.startswith('■') else f"■ {scene_title}"
                story.append(Paragraph(escape_xml(display_title), pdf_styles['SceneTitle']))

            # 엔트리 처리
            for entry in scene_entries:
                entry_type = entry.get('type', 'dialogue')
                content = entry.get('content', '')
                name = entry.get('name', '')
                img = entry.get('image')

                # 이미지 처리
                if img:
                    img_path = find_image_file(img, config)
                    if img_path:
                        add_image_to_story(story, img_path, config, pdf_styles, page_size, img)

                if not content or not content.strip():
                    continue

                # 내용 이스케이프
                content_escaped = escape_xml(content)
                name_escaped = escape_xml(name) if name else ''

                # 타입별 처리
                if entry_type == 'dialogue':
                    if name_escaped:
                        text = f"<b>{name_escaped}</b>   {content_escaped}"
                    else:
                        text = content_escaped
                    story.append(Paragraph(text, pdf_styles['Dialogue']))

                elif entry_type == 'narration':
                    prefix = narration_prefix if narration_prefix else ''
                    story.append(Paragraph(f"{prefix}{content_escaped}", pdf_styles['Narration']))

                elif entry_type == 'dice':
                    dice_text = f"{name_escaped} : {content_escaped}" if name_escaped else content_escaped
                    story.append(Paragraph(dice_text, pdf_styles['Dice']))

                elif entry_type == 'system':
                    story.append(Paragraph(content_escaped, pdf_styles['System']))

                elif entry_type == 'effect':
                    if name_escaped:
                        story.append(Paragraph(f"<b>{name_escaped}</b>", pdf_styles['DialogueName']))
                    story.append(Paragraph(content_escaped, pdf_styles['Effect']))

                else:
                    story.append(Paragraph(content_escaped, pdf_styles['Dialogue']))

        # 원자적 쓰기: 임시 파일에 빌드 후 rename
        import tempfile
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pdf', dir=os.path.dirname(output_path) or '.')
        os.close(tmp_fd)
        try:
            tmp_doc = SimpleDocTemplate(
                tmp_path, pagesize=page_size,
                rightMargin=right_margin, leftMargin=left_margin,
                topMargin=top_margin, bottomMargin=bottom_margin,
                title=title, author=author,
            )
            tmp_doc.build(story, canvasmaker=NumberedCanvas)
            if os.path.exists(output_path):
                os.replace(tmp_path, output_path)
            else:
                os.rename(tmp_path, output_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
        logger.info(f"PDF 생성 완료: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"PDF 생성 실패: {e}", exc_info=True)
        return None


def create_pdf_simple(entries: List[Dict], output_path: str, config: Dict,
                      title: str = "TRPG 리플레이", author: str = None) -> Optional[str]:
    """간단한 PDF 생성 (목차/표지 없음, 대용량 파일용)"""
    if not PDF_AVAILABLE:
        return None

    try:
        if author is None:
            author = config.get('metadata', {}).get('author', 'GM')

        body_font, name_font = register_fonts(config)

        page_format = config.get('page', {}).get('format', 'A5')
        page_size = PAGE_SIZES.get(page_format, A5)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )

        styles = getSampleStyleSheet()
        dialogue_style = ParagraphStyle(
            'SimpleDialogue',
            parent=styles['Normal'],
            fontName=body_font,
            fontSize=10,
            leading=14,
            spaceBefore=2,
            spaceAfter=2,
        )

        story = []
        batch_size = 1000  # 메모리 최적화

        for i, entry in enumerate(entries):
            content = entry.get('content', '')
            name = entry.get('name', '')

            if not content.strip():
                continue

            content_escaped = escape_xml(content)
            name_escaped = escape_xml(name) if name else ''

            if name_escaped:
                text = f"<b>{name_escaped}</b>: {content_escaped}"
            else:
                text = content_escaped

            story.append(Paragraph(text, dialogue_style))

            # 메모리 관리: 일정 간격으로 가비지 컬렉션 힌트
            if i > 0 and i % batch_size == 0:
                import gc
                gc.collect()

        doc.build(story)
        logger.info(f"간단 PDF 생성 완료: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"간단 PDF 생성 실패: {e}")
        return None
