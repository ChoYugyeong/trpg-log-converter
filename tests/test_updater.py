"""Tests for UpdateService — mocking the GitHub API for offline runs."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.services.updater import UpdateInfo, UpdateService, _extract_sha256


@pytest.fixture(autouse=True)
def _clear_updater_cache():
    """Class-level cache isolation between tests."""
    UpdateService.clear_cache()
    yield
    UpdateService.clear_cache()


def _mock_release_payload(tag: str, asset_name: str, size: int = 1024) -> dict:
    return {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": "Bug fixes and improvements.",
        "published_at": "2026-05-01T00:00:00Z",
        "assets": [
            {
                "name": asset_name,
                "size": size,
                "browser_download_url": f"https://example.test/{asset_name}",
            }
        ],
    }


class TestCheck:
    def test_returns_none_when_remote_not_newer(self, monkeypatch):
        payload = _mock_release_payload("v1.0.0", "TRPG_Converter_Pro_Windows.zip")

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None

        with patch("core.services.updater._OPENER.open", return_value=mock_resp):
            result = UpdateService(repo="fake/repo").check()
        assert result is None

    def test_returns_info_when_remote_is_newer(self, monkeypatch):
        from core.version import version_tuple
        major, _minor, _patch_v = version_tuple()
        future_tag = f"v{major + 1}.0.0"
        platform_asset = (
            "TRPG_Converter_Pro_Windows.zip" if sys.platform == "win32"
            else "TRPG_Converter_Pro_macOS.zip" if sys.platform == "darwin"
            else "TRPG_Converter_Pro_linux.zip"
        )
        payload = _mock_release_payload(future_tag, platform_asset, size=12345)

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None

        with patch("core.services.updater._OPENER.open", return_value=mock_resp):
            info = UpdateService(repo="fake/repo").check()

        assert info is not None
        assert info.tag == future_tag
        assert info.version == future_tag.lstrip("v")
        assert info.asset_size == 12345
        assert "example.test" in info.download_url

    def test_returns_none_on_network_error(self):
        import urllib.error
        with patch(
            "core.services.updater._OPENER.open",
            side_effect=urllib.error.URLError("DNS fail"),
        ):
            result = UpdateService(repo="fake/repo").check()
        assert result is None

    def test_returns_none_when_no_platform_asset(self):
        # Only a Linux asset present, on Windows / macOS this gives nothing.
        payload = _mock_release_payload("v99.0.0", "weird_artifact.tar.gz")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None

        with patch("core.services.updater._OPENER.open", return_value=mock_resp):
            info = UpdateService(repo="fake/repo").check()
        # Fallback rule includes any .zip; weird_artifact.tar.gz won't match — returns None.
        assert info is None


class TestSha256Extraction:
    def test_extracts_lowercase_hash(self):
        body = "Some text\nsha256: ABCD" + "12" * 30 + "\nmore text"
        result = _extract_sha256(body)
        assert result == ("abcd" + "12" * 30)

    def test_returns_none_when_absent(self):
        assert _extract_sha256("nothing here") is None

    def test_handles_equals_sign(self):
        body = f"sha256={'a' * 64}"
        result = _extract_sha256(body)
        assert result == "a" * 64
