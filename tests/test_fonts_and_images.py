"""Coverage tests for font discovery and image utilities."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from core.parsers.fonts import get_font_family_name, get_font_files
from core.parsers.images import (
    extract_image_markers,
    find_image_file,
    optimize_image,
)

# ── Fonts ────────────────────────────────────────────────────────────────


def test_get_font_files_returns_empty_when_dir_missing(tmp_path: Path):
    config = {"paths": {"fonts_dir": str(tmp_path / "does-not-exist")}, "fonts": {"embed": {}}}
    fonts = get_font_files(config)
    assert fonts == {"body": None, "name": None, "all": []}


def test_get_font_files_picks_up_embedded_paths(tmp_path: Path):
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    body_font = fonts_dir / "Body-Regular.ttf"
    name_font = fonts_dir / "Name-Bold.otf"
    body_font.write_bytes(b"fake")
    name_font.write_bytes(b"fake")

    config = {
        "paths": {"fonts_dir": str(fonts_dir)},
        "fonts": {"embed": {"body": "Body-Regular.ttf", "name": "Name-Bold.otf"}},
    }
    fonts = get_font_files(config)
    assert fonts["body"] == body_font
    assert fonts["name"] == name_font
    assert len(fonts["all"]) == 2


def test_get_font_files_skips_missing_embed_entries(tmp_path: Path):
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    config = {
        "paths": {"fonts_dir": str(fonts_dir)},
        "fonts": {"embed": {"body": "NotThere.ttf"}},
    }
    fonts = get_font_files(config)
    assert fonts["body"] is None


def test_get_font_family_name_strips_weight_suffixes():
    assert get_font_family_name(Path("Pretendard-Regular.ttf")) == "Pretendard"
    assert get_font_family_name(Path("Nanum-Bold.otf")) == "Nanum"
    assert get_font_family_name(Path("Foo-SemiBold.ttf")) == "Foo"
    assert get_font_family_name(Path("PlainFont.ttf")) == "PlainFont"


# ── Image markers ────────────────────────────────────────────────────────


@pytest.fixture
def base_config():
    return {
        "images": {
            "enable": True,
            "markers": [r"\[IMG:\s*(.+?)\]", r"\[삽화:\s*(.+?)\]"],
        }
    }


def test_extract_image_markers_finds_filename(base_config):
    fname, remaining = extract_image_markers("[IMG: cover.png]", base_config)
    assert fname == "cover.png"
    assert remaining == ""


def test_extract_image_markers_handles_korean(base_config):
    fname, _remaining = extract_image_markers("[삽화: scene1.jpg]", base_config)
    assert fname == "scene1.jpg"


def test_extract_image_markers_disabled(base_config):
    base_config["images"]["enable"] = False
    fname, _remaining = extract_image_markers("[IMG: nope.png]", base_config)
    assert fname is None


def test_extract_image_markers_ignores_unmatched(base_config):
    fname, remaining = extract_image_markers("regular text", base_config)
    assert fname is None
    assert remaining == "regular text"


def test_extract_image_markers_survives_bad_pattern(base_config, caplog):
    base_config["images"]["markers"] = ["[unterminated"]
    fname, _ = extract_image_markers("hello", base_config)
    assert fname is None


# ── find_image_file ──────────────────────────────────────────────────────


def test_find_image_file_resolves_absolute_paths(tmp_path: Path):
    img = tmp_path / "thing.png"
    img.write_bytes(b"\x89PNG\r\n")
    config = {"paths": {"images_dir": str(tmp_path / "nope")}}
    assert find_image_file(str(img), config) == Path(str(img))


def test_find_image_file_resolves_via_images_dir(tmp_path: Path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    img = images_dir / "cover.png"
    img.write_bytes(b"\x89PNG\r\n")
    config = {"paths": {"images_dir": str(images_dir)}}
    assert find_image_file("cover.png", config) == img


def test_find_image_file_returns_none_when_missing(tmp_path: Path):
    config = {"paths": {"images_dir": str(tmp_path / "images")}}
    assert find_image_file("ghost.png", config) is None


# ── optimize_image ───────────────────────────────────────────────────────


@pytest.fixture
def tiny_png(tmp_path: Path) -> Path:
    """Produce a 10x10 red PNG to feed Pillow."""
    pytest.importorskip("PIL")
    from PIL import Image

    p = tmp_path / "tiny.png"
    Image.new("RGB", (10, 10), color=(255, 0, 0)).save(p, format="PNG")
    return p


def test_optimize_image_passes_through_small_png(tiny_png: Path):
    config = {"images": {"max_resolution": 0, "jpeg_quality": 85, "convert_webp": True}}
    data, mime, fname = optimize_image(tiny_png, config)
    assert mime == "image/png"
    assert fname.endswith(".png")
    assert len(data) > 0


def test_optimize_image_resizes_when_over_limit(tmp_path: Path):
    pytest.importorskip("PIL")
    from PIL import Image

    p = tmp_path / "big.png"
    Image.new("RGB", (4000, 2000), color=(0, 255, 0)).save(p, format="PNG")
    config = {"images": {"max_resolution": 500, "jpeg_quality": 85, "convert_webp": True}}
    data, _mime, _ = optimize_image(p, config)
    # Re-open the optimised bytes to verify dimensions.
    out_img = Image.open(io.BytesIO(data))
    assert max(out_img.size) <= 500


def test_optimize_image_converts_webp_to_jpeg(tmp_path: Path):
    pytest.importorskip("PIL")
    from PIL import Image

    p = tmp_path / "thing.webp"
    Image.new("RGB", (50, 50), color=(0, 0, 255)).save(p, format="WEBP")
    config = {"images": {"max_resolution": 0, "jpeg_quality": 80, "convert_webp": True}}
    _, mime, fname = optimize_image(p, config)
    assert mime == "image/jpeg"
    assert fname.endswith(".jpg")
