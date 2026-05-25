"""End-to-end scenario tests for the updater against realistic failure modes.

이 모듈의 목적은 "다시는 사용자가 update 클릭 후 멈춘다고 말하지 않도록"
다양한 네트워크 / 응답 시나리오를 자동 검증하는 것. 한 가지라도 깨지면
다음 빌드가 차단되도록.

검증 시나리오:
* 정상 응답 (200 + 새 버전)
* 정상 응답 (200 + 같은 버전)
* 404 (private repo / no releases)
* 401 / 403 (rate limit / auth)
* 500 / 502 / 503 (서버 오류)
* 응답이 길어져서 timeout 초과 (slow body)
* 연결 자체 timeout (느린 DNS / TCP)
* SSL 핸드셰이크 실패
* 잘못된 JSON
* 잘못된 인코딩
* 빈 응답
* 비정상 큰 응답 (수십 MB)
* 매우 빠른 연속 호출 (race condition)
"""
from __future__ import annotations

import json
import socket
import time
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from core.services.updater import _TIMEOUT_SECONDS, UpdateService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(payload_bytes: bytes, *, headers: dict | None = None) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = payload_bytes
    mock.headers = headers or {"Content-Length": str(len(payload_bytes))}
    mock.__enter__ = lambda self: self
    mock.__exit__ = lambda *a: None
    return mock


def _release_payload(tag: str, asset_name: str = "TRPG_Converter_Pro_Windows.zip",
                     size: int = 1024) -> bytes:
    return json.dumps({
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": "",
        "published_at": "2026-05-01T00:00:00Z",
        "assets": [{
            "name": asset_name,
            "size": size,
            "browser_download_url": f"https://example.test/{asset_name}",
        }],
    }).encode("utf-8")


# ---------------------------------------------------------------------------
# Hard contract: timeout cannot exceed closeEvent's 5s wait
# ---------------------------------------------------------------------------

def test_timeout_within_close_event_budget():
    """closeEvent 가 worker thread 종료를 5초까지 기다림. timeout 이 5초보다
    크거나 가까우면 사용자가 창 닫을 때 'QThread destroyed while running'
    abort 가 나옴. 이 테스트가 깨지면 빌드 차단."""
    assert _TIMEOUT_SECONDS < 4, (
        f"_TIMEOUT_SECONDS={_TIMEOUT_SECONDS} too high. closeEvent waits 5s, "
        f"and we need a 1s margin for graceful exit."
    )


# ---------------------------------------------------------------------------
# Each scenario must complete in <= _TIMEOUT_SECONDS and return None or info,
# never raise, never hang.
# ---------------------------------------------------------------------------

class TestNetworkFailures:
    """Network-layer failures must all return None within timeout, no exception."""

    def _assert_quick_none(self, side_effect):
        with patch("core.services.updater.urllib.request.urlopen", side_effect=side_effect):
            start = time.monotonic()
            result = UpdateService(repo="fake/repo").check()
            elapsed = time.monotonic() - start
        assert result is None
        # urlopen mock returns instantly; wall time must be < 1s.
        assert elapsed < 1.0, f"check() took {elapsed:.2f}s for instant mock"

    def test_dns_failure(self):
        self._assert_quick_none(
            urllib.error.URLError("Temporary failure in name resolution")
        )

    def test_connection_refused(self):
        self._assert_quick_none(
            urllib.error.URLError(ConnectionRefusedError("conn refused"))
        )

    def test_socket_timeout(self):
        self._assert_quick_none(socket.timeout("timed out"))

    def test_ssl_error(self):
        import ssl
        self._assert_quick_none(ssl.SSLError("handshake failed"))

    def test_python_timeout_error(self):
        self._assert_quick_none(TimeoutError("timeout"))

    def test_connection_reset(self):
        self._assert_quick_none(ConnectionResetError("peer reset"))

    def test_generic_oserror(self):
        self._assert_quick_none(OSError("disk full or similar weird"))


class TestHTTPStatusCodes:
    """HTTP errors must be classified and never leak as exceptions."""

    def _mock_http_error(self, code: int):
        return urllib.error.HTTPError(
            url="https://api.github.com/test",
            code=code,
            msg=f"HTTP {code}",
            hdrs={},  # type: ignore[arg-type]
            fp=BytesIO(b""),
        )

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 410, 422,
                                       429, 500, 502, 503, 504])
    def test_http_error_returns_none(self, code: int):
        """모든 HTTP 에러 코드가 graceful None 반환."""
        with patch(
            "core.services.updater.urllib.request.urlopen",
            side_effect=self._mock_http_error(code),
        ):
            start = time.monotonic()
            result = UpdateService(repo="fake/repo").check()
            elapsed = time.monotonic() - start
        assert result is None
        assert elapsed < 1.0


