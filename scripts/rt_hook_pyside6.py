"""PyInstaller runtime hook — bullet-proof PySide6 ↔ shiboken6 DLL wiring.

Why this exists
---------------
PySide6 6.11.x 의 ``_additional_dll_directories(package_dir)`` 는

    root = Path(package_dir).parent
    if (root / 'shiboken6').is_dir():
        return [root / 'shiboken6']
    fallback = root.parent / 'shiboken6' / 'libshiboken'
    if not fallback.is_dir():
        raise ImportError(str(fallback) + ' does not exist')

대부분의 경우 첫 분기가 ``_internal/shiboken6`` 를 잡아 잘 동작하는데,
드물게 path 가 Unicode (예: ``C:/Users/사용자/새 폴더/...``) 거나 PyInstaller
가 ``__file__`` 을 해석하는 방식이 미세하게 달라지면 ``is_dir()`` 가 False
를 반환하면서 **fallback 도 없는 ``libshiboken``** 경로로 떨어져 ImportError.

이 훅은 PySide6 가 import 되기 전에 sys._MEIPASS (PyInstaller 가 모든
번들 파일을 푸는 임시 디렉터리) 와 그 ``_internal`` 자식을 ``os.add_dll_
directory`` 로 직접 등록해, PySide6 의 자동 감지 분기와 관계없이 shiboken6
DLL 들이 로딩되도록 보장한다.

PyInstaller spec 에 ``runtime_hooks=['scripts/rt_hook_pyside6.py']`` 로 연결.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _install_pyside6_dll_search_paths() -> None:
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        return  # 비 frozen — 일반 venv 실행 시 아무 작업 없음.

    candidates = []
    # PyInstaller 6.x onedir layout: 모든 bundle 자원이 _MEIPASS 아래에 풀림.
    # shiboken6 는 보통 _MEIPASS/shiboken6 (== <install>/_internal/shiboken6).
    base_path = Path(base)
    candidates.append(base_path / "shiboken6")
    candidates.append(base_path / "PySide6")
    # 일부 PyInstaller 5.x / spec 변형은 _MEIPASS 자체가 install 루트.
    candidates.append(base_path.parent / "shiboken6")

    seen = set()
    for path in candidates:
        try:
            real = os.fspath(path.resolve())
        except OSError:
            continue
        if real in seen:
            continue
        seen.add(real)
        if not os.path.isdir(real):
            continue
        try:
            os.add_dll_directory(real)
        except (OSError, FileNotFoundError):
            # 권한/경로 문제 — 무시하고 다음 후보 시도.
            continue
        # PySide6 의 명시적 PATH 의존 (Qt plugin 검색 등) 도 같이 채워줌.
        os.environ["PATH"] = real + os.pathsep + os.environ.get("PATH", "")


if sys.platform == "win32":
    _install_pyside6_dll_search_paths()
