"""Self-update service via GitHub Releases API.

Production-grade auto-updater modelled on Sparkle (macOS) / NSIS (Windows)
patterns adapted for a PyInstaller --onedir bundle.

Workflow
--------
1. ``check()`` polls the GitHub Releases REST API for the latest tag.
2. If newer than ``core.version.__version__``, return ``UpdateInfo``.
3. ``download(info, on_progress=...)`` streams the platform-specific asset
   ZIP into ``%APPDATA%/TRPG_Converter_Pro/updates/<version>/`` and verifies
   the size against the API metadata.
4. ``apply(info)`` writes a small shim script (``apply_update.bat`` on
   Windows / ``apply_update.sh`` on macOS) and launches it, then exits the
   current process. The shim waits for the current exe to release locks,
   extracts the ZIP into a staging directory, swaps the old install for the
   new one (preserving ``gui_settings.json`` + ``logs/``), and re-launches.

Why a shim instead of in-process replace
----------------------------------------
On Windows you can't overwrite a running .exe / DLL — the OS holds locks
until the process exits. The shim lives outside the install dir and runs
after the app quits, which is the canonical Sparkle/Squirrel approach.

Safety
------
- HTTPS only (urllib defaults; certificate verification on).
- Downloads validated against ``size`` from the API; SHA256 also verified
  if the release notes contain ``sha256: <hex>`` (best-effort, opt-in
  release contract — not required for the update to apply).
- ``gui_settings.json`` and ``logs/`` are explicitly preserved before swap.
- All operations log to the rotating ``app.log``.

Privacy
-------
- No telemetry: only requests the public Releases API endpoint.
- Disabled when ``updates.check_on_startup`` is False in settings.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.version import __update_repo__, __version__, is_newer_than

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]  # (downloaded_bytes, total_bytes)

_API_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
_USER_AGENT = f"TRPG-Log-Converter-Pro/{__version__} (+https://github.com/{__update_repo__})"

# 1.5초 타이트한 timeout — GitHub 정상 응답은 < 0.5s. 사용자가 [업데이트 확인]
# 눌렀을 때 1.5초 이상 "멈춤"으로 느끼지 않게.
# DNS getaddrinfo 도 ``socket.setdefaulttimeout`` 으로 같은 제한.
# closeEvent thread wait (5s) 안에 확실히 종료.
_TIMEOUT_SECONDS = 1.5


@dataclass(frozen=True)
class UpdateInfo:
    """Resolved update available on the remote."""
    version: str                       # "2.3.0" (no 'v')
    tag: str                           # "v2.3.0"
    title: str                         # release name
    body: str                          # release notes (markdown)
    download_url: str                  # platform asset URL
    asset_name: str
    asset_size: int                    # bytes
    sha256: Optional[str] = None       # parsed from release body if present
    published_at: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class UpdateService:
    """Stateless service object; safe to instantiate per-call."""

    def __init__(self, repo: str = __update_repo__, app_dir: Optional[Path] = None) -> None:
        self.repo = repo
        self.app_dir = Path(app_dir) if app_dir else self._guess_app_dir()

    # ── 1. Check ─────────────────────────────────────────────────────

    def check(self) -> Optional[UpdateInfo]:
        """Query GitHub for the latest release. Returns None if no newer version.

        Network safety:
          - urlopen ``timeout`` argument bounds the entire HTTP operation.
          - ``socket.setdefaulttimeout`` bounds DNS getaddrinfo / TCP connect
            which urlopen's timeout doesn't always cover on slow networks.
          - HTTPError (404 등) 는 URLError 의 서브클래스라 같은 except 로 잡힘.
        """
        import socket
        import time

        url = _API_LATEST.format(repo=self.repo)
        logger.info("Checking for updates: %s", url)
        prev_default_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(_TIMEOUT_SECONDS)
        start = time.monotonic()
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": _USER_AGENT,
                },
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS,
                                         context=ssl.create_default_context()) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # 404 == 저장소가 private 거나 아직 release 가 없음. 둘 다 "조용히
            # 최신 버전" 으로 처리하는 게 사용자에게 가장 덜 거슬림.
            elapsed = time.monotonic() - start
            if exc.code == 404:
                logger.info(
                    "Update endpoint 404 after %.2fs (private repo or no releases yet)",
                    elapsed,
                )
            else:
                logger.warning("Update check HTTP %d after %.2fs", exc.code, elapsed)
            return None
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
            UnicodeDecodeError,  # binary 응답 / 잘못된 BOM
            ValueError,           # ssl context build 실패 등 광범위 안전망
        ) as exc:
            elapsed = time.monotonic() - start
            logger.warning("Update check failed after %.2fs: %s", elapsed, exc)
            return None
        finally:
            socket.setdefaulttimeout(prev_default_timeout)
        elapsed = time.monotonic() - start
        logger.info("Update check succeeded in %.2fs", elapsed)

        tag = payload.get("tag_name", "")
        version = tag.lstrip("v").strip()
        if not version or not is_newer_than(tag):
            logger.info("No update available (latest=%s, current=%s)", tag, __version__)
            return None

        # Pick the asset matching the current platform.
        asset = self._select_platform_asset(payload.get("assets", []))
        if asset is None:
            logger.warning("Update %s has no matching asset for this platform", tag)
            return None

        body = payload.get("body", "") or ""
        sha256 = _extract_sha256(body)

        return UpdateInfo(
            version=version,
            tag=tag,
            title=payload.get("name", tag),
            body=body,
            download_url=asset["browser_download_url"],
            asset_name=asset["name"],
            asset_size=int(asset.get("size", 0)),
            sha256=sha256,
            published_at=payload.get("published_at", ""),
        )

    # ── 2. Download ─────────────────────────────────────────────────

    def download(
        self,
        info: UpdateInfo,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """Stream the asset to a local cache. Returns the path on disk.

        Raises:
            urllib.error.URLError: network / TLS failure.
            ValueError: size or sha256 mismatch.
        """
        cache_dir = self._cache_dir() / info.version
        cache_dir.mkdir(parents=True, exist_ok=True)
        target = cache_dir / info.asset_name

        if target.exists() and target.stat().st_size == info.asset_size:
            logger.info("Update already downloaded: %s", target)
            if info.sha256 and not _verify_sha256(target, info.sha256):
                logger.warning("Cached file failed checksum; re-downloading")
                target.unlink(missing_ok=True)
            else:
                return target

        logger.info("Downloading %s -> %s", info.download_url, target)
        req = urllib.request.Request(info.download_url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp, \
                open(target, "wb") as out:
            total = int(resp.headers.get("Content-Length", info.asset_size or 0))
            downloaded = 0
            chunk = 64 * 1024
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                out.write(buf)
                downloaded += len(buf)
                if on_progress:
                    on_progress(downloaded, total)

        if info.asset_size and target.stat().st_size != info.asset_size:
            target.unlink(missing_ok=True)
            raise ValueError(
                f"download size mismatch: got {target.stat().st_size}, expected {info.asset_size}"
            )
        if info.sha256 and not _verify_sha256(target, info.sha256):
            target.unlink(missing_ok=True)
            raise ValueError("download checksum mismatch")

        return target

    # ── 3. Apply ────────────────────────────────────────────────────

    def apply(self, info: UpdateInfo, archive_path: Path) -> None:
        """Write the platform-specific apply script and execute it.

        After this returns the caller should ``sys.exit(0)`` immediately —
        the shim is waiting for our exe to release file locks.
        """
        if sys.platform == "win32":
            self._apply_windows(info, archive_path)
        elif sys.platform == "darwin":
            self._apply_macos(info, archive_path)
        else:
            raise RuntimeError("Self-update not supported on this platform")

    # ── Internals ───────────────────────────────────────────────────

    def _select_platform_asset(self, assets: list) -> Optional[dict]:
        """Pick the .zip asset matching this OS by filename convention."""
        if sys.platform == "win32":
            patterns = ("windows.zip", "win.zip", "win64.zip")
        elif sys.platform == "darwin":
            patterns = ("macos.zip", "mac.zip", "darwin.zip")
        else:
            patterns = ("linux.zip", "x86_64.zip")
        for asset in assets:
            name = asset.get("name", "").lower()
            if any(p in name for p in patterns):
                return asset
        # Fallback: any .zip asset
        for asset in assets:
            if asset.get("name", "").lower().endswith(".zip"):
                return asset
        return None

    def _cache_dir(self) -> Path:
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home())) / "TRPG_Converter_Pro" / "updates"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Caches" / "TRPG_Converter_Pro" / "updates"
        else:
            base = Path.home() / ".cache" / "TRPG_Converter_Pro" / "updates"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _guess_app_dir(self) -> Path:
        """Resolve the install directory (parent of the running exe in --onedir)."""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent.parent.parent

    def _apply_windows(self, info: UpdateInfo, archive_path: Path) -> None:
        """Write apply_update.bat next to the install and start it detached."""
        install_dir = self.app_dir.resolve()
        exe_name = Path(sys.executable).name
        # Place the script in the parent of install_dir so it can delete the
        # install_dir contents while we're not running anymore.
        script_dir = self._cache_dir() / info.version
        script_path = script_dir / "apply_update.bat"

        # Backslash-escape paths for cmd.
        archive = str(archive_path).replace("/", "\\")
        install = str(install_dir).replace("/", "\\")
        relauncher = str(install_dir / exe_name).replace("/", "\\")
        log_path = str(script_dir / "apply.log").replace("/", "\\")

        script = f"""@echo off
