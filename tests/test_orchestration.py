"""Coverage for ``core.engine`` orchestration helpers: ``convert`` & ``batch_convert``.

These functions are used by the GUI/CLI and previously had no test coverage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.engine import batch_convert, convert, load_config
from tests.fixtures.dummy_logs import (
    make_cocofolia_basic,
    make_roll20_basic,
)


@pytest.fixture
def temp_config(tmp_path: Path) -> dict:
    cfg = load_config()
    cfg["paths"]["output_dir"] = str(tmp_path / "out")
    (tmp_path / "out").mkdir(exist_ok=True)
    return cfg


def test_convert_single_file_epub_only(tmp_path: Path, temp_config):
    src = tmp_path / "log.html"
    src.write_text(make_cocofolia_basic(), encoding="utf-8")
    out = convert(str(src), config=temp_config, format="epub")
    assert len(out) == 1
    assert out[0].endswith(".epub")
    assert Path(out[0]).exists()


def test_convert_both_outputs(tmp_path: Path, temp_config):
    src = tmp_path / "log.html"
    src.write_text(make_roll20_basic(), encoding="utf-8")
    out = convert(str(src), config=temp_config, format="both")
    assert len(out) == 2
    suffixes = {Path(p).suffix for p in out}
    assert suffixes == {".epub", ".docx"}


def test_convert_pdf_when_available(tmp_path: Path, temp_config):
    from core.pdf_generator import PDF_AVAILABLE

    if not PDF_AVAILABLE:
        pytest.skip("reportlab not installed")

    src = tmp_path / "log.html"
    src.write_text(make_cocofolia_basic(), encoding="utf-8")
    out = convert(str(src), config=temp_config, format="pdf")
    assert any(p.endswith(".pdf") for p in out)


def test_convert_uses_filename_as_default_title(tmp_path: Path, temp_config):
    src = tmp_path / "myCoolLog.html"
    src.write_text(make_cocofolia_basic(), encoding="utf-8")
    out = convert(str(src), config=temp_config, format="epub")
    assert "myCoolLog.epub" in out[0]


def test_batch_convert_handles_multiple_files(tmp_path: Path, temp_config):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (input_dir / "a.html").write_text(make_cocofolia_basic(), encoding="utf-8")
    (input_dir / "b.html").write_text(make_roll20_basic(), encoding="utf-8")

    temp_config["paths"]["input_dir"] = str(input_dir)
    results = batch_convert(str(input_dir), config=temp_config, format="epub")
    # 2 files × 1 format = 2 epubs
    assert len(results) == 2


def test_batch_convert_empty_dir_returns_empty(tmp_path: Path, temp_config):
    empty = tmp_path / "empty"
    empty.mkdir()
    results = batch_convert(str(empty), config=temp_config, format="epub")
    assert results == []


def test_load_config_no_path_returns_defaults():
    cfg = load_config(None)
    # Defaults always include core sections
    assert "paths" in cfg
    assert "chapter" in cfg
    assert "performance" in cfg
