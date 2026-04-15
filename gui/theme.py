"""
TRPG Log Converter Pro - 테마 상수
UI 전역에서 사용되는 색상, 크기, 간격 등의 중앙 관리
"""


# ==================== Colors ====================
class Colors:
    """앱 전역 색상"""
    ACCENT = "#0A84FF"
    ACCENT_HOVER = "#3399FF"
    ACCENT_PRESSED = "#005BBB"
    ACCENT_DARK = "#0066CC"

    SUCCESS = "#22C55E"
    SUCCESS_DARK = "#16A34A"
    ERROR = "#FF3B30"
    ERROR_DARK = "#D93025"
    WARNING = "#FF9500"

    # 시맨틱 배경 (rgba — 카드/버튼 hover 등)
    ACCENT_BG = "rgba(10, 132, 255, 0.1)"
    ACCENT_BG_HOVER = "rgba(10, 132, 255, 0.2)"
    ACCENT_BG_PRESSED = "rgba(10, 132, 255, 0.3)"
    ACCENT_BG_SOFT = "rgba(0, 122, 255, 0.08)"
    ERROR_BG = "rgba(255, 59, 48, 0.06)"
    ERROR_BG_SOFT = "rgba(255, 59, 48, 0.1)"
    ERROR_BG_HOVER = "rgba(255, 59, 48, 0.2)"
    ERROR_BG_PRESSED = "rgba(255, 59, 48, 0.3)"
    ERROR_BORDER = "rgba(255, 59, 48, 0.5)"
    SUCCESS_BG = "rgba(34, 197, 94, 0.1)"

    # 텍스트
    TEXT_PRIMARY = "palette(text)"
    TEXT_SECONDARY = "palette(dark)"
    TEXT_MUTED = "palette(mid)"
    TEXT_MUTED_LIGHT = "#6E6E73"   # SubtitleLabel light mode
    TEXT_MUTED_DARK = "#98989D"    # SubtitleLabel dark mode

    # 표면
    SURFACE = "palette(base)"
    SURFACE_HOVER = "rgba(128, 128, 128, 0.1)"
    SURFACE_PRESSED = "rgba(128, 128, 128, 0.15)"
    BORDER = "rgba(128, 128, 128, 0.2)"
    BORDER_HOVER = "rgba(128, 128, 128, 0.35)"
    BORDER_ACCENT = "rgba(10, 132, 255, 0.4)"

    # 도움말 버튼
    HELP_BG = "rgba(128, 128, 128, 0.1)"
    HELP_BORDER = "rgba(128, 128, 128, 0.2)"
    HELP_TEXT = "rgba(128, 128, 128, 0.55)"
    HELP_HOVER_BG = "rgba(10, 132, 255, 0.12)"
    HELP_HOVER_BORDER = "rgba(10, 132, 255, 0.4)"

    # 네비게이션 (미리보기)
    NAV_BG = "rgba(0, 122, 255, 0.08)"
    NAV_BORDER = "rgba(0, 122, 255, 0.2)"
    NAV_HOVER_BG = "rgba(0, 122, 255, 0.18)"
    NAV_HOVER_BORDER = "rgba(0, 122, 255, 0.4)"


# ==================== Sizes ====================
class Sizes:
    """크기 상수"""
    # 페이지 레이아웃
    PAGE_MARGIN_H = 28
    PAGE_MARGIN_V_TOP = 24
    PAGE_MARGIN_V_BOTTOM = 28
    PAGE_SPACING = 16

    # 헤더
    HEADER_TITLE_H = 36
    HEADER_SUBTITLE_H = 28
    HEADER_BOTTOM_SPACE = 8

    # 버튼 높이
    BUTTON_SM_H = 34
    BUTTON_MD_H = 38
    BUTTON_LG_H = 40

    # 도움말 버튼 (? 스타일 - Notion/Figma)
    HELP_BUTTON = 20
    HELP_BORDER_RADIUS = 10

    # 카드
    CARD_PADDING_H = 20
    CARD_PADDING_V_TOP = 16
    CARD_PADDING_V_BOTTOM = 18
    CARD_SPACING = 8
    CARD_CONTENT_SPACING = 12

    # 필드
    FIELD_LABEL_MIN_WIDTH = 110
    FIELD_MIN_HEIGHT = 30
    FIELD_SPACING = 14

    # 미리보기
    PREVIEW_TOOLBAR_BTN = 28
    PREVIEW_PAGE_SPIN_W = 44
    PREVIEW_FORMAT_MIN_W = 200
    PREVIEW_ZOOM_COMBO_W = 66
    PREVIEW_MIN_WIDTH = 280

    # 입력
    INPUT_MIN_HEIGHT = 38
    INPUT_NUMERIC_MAX_W = 200
    MARGIN_INPUT_W = 80
    MARGIN_LABEL_W = 24

    # 색상 피커
    COLOR_SWATCH = 32
    COLOR_HEX_MIN_W = 90
    COLOR_HEX_MAX_W = 100


# ==================== Spacing ====================
class Spacing:
    """간격 상수"""
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 28


# ==================== Typography ====================
class Typography:
    """타이포그래피 상수"""
    FONT_FAMILY = '"Pretendard", "Malgun Gothic", sans-serif'
    FONT_MONO = '"Consolas", "Monaco", "Menlo", monospace'

    # 크기
    SIZE_TINY = 10
    SIZE_XS = 11
    SIZE_SM = 12
    SIZE_MD = 13
    SIZE_LG = 14
    SIZE_LG_PLUS = 15
    SIZE_XL = 16
    SIZE_XL_PLUS = 18
    SIZE_XXL = 20
    SIZE_TITLE = 24
    SIZE_HERO = 32
    SIZE_DISPLAY = 48

    # 무게
    WEIGHT_NORMAL = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


# ==================== 언어 매핑 ====================
LANGUAGE_MAP = {
    "한국어 (Korean)": "ko",
    "English": "en",
    "日本語 (Japanese)": "ja",
}
LANGUAGE_REVERSE_MAP = {v: k for k, v in LANGUAGE_MAP.items()}

# ==================== 기본값 ====================
DEFAULTS = {
    "narrators": "GM, KP, DM, Keeper, 나레이터, 진행자",
    "language": "ko",
    "split_mode": "scene",
    "scene_patterns": "■, 씬, Scene, 장면, Act",
    "entries_per_chapter": "300",
    "min_scene_entries": "10",
    "title_format": "장면 {n}",
    "margin": "1.0",
}