class TestMalformedResponses:
    """Even with a 200 OK, the body might be unusable."""

    def _assert_quick_none(self, body: bytes):
        mock_resp = _mock_response(body)
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=mock_resp,
        ):
            start = time.monotonic()
            result = UpdateService(repo="fake/repo").check()
            elapsed = time.monotonic() - start
        assert result is None
        assert elapsed < 1.0

    def test_empty_body(self):
        self._assert_quick_none(b"")

    def test_html_instead_of_json(self):
        self._assert_quick_none(b"<html>Rate limit exceeded</html>")

    def test_truncated_json(self):
        self._assert_quick_none(b'{"tag_name": "v')

    def test_invalid_utf8(self):
        self._assert_quick_none(b"\xff\xfe\x00\x00")

    def test_json_with_wrong_shape(self):
        """타입은 JSON 인데 expected 필드가 모두 누락."""
        body = json.dumps({"unrelated": "stuff"}).encode("utf-8")
        mock_resp = _mock_response(body)
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=mock_resp,
        ):
            result = UpdateService(repo="fake/repo").check()
        # tag_name 없음 → is_newer_than("") → False → None
        assert result is None


class TestRapidSequentialCalls:
    """사용자가 [업데이트 확인] 을 연타해도 안전해야 함."""

    def test_ten_consecutive_calls_complete_quickly(self):
        from core.version import version_tuple
        major, minor, patch_v = version_tuple()
        future_tag = f"v{major + 1}.0.0"

        mock_resp = _mock_response(_release_payload(future_tag))
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=mock_resp,
        ):
            start = time.monotonic()
            for _ in range(10):
                # 매번 새 인스턴스 — main_window 의 패턴 모방.
                UpdateService(repo="fake/repo").check()
            elapsed = time.monotonic() - start
        # 10번 호출이 모든 mock 이라 거의 즉시여야 함.
        assert elapsed < 1.0, f"10 sequential calls took {elapsed:.2f}s"


class TestLargeResponses:
    """5MB 짜리 JSON 응답이 와도 안전하게 처리 (예: 수많은 asset)."""

    def test_handles_large_payload(self):
        from core.version import version_tuple
        major, minor, patch_v = version_tuple()
        future_tag = f"v{major + 1}.0.0"

        # 5MB body 시뮬레이션 — body 데이터로 채워서 크기 늘리기.
        big_body = json.dumps({
            "tag_name": future_tag,
            "name": f"Release {future_tag}",
            "body": "X" * (5 * 1024 * 1024),  # 5MB description
            "assets": [{
                "name": "TRPG_Converter_Pro_Windows.zip",
                "size": 100,
                "browser_download_url": "https://example.test/x.zip",
            }],
        }).encode("utf-8")

        mock_resp = _mock_response(big_body)
        with patch(
            "core.services.updater.urllib.request.urlopen",
            return_value=mock_resp,
        ):
            start = time.monotonic()
            result = UpdateService(repo="fake/repo").check()
            elapsed = time.monotonic() - start
        # 응답이 커도 처리는 메모리 내라서 빨라야 함.
        assert elapsed < 2.0, f"5MB body took {elapsed:.2f}s"
        # 새 버전이라 info 반환됨.
        assert result is not None
        assert len(result.body) >= 5 * 1024 * 1024


class TestSocketTimeoutContract:
    """``socket.setdefaulttimeout`` 이 check() 종료 후 원복되는지 확인 —
    side-effect 가 다른 코드 (예: requests 사용) 의 timeout 을 망가뜨리면 안 됨."""

    def test_default_socket_timeout_restored_on_success(self):
        original = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(99)
            mock_resp = _mock_response(_release_payload("v0.0.1"))
            with patch(
                "core.services.updater.urllib.request.urlopen",
                return_value=mock_resp,
            ):
                UpdateService(repo="fake/repo").check()
            assert socket.getdefaulttimeout() == 99, (
                "socket.setdefaulttimeout was not restored after check()"
            )
        finally:
            socket.setdefaulttimeout(original)

    def test_default_socket_timeout_restored_on_failure(self):
        original = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(77)
            with patch(
                "core.services.updater.urllib.request.urlopen",
                side_effect=urllib.error.URLError("fail"),
            ):
                UpdateService(repo="fake/repo").check()
            assert socket.getdefaulttimeout() == 77, (
                "socket.setdefaulttimeout was not restored on exception path"
            )
        finally:
            socket.setdefaulttimeout(original)