REM TRPG_Converter_Pro update applier - auto-generated, do not commit.
chcp 65001 >nul 2>&1
setlocal
set "LOG={log_path}"
echo [%date% %time%] Update applier started > "%LOG%"
echo Waiting for {exe_name} to exit... >> "%LOG%"

REM Give the parent process up to 30 seconds to release locks.
set /a wait=0
:wait_loop
tasklist /FI "IMAGENAME eq {exe_name}" 2>nul | find /I "{exe_name}" >nul
if errorlevel 1 goto extract
timeout /t 1 /nobreak >nul
set /a wait+=1
if %wait% lss 30 goto wait_loop
echo Timed out waiting for exit; forcing >> "%LOG%"
taskkill /F /IM {exe_name} >nul 2>&1

:extract
echo Preserving user data... >> "%LOG%"
if exist "{install}\\gui_settings.json" copy /Y "{install}\\gui_settings.json" "{script_dir}\\gui_settings.bak" >nul
if exist "{install}\\logs" xcopy /E /I /Y "{install}\\logs" "{script_dir}\\logs.bak" >nul

echo Extracting {archive_path.name}... >> "%LOG%"
powershell -NoProfile -Command "Expand-Archive -LiteralPath '{archive}' -DestinationPath '{script_dir}\\staging' -Force"
if errorlevel 1 (
    echo Extract failed >> "%LOG%"
    exit /b 1
)

