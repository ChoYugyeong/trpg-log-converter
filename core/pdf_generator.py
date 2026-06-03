#!/usr/bin/env python3
"""
PDF 생성 모듈
reportlab 사용 - 표지, 목차, 이미지 처리 완전 지원
"""

import logging
import os
from pathlib import Path

try:
    from reportlab.lib.colors import HexColor, black, gray
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4, A5, B5, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch, mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

logger = logging.getLogger(__name__)

# 페이지 크기 매핑
PAGE_SIZES = {
    "A4": A4,
    "A5": A5,
    "B5": B5,
    "Letter": letter,
    "신국판": (152 * mm, 225 * mm),
    "국판": (148 * mm, 210 * mm),
    "46배판": (128 * mm, 188 * mm),
    "문고판": (105 * mm, 148 * mm),
}


class NumberedCanvas(canvas.Canvas):
    """페이지 번호가 있는 캔버스.

    ``skip_first_pages`` 는 표지 + 목차 등 본문 앞에 붙는 페이지 수를 반영해야
    하며, ``make_numbered_canvas(skip)`` 으로 생성된 콜러블을
    ``SimpleDocTemplate.build(canvasmaker=...)`` 에 전달해 주입한다.
    """

    skip_first_pages: int = 0

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self._page_number_start = 1

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        for idx, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            if idx >= self.skip_first_pages:
                self.draw_page_number(idx - self.skip_first_pages + 1)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(gray)
        page_width = self._pagesize[0]
        self.drawCentredString(page_width / 2, 15 * mm, str(page_num))
        self.restoreState()


def make_numbered_canvas(skip_first_pages: int) -> type:
    """Return a NumberedCanvas subclass bound to ``skip_first_pages``.

    ``SimpleDocTemplate.build(canvasmaker=...)`` instantiates the canvas itself,
    so we can't pass constructor args. We bake the value into a fresh subclass.
    """
    skip = max(0, int(skip_first_pages))
    cls_name = f"NumberedCanvas_skip{skip}"
    return type(cls_name, (NumberedCanvas,), {"skip_first_pages": skip})


