"""End-to-end smoke test for the live updater against the public release channel.

What this verifies (real network, no mocks for API call):
  1. `UpdateService().check()` hits the public repo, returns 200 within timeout.
  2. Current version (2.4.0) sees outcome=LATEST and info=None (=  "최신 버전입니다").
  3. With current version monkey-patched lower (2.3.0), the same release shows
     up as an UpdateInfo with the correct windows.zip asset URL — the path the
     UpdateDialog would consume.
  4. `_select_platform_asset` matches our uploaded asset name.

Run:
    python scripts/smoke_updater_e2e.py
Exits 0 on success, non-zero with a printed reason on any failure.
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

# Korean Windows console defaults to cp949; release-note bodies contain em-dash
# and other Unicode that crashes the print(). Match build.py's mitigation.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# Make repo root importable when invoked as `python scripts/smoke_updater_e2e.py`.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.services.updater import CheckOutcome, UpdateService  # noqa: E402
from core import version as version_mod  # noqa: E402


FAIL = "\x1b[31m[FAIL]\x1b[0m"
OK = "\x1b[32m[OK]\x1b[0m"


def assert_eq(label: str, got, want) -> None:
    if got != want:
        raise AssertionError(f"{label}: got={got!r}, want={want!r}")
    print(f"  {OK} {label}: {got!r}")


def assert_truthy(label: str, got) -> None:
    if not got:
        raise AssertionError(f"{label}: falsy ({got!r})")
    print(f"  {OK} {label}: {got!r}")


def case_1_current_version_is_latest() -> None:
    print("[1] check() with current __version__ → LATEST, info=None")
    UpdateService.clear_cache()
    svc = UpdateService()
    t0 = time.monotonic()
    info = svc.check()
    elapsed = time.monotonic() - t0
    print(f"  elapsed: {elapsed:.2f}s")
    assert_eq("info", info, None)
    assert_eq("last_outcome", svc.last_outcome, CheckOutcome.LATEST)
    if elapsed > 3.0:
        raise AssertionError(f"check() too slow: {elapsed:.2f}s (timeout=1.5s expected)")
    print(f"  {OK} elapsed under 3s")


def case_2_older_version_sees_update() -> None:
    print("[2] check() with __version__ monkey-patched to '2.3.0' → UpdateInfo for v2.4.0")
    UpdateService.clear_cache()
    original = version_mod.__version__
    original_tuple_fn = version_mod.version_tuple
    try:
        version_mod.__version__ = "2.3.0"
        version_mod.version_tuple = lambda: (2, 3, 0)
        # The updater module imported `is_newer_than` and `__version__` directly
        # at import time, so patch those too.
        import core.services.updater as updater_mod
        updater_mod.__version__ = "2.3.0"
        original_is_newer = updater_mod.is_newer_than
        updater_mod.is_newer_than = version_mod.is_newer_than  # rebind to use patched tuple

        svc = UpdateService()
        info = svc.check()
        assert_truthy("info", info)
        assert_eq("info.tag", info.tag, "v2.4.0")
        assert_eq("info.version", info.version, "2.4.0")
        assert_eq("asset name lowercase contains 'windows.zip'",
                  "windows.zip" in info.asset_name.lower(), True)
        assert_truthy("download_url", info.download_url)
        assert_truthy("asset_size > 0", info.asset_size > 0)
        assert_truthy("download_url is https github", info.download_url.startswith("https://github.com/"))
        print(f"  asset: {info.asset_name} ({info.asset_size/1024/1024:.1f} MB)")
        print(f"  url:   {info.download_url}")
    finally:
        version_mod.__version__ = original
        version_mod.version_tuple = original_tuple_fn
        import core.services.updater as updater_mod
        updater_mod.__version__ = original
        updater_mod.is_newer_than = original_is_newer


def case_3_cache_hit_is_instant() -> None:
    print("[3] Second check() within TTL → cache hit, no network")
    UpdateService.clear_cache()
    svc = UpdateService()
    svc.check()  # populate
    t0 = time.monotonic()
    svc.check()
    elapsed = time.monotonic() - t0
    print(f"  cached call elapsed: {elapsed*1000:.1f}ms")
    if elapsed > 0.05:
        raise AssertionError(f"cache hit too slow: {elapsed*1000:.1f}ms (should be <50ms)")
    print(f"  {OK} cache hit under 50ms")


def case_4_private_outcome_no_longer_triggered() -> None:
    print("[4] Verify the configured repo is now public (no PRIVATE_OR_MISSING)")
    UpdateService.clear_cache()
    svc = UpdateService()
    svc.check()
    if svc.last_outcome == CheckOutcome.PRIVATE_OR_MISSING:
        raise AssertionError("Still hitting 404 — updater still pointed at a private/missing repo")
    print(f"  {OK} outcome={svc.last_outcome} (≠ PRIVATE_OR_MISSING)")


def main() -> int:
    cases = [
        case_1_current_version_is_latest,
        case_2_older_version_sees_update,
        case_3_cache_hit_is_instant,
        case_4_private_outcome_no_longer_triggered,
    ]
    failed = []
    for case in cases:
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            failed.append((case.__name__, exc))
            print(f"  {FAIL} {exc}")
            traceback.print_exc()
        print()
    if failed:
        print(f"{FAIL} {len(failed)} / {len(cases)} cases failed:")
        for name, exc in failed:
            print(f"  - {name}: {exc}")
        return 1
    print(f"{OK} all {len(cases)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
