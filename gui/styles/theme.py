"""
TRPG Log Converter Pro - 테마 정의
macOS Human Interface Guidelines 기반
"""

from pathlib import Path


class MacOSPalette:
    """macOS 시스템 색상 팔레트"""

    # 시스템 색상 (라이트/다크 모드 자동 전환)
    WINDOW_BG = "palette(window)"
    SIDEBAR_BG = "rgba(245, 245, 247, 0.95)"
    SIDEBAR_BG_DARK = "rgba(30, 30, 32, 0.95)"

    # 액센트 (시스템 연동)
    ACCENT = "#007AFF"  # macOS 기본 블루
    ACCENT_HOVER = "#0066DD"
    ACCENT_PRESSED = "#0055CC"

    # 텍스트
    TEXT_PRIMARY = "#1d1d1f"
    TEXT_SECONDARY = "#86868b"
    TEXT_TERTIARY = "#aeaeb2"
    TEXT_ON_ACCENT = "#ffffff"

    # 카드/컨테이너
    CARD_BG = "#ffffff"
    CARD_BG_DARK = "#2c2c2e"
    CARD_BORDER = "rgba(0, 0, 0, 0.1)"
    CARD_SHADOW = "rgba(0, 0, 0, 0.08)"

    # 입력 필드
    INPUT_BG = "#ffffff"
    INPUT_BORDER = "rgba(0, 0, 0, 0.15)"
    INPUT_BORDER_FOCUS = "#007AFF"

    # 상태 색상 (Apple HIG)
    SUCCESS = "#34C759"
    WARNING = "#FF9500"
    DANGER = "#FF3B30"
    INFO = "#5856D6"

    # 구분선
    SEPARATOR = "rgba(0, 0, 0, 0.1)"
    SEPARATOR_DARK = "rgba(255, 255, 255, 0.1)"


class Theme:
    """앱 전체 테마 관리"""

    # 테마 프리셋
    PRESETS = {
        "Tokyo Night": {
            "colors": ["#1a1b26", "#24283b", "#414868", "#7aa2f7", "#bb9af7",
                       "#7dcfff", "#9ece6a", "#e0af68", "#f7768e", "#c0caf5"],
            "body_bg": "#1a1b26",
            "body_text": "#c0caf5",
            "name_color": "#7aa2f7",
        },
        "Tokyo Night Light": {
            "colors": ["#d5d6db", "#9699a3", "#4e5173", "#34548a", "#5a4a78",
                       "#166775", "#485e30", "#8f5e15", "#8c4351", "#343b59"],
            "body_bg": "#d5d6db",
            "body_text": "#343b59",
            "name_color": "#34548a",
        },
        "Sepia": {
            "colors": ["#f8f4e8", "#e8e0c8", "#d4c8a8", "#8b7355", "#6b5344",
                       "#4a3728", "#3d2f24", "#2d1f1a", "#8b4513", "#a0522d"],
            "body_bg": "#f8f4e8",
            "body_text": "#3d2f24",
            "name_color": "#6b5344",
        },
        "Classic Light": {
            "colors": ["#ffffff", "#f5f5f5", "#e0e0e0", "#cccccc", "#999999",
                       "#666666", "#333333", "#1a1a1a", "#2d2d2d", "#4a4a4a"],
            "body_bg": "#ffffff",
            "body_text": "#1a1a1a",
            "name_color": "#2d2d2d",
        },
        "Dark Mode": {
            "colors": ["#121212", "#1e1e1e", "#2d2d2d", "#3d3d3d", "#4d4d4d",
                       "#6d6d6d", "#8d8d8d", "#adadad", "#cdcdcd", "#ededed"],
            "body_bg": "#121212",
            "body_text": "#ededed",
            "name_color": "#adadad",
        },
    }

    # 캐릭터 색상 팔레트
    CHARACTER_COLORS = [
        "#007AFF",  # Blue
        "#34C759",  # Green
        "#FF9500",  # Orange
        "#AF52DE",  # Purple
        "#FF2D55",  # Pink
        "#5856D6",  # Indigo
        "#00C7BE",  # Teal
        "#FF3B30",  # Red
        "#FFCC00",  # Yellow
        "#64D2FF",  # Cyan
    ]

    @staticmethod
    def get_stylesheet() -> str:
        """Qt 스타일시트 로드"""
        qss_path = Path(__file__).parent / "stylesheet.qss"
        if qss_path.exists():
            return qss_path.read_text(encoding='utf-8')
        return ""

    @staticmethod
    def get_preset(name: str) -> dict:
        """테마 프리셋 가져오기"""
        return Theme.PRESETS.get(name, Theme.PRESETS["Classic Light"])