def register_fonts(config: dict) -> tuple:
    """한글 폰트 등록.

    DOCX 와 동일한 폰트(``fonts.docx_fallback.body/name``)를 우선 사용한다.
    해당 이름의 TTF/OTF 파일을 시스템 폰트 디렉터리에서 찾아 reportlab 에
    등록한다. 못 찾으면 기존 fallback(malgun / NanumGothic 등).
    """
    if not PDF_AVAILABLE:
        return None, None

    fonts_dir = Path(config.get("paths", {}).get("fonts_dir", "./fonts"))
    body_font = "Helvetica"
    name_font = "Helvetica-Bold"
    registered_fonts = set()

    # DOCX 와 동일하게 fonts.docx_fallback 의 폰트 이름을 우선 탐색
    fallback = config.get("fonts", {}).get("docx_fallback", {}) or {}
    requested_body = fallback.get("body")
    requested_name = fallback.get("name")

    # 시스템 폰트 경로 동적 탐색
    import sys

    system_fonts = []

    if sys.platform == "darwin":
        font_dirs = [
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library/Fonts",
        ]
        font_candidates = [
            {"filename": "AppleSDGothicNeo.ttc", "index": 0, "name": "AppleSDGothicNeo"},
            {"filename": "NanumMyeongjo.ttf", "index": None, "name": "NanumMyeongjo"},
            {"filename": "NanumGothic.ttf", "index": None, "name": "NanumGothic"},
        ]
    elif sys.platform == "win32":
        win_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        local_fonts = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"
        font_dirs = [win_fonts, local_fonts]
        font_candidates = [
            {"filename": "malgun.ttf", "index": None, "name": "MalgunGothic"},
            {"filename": "malgunbd.ttf", "index": None, "name": "MalgunGothicBold"},
            {"filename": "NanumGothic.ttf", "index": None, "name": "NanumGothic"},
            {"filename": "gulim.ttc", "index": 0, "name": "Gulim"},
        ]
    else:  # Linux
        font_dirs = [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".local/share/fonts",
            Path.home() / ".fonts",
        ]
        font_candidates = [
            {"filename": "NanumGothic.ttf", "index": None, "name": "NanumGothic"},
            {"filename": "NanumMyeongjo.ttf", "index": None, "name": "NanumMyeongjo"},
        ]

    for candidate in font_candidates:
        # candidate dict 의 value 가 ``str | int | None`` 으로 추론되는 것을
        # 좁히기 위해 명시적 str 캐스트. filename 은 위 리터럴 정의에서 항상 str.
        filename = str(candidate["filename"])
        for font_dir in font_dirs:
            font_path = font_dir / filename
            if font_path.exists():
                system_fonts.append(
                    {"path": str(font_path), "index": candidate["index"], "name": candidate["name"]}
                )
                break  # 첫 번째 발견 경로 사용

    # 앱 내장 폰트 우선 등록
    app_fonts_dir = Path(__file__).parent.parent / "resources" / "fonts"
    for fonts_path in [fonts_dir, app_fonts_dir]:
        if fonts_path.exists():
            for font_file in fonts_path.glob("*.ttf"):
                try:
                    font_name = font_file.stem
                    if font_name not in registered_fonts:
                        pdfmetrics.registerFont(TTFont(font_name, str(font_file)))
                        registered_fonts.add(font_name)

                        if "pretendard" in font_name.lower():
                            body_font = font_name
                            name_font = font_name
                        elif "myeongjo" in font_name.lower() or "body" in font_name.lower():
                            body_font = font_name
                        elif "gothic" in font_name.lower() or "name" in font_name.lower():
                            name_font = font_name

                        logger.debug(f"폰트 로드: {font_name}")
                except Exception as e:
                    logger.warning(f"폰트 로드 실패: {font_file} - {e}")

    # 시스템 폰트 (폴백)
    if body_font == "Helvetica":
        for font_info in system_fonts:
            font_path = font_info["path"]
            if os.path.exists(font_path):
                try:
                    font_name = font_info["name"]
                    if font_name not in registered_fonts:
                        if font_info["index"] is not None:
                            pdfmetrics.registerFont(
                                TTFont(font_name, font_path, subfontIndex=font_info["index"])
                            )
                        else:
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                        registered_fonts.add(font_name)
                        body_font = font_name
                        name_font = font_name
                        logger.debug(f"시스템 폰트 로드: {font_name}")
                        break
                except Exception as e:
                    logger.warning(f"시스템 폰트 로드 실패: {font_path} - {e}")

    # DOCX 와 동일한 한글 폰트 이름(본명조/부크크 고딕 등)을 reportlab 에 등록 시도.
    # Windows 에서는 폰트 family name 과 파일명이 다를 수 있어 QFontDatabase 를
    # 이용해 family → 파일 경로 매핑을 시도한다.
    try:
        from PySide6.QtGui import QFont, QFontInfo, QRawFont  # noqa: F401
        from PySide6.QtWidgets import QApplication

        if QApplication.instance() is not None:
            import sys as _sys

            win_dir = (
                Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
                if _sys.platform == "win32"
                else None
            )
            for label, family in (("body", requested_body), ("name", requested_name)):
                if not family:
                    continue
                try:
                    qf = QFont(family)
                    raw = QRawFont.fromFont(qf)
                    actual_family = raw.familyName()
                    if not actual_family:
                        continue
                    # Windows 폰트 폴더에서 파일명으로 매칭 시도
                    if win_dir and win_dir.exists():
                        candidates = []
                        for ext in ("*.ttf", "*.otf", "*.ttc"):
                            candidates.extend(win_dir.glob(ext))
                        # 한글 가족명 혹은 파일명 prefix 매칭
                        base_key = family.replace(" ", "").lower()
                        for f in candidates:
                            stem = f.stem.lower().replace(" ", "").replace("_", "").replace("-", "")
                            if base_key in stem or any(
                                k in stem for k in (base_key[:4], base_key[-4:])
                            ):
                                try:
                                    reg_name = f.stem
                                    if reg_name not in registered_fonts:
                                        if f.suffix.lower() == ".ttc":
                                            pdfmetrics.registerFont(
                                                TTFont(reg_name, str(f), subfontIndex=0)
                                            )
                                        else:
                                            pdfmetrics.registerFont(TTFont(reg_name, str(f)))
                                        registered_fonts.add(reg_name)
                                    if label == "body":
                                        body_font = reg_name
                                    else:
                                        name_font = reg_name
                                    logger.info("PDF 폰트 매칭: %s → %s", family, f.name)
                                    break
                                except Exception as fe:
                                    logger.debug("폰트 등록 실패 %s: %s", f, fe)
                except Exception as fe:
                    logger.debug("폰트 매칭 실패 %s: %s", family, fe)
    except ImportError:
        pass

    if body_font == "Helvetica":
        logger.warning("한글 폰트를 찾을 수 없음 - 한글이 깨질 수 있습니다")

    return body_font, name_font


