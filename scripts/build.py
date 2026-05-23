#!/usr/bin/env python3
"""
TRPG 로그 변환기 Pro - 빌드 스크립트
macOS / Windows용 실행 파일 생성 (PySide6)
"""

import subprocess
import sys
import os
from pathlib import Path

APP_NAME = "TRPG_Converter_Pro"
MAIN_SCRIPT = "main.py"

def install_pyinstaller():
    """PyInstaller 설치"""
    print("PyInstaller 설치 중...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

def clean_dist():
    """기존 dist 폴더 정리"""
    import shutil
    import time

    app_dir = Path(__file__).resolve().parent.parent
    dist_path = app_dir / "dist" / APP_NAME

    if not dist_path.exists():
        return

    print(f"기존 빌드 폴더 정리 중: {dist_path}")
    for attempt in range(3):
        try:
            shutil.rmtree(dist_path)
            print("정리 완료")
            return
        except PermissionError:
            print(f"폴더 잠김, 재시도 {attempt + 1}/3...")
            time.sleep(2)

    print(
        f"\n[FAIL] dist 폴더가 다른 프로세스에 잠겨 있습니다: {dist_path}\n"
        f"       실행 중인 {APP_NAME}.exe / 탐색기 창을 닫고 다시 시도하세요."
    )
    sys.exit(1)

def trim_bundle():
    """PyInstaller 가 plugins/binaries 로 끌어오는 거대 Qt 자산을 후처리로 제거.

    ``--exclude-module`` 은 Python 래퍼만 떼는데, Qt6WebEngineCore.dll(196MB)
    같은 바이너리는 그대로 따라오므로 명시적으로 지워야 한다. 안 쓰는 것만
    골라 지우므로 실행에는 영향 없음. 검증된 절감량은 빌드 시 출력된다.
    """
    import shutil
    from fnmatch import fnmatch

    app_dir = Path(__file__).resolve().parent.parent
    pyside_dir = app_dir / "dist" / APP_NAME / "_internal" / "PySide6"
    if not pyside_dir.exists():
        return

    before_total = _dir_size(pyside_dir)

    # 1. Qt 번역(.qm) — 앱은 한국어 고정, Qt 위젯 번역은 영어 폴백으로 충분.
    translations_dir = pyside_dir / "translations"
    if translations_dir.exists():
        shutil.rmtree(translations_dir, ignore_errors=True)

    # 2. QML — 우리는 Widgets 만 사용 (QML 미사용).
    qml_dir = pyside_dir / "qml"
    if qml_dir.exists():
        shutil.rmtree(qml_dir, ignore_errors=True)

    # 3. WebEngine 리소스 — 본체 DLL 을 빼도 ICU/locales 등은 100MB 가까이 남는다.
    resources_dir = pyside_dir / "resources"
    if resources_dir.exists():
        shutil.rmtree(resources_dir, ignore_errors=True)

    # 4. 명백히 안 쓰는 Qt DLL/실행파일 패턴.
    HEAVY_DLL_PATTERNS = (
        "Qt6WebEngine*.dll", "QtWebEngine*.pyd",
        "Qt6WebChannel*.dll", "QtWebChannel*.pyd",
        "Qt6WebSockets*.dll", "QtWebSockets*.pyd",
        "Qt6Multimedia*.dll", "QtMultimedia*.pyd",
        "Qt6Qml*.dll", "QtQml*.pyd",
        "Qt6Quick*.dll", "QtQuick*.pyd",
        "Qt6Pdf*.dll", "QtPdf*.pyd",
        "Qt6Designer*.dll", "QtDesigner*.pyd",
        "Qt6Charts*.dll", "QtCharts*.pyd",
        "Qt6DataVisualization*.dll", "QtDataVisualization*.pyd",
        "Qt63D*.dll", "Qt3D*.pyd",
        "Qt6Sensors*.dll", "QtSensors*.pyd",
        "Qt6Bluetooth*.dll", "QtBluetooth*.pyd",
        "Qt6Positioning*.dll", "QtPositioning*.pyd",
        "Qt6Location*.dll", "QtLocation*.pyd",
        "Qt6SerialPort*.dll", "QtSerialPort*.pyd",
        "Qt6Nfc*.dll", "QtNfc*.pyd",
        "Qt6TextToSpeech*.dll", "QtTextToSpeech*.pyd",
        "Qt6SpatialAudio*.dll", "QtSpatialAudio*.pyd",
        "Qt6Remote*.dll", "QtRemote*.pyd",
        "Qt6Scxml*.dll", "QtScxml*.pyd",
        "Qt6StateMachine*.dll", "QtStateMachine*.pyd",
        "Qt6Test*.dll", "QtTest*.pyd",
        "Qt6Help*.dll", "QtHelp*.pyd",
        "Qt6UiTools*.dll", "QtUiTools*.pyd",
        "Qt6ShaderTools*.dll",
        "Qt6OpenGL*.dll", "QtOpenGL*.pyd",
        "opengl32sw.dll",
        "Qt6Designer*.exe", "QtDesigner*.exe",
        "linguist*.exe", "lupdate*.exe", "lrelease*.exe", "lconvert*.exe",
        "designer*.exe", "uic*.exe", "rcc*.exe", "qmlscene*.exe", "qml*.exe",
        # FFmpeg 멀티미디어 코덱 — 우리는 사용 안 함
        "avcodec*.dll", "avformat*.dll", "avutil*.dll",
        "swresample*.dll", "swscale*.dll",
    )

    for entry in pyside_dir.iterdir():
        if not entry.is_file():
            continue
        if any(fnmatch(entry.name, pat) for pat in HEAVY_DLL_PATTERNS):
            entry.unlink(missing_ok=True)

    # 5. 안 쓰는 Qt plugins (SQL/멀티미디어/위치/3D 등).
    plugins_dir = pyside_dir / "plugins"
    if plugins_dir.exists():
        UNUSED_PLUGIN_SUBDIRS = (
            # SQL/멀티미디어/위치
            "sqldrivers", "multimedia", "mediaservice", "audio",
            "position", "geoservices",
            # 3D / QML
            "3dinputdevices", "renderplugins", "sceneparsers",
            "geometryloaders", "renderers", "qml1tooling", "qmltooling",
            "qmllint", "assetimporters",
            # 디자이너/도구
            "designer",
            # 안 쓰는 Qt 기능 모듈
            "tls", "networkinformation", "sensors", "texttospeech",
            "webview", "scxmldatamodel", "canbus", "generic",
            # 한국어 IME 는 platforms 플러그인이 처리하므로 별도 IM 컨텍스트 불필요
            "platforminputcontexts",
        )
        for sub in UNUSED_PLUGIN_SUBDIRS:
            target = plugins_dir / sub
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)

    after_total = _dir_size(pyside_dir)
    saved_mb = (before_total - after_total) / (1024 * 1024)
    print(f"[trim] PySide6: {before_total/1024/1024:.0f}MB → {after_total/1024/1024:.0f}MB"
          f" (절감 {saved_mb:.0f}MB)")


