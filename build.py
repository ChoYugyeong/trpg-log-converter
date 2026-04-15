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

    app_dir = Path(__file__).parent
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

def build_app():
    """앱 빌드"""
    print(f"\n{APP_NAME} 빌드 시작...\n")

    # 기존 빌드 정리
    clean_dist()

    # 현재 디렉토리
    app_dir = Path(__file__).parent
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
    for data_dir in ["core", "gui", "utils", "resources"]:
        if (app_dir / data_dir).exists():
            cmd.extend(["--add-data", f"{data_dir}{os.pathsep}{data_dir}"])

    cmd.extend([

        # PySide6 관련 hidden imports
        "--hidden-import", "PySide6",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",

        # QFluentWidgets hidden imports
        "--hidden-import", "qfluentwidgets",
        "--hidden-import", "qfluentwidgets.components",
        "--hidden-import", "qfluentwidgets.common",
        "--hidden-import", "qfluentwidgets.window",

        # 기타 라이브러리 hidden imports
        "--hidden-import", "ebooklib",
        "--hidden-import", "bs4",
        "--hidden-import", "lxml",
        "--hidden-import", "docx",
        "--hidden-import", "yaml",
        "--hidden-import", "PIL",

        # pydantic v2: pydantic_core C 확장과 동적 모듈을 모두 수집
        # (GUI 설정 스키마 SSOT인 gui.config_models.AppSettings가 의존함)
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_core",
        "--hidden-import", "annotated_types",

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
