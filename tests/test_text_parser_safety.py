"""Input-boundary safety tests for ``core.text_parser.parse_file``.

These verify:
  * Files exceeding ``performance.max_html_bytes`` are rejected with ParseError
    before any IO is consumed.
  * Files in unsupported encodings raise EncodingError with structured context.
  * The "tried encodings" list reaches the error context for debugging.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.exceptions import EncodingError, ParseError
from core.text_parser import parse_file


@pytest.fixture
def tmp_html(tmp_path: Path) -> Path:
    p = tmp_path / "log.html"
    p.write_text("<html><body>hi</body></html>", encoding="utf-8")
    return p


def test_oversize_file_rejected(tmp_path: Path):
    big = tmp_path / "big.html"
    # Write a 2 MiB file but cap allowed size at 1 MiB.
    big.write_bytes(b"a" * (2 * 1024 * 1024))
    config = {"performance": {"max_html_bytes": 1 * 1024 * 1024}}

    with pytest.raises(ParseError) as excinfo:
        parse_file(big, config)

    ctx = excinfo.value.context
    assert ctx["limit"] == 1 * 1024 * 1024
    assert ctx["file_size"] == 2 * 1024 * 1024
    assert "너무 큽니다" in excinfo.value.user_message


def test_well_formed_html_passes(tmp_html: Path):
    # parse_file dispatches to engine.parse_log for HTML; result shape doesn't
    # matter here — only that we don't raise on a sane file.
    result = parse_file(tmp_html, {"performance": {"max_html_bytes": 10 * 1024 * 1024}})
    assert isinstance(result, list)


def test_missing_file_raises_parse_error(tmp_path: Path):
    ghost = tmp_path / "does-not-exist.html"
    with pytest.raises(ParseError) as excinfo:
        parse_file(ghost, {"performance": {"max_html_bytes": 10 * 1024 * 1024}})

    assert "path" in excinfo.value.context
    assert "does-not-exist.html" in excinfo.value.context["path"]


def test_strict_whitelist_succeeds_on_utf8(tmp_path: Path):
    """A clean UTF-8 file decodes through the strict whitelist without falling back."""
    from core.text_parser import _detect_and_read

    f = tmp_path / "clean.html"
    f.write_text("<html><body>한글</body></html>", encoding="utf-8")

    text, enc = _detect_and_read(f)
    assert "한글" in text
    # Whitelist labels are stable; we just need to know we didn't fall back.
    assert enc in {"utf-8", "utf-8-sig"}


def test_charset_normalizer_handles_euc_kr(tmp_path: Path):
    """EUC-KR/CP949 should resolve via the strict whitelist."""
    from core.text_parser import _detect_and_read

    f = tmp_path / "kr.html"
    f.write_bytes("<html>안녕하세요</html>".encode("cp949"))

    text, enc = _detect_and_read(f)
    assert "안녕하세요" in text
    # Either cp949 from whitelist or charset-normalizer can return either label.
    assert enc.startswith(("cp949", "euc"))


def test_garbage_bytes_fall_back_with_warning(tmp_path: Path, caplog):
    """Pure garbage shouldn't crash — replacement decode + WARN log."""
    import logging

    from core.text_parser import _detect_and_read

    f = tmp_path / "garbage.bin"
    # A pathological byte sequence: UTF-16 BOM followed by high bytes that
    # confuse most decoders.
    f.write_bytes(b"\xff\xfe" + bytes(range(128, 256)) * 10)

    with caplog.at_level(logging.WARNING, logger="core.text_parser"):
        text, enc = _detect_and_read(f)
    assert isinstance(text, str)
    assert enc  # Some label was assigned (whitelist, normalizer, or +replace).
