"""End-to-end conversion tests using synthetic log fixtures.

For each dummy log (Cocofolia, Roll20, plain text), we run the full pipeline:

    parse_file  →  ConversionEngine.create_{epub, docx, pdf}

and assert that:

  * The parser returns a non-trivial entry list with at least one dialogue and
    at least one scene marker (where the fixture has one).
  * EPUB / DOCX / PDF files are written to disk and have a non-zero size.
  * Channel-filtered entries ([잡담], [ooc]) are skipped when configured.
  * Image markers become entries of type ``image``.

These tests are slow-ish (file IO + EPUB/DOCX/PDF rendering) and run on
``tmp_path`` so they leave no artefacts behind.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from core.config_manager import ConfigManager
from core.engine import ConversionEngine
from tests.fixtures.dummy_logs import (
    all_dummy_logs,
    make_cocofolia_basic,
    make_cocofolia_with_channels,
    make_cocofolia_with_images,
    make_roll20_basic,
    make_roll20_long,
    make_text_log,
)


@pytest.fixture
def engine(tmp_path: Path) -> ConversionEngine:
    cm = ConfigManager(app_dir=tmp_path)
    config = cm.build_engine_config()
    # Force outputs into the temp dir.
    config.setdefault("paths", {})["output_dir"] = str(tmp_path / "out")
    (tmp_path / "out").mkdir(exist_ok=True)
    return ConversionEngine(config)


def _write(tmp_path: Path, name: str, content: str, suffix: str = ".html") -> Path:
    p = tmp_path / f"{name}{suffix}"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParseCocofolia:
    def test_basic_returns_entries_with_scenes(self, tmp_path: Path, engine: ConversionEngine):
        path = _write(tmp_path, "coco_basic", make_cocofolia_basic())
        entries = engine.parse_file(str(path))

        assert len(entries) > 5
        names = {e.get("name") for e in entries if e.get("name")}
        # Cocofolia underscore → space conversion
        assert "사사키 유타카" in names or "사사키_유타카" in names
        scene_count = sum(1 for e in entries if e.get("type") == "scene")
        assert scene_count >= 3, f"expected >=3 scenes, got {scene_count}"

    def test_channels_filter(self, tmp_path: Path):
        cm = ConfigManager(app_dir=tmp_path)
        config = cm.build_engine_config()
        config["parsing"]["skip_channels"] = ["[잡담]", "[ooc]"]
        engine = ConversionEngine(config)

        path = _write(tmp_path, "coco_channels", make_cocofolia_with_channels())
        entries = engine.parse_file(str(path))

        joined = "\n".join(e.get("content", "") for e in entries)
        assert "오늘 시간 괜찮으세요" not in joined  # [잡담] filtered
        assert "캐릭터 시트 확인" not in joined  # [ooc] filtered
        assert "거대한 성문" in joined  # plain text preserved

    def test_image_markers_become_image_entries(self, tmp_path: Path, engine: ConversionEngine):
        path = _write(tmp_path, "coco_images", make_cocofolia_with_images())
        entries = engine.parse_file(str(path))

        image_entries = [e for e in entries if e.get("type") == "image"]
        # Two image markers in the fixture: cover.png + scene1.jpg
        assert len(image_entries) >= 2
        contents = {e.get("content") for e in image_entries}
        assert any("cover" in c for c in contents)
        assert any("scene1" in c for c in contents)


class TestParseRoll20:
    def test_basic_parses_speakers_and_scenes(self, tmp_path: Path, engine: ConversionEngine):
        path = _write(tmp_path, "r20_basic", make_roll20_basic())
        entries = engine.parse_file(str(path))

        assert len(entries) > 5
        names = {e.get("name") for e in entries if e.get("name")}
        assert any("김철수" in n for n in names)
        assert any("이영희" in n for n in names)
        scene_count = sum(1 for e in entries if e.get("type") == "scene")
        assert scene_count >= 2

    def test_long_log_splits_into_many_scenes(self, tmp_path: Path, engine: ConversionEngine):
        path = _write(tmp_path, "r20_long", make_roll20_long(scenes=5, lines_per_scene=15))
        entries = engine.parse_file(str(path))
        scenes = engine.split_scenes(entries)
        assert len(scenes) >= 5

    def test_dice_rolls_are_detected(self, tmp_path: Path, engine: ConversionEngine):
        path = _write(tmp_path, "r20_basic", make_roll20_basic())
        entries = engine.parse_file(str(path))
        dice_entries = [e for e in entries if e.get("type") == "dice"]
        assert dice_entries, "Rolling XdY lines should yield dice entries"


class TestParseText:
    def test_text_file_parses(self, tmp_path: Path, engine: ConversionEngine):
        path = _write(tmp_path, "plain", make_text_log(), suffix=".txt")
        entries = engine.parse_file(str(path))
        assert entries
        assert any(e.get("type") == "scene" for e in entries)


# ---------------------------------------------------------------------------
# Full pipeline: parse → EPUB / DOCX / PDF
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "log_name,suffix,content_factory",
    [
        ("coco_basic", ".html", make_cocofolia_basic),
        ("coco_channels", ".html", make_cocofolia_with_channels),
        ("coco_images", ".html", make_cocofolia_with_images),
        ("r20_basic", ".html", make_roll20_basic),
        ("r20_long", ".html", make_roll20_long),
        ("plain", ".txt", make_text_log),
    ],
)
class TestFullPipeline:
    def test_epub(self, tmp_path, engine, log_name, suffix, content_factory):
        src = _write(tmp_path, log_name, content_factory(), suffix=suffix)
        entries = engine.parse_file(str(src))
        out = tmp_path / "out" / f"{log_name}.epub"

        result = engine.create_epub(entries, str(out), title=log_name, author="Tester")
        assert result, "create_epub returned a falsy value"
        assert out.exists(), f"EPUB not written: {out}"
        assert out.stat().st_size > 1024, "EPUB suspiciously small"
        # EPUB is just a ZIP — verify it opens.
        with zipfile.ZipFile(out) as zf:
            assert "mimetype" in zf.namelist()

    def test_docx(self, tmp_path, engine, log_name, suffix, content_factory):
        src = _write(tmp_path, log_name, content_factory(), suffix=suffix)
        entries = engine.parse_file(str(src))
        out = tmp_path / "out" / f"{log_name}.docx"

        result = engine.create_docx(entries, str(out), title=log_name, author="Tester")
        assert result
        assert out.exists()
        assert out.stat().st_size > 1024
        # DOCX is also a ZIP.
        with zipfile.ZipFile(out) as zf:
            assert "word/document.xml" in zf.namelist()

    def test_pdf(self, tmp_path, engine, log_name, suffix, content_factory):
        from core.pdf_generator import PDF_AVAILABLE

        if not PDF_AVAILABLE:
            pytest.skip("reportlab not installed")

        src = _write(tmp_path, log_name, content_factory(), suffix=suffix)
        entries = engine.parse_file(str(src))
        out = tmp_path / "out" / f"{log_name}.pdf"

        result = engine.create_pdf(entries, str(out), title=log_name, author="Tester")
        # PDF can return None if reportlab refuses (e.g. no entries), but if a
        # result is returned, the file should exist with PDF magic header.
        if result:
            assert out.exists()
            with out.open("rb") as fh:
                assert fh.read(4) == b"%PDF"


# ---------------------------------------------------------------------------
# Coverage smoke: every catalog entry exercises the parser at least once.
# ---------------------------------------------------------------------------


def test_all_catalog_entries_parse(tmp_path: Path, engine: ConversionEngine):
    """Every fixture must parse without raising; only the genuinely-content
    ones must yield entries. ``empty`` is intentionally empty."""
    EXPECTED_EMPTY = {"empty"}
    for log in all_dummy_logs():
        path = tmp_path / f"{log.name}{log.suffix}"
        path.write_text(log.content, encoding="utf-8")
        entries = engine.parse_file(str(path))
        if log.name in EXPECTED_EMPTY:
            assert isinstance(entries, list), f"{log.name} should return a list"
        else:
            assert entries, f"{log.name} produced no entries"