def find_image_file(filename: str, config: dict) -> Path | None:
    """이미지 파일 찾기 - 에러 처리 강화"""
    if not filename:
        return None

    images_dir = Path(config.get("paths", {}).get("images_dir", "./images"))

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
        Path(__file__).parent.parent / "images" / filename,
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


def _safe_float(value, default: float) -> float:
    """설정값을 안전하게 float 로 변환한다 (문자열일 수 있음)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_hex(value, default: str) -> str:
    """'#' 으로 시작하는 hex 문자열만 허용하고, 아니면 default 를 돌려준다."""
    if isinstance(value, str) and value.startswith("#"):
        return value
    return default


def create_styles(body_font: str, name_font: str, config: dict) -> dict[str, ParagraphStyle]:
    """PDF 스타일 정의"""
    styles = getSampleStyleSheet()
    style_config = config.get("style", {})
    cover_config = config.get("cover", {})
    header_config = config.get("header", {}) or {}

    name_color = _safe_hex(style_config.get("name_color", "#2d2d2d"), "#2d2d2d")
    body_text = _safe_hex(style_config.get("body_text", "#1a1a1a"), "#1a1a1a")
    system_color = _safe_hex(style_config.get("system_color", "#666666"), "#666666")
    effect_bg = _safe_hex(style_config.get("effect_bg", "#f5f5f5"), "#f5f5f5")
    effect_border = _safe_hex(style_config.get("effect_border", "#cccccc"), "#cccccc")
    dialogue_line_height = _safe_float(style_config.get("dialogue_line_height", 1.5), 1.5)
    narration_line_height = _safe_float(style_config.get("narration_line_height", 1.7), 1.7)
    narration_indent = _safe_float(style_config.get("narration_indent", 1.5), 1.5)

    header_box = bool(header_config.get("box", False))
    header_box_color = _safe_hex(header_config.get("box_color", "#f5f5f5"), "#f5f5f5")

    custom_styles = {
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontName=name_font,
            fontSize=28,
            leading=36,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=HexColor(cover_config.get("title_color", "#ffffff")),
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=14,
            alignment=TA_CENTER,
            textColor=HexColor("#cccccc"),
            spaceAfter=10,
        ),
        "CoverAuthor": ParagraphStyle(
            "CoverAuthor",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=12,
            textColor=gray,
            spaceAfter=40,
            alignment=TA_CENTER,
        ),
        "TOCTitle": ParagraphStyle(
            "TOCTitle",
            parent=styles["Heading1"],
            fontName=name_font,
            fontSize=18,
            alignment=TA_CENTER,
            spaceBefore=30,
            spaceAfter=30,
        ),
        "TOCEntry": ParagraphStyle(
            "TOCEntry",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=11,
            leading=20,
            leftIndent=20,
        ),
        "SceneTitle": (
            lambda hc: ParagraphStyle(
                "SceneTitle",
                parent=styles["Heading2"],
                fontName=name_font,
                fontSize=hc["size"],
                spaceBefore=hc["size"] * 2.5,
                spaceAfter=hc["size"] * 1.2,
                alignment=TA_CENTER,
                textColor=HexColor(hc["color"])
                if isinstance(hc["color"], str) and hc["color"].startswith("#")
                else black,
                keepWithNext=True,
                **(
                    {
                        "backColor": HexColor(header_box_color),
                        "borderPadding": 6,
                    }
                    if header_box
                    else {}
                ),
            )
        )(
            {
                "size": _safe_float(header_config.get("size", 24), 24),
                "color": header_config.get("color", "#1a1a1a"),
            }
        ),
        "SceneEnd": ParagraphStyle(
            "SceneEnd",
            parent=styles["Normal"],
            fontName=name_font,
            fontSize=9,
            textColor=HexColor("#999999"),
            alignment=TA_CENTER,
            spaceBefore=18,
            spaceAfter=6,
        ),
        "Dialogue": ParagraphStyle(
            "Dialogue",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=10.5,
            leading=10.5 * dialogue_line_height,
            textColor=HexColor(body_text),
            spaceBefore=3,
            spaceAfter=3,
            alignment=TA_JUSTIFY,
        ),
        "DialogueName": ParagraphStyle(
            "DialogueName",
            parent=styles["Normal"],
            fontName=name_font,
            fontSize=10.5,
            textColor=HexColor(name_color),
        ),
        "Narration": ParagraphStyle(
            "Narration",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=10,
            leading=10 * narration_line_height,
            textColor=HexColor(body_text),
            leftIndent=narration_indent * 8 * mm,
            spaceBefore=8,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
        ),
        "Dice": ParagraphStyle(
            "Dice",
            parent=styles["Normal"],
            fontName=name_font,
            fontSize=8.5,
            textColor=HexColor(style_config.get("dice_color", "#888888")),
            leftIndent=6 * mm,
            spaceBefore=2,
            spaceAfter=2,
        ),
        "System": ParagraphStyle(
            "System",
            parent=styles["Normal"],
            fontName=name_font,
            fontSize=9.5,
            textColor=HexColor(system_color),
            spaceBefore=12,
            spaceAfter=12,
            alignment=TA_CENTER,
        ),
        "Effect": ParagraphStyle(
            "Effect",
            parent=styles["Normal"],
            fontName=name_font,
            fontSize=9,
            textColor=HexColor("#444444"),
            leftIndent=8 * mm,
            spaceBefore=5,
            spaceAfter=5,
            backColor=HexColor(effect_bg),
            borderColor=HexColor(effect_border),
            borderWidth=1,
            borderPadding=4,
        ),
        "ImageCaption": ParagraphStyle(
            "ImageCaption",
            parent=styles["Normal"],
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
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def create_cover(
    story: list,
    config: dict,
    title: str,
    author: str,
    styles: dict[str, ParagraphStyle],
    page_size: tuple,
):
    """표지 생성"""
    cover_config = config.get("cover", {})
    if not cover_config.get("include", True):
        return

    page_width, page_height = page_size

    # 표지 이미지
    cover_image = cover_config.get("image", "")
    if cover_image:
        img_path = find_image_file(cover_image, config)
        if img_path:
            try:
                img_width, img_height = get_image_size(
                    img_path, page_width - 40 * mm, page_height - 100 * mm
                )
                story.append(Spacer(1, 20 * mm))
                story.append(Image(str(img_path), width=img_width, height=img_height))
                story.append(Spacer(1, 15 * mm))
            except Exception as e:
                logger.error(f"표지 이미지 로드 실패: {e}")
    else:
        story.append(Spacer(1, page_height * 0.3))

    # 제목
    if cover_config.get("title_on_cover", True):
        story.append(Paragraph(escape_xml(title), styles["CoverTitle"]))

    # 부제
    subtitle = cover_config.get("subtitle", "")
    if subtitle:
        story.append(Paragraph(escape_xml(subtitle), styles["CoverSubtitle"]))

    # 저자
    if cover_config.get("author_on_cover", True):
        story.append(Spacer(1, 20 * mm))
        story.append(Paragraph(escape_xml(author), styles["CoverAuthor"]))

    story.append(PageBreak())


def create_toc(story: list, scenes: list[dict], config: dict, styles: dict[str, ParagraphStyle]):
    """목차 생성"""
    from core.renderers.toc_filter import filter_toc_scenes

    toc_config = config.get("toc", {})
    if not toc_config.get("include", True) or len(scenes) <= 1:
        return

    filtered = filter_toc_scenes(scenes, config)
    if not filtered:
        return  # 필터링 결과 전부 제외 → TOC 생략 (빈 페이지 방지)

    toc_title = toc_config.get("title", "목차")
    story.append(Paragraph(escape_xml(toc_title), styles["TOCTitle"]))
    story.append(Spacer(1, 10 * mm))

    # 표시 번호는 1부터 순차 — 원본 인덱스(original_idx) 와 다를 수 있음.
    # 본문 챕터 매핑은 PDF 의 bookmark 가 별도 처리하므로 표시 번호 재할당 안전.
    for display_n, (_orig_idx, scene) in enumerate(filtered, start=1):
        scene_title = scene.get("title") or f"장면 {display_n}"
        toc_entry = f"{display_n}. {escape_xml(scene_title)}"
        story.append(Paragraph(toc_entry, styles["TOCEntry"]))

    story.append(PageBreak())


def _pdf_divider_flowables(config: dict, pdf_styles: dict) -> list:
    """장면 구분선(장식)을 PDF flowable 리스트로. type 별 텍스트/이미지/선."""
    d = (config or {}).get("divider", {}) or {}
    dtype = d.get("type", "텍스트/기호")
    if dtype == "사용 안 함":
        return []
    flow: list = []
    if dtype == "이미지":
        img_b64 = d.get("image", "")
        if not img_b64:
            return []
        try:
            import base64
            import io as _io

            from PIL import Image as PILImage

            data = base64.b64decode(img_b64)
            pil = PILImage.open(_io.BytesIO(data))
            w, h = pil.size
            target_h = float(d.get("img_height", 40)) * 0.75  # px → pt
            target_w = target_h * (w / h) if h else target_h
            img = Image(_io.BytesIO(data), width=target_w, height=target_h)
            img.hAlign = "CENTER"
            flow.append(img)
        except Exception:
            return []
    elif dtype == "선 스타일":
        try:
            from reportlab.platypus import HRFlowable

            try:
                col = HexColor(d.get("line_color", "#cccccc"))
            except Exception:
                col = gray
            flow.append(
                HRFlowable(
                    width=f"{float(d.get('line_width', 60))}%",
                    thickness=float(d.get("line_thickness", 1)),
                    color=col,
                    spaceBefore=2,
                    spaceAfter=2,
                    hAlign="CENTER",
                )
            )
        except Exception:
            return []
    else:  # 텍스트/기호
        text = d.get("text", "")
        if not text.strip():
            return []
        c = d.get("color", "#888888")
        flow.append(Paragraph(f'<font color="{c}">{escape_xml(text)}</font>', pdf_styles["SceneEnd"]))
    if flow:
        flow.append(Spacer(1, 8))
    return flow


def add_image_to_story(
    story: list,
    img_path: Path,
    config: dict,
    styles: dict[str, ParagraphStyle],
    page_size: tuple,
    caption: str | None = None,
):
    """이미지를 스토리에 추가"""
    page_width, page_height = page_size
    max_width = page_width - 50 * mm
    max_height = page_height * 0.5

    try:
        img_width, img_height = get_image_size(img_path, max_width, max_height)
        story.append(Spacer(1, 5 * mm))
        story.append(Image(str(img_path), width=img_width, height=img_height))

        if caption and config.get("images", {}).get("show_caption", True):
            story.append(Paragraph(escape_xml(caption), styles["ImageCaption"]))
        else:
            story.append(Spacer(1, 5 * mm))
    except Exception as e:
        logger.error(f"이미지 추가 실패: {img_path} - {e}")


def create_pdf(
    entries: list[dict],
    output_path: str,
    config: dict,
    title: str = "TRPG 리플레이",
    author: str | None = None,
) -> str | None:
    """PDF 생성 - 완전한 기능"""
    if not PDF_AVAILABLE:
        logger.error("PDF 라이브러리 없음 (reportlab 설치 필요)")
        return None

    try:
        if author is None:
            author = config.get("metadata", {}).get("author", "GM")

        # 폰트 등록
        body_font, name_font = register_fonts(config)

        # 페이지 크기 — DOCX 와 공용인 core.layout 헬퍼 사용
        from core.layout import get_page_format, get_page_margins_inch, parse_page_format

        page_w_mm, page_h_mm = parse_page_format(get_page_format(config))
        page_size = (page_w_mm * mm, page_h_mm * mm)

        # 여백 — DOCX 와 같은 inch 단위
        margins_inch = get_page_margins_inch(config)
        left_margin = margins_inch["left"] * inch
        right_margin = margins_inch["right"] * inch
        top_margin = margins_inch["top"] * inch
        bottom_margin = margins_inch["bottom"] * inch

        # 문서 생성
        SimpleDocTemplate(
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
        style_config = config.get("style", {})
        narration_prefix = style_config.get("narration_prefix", "＿")

        story = []

        # 장면 분할
        from core.parsers.pipeline import split_into_scenes

        scenes = split_into_scenes(entries, config)

        # 표지
        create_cover(story, config, title, author, pdf_styles, page_size)

        # 목차
        create_toc(story, scenes, config, pdf_styles)

        # 본문
        drop_cap = bool(config.get("style", {}).get("first_letter", False))
        page_break_enabled = config.get("layout", {}).get("page_break", True)
        for scene_idx, scene in enumerate(scenes):
            scene_title = scene.get("title")
            scene_entries = scene.get("entries", [])
            # 드롭캡: 이 챕터의 첫 나레이션 문단에만 적용.
            dropcap_pending = drop_cap

            if scene_idx > 0 and page_break_enabled:
                story.append(PageBreak())

            # 장면 제목 — 시각적 마커는 제거하고 prefix/suffix 적용
            if scene_title:
                header_cfg = config.get("header", {}) or {}
                base_title = scene_title.lstrip("■▶ ").strip() or scene_title
                display_title = (
                    f"{header_cfg.get('prefix', '')}{base_title}{header_cfg.get('suffix', '')}"
                )
                story.append(Paragraph(escape_xml(display_title), pdf_styles["SceneTitle"]))
                # 장면 구분선(장식) — 제목 아래
                for _f in _pdf_divider_flowables(config, pdf_styles):
                    story.append(_f)

            # 엔트리 처리
            for entry in scene_entries:
                entry_type = entry.get("type", "dialogue")
                content = entry.get("content", "")
                name = entry.get("name", "")
                img = entry.get("image")

                # 이미지 처리
                if img:
                    img_path = find_image_file(img, config)
                    if img_path:
                        add_image_to_story(story, img_path, config, pdf_styles, page_size, img)

                if not content or not content.strip():
                    continue

                # 내용 이스케이프
                content_escaped = escape_xml(content)
                name_escaped = escape_xml(name) if name else ""

                # 타입별 처리
                if entry_type == "dialogue":
                    if name_escaped:
                        text = f"<b>{name_escaped}</b>   {content_escaped}"
                    else:
                        text = content_escaped
                    story.append(Paragraph(text, pdf_styles["Dialogue"]))

                elif entry_type == "narration":
                    prefix = narration_prefix if narration_prefix else ""
                    if dropcap_pending:
                        from core.utils import split_first_grapheme

                        first, rest = split_first_grapheme(content.lstrip())
                        cap = f'<font size="30">{escape_xml(first)}</font>'
                        story.append(
                            Paragraph(f"{cap}{escape_xml(rest)}", pdf_styles["Narration"])
                        )
                        dropcap_pending = False
                    else:
                        story.append(
                            Paragraph(f"{prefix}{content_escaped}", pdf_styles["Narration"])
                        )

                elif entry_type == "dice":
                    dice_text = (
                        f"{name_escaped} : {content_escaped}" if name_escaped else content_escaped
                    )
                    story.append(Paragraph(dice_text, pdf_styles["Dice"]))

                elif entry_type == "system":
                    story.append(Paragraph(content_escaped, pdf_styles["System"]))

                elif entry_type == "effect":
                    if name_escaped:
                        story.append(
                            Paragraph(f"<b>{name_escaped}</b>", pdf_styles["DialogueName"])
                        )
                    story.append(Paragraph(content_escaped, pdf_styles["Effect"]))

                elif entry_type == "scene_end":
                    # 직전 챕터 마지막 줄에 작은 폰트로 가운데 정렬
                    story.append(Paragraph(content_escaped, pdf_styles["SceneEnd"]))

                else:
                    story.append(Paragraph(content_escaped, pdf_styles["Dialogue"]))

        # 원자적 쓰기: 임시 파일에 빌드 후 rename
        import tempfile

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf", dir=os.path.dirname(output_path) or ".")
        os.close(tmp_fd)
        try:
            tmp_doc = SimpleDocTemplate(
                tmp_path,
                pagesize=page_size,
                rightMargin=right_margin,
                leftMargin=left_margin,
                topMargin=top_margin,
                bottomMargin=bottom_margin,
                title=title,
                author=author,
            )
            # 본문 앞에 들어간 페이지 수만큼 페이지 번호 표시를 지연시킨다.
            cover_included = bool(config.get("cover", {}).get("include", True))
            toc_included = bool(config.get("toc", {}).get("include", True) and len(scenes) > 1)
            skip = int(cover_included) + int(toc_included)
            tmp_doc.build(story, canvasmaker=make_numbered_canvas(skip))
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


def create_pdf_simple(
    entries: list[dict],
    output_path: str,
    config: dict,
    title: str = "TRPG 리플레이",
    author: str | None = None,
) -> str | None:
    """간단한 PDF 생성 (목차/표지 없음, 대용량 파일용)"""
    if not PDF_AVAILABLE:
        return None

    try:
        if author is None:
            author = config.get("metadata", {}).get("author", "GM")

        body_font, _name_font = register_fonts(config)

        page_format = config.get("page", {}).get("format", "A5")
        page_size = PAGE_SIZES.get(page_format, A5)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        dialogue_style = ParagraphStyle(
            "SimpleDialogue",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=10,
            leading=14,
            spaceBefore=2,
            spaceAfter=2,
        )

        story = []
        batch_size = 1000  # 메모리 최적화

        for i, entry in enumerate(entries):
            content = entry.get("content", "")
            name = entry.get("name", "")

            if not content.strip():
                continue

            content_escaped = escape_xml(content)
            name_escaped = escape_xml(name) if name else ""

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