def _dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def build_app():
    """앱 빌드"""
    print(f"\n{APP_NAME} 빌드 시작...\n")

    # 기존 빌드 정리
    clean_dist()

    # 현재 디렉토리
    app_dir = Path(__file__).resolve().parent.parent
    os.chdir(app_dir)

    # PyInstaller 옵션
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",  # GUI 앱 (콘솔 창 없음)
        "--onedir",    # 하나의 폴더로 묶기
        "--clean",     # 캐시 정리
        "--noconfirm", # 기존 빌드 덮어쓰기
    ]

    # 데이터 파일 포함 (존재하는 디렉토리만)
    for data_dir in ["core", "gui", "resources"]:
        if (app_dir / data_dir).exists():
            cmd.extend(["--add-data", f"{data_dir}{os.pathsep}{data_dir}"])

    cmd.extend([
        # PySide6: 우리는 QtCore/QtGui/QtWidgets + qfluentwidgets 가 쓰는
        # QtSvg/QtNetwork 정도만 사용한다. 기본 --collect-all 은 196MB Qt6WebEngineCore
        # 까지 끌어오므로, 명시적으로 안 쓰는 거대 모듈을 제외해 패키지를 ~5배 줄인다.
        "--collect-submodules", "PySide6",
        "--collect-binaries", "PySide6",
        "--collect-data", "PySide6",
        "--collect-all", "shiboken6",

        # 사용하지 않는 거대한 Qt 서브모듈 — 200MB+ 절감
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.QtWebEngineQuick",
        "--exclude-module", "PySide6.QtWebChannel",
        "--exclude-module", "PySide6.QtWebSockets",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtMultimediaWidgets",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtQuick3D",
        "--exclude-module", "PySide6.QtQuickWidgets",
        "--exclude-module", "PySide6.QtQuickControls2",
        "--exclude-module", "PySide6.QtPdf",
        "--exclude-module", "PySide6.QtPdfWidgets",
        "--exclude-module", "PySide6.QtDesigner",
        "--exclude-module", "PySide6.QtCharts",
        "--exclude-module", "PySide6.QtDataVisualization",
        "--exclude-module", "PySide6.QtSensors",
        "--exclude-module", "PySide6.QtBluetooth",
        "--exclude-module", "PySide6.QtPositioning",
        "--exclude-module", "PySide6.QtLocation",
        "--exclude-module", "PySide6.QtSerialPort",
        "--exclude-module", "PySide6.QtSerialBus",
        "--exclude-module", "PySide6.QtNfc",
        "--exclude-module", "PySide6.QtTextToSpeech",
        "--exclude-module", "PySide6.QtSpatialAudio",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.Qt3DRender",
        "--exclude-module", "PySide6.Qt3DInput",
        "--exclude-module", "PySide6.Qt3DLogic",
        "--exclude-module", "PySide6.Qt3DAnimation",
        "--exclude-module", "PySide6.Qt3DExtras",
        "--exclude-module", "PySide6.QtRemoteObjects",
        "--exclude-module", "PySide6.QtScxml",
        "--exclude-module", "PySide6.QtStateMachine",
        "--exclude-module", "PySide6.QtTest",
        "--exclude-module", "PySide6.QtHelp",
        "--exclude-module", "PySide6.QtUiTools",

        # QFluentWidgets: 리소스(QSS/아이콘)까지 포함해야 import 성공
        "--collect-all", "qfluentwidgets",

        # 기타 라이브러리 hidden imports
        "--hidden-import", "ebooklib",
        "--hidden-import", "bs4",
        "--hidden-import", "lxml",
        "--hidden-import", "docx",
        "--hidden-import", "yaml",
        "--hidden-import", "PIL",
        "--hidden-import", "charset_normalizer",
        "--collect-submodules", "charset_normalizer",

        # pydantic v2: pydantic_core C 확장과 동적 모듈을 모두 수집
        # (GUI 설정 스키마 SSOT인 gui.config_models.AppSettings가 의존함)
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_core",
        "--hidden-import", "annotated_types",

        # 개발 전용 / 미사용 패키지는 번들에서 제외.
        # 주의: --collect-all 로 끌어온 패키지의 서브모듈을 --exclude-module 로
        #       빼면 PyInstaller 의 의존성 그래프에서 모듈이 사라지지만 collect
        #       단계의 raw file copy 가 종종 함께 사라져 import 자체가 깨진다.
        #       대표 사례: pydantic.mypy / pydantic.v1 을 제외하면 pydantic 패키지
        #       전체가 번들에서 누락. 그래서 pydantic 관련 exclude 는 두지 않는다.
        "--exclude-module", "tkinter",
        "--exclude-module", "test",
        "--exclude-module", "unittest",
        "--exclude-module", "pytest",
        "--exclude-module", "mypy",
        "--exclude-module", "ruff",
        "--exclude-module", "setuptools",
        "--exclude-module", "pip",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "notebook",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy.testing",

        # macOS 전용
        "--osx-bundle-identifier", "com.trpg.converter",

        MAIN_SCRIPT
    ])

    # config.yaml이 있으면 포함
    if (app_dir / "config.yaml").exists():
        cmd.insert(-1, "--add-data")
        cmd.insert(-1, f"config.yaml{os.pathsep}.")

    # 스타일시트 포함 (별도 명시)
    qss_file = app_dir / "gui" / "styles" / "stylesheet.qss"
    if qss_file.exists():
        cmd.insert(-1, "--add-data")
        cmd.insert(-1, f"gui/styles/stylesheet.qss{os.pathsep}gui/styles")

    print("실행 명령:", " ".join(cmd))
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        # PyInstaller 가 끌어오는 거대 Qt 자산 정리 (WebEngine/QML/translations 등).
        trim_bundle()

        # 빌드된 exe 가 import 단계에서 죽지 않는지 빠르게 확인.
        # PyInstaller 가 모든 hidden import 를 잡지 못해 ModuleNotFoundError 가
        # 사용자에게 도달하는 사고를 막기 위한 production-grade smoke gate.
        if not _smoke_test_bundle():
            print(f"\n[FAIL] Smoke test failed — built exe crashes on launch")
            sys.exit(2)

        print(f"\n[OK] Build Success!")
        print(f"\n[OUTPUT]")
        print(f"   - dist/{APP_NAME}/  (distribution folder)")

        if sys.platform == "darwin":
            print(f"   - dist/{APP_NAME}.app  (macOS app)")
            print(f"\n[TIP] Compress dist/{APP_NAME}.app to zip for distribution.")
        else:
            print(f"   - dist/{APP_NAME}/{APP_NAME}.exe  (Windows executable)")
            print(f"\n[TIP] Compress dist/{APP_NAME} folder to zip for distribution.")
    else:
        print(f"\n[FAIL] Build failed")
        sys.exit(1)


