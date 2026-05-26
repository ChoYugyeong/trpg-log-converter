"""Tests for the diagnostic bundle exporter."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from core.services.diagnostics import _redact_large_blobs, build_diagnostic_zip


class TestBundleContent:
    def test_zip_is_created(self, tmp_path: Path, monkeypatch):
        out = tmp_path / "diag.zip"
        build_diagnostic_zip(out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_zip_contains_info_txt(self, tmp_path: Path):
        out = tmp_path / "diag.zip"
        build_diagnostic_zip(out)
        with zipfile.ZipFile(out) as zf:
            assert "info.txt" in zf.namelist()
            info = zf.read("info.txt").decode("utf-8")
            assert "version:" in info
            assert "os:" in info
            assert "python:" in info

    def test_zip_contains_listing(self, tmp_path: Path):
        out = tmp_path / "diag.zip"
        build_diagnostic_zip(out)
        with zipfile.ZipFile(out) as zf:
            assert "user_data_listing.txt" in zf.namelist()


class TestRedaction:
    def test_short_strings_kept(self):
        data = {"name": "Aragorn", "age": 87, "tags": ["short", "list"]}
        result = _redact_large_blobs(data)
        assert result == data

    def test_long_string_redacted(self):
        big = "A" * 5000
        result = _redact_large_blobs({"cover": big, "title": "ok"})
        assert "redacted" in result["cover"]
        assert "5000" in result["cover"]
        assert result["title"] == "ok"

    def test_nested_redaction(self):
        data = {
            "level1": {
                "level2": {
                    "blob": "X" * 10_000,
                    "ok": "small",
                }
            },
        }
        result = _redact_large_blobs(data)
        assert "redacted" in result["level1"]["level2"]["blob"]
        assert result["level1"]["level2"]["ok"] == "small"

    def test_list_redaction(self):
        data = {"items": ["ok", "B" * 5000, "ok2"]}
        result = _redact_large_blobs(data)
        assert result["items"][0] == "ok"
        assert "redacted" in result["items"][1]
        assert result["items"][2] == "ok2"
