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
    # PyInstaller _internal 디렉토리 (리소스, 모듈 등)
    RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', APP_DIR))
else:
    APP_DIR = Path(__file__).parent
    RESOURCE_DIR = APP_DIR

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

    fonts_dir = RESOURCE_DIR / "resources" / "fonts"
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

        if 'Pretendard' in available_fonts:
            font_name = 'Pretendard'
        else:
            font_name = 'Malgun Gothic'
            for name in ['Malgun Gothic', '맑은 고딕', 'Segoe UI']:
                if name in available_fonts:
                    font_name = name
                    break

        font = QFont(font_name, 10)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        app.setFont(font)

    # 앱 메타데이터
    app.setApplicationName("TRPG Log Converter Pro")
    app.setApplicationVersion("2.1")
    app.setOrganizationName("TRPG Tools")

    # QSS 스타일시트 로드 (Typography 토큰 __FS_*__ 를 실제 px 값으로 치환)
    # 치환을 건너뛰면 Qt가 "__FS_SM__px" 같은 잘못된 값을 무시해 폰트/높이 규칙이
    # 전부 깨지고, 미리보기 패널 판형 콤보 등의 글자가 잘려 보임.
    from gui.styles.theme import Theme as StyleTheme
    qss_path = RESOURCE_DIR / "gui" / "styles" / "stylesheet.qss"
    if qss_path.exists():
        qss_text = StyleTheme.get_stylesheet()
        if not qss_text:
            qss_text = qss_path.read_text(encoding='utf-8')
        app.setStyleSheet(qss_text)
        logging.info("스타일시트 로드 완료: %s", qss_path)
    else:
        logging.warning("스타일시트를 찾을 수 없음: %s", qss_path)

    # ConfigManager 및 메인 윈도우 로드
    from core.config_manager import ConfigManager
    from gui import MainWindow

    config_manager = ConfigManager(APP_DIR)
    window = MainWindow(config_manager)
    window.show()

    # FluentWindow(frameless)는 show() 전 resize()가 무시되어 첫 프레임이
    # 작게 뜨는 경우가 있음 → show() 직후 의도한 크기로 다시 잡고 화면 중앙 배치
    screen = window.screen() or app.primaryScreen()
    if screen is not None:
        avail = screen.availableGeometry()
        target_w = min(1300, avail.width() - 80)
        target_h = min(800, avail.height() - 80)
        window.resize(target_w, target_h)
        window.move(
            avail.x() + (avail.width() - target_w) // 2,
            avail.y() + (avail.height() - target_h) // 2,
        )

    # macOS에서 창을 앞으로 가져오기
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
