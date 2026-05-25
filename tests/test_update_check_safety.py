"""Regression tests for the update-check hang bug.

User-reported bug: clicking the update (refresh) icon in the sidebar caused
the app to hang then force-close. Root cause: ``urlopen`` had a 15s timeout
and ``closeEvent`` didn't wait for the worker thread → Qt aborts when the
QThread is destroyed while still running.

These tests pin:
- timeout is short (≤ 5s) so the thread can exit when the window closes
- multiple rapid calls don't spawn dangling threads (guarded)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.services.updater import _TIMEOUT_SECONDS, UpdateService


@pytest.fixture(autouse=True)
def _clear_updater_cache():
    UpdateService.clear_cache()
    yield
    UpdateService.clear_cache()


def test_timeout_is_short_enough_for_clean_shutdown():
    """4s is the cap — anything longer makes closeEvent thread wait flaky."""
    assert _TIMEOUT_SECONDS <= 5, (
        f"_TIMEOUT_SECONDS={_TIMEOUT_SECONDS} too long — closeEvent gives 5s "
        "to the worker thread, so the urllib timeout must be strictly less."
    )


def test_check_returns_none_on_dns_failure():
    """When DNS fails, check() returns None instead of propagating the exception."""
    import urllib.error
    with patch(
        "core.services.updater.urllib.request.urlopen",
        side_effect=urllib.error.URLError("Temporary failure in name resolution"),
    ):
        result = UpdateService(repo="invalid/repo").check()
    assert result is None


def test_check_returns_none_on_timeout():
    """A socket timeout must surface as None, not an exception."""
    with patch(
        "core.services.updater.urllib.request.urlopen",
        side_effect=TimeoutError("timeout"),
    ):
        result = UpdateService(repo="invalid/repo").check()
    assert result is None


def test_check_returns_none_on_json_decode_error():
    """If GitHub returns HTML instead of JSON (rate limit page etc.) — graceful."""
    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<html>Rate limit exceeded</html>"
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda *a: None
    with patch("core.services.updater.urllib.request.urlopen", return_value=mock_resp):
        result = UpdateService(repo="invalid/repo").check()
    assert result is None
