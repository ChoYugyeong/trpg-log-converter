"""TRPG log → EPUB/DOCX/PDF conversion engine.

This module is a **thin orchestration layer** that wires the parsing and
rendering packages together. The heavy code lives in:

  * :mod:`core.parsers`   — Roll20/Cocofolia/text parsing, helpers, image markers
  * :mod:`core.renderers` — EPUB/DOCX/PDF generation, CSS
  * :mod:`core.config`    — single-source defaults & schema migrations

All previously top-level symbols (``parse_log``, ``create_epub``, ``escape_html``,
``optimize_image``, etc.) are re-exported here for backwards compatibility.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from core.config.defaults import DEFAULT_ENGINE_CONFIG, default_engine_config
from core.utils import deep_merge

# ── Re-exports for backwards compatibility ────────────────────────────────
# Old call sites import these directly from core.engine; keep that working.
from core.parsers import (  # noqa: F401
    escape_html,
    extract_image_markers,
    extract_scene_title,
    filter_entries,
    find_image_file,
    get_font_family_name,
    get_font_files,
    hex_to_rgb,
    is_dice_roll,
    is_narration_user,
    is_scene_end,
    is_scene_marker,
    match_custom_style,
    merge_consecutive_dialogues,
    normalize_punctuation,
    optimize_image,
    parse_log,
    smart_split_name_content,
    split_by_count,
    split_by_scene,
    split_into_scenes,
    strip_channel_prefix,
    validate_regex,
)
from core.renderers import (  # noqa: F401
    create_cover_html,
    create_docx,
    create_epub,
    create_toc_html,
    entries_to_html,
    generate_css,
)
from core.docx_builder import add_paragraph_spacing, set_run_font  # noqa: F401

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]

# Backwards-compatible alias — new code should call
# ``core.config.default_engine_config()`` directly.
DEFAULT_CONFIG = DEFAULT_ENGINE_CONFIG


def load_config(config_path: Optional[str | Path] = None) -> Dict[str, Any]:
    config = default_engine_config()
    resolved = Path(config_path) if config_path else Path(__file__).parent / "config.yaml"
    if resolved.exists():
        with open(resolved, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f)
            if user_config:
                config = deep_merge(config, user_config)
        logger.info("Config loaded: %s", resolved)
    return config


class ConversionEngine:
    """Convenience facade used by the GUI and CLI.

    Holds a single ``config`` instance and exposes parse/filter/render methods
    so callers don't thread config through every call.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = config or load_config()

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        from core.text_parser import parse_file as text_parse_file
        result: List[Dict[str, Any]] = text_parse_file(file_path, self.config)
        return result

    def parse_html(self, html_content: str) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = parse_log(html_content, self.config)
        return result

    def filter(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return filter_entries(entries, self.config)

    def merge(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return merge_consecutive_dialogues(entries, self.config)

    def split_scenes(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return split_into_scenes(entries, self.config)

    def create_epub(
        self,
        entries: List[Dict[str, Any]],
        output_path: str,
        title: str = "TRPG 리플레이",
        author: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        return create_epub(
            entries, output_path, self.config, title, author,
            progress_callback=progress_callback,
        )

    def create_docx(
        self,
        entries: List[Dict[str, Any]],
        output_path: str,
        title: str = "TRPG 리플레이",
        author: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        result: str = create_docx(
            entries, output_path, self.config, title, author,
            progress_callback=progress_callback,
        )
        return result

    def create_pdf(
        self,
        entries: List[Dict[str, Any]],
        output_path: str,
        title: str = "TRPG 리플레이",
        author: Optional[str] = None,
    ) -> Optional[str]:
        try:
            from core.pdf_generator import PDF_AVAILABLE, create_pdf as pdf_create
            if PDF_AVAILABLE:
                return pdf_create(entries, output_path, self.config, title, author)
            return None
        except ImportError:
            logger.warning("PDF 모듈 로드 실패. reportlab 설치를 확인하세요.")
            return None

    def convert_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        format: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[str]:
        return convert(
            input_path, output_path, title, author, self.config, format,
            progress_callback=progress_callback,
        )

    def batch_convert(
        self,
        input_files: List[str],
        output_dir: Optional[str] = None,
        title_prefix: Optional[str] = None,
        author: Optional[str] = None,
        format: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[Dict[str, Any]]:
        if output_dir:
            self.config["paths"]["output_dir"] = output_dir

        results: List[Dict[str, Any]] = []
        for i, file_path in enumerate(input_files, 1):
            base = os.path.splitext(os.path.basename(file_path))[0]
            try:
                title = f"{title_prefix} - {base}" if title_prefix else base
                if progress_callback:
                    progress_callback(i - 1, len(input_files), f"변환 중: {base}")
                output_paths = convert(
                    file_path, None, title, author, self.config, format,
                    progress_callback=progress_callback,
                )
                results.append({"file": file_path, "success": True, "outputs": output_paths})
                logger.info("[%d/%d] OK: %s", i, len(input_files), base)
            except Exception as e:  # noqa: BLE001
                results.append({"file": file_path, "success": False, "error": str(e)})
                logger.error("[%d/%d] FAIL: %s: %s", i, len(input_files), base, e)
        return results


def convert(
    input_path: str,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    format: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> List[str]:
    """Convert one log file into the requested output format(s)."""
    if config is None:
        config = load_config()

    output_dir = config.get("paths", {}).get("output_dir", "./export")
    os.makedirs(output_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(input_path))[0]
    if title is None:
        title = base

    if progress_callback:
        progress_callback(0, 100, "파일 읽기 중...")

    # 파싱은 ``core.text_parser.parse_file`` 의 인코딩 자동 감지 + 사이즈 가드를
    # 통해 처리한다. 과거에는 여기서 직접 ``open()`` 인코딩 루프를 돌렸지만
    # 동일한 안전성을 양쪽에서 유지하기 어려워 단일 경로로 통일.
    from core.text_parser import parse_file as text_parse_file
    logger.info("Input: %s", input_path)

    if progress_callback:
        progress_callback(10, 100, "파일 파싱 중...")
    entries = text_parse_file(input_path, config)
    logger.info("Parsed %d entries", len(entries))

    entries = filter_entries(entries, config)
    entries = merge_consecutive_dialogues(entries, config)

    if logger.isEnabledFor(logging.DEBUG):
        stats: Dict[str, int] = {}
        for e in entries:
            stats[e["type"]] = stats.get(e["type"], 0) + 1
        logger.debug(
            "Entry stats: %s",
            " | ".join(f"{k} {v}" for k, v in sorted(stats.items())),
        )

    output_format = format or config.get("output_format", "both")
    results: List[str] = []

    if output_format in ("epub", "both", "all"):
        if progress_callback:
            progress_callback(30, 100, "EPUB 생성 중...")
        epub_path = output_path or os.path.join(output_dir, f"{base}.epub")
        create_epub(entries, epub_path, config, title, author, progress_callback=progress_callback)
        results.append(epub_path)

    if output_format in ("docx", "both", "all"):
        if progress_callback:
            progress_callback(60, 100, "DOCX 생성 중...")
        docx_path = os.path.join(output_dir, f"{base}.docx")
        create_docx(entries, docx_path, config, title, author, progress_callback=progress_callback)
        results.append(docx_path)

    if output_format in ("pdf", "all"):
        try:
            from core.pdf_generator import PDF_AVAILABLE, create_pdf
            if PDF_AVAILABLE:
                pdf_path = os.path.join(output_dir, f"{base}.pdf")
                result = create_pdf(entries, pdf_path, config, title, author)
                if result:
                    results.append(pdf_path)
            else:
                logger.warning("PDF unavailable (reportlab not installed)")
        except ImportError:
            logger.warning("PDF module load failed")

    return results


def batch_convert(
    input_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    format: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> List[str]:
    """Convert every HTML file in ``input_dir`` to the configured output format(s)."""
    if config is None:
        config = load_config()

    if input_dir is None:
        input_dir = config.get("paths", {}).get("input_dir", "./input")

    html_files = list(Path(input_dir).glob("*.html")) + list(Path(input_dir).glob("*.htm"))
    if not html_files:
        logger.warning("No HTML files in %s", input_dir)
        return []

    logger.info("Batch converting %d files", len(html_files))

    results: List[str] = []
    for html_file in sorted(html_files):
        try:
            output_paths = convert(str(html_file), config=config, format=format)
            results.extend(output_paths)
        except Exception as e:  # noqa: BLE001
            logger.error("Conversion error: %s - %s", html_file, e)

    logger.info("Batch complete: %d files created", len(results))
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TRPG 로그 → EPUB/DOCX/PDF")
    parser.add_argument("input", nargs="?", help="입력 HTML")
    parser.add_argument("-o", "--output", help="출력 경로")
    parser.add_argument("-t", "--title", help="제목")
    parser.add_argument("-a", "--author", help="저자")
    parser.add_argument("-c", "--config", help="설정 파일")
    parser.add_argument("-f", "--format", choices=["epub", "docx", "both", "pdf", "all"])
    parser.add_argument("--batch", action="store_true")

    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.batch or args.input is None:
        batch_convert(args.input, args.output, cfg, args.format)
    else:
        convert(args.input, args.output, args.title, args.author, cfg, args.format)