def _smoke_test_bundle() -> bool:
    """Launch the built exe briefly to catch import errors.

    Returns True if the process is still running after a short delay (= GUI
    event loop reached). Returns False if it crashed before then, which
    typically means a ``ModuleNotFoundError`` from a missing hidden import.
    """
    import time
    app_dir = Path(__file__).resolve().parent.parent
    if sys.platform == "win32":
        exe = app_dir / "dist" / APP_NAME / f"{APP_NAME}.exe"
    elif sys.platform == "darwin":
        exe = app_dir / "dist" / f"{APP_NAME}.app" / "Contents" / "MacOS" / APP_NAME
    else:
        exe = app_dir / "dist" / APP_NAME / APP_NAME
    if not exe.exists():
        print(f"[smoke] executable not found: {exe}")
        return False

    print(f"\n[smoke] launching {exe.name}...")
    proc = subprocess.Popen(
        [str(exe)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(exe.parent),
    )
    # 4s is enough for QApplication to construct + a window to appear.
    time.sleep(4)
    if proc.poll() is None:
        print("[smoke] process still running - OK")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        return True

    # Process exited before timeout - capture output for diagnosis.
    stdout, stderr = proc.communicate(timeout=2)
    rc = proc.returncode
    print(f"[smoke] process exited early with code {rc}")
    if stderr:
        try:
            print("[smoke] stderr tail:")
            tail = stderr.decode("utf-8", errors="replace").splitlines()[-15:]
            for line in tail:
                print(f"  {line}")
        except Exception:
            pass
    return False

def main():
    print("=" * 50)
    print(f"  {APP_NAME} 빌드 스크립트 (PySide6)")
    print("=" * 50)

    # PyInstaller 확인/설치
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} 발견")
    except ImportError:
        install_pyinstaller()

    # 빌드
    build_app()

if __name__ == "__main__":
    main()
