"""EPUB 3 spec compliance smoke tests.

These tests don't run the official ``epubcheck`` JAR (heavy, requires Java) but
verify the structural requirements that 90% of broken EPUBs fail:

* ``mimetype`` is the first file in the archive, stored (uncompressed), and
  contains exactly ``application/epub+zip``.
* ``META-INF/container.xml`` exists and points to a real OPF.
* The OPF (``package.opf``) parses as XML and lists manifest items.
* Every ``manifest`` entry resolves to a file inside the archive.
* No ``..`` traversal in file names.
* XHTML chapters parse (lxml will reject unbalanced tags).

If these pass, the file is overwhelmingly likely to open in Calibre, Apple
Books, and ReadiumJS without issue.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from core.config_manager import ConfigManager
from core.engine import ConversionEngine
from tests.fixtures.dummy_logs import (
    make_cocofolia_basic,
    make_cocofolia_with_images,
    make_roll20_basic,
    make_roll20_long,
)

NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
}


@pytest.fixture
def engine(tmp_path: Path) -> ConversionEngine:
    cm = ConfigManager(app_dir=tmp_path)
    config = cm.build_engine_config()
    config["paths"]["output_dir"] = str(tmp_path / "out")
    (tmp_path / "out").mkdir(exist_ok=True)
    return ConversionEngine(config)


def _build_epub(tmp_path: Path, engine: ConversionEngine, name: str, html: str) -> Path:
    src = tmp_path / f"{name}.html"
    src.write_text(html, encoding="utf-8")
    entries = engine.parse_file(str(src))
    out = tmp_path / "out" / f"{name}.epub"
    engine.create_epub(entries, str(out), title=name, author="Tester")
    assert out.exists(), f"EPUB not written: {out}"
    return out


def _assert_valid_epub(epub_path: Path) -> None:
    """Run the structural checks. Raises ``AssertionError`` on failure."""
    with zipfile.ZipFile(epub_path) as zf:
        names = zf.namelist()

        # 1. ``mimetype`` must be the first entry, stored (uncompressed).
        info_list = zf.infolist()
        assert info_list, "EPUB is empty"
        first = info_list[0]
        assert first.filename == "mimetype", (
            f"first entry must be 'mimetype', got '{first.filename}'"
        )
        assert first.compress_type == zipfile.ZIP_STORED, (
            "'mimetype' must be stored uncompressed (compress_type=ZIP_STORED)"
        )
        assert zf.read("mimetype") == b"application/epub+zip", (
            "'mimetype' content must be exactly 'application/epub+zip'"
        )

        # 2. ``META-INF/container.xml`` must exist and reference an OPF rootfile.
        assert "META-INF/container.xml" in names
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        rootfile = container.find(".//container:rootfile", NS)
        assert rootfile is not None, "container.xml missing <rootfile>"
        opf_path = rootfile.get("full-path")
        assert opf_path, "rootfile@full-path missing"
        assert opf_path in names, f"OPF not in archive: {opf_path}"

        # 3. OPF parses and lists manifest items.
        opf = ET.fromstring(zf.read(opf_path))
        manifest_items = opf.findall(".//opf:manifest/opf:item", NS)
        assert manifest_items, "manifest has no items"

        # 4. Every manifest href must resolve to a file in the archive.
        opf_dir = Path(opf_path).parent
        for item in manifest_items:
            href = item.get("href")
            assert href, f"manifest item missing href: {ET.tostring(item)!r}"
            resolved = str(opf_dir / href).replace("\\", "/")
            # Some EPUBs use absolute paths in href; normalise.
            if resolved not in names and href not in names:
                pytest.fail(f"manifest references missing file: href={href}")

        # 5. No path-traversal entries.
        for n in names:
            assert ".." not in Path(n).parts, f"archive contains ..: {n}"

        # 6. XHTML chapter files parse.
        for n in names:
            if n.endswith((".xhtml", ".html")):
                # ET will raise on malformed XML.
                ET.fromstring(zf.read(n))


@pytest.mark.parametrize(
    "name,factory",
    [
        ("coco_basic", make_cocofolia_basic),
        ("coco_images", make_cocofolia_with_images),
        ("r20_basic", make_roll20_basic),
        ("r20_long", make_roll20_long),
    ],
)
def test_epub_structure_valid(tmp_path: Path, engine, name: str, factory):
    epub_path = _build_epub(tmp_path, engine, name, factory())
    _assert_valid_epub(epub_path)


def test_epub_has_navigation_doc(tmp_path: Path, engine):
    """EPUB 3 navigation document must exist in the manifest."""
    epub_path = _build_epub(tmp_path, engine, "nav_check", make_cocofolia_basic())
    with zipfile.ZipFile(epub_path) as zf:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        opf_path = container.find(".//container:rootfile", NS).get("full-path")
        opf = ET.fromstring(zf.read(opf_path))
        # Either properties="nav" (EPUB3) or a toc.ncx (EPUB2 compat)
        nav_items = [
            it
            for it in opf.findall(".//opf:manifest/opf:item", NS)
            if "nav" in (it.get("properties") or "")
            or it.get("media-type") == "application/x-dtbncx+xml"
        ]
        assert nav_items, "EPUB must have a nav doc or NCX for table of contents"


def test_epub_unique_manifest_ids(tmp_path: Path, engine):
    """Duplicate manifest ids cause readers to fail silently."""
    epub_path = _build_epub(tmp_path, engine, "ids", make_roll20_long())
    with zipfile.ZipFile(epub_path) as zf:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        opf_path = container.find(".//container:rootfile", NS).get("full-path")
        opf = ET.fromstring(zf.read(opf_path))
        ids = [it.get("id") for it in opf.findall(".//opf:manifest/opf:item", NS)]
        assert len(ids) == len(set(ids)), f"duplicate manifest ids: {ids}"
