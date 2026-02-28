"""
TRPG Log Converter Pro
PySide6 기반 macOS 네이티브 스타일 GUI 애플리케이션
"""

import sys
import os
import logging
from pathlib import Path

# 경로 설정 - 모듈 import 전에 수행
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)


def setup_app_logging():
    """애플리케이션 로깅 설정"""
    try:
        from core.services.logger import setup_logging
        # 개발 모드면 DEBUG, 아니면 INFO
        debug_mode = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')
        setup_logging(APP_DIR, debug=debug_mode)
        logging.info("TRPG Log Converter Pro 시작")
    except ImportError:
        # 로깅 모듈이 없으면 기본 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )


def load_embedded_fonts():
    """앱에 포함된 폰트 로드"""
    from PySide6.QtGui import QFontDatabase

    fonts_dir = APP_DIR / "resources" / "fonts"
    loaded_fonts = []

    if fonts_dir.exists():
        for font_file in fonts_dir.glob("*.ttf"):
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                loaded_fonts.extend(families)
        for font_file in fonts_dir.glob("*.otf"):
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                loaded_fonts.extend(families)

    return loaded_fonts


def main():
    # 로깅 설정 (가장 먼저)
    setup_app_logging()

    # PySide6 임포트
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QFontDatabase

    # 고해상도 DPI 지원
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # 앱에 포함된 폰트 로드
    embedded_fonts = load_embedded_fonts()

    # QFluentWidgets 폰트 설정 (QFluentWidgets 임포트 전에 폰트 로드 필요)
    from qfluentwidgets import qconfig

    # Pretendard 폰트를 QFluentWidgets 설정에 추가
    if 'Pretendard' in QFontDatabase.families():
        qconfig.set(qconfig.fontFamilies, ['Pretendard', 'Malgun Gothic', 'Segoe UI'])
    else:
        qconfig.set(qconfig.fontFamilies, ['Malgun Gothic', 'Segoe UI', 'Microsoft YaHei'])

    # 플랫폼별 폰트 설정
    if sys.platform == 'darwin':
        # macOS: 시스템 기본 폰트 사용
        app.setStyle('macos')
        font = QFont('.AppleSystemUIFont', 13)
        app.setFont(font)
    elif sys.platform == 'win32':
        # Windows: 임베디드 Pretendard 폰트 우선 사용
        available_fonts = QFontDatabase.families()

        # Pretendard가 로드되었으면 사용
        if 'Pretendard' in available_fonts:
            font = QFont('Pretendard', 10)
            font.setStyleStrategy(QFont.PreferAntialias)
            app.setFont(font)
        else:
            # Fallback 폰트
            fallback_fonts = [
                'Malgun Gothic',
                '맑은 고딕',
                'Segoe UI',
            ]
            for font_name in fallback_fonts:
                if font_name in available_fonts:
                    font = QFont(font_name, 10)
                    font.setStyleStrategy(QFont.PreferAntialias)
                    app.setFont(font)
                    break

    # 앱 메타데이터
    app.setApplicationName("TRPG Log Converter Pro")
    app.setApplicationVersion("2.1")
    app.setOrganizationName("TRPG Tools")

    # ConfigManager 및 메인 윈도우 로드
    from core.config_manager import ConfigManager
    from gui import MainWindow

    config_manager = ConfigManager(APP_DIR)
    window = MainWindow(config_manager)
    window.show()

    # macOS에서 창을 앞으로 가져오기
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