echo Swapping install dir... >> "%LOG%"
REM Find the inner folder produced by PyInstaller --onedir.
for /D %%D in ("{script_dir}\\staging\\*") do set "NEW_DIR=%%D"
if not defined NEW_DIR (
    echo No inner dir in archive >> "%LOG%"
    exit /b 1
)

REM Delete old install contents (keep the dir itself so paths stay valid).
del /F /Q "{install}\\*.*" >nul 2>&1
for /D %%D in ("{install}\\*") do rd /S /Q "%%D"

REM Copy new files in.
xcopy /E /I /Y "%NEW_DIR%\\*" "{install}\\" >nul

echo Restoring user data... >> "%LOG%"
if exist "{script_dir}\\gui_settings.bak" copy /Y "{script_dir}\\gui_settings.bak" "{install}\\gui_settings.json" >nul
if exist "{script_dir}\\logs.bak" xcopy /E /I /Y "{script_dir}\\logs.bak" "{install}\\logs" >nul

echo Launching new version... >> "%LOG%"
start "" "{relauncher}"
echo Done. >> "%LOG%"
"""
        script_path.write_text(script, encoding="utf-8")
        logger.info("Spawning update applier: %s", script_path)
        # Detach so we can exit cleanly.
        subprocess.Popen(
            ["cmd", "/c", "start", "", "/min", str(script_path)],
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                          | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            close_fds=True,
            shell=False,
        )

    def _apply_macos(self, info: UpdateInfo, archive_path: Path) -> None:
        """macOS apply: unzip into staging, swap .app bundle, relaunch."""
        install_dir = self.app_dir.resolve()
        # On macOS our app_dir is the .app's Contents/MacOS, so install root is 3 up.
        app_root = install_dir
        for _ in range(3):
            if app_root.name.endswith(".app"):
                break
            app_root = app_root.parent

        script_dir = self._cache_dir() / info.version
        script_path = script_dir / "apply_update.sh"
        log_path = script_dir / "apply.log"
        staging = script_dir / "staging"

        script = f"""#!/bin/bash
set -e
LOG="{log_path}"
echo "[$(date)] Update applier started" > "$LOG"

# Wait for the app to exit (parent pid is passed as arg 1).
PARENT_PID="$1"
for i in {{1..30}}; do
    kill -0 "$PARENT_PID" 2>/dev/null || break
    sleep 1
done

mkdir -p "{staging}"
echo "Extracting..." >> "$LOG"
unzip -o "{archive_path}" -d "{staging}" >> "$LOG" 2>&1

NEW_APP=$(find "{staging}" -maxdepth 2 -name "*.app" | head -1)
if [ -z "$NEW_APP" ]; then
    echo "No .app in archive" >> "$LOG"
    exit 1
fi

echo "Preserving user data..." >> "$LOG"
USER_SETTINGS="{app_root}/Contents/Resources/gui_settings.json"
[ -f "$USER_SETTINGS" ] && cp "$USER_SETTINGS" "{script_dir}/gui_settings.bak"

echo "Swapping bundle..." >> "$LOG"
rm -rf "{app_root}"
mv "$NEW_APP" "{app_root}"

if [ -f "{script_dir}/gui_settings.bak" ]; then
    cp "{script_dir}/gui_settings.bak" "{app_root}/Contents/Resources/gui_settings.json"
fi

echo "Launching..." >> "$LOG"
open "{app_root}"
"""
        script_path.write_text(script, encoding="utf-8")
        script_path.chmod(0o755)
        logger.info("Spawning macOS update applier: %s", script_path)
        subprocess.Popen(
            ["/bin/bash", str(script_path), str(os.getpid())],
            start_new_session=True,
            close_fds=True,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SHA256_RE = re.compile(r"sha256\s*[:=]\s*([0-9a-f]{64})", re.IGNORECASE)


def _extract_sha256(body: str) -> Optional[str]:
    match = _SHA256_RE.search(body)
    return match.group(1).lower() if match else None


def _verify_sha256(path: Path, expected: str) -> bool:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    actual = h.hexdigest().lower()
    if actual != expected.lower():
        logger.warning("sha256 mismatch: got %s, expected %s", actual, expected)
        return False
    return True


__all__ = ["UpdateService", "UpdateInfo", "ProgressCallback"]
