"""DOCX / PDF 가 공유하는 페이지 판형·여백 헬퍼.

두 렌더러의 출력이 동일한 판형과 여백을 갖도록 하나의 진실 소스를 제공한다.
"""
from __future__ import annotations

import re

# 표준 판형 (mm)
STANDARD_SIZES_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "B5": (182.0, 257.0),
    "Letter": (216.0, 279.0),
    "신국판": (152.0, 225.0),
    "국판": (148.0, 210.0),
    "46배판": (128.0, 188.0),
    "문고판": (105.0, 148.0),
    "EPUB (6x9)": (152.4, 228.6),  # 6×9 inch
    "EPUB (5x8)": (127.0, 203.2),  # 5×8 inch
}


def parse_page_format(format_str: str) -> tuple[float, float]:
    """GUI 판형 문자열을 (너비_mm, 높이_mm) 로 파싱.

    예시:
      'A5 (148x210mm)' → (148, 210)
      '신국판 (152x225mm)' → (152, 225)
      'A4' → (210, 297)
      빈 문자열 / 잘못된 값 → A5 기본값 (148, 210)
    """
    if not format_str:
        return STANDARD_SIZES_MM["A5"]

    # "NxMmm" / "N×Mmm" 패턴 추출
    m = re.search(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*mm", format_str)
    if m:
        return float(m.group(1)), float(m.group(2))

    # 표준 명칭 prefix 매칭
    for key, size in STANDARD_SIZES_MM.items():
        if format_str.startswith(key):
            return size

    return STANDARD_SIZES_MM["A5"]


def get_page_format(config: dict, *, for_epub: bool = False) -> str:
    """config 에서 판형 문자열을 얻는다.

    엔진 config 의 통합 경로는 ``config['page_format']`` (DOCX/PDF 공통) 과
    ``config['epub_page_format']`` (EPUB 전용) 이다. 둘 다 없으면 fallback.
    """
    if for_epub:
        return (
            config.get("epub_page_format")
            or config.get("page_format")
            or "EPUB (6x9)"
        )
    return config.get("page_format") or "A5 (148x210mm)"


def get_page_margins_inch(config: dict) -> dict[str, float]:
    """DOCX/PDF 가 공통으로 사용할 페이지 여백(인치 단위)을 얻는다.

    우선순위:
      1. ``config['layout']['docx_margin']`` (GUI margins 를 매핑한 값)
      2. ``config['page']['margins']`` (구 PDF 경로)
      3. 기본값 1.0 inch
    """
    def to_float(value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    layout = config.get("layout") or {}
    margin = layout.get("docx_margin") if isinstance(layout, dict) else None
    if not isinstance(margin, dict):
        page = config.get("page") or {}
        margin = page.get("margins") if isinstance(page, dict) else None
    if not isinstance(margin, dict):
        margin = {}

    return {
        "top": to_float(margin.get("top"), 1.0),
        "bottom": to_float(margin.get("bottom"), 1.0),
        "left": to_float(margin.get("left"), 1.0),
        "right": to_float(margin.get("right"), 1.0),
    }
