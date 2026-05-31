"""Output renderers.

Public API:
    create_epub  — EPUB generation
    create_docx  — DOCX generation (lives in core.docx_builder)
    create_pdf   — PDF generation via reportlab (lives in core.pdf_generator)

Lower-level helpers:
    renderers.css  — CSS stylesheet generation
    renderers.epub — HTML/EPUB-specific builders
"""

from core.docx_builder import create_docx
from core.renderers.css import generate_css
from core.renderers.epub import (
    create_cover_html,
    create_epub,
    create_toc_html,
    entries_to_html,
)

try:
    from core.pdf_generator import PDF_AVAILABLE, create_pdf
except ImportError:  # pragma: no cover
    PDF_AVAILABLE = False
    create_pdf = None  # type: ignore[assignment]
