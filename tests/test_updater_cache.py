"""Tests for the UpdateService outcome cache + classification.

핵심 보장:
- 같은 ``repo`` 에 대한 두 번째 ``check()`` 호출은 네트워크 호출 없이
  ``_cache`` hit. UI 연타에 멈춤 0.
- 응답 결과에 따라 ``last_outcome`` 이 정확한 ``CheckOutcome.*`` 코드로 세팅.
"""
from __future__ import annotations

import json
import time
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from core.services.updater import CheckOutcome, UpdateService


def _mock_resp(body: bytes) -> MagicMock:
    m = MagicMock()
    m.read.return_value = body
    m.__enter__ = lambda self: self
    m.__exit__ = lambda *a: None
    return m


def _http_error(code: int):
    return urllib.error.HTTPError(
        url="https://api.github.com/test",
        code=code, msg=f"{code}", hdrs={}, fp=BytesIO(b""),
    )


@pytest.fixture(autouse=True)
def clear_cache():
    """매 테스트마다 클래스 캐시 격리."""
    UpdateService.clear_cache()
    yield
    UpdateService.clear_cache()


class TestCache:
    def test_second_call_hits_cache_no_network(self):
        mock_resp = _mock_resp(json.dumps({"tag_name": "v0.0.1"}).encode())
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=mock_resp,
        ) as urlopen_mock:
            svc = UpdateService(repo="fake/repo")
            svc.check()
            svc.check()
            svc.check()
        # 단 한 번만 urlopen 호출됨 — 나머지는 캐시 hit.
        assert urlopen_mock.call_count == 1

    def test_cache_is_per_repo(self):
        mock_resp = _mock_resp(json.dumps({"tag_name": "v0.0.1"}).encode())
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=mock_resp,
        ) as urlopen_mock:
            UpdateService(repo="a/b").check()
            UpdateService(repo="c/d").check()
        # 다른 repo 두 개 → 두 번 모두 네트워크.
        assert urlopen_mock.call_count == 2

    def test_clear_cache_forces_refetch(self):
        mock_resp = _mock_resp(json.dumps({"tag_name": "v0.0.1"}).encode())
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=mock_resp,
        ) as urlopen_mock:
            UpdateService(repo="r/r").check()
            UpdateService.clear_cache()
            UpdateService(repo="r/r").check()
        assert urlopen_mock.call_count == 2

    def test_cache_returns_within_few_ms(self):
        """1차 호출 후 2차는 네트워크 없이 즉시 반환되는지 시간 측정."""
        mock_resp = _mock_resp(json.dumps({"tag_name": "v0.0.1"}).encode())
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=mock_resp,
        ):
            svc = UpdateService(repo="r/r")
            svc.check()
            start = time.monotonic()
            svc.check()
            elapsed = time.monotonic() - start
        assert elapsed < 0.01, f"cache hit took {elapsed*1000:.1f}ms (should be < 10ms)"


class TestOutcomeClassification:
    def test_outcome_private_on_404(self):
        with patch(
            "core.services.updater.urllib.request.urlopen",
            side_effect=_http_error(404),
        ):
            svc = UpdateService(repo="r/r")
            svc.check()
        assert svc.last_outcome == CheckOutcome.PRIVATE_OR_MISSING

    def test_outcome_network_on_dns_fail(self):
        with patch(
            "core.services.updater.urllib.request.urlopen",
            side_effect=urllib.error.URLError("DNS"),
        ):
            svc = UpdateService(repo="r/r")
            svc.check()
        assert svc.last_outcome == CheckOutcome.NETWORK_ERROR

    def test_outcome_network_on_timeout(self):
        with patch(
            "core.services.updater.urllib.request.urlopen",
            side_effect=TimeoutError(),
        ):
            svc = UpdateService(repo="r/r")
            svc.check()
        assert svc.last_outcome == CheckOutcome.NETWORK_ERROR

    def test_outcome_network_on_500(self):
        with patch(
            "core.services.updater.urllib.request.urlopen",
            side_effect=_http_error(503),
        ):
            svc = UpdateService(repo="r/r")
            svc.check()
        assert svc.last_outcome == CheckOutcome.NETWORK_ERROR

    def test_outcome_latest_on_same_version(self):
        # 현재와 같은 버전을 응답으로 줌 → "not newer" → LATEST.
        from core.version import __version__
        body = json.dumps({"tag_name": f"v{__version__}"}).encode()
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=_mock_resp(body),
        ):
            svc = UpdateService(repo="r/r")
            svc.check()
        assert svc.last_outcome == CheckOutcome.LATEST


class TestPrivateRepoFastPath:
    """Private 저장소 사용자의 흐름 — 첫 클릭은 1.5초 timeout (404), 그 다음
    부터는 캐시로 즉시 응답. UI freeze 0."""

    def test_repeated_clicks_on_private_repo_are_instant(self):
        with patch(
            "core.services.updater.urllib.request.urlopen",
            side_effect=_http_error(404),
        ) as urlopen_mock:
            svc = UpdateService(repo="private/repo")
            # 첫 호출 — 네트워크.
            svc.check()
            # 1초 이내 연속 클릭 5번 — 모두 캐시.
            for _ in range(5):
                start = time.monotonic()
                svc.check()
                assert (time.monotonic() - start) < 0.01
        # 네트워크 호출은 정확히 1번.
        assert urlopen_mock.call_count == 1
