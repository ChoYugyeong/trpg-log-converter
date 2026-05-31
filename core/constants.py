"""Centralized magic numbers and tunables used across the GUI / services layer.

Why a separate module
---------------------
* Lets tests and operations toggle these without diving into business code.
* Makes obvious to reviewers that a "5000ms" or "1.5s" appearing in code is
  an intentional, named decision — not a wild guess.
* When tuning UX (e.g. "toast feels too brief"), one file to touch.

Naming convention
-----------------
* ``*_MS`` suffix for milliseconds (matches Qt / qfluentwidgets conventions —
  QTimer.singleShot, InfoBar.duration etc. all take int ms).
* ``*_S`` suffix for seconds (used by ``urllib`` / ``socket`` APIs).
* ``Final[…]`` annotations advertise immutability to mypy / IDE.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Update checker / network
# ---------------------------------------------------------------------------

#: Per-call HTTP timeout for the GitHub releases API. 1.5s leaves comfortable
#: headroom under the closeEvent worker-wait budget (5s) so the app can always
#: shut down cleanly even mid-check.
UPDATE_CHECK_NETWORK_TIMEOUT_S: Final[float] = 1.5

#: Hard cap on how long the **whole** UI flow waits for a worker result before
#: forcibly cleaning up and surfacing a "응답이 없어요" warning. Must exceed
#: ``UPDATE_CHECK_NETWORK_TIMEOUT_S`` plus thread-spawn jitter.
UPDATE_CHECK_HARD_TIMEOUT_MS: Final[int] = 5_000

#: Cached check result TTL — repeated clicks within this window return the
#: prior outcome instantly, no network call.
UPDATE_CHECK_CACHE_TTL_S: Final[int] = 300

#: Delay between window paint and the silent startup update check.  Gives the
#: UI a chance to fully settle so the (background) check doesn't compete with
#: first-paint work for the GIL.
UPDATE_CHECK_STARTUP_DELAY_MS: Final[int] = 5_000


# ---------------------------------------------------------------------------
# InfoBar (qfluentwidgets toast) durations
# ---------------------------------------------------------------------------

#: "확인 중 / 진행 중" 류 — 짧고 가벼운 안내. 사용자가 곧 사라질 것을 알아야 함.
INFOBAR_DURATION_TRANSIENT_MS: Final[int] = 2_500

#: 일반 정보 (작업 완료, 최신 버전 확인됨 등).
INFOBAR_DURATION_INFO_MS: Final[int] = 3_500

#: 경고 (네트워크 오류, 응답 해석 실패 등) — 잠시 더 머물러야 사용자가 읽음.
INFOBAR_DURATION_WARNING_MS: Final[int] = 4_500

#: 사용자가 액션을 취해야 할 만한 알림 (private repo 안내 등).
INFOBAR_DURATION_ATTENTION_MS: Final[int] = 8_000

#: Sticky InfoBar marker — qfluentwidgets 가 ``duration < 0`` 이면 auto-close
#: 타이머를 안 걸어서 영구 표시. 결과 도착 시 코드가 명시적으로 close() 해야 함.
INFOBAR_STICKY: Final[int] = -1


# ---------------------------------------------------------------------------
# Welcome / startup misc
# ---------------------------------------------------------------------------

#: 첫 실행 환영 다이얼로그 노출까지의 지연 — 메인 윈도우 렌더가 끝나길 기다림.
WELCOME_DIALOG_DELAY_MS: Final[int] = 800


# ---------------------------------------------------------------------------
# Worker / thread shutdown budgets
# ---------------------------------------------------------------------------

#: 변환 워커가 정상 종료를 기다리는 최대 시간. 초과 시 terminate.
CONVERT_WORKER_SHUTDOWN_TIMEOUT_MS: Final[int] = 5_000

#: 업데이트 체크 워커가 정상 종료를 기다리는 최대 시간 (closeEvent 정리용).
UPDATE_THREAD_SHUTDOWN_TIMEOUT_MS: Final[int] = 5_000

#: terminate() 이후 OS thread 정리 보장 시간.
THREAD_TERMINATE_GRACE_MS: Final[int] = 1_000


# ---------------------------------------------------------------------------
# Backwards-compat aliases (deprecated; new code should use the long names)
# ---------------------------------------------------------------------------

#: 외부 모듈에서 이전 이름으로 import 하던 경우의 alias.  새 코드는 위의
#: 정식 이름 사용. 한 사이클 후 제거 예정.
_TIMEOUT_SECONDS = UPDATE_CHECK_NETWORK_TIMEOUT_S
_CACHE_TTL_SECONDS = UPDATE_CHECK_CACHE_TTL_S


__all__ = [
    "CONVERT_WORKER_SHUTDOWN_TIMEOUT_MS",
    "INFOBAR_DURATION_ATTENTION_MS",
    "INFOBAR_DURATION_INFO_MS",
    "INFOBAR_DURATION_TRANSIENT_MS",
    "INFOBAR_DURATION_WARNING_MS",
    "INFOBAR_STICKY",
    "THREAD_TERMINATE_GRACE_MS",
    "UPDATE_CHECK_CACHE_TTL_S",
    "UPDATE_CHECK_HARD_TIMEOUT_MS",
    "UPDATE_CHECK_NETWORK_TIMEOUT_S",
    "UPDATE_CHECK_STARTUP_DELAY_MS",
    "UPDATE_THREAD_SHUTDOWN_TIMEOUT_MS",
    "WELCOME_DIALOG_DELAY_MS",
]
