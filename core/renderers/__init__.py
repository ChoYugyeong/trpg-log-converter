"""Output renderers.

Public API:
    create_epub  — EPUB generation
    create_docx  — DOCX generation (lives in core.docx_builder)
    create_pdf   — PDF generation via reportlab (lives in core.pdf_generator)

Lower-level helpers:
    renderers.css  — CSS stylesheet generation
    renderers.epub — HTML/EPUB-specific builders
"""
from core.renderers.css import generate_css  # noqa: F401
from core.renderers.epub import (  # noqa: F401
    create_cover_html,
    create_epub,
    create_toc_html,
    entries_to_html,
)
from core.docx_builder import create_docx  # noqa: F401

try:
    from core.pdf_generator import PDF_AVAILABLE, create_pdf  # noqa: F401
except ImportError:  # pragma: no cover
    PDF_AVAILABLE = False
    create_pdf = None  # type: ignore[assignment]
