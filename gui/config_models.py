"""
Pydantic V2 기반 GUI 설정 모델

~50개의 플랫 GUI 설정을 4-탭 UI 구조에 맞는 논리적 계층 그룹으로 구성합니다.
기존 config_manager의 DEFAULT_GUI_SETTINGS(플랫 dict)와 양방향 변환을 지원합니다.

그룹 구조:
  - HomeSettings          : 변환 페이지 (플랫폼, 제목, 저자, 출력 등)
  - FormatStyleGroup      : 서식 탭 (스타일 + 폰트 + 표지 + 장식)
  - ParsingContentGroup   : 콘텐츠/파싱 탭 (콘텐츠 필터 + 장면 분할 + 파싱 규칙)
  - AdvancedGroup         : 고급 탭 (출력 레이아웃 + 고급 옵션)
  - AppSettings           : 최상위 통합 모델
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ──────────────────────────────────────────────
# 1. HomeSettings - 변환 페이지 (홈)
# ──────────────────────────────────────────────

class HomeSettings(BaseModel):
    """변환 페이지: 플랫폼, 메타데이터, 출력 기본 설정"""

    platform: str = Field("cocofolia", description="로그 소스 플랫폼")
    title: str = Field("TRPG 리플레이", description="작품 제목")
    author: str = Field("GM", description="저자")
    output_dir: str = Field("./export", description="출력 폴더 경로")
    narrators: str = Field(
        # '-' 는 cocofolia 에서 GM 메시지의 기본 표기. 넣어둬야 GM 내래이션이
        # 대사로 잘못 분류되지 않는다.
        "-, GM, KP, DM, Keeper, 나레이터, 진행자",
        description="나레이터 이름 목록 (쉼표 구분). '-' 는 cocofolia GM 기본 표기.",
    )
    language: str = Field("ko", description="EPUB 메타데이터 언어 코드")
    convert_mode: str = Field("single", description="변환 모드: single, batch")
    output_format: str = Field("both", description="출력 형식: epub, docx, both")


# ──────────────────────────────────────────────
# 2. StyleSettings - 시각적 스타일
# ──────────────────────────────────────────────

class ColorPalette(BaseModel):
    """요소별 색상 팔레트"""

    text_color: str = Field("#1a1a1a", description="본문 텍스트 색상")
    name_color: str = Field("#2d2d2d", description="캐릭터 이름 색상")
    dice_color: str = Field("#888888", description="주사위 결과 색상")
    system_color: str = Field("#666666", description="시스템 메시지 색상")
    effect_bg: str = Field("#f5f5f5", description="효과 배경색")
    effect_border: str = Field("#cccccc", description="효과 테두리 색상")


class StyleSettings(BaseModel):
    """스타일 설정: 본문 배경/텍스트, 폰트 크기, 줄 간격, 이름 스타일, 대사 구분자, 색상"""

    style_body_bg: str = Field("#ffffff", description="본문 배경색")
    style_body_text: str = Field("#1a1a1a", description="본문 텍스트 색상")
    style_font_size: int = Field(14, ge=10, le=24, description="기본 폰트 크기 (px)")
    style_line_height: float = Field(1.6, ge=1.2, le=2.4, description="줄 간격")
    style_name_color: str = Field("#2d2d2d", description="캐릭터 이름 색상")
    style_name_bold: bool = Field(True, description="캐릭터 이름 굵게 표시")
    style_separator: str = Field("「 」 (꺾쇠)", description="대사 구분자 스타일")
    custom_separator_text: str = Field("", description="직접 입력 대사 구분자")
    character_colors: Dict[str, str] = Field(
        default_factory=dict,
        description="캐릭터별 색상 매핑",
    )
    colors: ColorPalette = Field(
        default_factory=ColorPalette,
        description="요소별 색상 팔레트",
    )
    custom_theme_presets: Dict[str, Any] = Field(
        default_factory=dict,
        description="사용자 정의 테마 프리셋",
    )


# ──────────────────────────────────────────────
# 3. FontSettings - 폰트 설정
# ──────────────────────────────────────────────

class FontSettings(BaseModel):
    """폰트 설정: EPUB/DOCX 폰트, 임베드 경로, 줄 간격, 기본 폰트 크기"""

    epub_body_font: str = Field(
        "'Nanum Myeongjo', 'Batang', serif",
        description="EPUB 본문 폰트",
    )
    epub_name_font: str = Field(
        "'Pretendard', 'Apple SD Gothic Neo', sans-serif",
        description="EPUB 캐릭터 이름 폰트",
    )
    embed_body_font: str = Field("", description="임베드할 본문 폰트 파일 경로")
    embed_name_font: str = Field("", description="임베드할 이름 폰트 파일 경로")
    docx_body_font: str = Field("맑은 고딕", description="DOCX 본문 폰트")
    docx_name_font: str = Field("맑은 고딕", description="DOCX 이름 폰트")
    docx_embed_body: str = Field("", description="DOCX 본문 폰트 파일 경로")
    docx_embed_name: str = Field("", description="DOCX 이름 폰트 파일 경로")
    body_line_height: str = Field("1.6", description="본문 줄 간격")
    dialogue_line_height: str = Field("1.5", description="대사 줄 간격")
    narration_line_height: str = Field("1.7", description="나레이션 줄 간격")
    base_font_size: str = Field("1.0", description="기본 폰트 크기 배율")


# ──────────────────────────────────────────────
# 4. CoverSettings - 표지 설정
# ──────────────────────────────────────────────

class CoverSettings(BaseModel):
    """표지 설정: 표지 포함 여부, 제목/저자 표시, 부제목, 배경/제목 색상, 표지 이미지, 목차"""

    include_cover: bool = Field(True, description="표지 포함 여부")
    title_on_cover: bool = Field(True, description="표지에 제목 표시")
    author_on_cover: bool = Field(True, description="표지에 저자 표시")
    cover_subtitle: str = Field("", description="부제목")
    cover_bg: str = Field("#1a1a1a", description="표지 배경색")
    cover_title_color: str = Field("#ffffff", description="표지 제목 색상")
    cover_image: str = Field("", description="표지 이미지 경로 또는 base64")
    include_toc: bool = Field(True, description="목차 포함 여부")
    toc_title: str = Field("목차", description="목차 제목")
    toc_scene_only: bool = Field(
        False,
        description="True 면 자동 생성된 '장면 N' 제목과 시스템 노이즈를 목차에서 제외",
    )
    toc_exclude_patterns: str = Field(
        "",
        description="목차에서 숨길 씬 제목 정규식 (쉼표로 여러 개)",
    )

    @field_validator("cover_bg", "cover_title_color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if v and v.startswith("#") and len(v) in (4, 7):
            return v
        return "#1a1a1a"


# ──────────────────────────────────────────────
# 5. DecorationSettings - 장식 설정
# ──────────────────────────────────────────────

class DecorationSettings(BaseModel):
    """장식 설정: 구분선 유형/텍스트/색상, 장면 마커, 챕터 장식, 장면 구분선"""

    divider_type: str = Field("텍스트/기호", description="구분선 유형")
    divider_text: str = Field("* * *", description="구분선 텍스트/기호")
    divider_color: str = Field("#888888", description="구분선 색상")
    divider_image: str = Field("", description="구분선 이미지 데이터")
    divider_img_height: int = Field(40, ge=10, le=200, description="구분선 이미지 높이 (px)")
    line_style: str = Field("실선", description="선 스타일")
    line_thickness: int = Field(1, ge=1, le=10, description="선 두께 (px)")
    line_color: str = Field("#cccccc", description="선 색상")
    line_width: int = Field(80, ge=10, le=100, description="선 너비 (%)")
    scene_marker: str = Field("■", description="장면 마커 기호")
    chapter_ornament: str = Field("─────  ✦  ─────", description="챕터 시작 장식")
    scene_separator: str = Field("＊　＊　＊", description="장면 구분선")
    narration_prefix: str = Field("＿", description="나레이션 접두사")
    narration_indent: str = Field("1.5", description="나레이션 들여쓰기 (em)")
    # 챕터 헤더 설정
    header_style: str = Field("기본", description="챕터 헤더 스타일")
    header_size: int = Field(24, ge=12, le=48, description="헤더 폰트 크기")
    header_color: str = Field("#1a1a1a", description="헤더 색상")
    header_bold: bool = Field(True, description="헤더 굵게")
    header_prefix: str = Field("", description="헤더 접두사")
    header_suffix: str = Field("", description="헤더 접미사")
    header_underline: bool = Field(False, description="헤더 밑줄")
    header_box: bool = Field(False, description="헤더 박스 표시")
    header_box_color: str = Field("#f0f0f0", description="헤더 박스 배경색")
    # 기타 장식
    quote_style: str = Field("기본", description="인용문 스타일")
    quote_bg: str = Field("#f9f9f9", description="인용문 배경색")
    quote_border: str = Field("#cccccc", description="인용문 테두리 색상")
    dice_style: str = Field("기본", description="주사위 스타일")
    dice_icon: bool = Field(False, description="주사위 아이콘 표시")
    dice_color: str = Field("#888888", description="주사위 색상")


# ──────────────────────────────────────────────
# 6. FormatStyleGroup - 서식 탭 그룹
# ──────────────────────────────────────────────

class FormatStyleGroup(BaseModel):
    """서식 탭: 스타일 + 폰트 + 표지 + 장식"""

    style: StyleSettings = Field(default_factory=StyleSettings)
    font: FontSettings = Field(default_factory=FontSettings)
    cover: CoverSettings = Field(default_factory=CoverSettings)
    decoration: DecorationSettings = Field(default_factory=DecorationSettings)


# ──────────────────────────────────────────────
# 7. ContentFilterSettings - 콘텐츠 필터
# ──────────────────────────────────────────────

class ContentFilterSettings(BaseModel):
    """콘텐츠 필터: 포함/제외 설정, 나레이션, 대화 병합, 이미지"""

    include_dice: bool = Field(True, description="주사위 결과 포함")
    include_effects: bool = Field(True, description="연출 효과 포함")
    include_system: bool = Field(True, description="시스템 메시지 포함")
    include_ooc: bool = Field(False, description="OOC 대화 포함")
    narration_prefix: str = Field("＿", description="나레이션 접두사")
    narration_indent: str = Field("1.5", description="나레이션 들여쓰기 (em)")
    merge_dialogue: bool = Field(False, description="연속 대화 병합")
    merge_separator: str = Field("newline", description="병합 구분자: newline, space, dash")
    merge_max: str = Field("5", description="최대 병합 수")
    empty_dialogue: str = Field("……", description="빈 대사 대체 텍스트")
    images_enable: bool = Field(True, description="이미지 삽입 활성화")
    show_caption: bool = Field(True, description="이미지 캡션 표시")
    image_align: str = Field("center", description="이미지 정렬: center, left, right")
    image_max_width: str = Field("100", description="이미지 최대 너비 (%)")


# ──────────────────────────────────────────────
# 8. SceneSplitSettings - 장면 분할
# ──────────────────────────────────────────────

class SceneSplitSettings(BaseModel):
    """장면 분할 설정"""

    split_mode: str = Field("scene", description="분할 모드: scene, count, none")
    scene_patterns: str = Field(
        # '▶Scene' / '▶씬' 은 cocofolia DX3/Insane 세션에서 자주 쓰는 장면 마커.
        # '^─+' 는 '─── Act 3 ───' 같은 구분선 마커.
        # '^제\\s*\\d+\\s*장' 는 '제 2 장' 형태의 한국 출판 스타일.
        "■, ▶Scene, ▶씬, Scene, 씬, 장면, Act, ^─+, ^제\\s*\\d+\\s*장",
        description="장면 분할 패턴 (쉼표 구분, '^' 또는 정규식 사용 가능)",
    )
    entries_per_chapter: str = Field("300", description="챕터당 항목 수 (count 모드)")
    min_scene_entries: str = Field("10", description="최소 장면 항목 수")
    title_format: str = Field("장면 {n}", description="챕터 제목 형식")
    scene_marker: str = Field("■", description="장면 마커 기호")
    chapter_ornament: str = Field("─────  ✦  ─────", description="챕터 장식")
    scene_separator: str = Field("＊　＊　＊", description="장면 구분선")


# ──────────────────────────────────────────────
# 9. ParsingRulesSettings - 파싱 규칙
# ──────────────────────────────────────────────

class ParsingRulesSettings(BaseModel):
    """파싱 규칙: 구분자, 이름 위치, 이름 최대 길이, 주사위/시스템 키워드"""

    custom_separator_type: str = Field(
        "콜론 (:)",
        description="이름/대사 구분 방식",
    )
    custom_name_position: str = Field(
        "구분자 앞 (이름: 대사)",
        description="이름 위치",
    )
    custom_name_max: str = Field("50", description="이름 최대 길이")
    narration_no_name: bool = Field(
        False,
        description="이름 없는 텍스트를 나레이션으로 처리",
    )
    scene_separator_pattern: str = Field("---", description="구분선 패턴")
    dice_keywords: str = Field(
        "CCB, 1D100, 1D20, roll, Rolling",
        description="주사위 키워드 (쉼표 구분)",
    )
    system_prefix: str = Field("System:", description="시스템 메시지 접두사")


# ──────────────────────────────────────────────
# 10. ParsingContentGroup - 콘텐츠/파싱 탭 그룹
# ──────────────────────────────────────────────

class ParsingContentGroup(BaseModel):
    """콘텐츠/파싱 탭: 콘텐츠 필터 + 장면 분할 + 파싱 규칙"""

    content_filter: ContentFilterSettings = Field(default_factory=ContentFilterSettings)
    scene_split: SceneSplitSettings = Field(default_factory=SceneSplitSettings)
    parsing_rules: ParsingRulesSettings = Field(default_factory=ParsingRulesSettings)


# ──────────────────────────────────────────────
# 11. OutputSettings - 출력 레이아웃
# ──────────────────────────────────────────────

class MarginsSettings(BaseModel):
    """페이지 여백 (인치)"""

    top: str = Field("1.0", description="상단 여백")
    bottom: str = Field("1.0", description="하단 여백")
    left: str = Field("1.0", description="좌측 여백")
    right: str = Field("1.0", description="우측 여백")


class OutputSettings(BaseModel):
    """출력 레이아웃: EPUB/DOCX 판형, 사용자 정의 크기, 여백"""

    epub_page_format: str = Field("EPUB (6x9)", description="EPUB 판형")
    page_format: str = Field("A5 (148x210mm)", description="DOCX 판형")
    custom_page_width: str = Field("148", description="사용자 정의 너비 (mm)")
    custom_page_height: str = Field("210", description="사용자 정의 높이 (mm)")
    margins: MarginsSettings = Field(default_factory=MarginsSettings)


# ──────────────────────────────────────────────
# 12. AdvancedOptions - 고급 옵션
# ──────────────────────────────────────────────

class AdvancedOptions(BaseModel):
    """고급 옵션: 파싱/Roll20/이미지/캠페인/CSS 등"""

    # 파싱
    name_max_length: str = Field("50", description="이름 최대 문자 수")
    skip_channels: str = Field(
        # 한국어 + 일본어(coccfolia 원본) + 영어 변형까지 함께 처리.
        "[잡담], [ooc], 雑談, 情報, info, other",
        description="제외 채널 (쉼표 구분). [main] 은 기본 채널이라 스킵 대상이 아님",
    )
    normalize_punct: bool = Field(True, description="구두점 정규화")
    # Roll20
    session_gap: str = Field("60", description="세션 구분 간격 (분)")
    emote_style: str = Field("italic", description="이모트 스타일: italic, normal, bold")
    include_whisper: bool = Field(False, description="귓속말 포함")
    # 이미지 (고급)
    images_enable: bool = Field(True, description="이미지 포함")
    show_caption: bool = Field(True, description="이미지 캡션")
    image_align: str = Field("center", description="이미지 정렬")
    image_max_width: str = Field("100", description="이미지 최대 너비 (%)")
    image_max_resolution: str = Field("1600", description="이미지 최대 해상도 (px)")
    image_jpeg_quality: str = Field("85 (권장)", description="JPEG 품질")
    image_convert_webp: bool = Field(True, description="WebP→JPEG 변환")
    # 캠페인
    campaign_enable: bool = Field(False, description="캠페인 모드 활성화")
    campaign_title: str = Field("캠페인 리플레이", description="캠페인 제목")
    session_title_format: str = Field(
        "Session {n}: {filename}",
        description="세션 제목 형식",
    )
    # 커스텀 CSS
    custom_css: str = Field("", description="EPUB 커스텀 CSS")


# ──────────────────────────────────────────────
# 13. AdvancedGroup - 고급 탭 그룹
# ──────────────────────────────────────────────

class AdvancedGroup(BaseModel):
    """고급 탭: 출력 레이아웃 + 고급 옵션"""

    output: OutputSettings = Field(default_factory=OutputSettings)
    advanced: AdvancedOptions = Field(default_factory=AdvancedOptions)


# ──────────────────────────────────────────────
# 14. AppSettings - 최상위 통합 모델
# ──────────────────────────────────────────────

class AppSettings(BaseModel, extra="allow"):
    """최상위 설정 모델 - 모든 그룹을 결합.

    ``extra="allow"``로 이전 버전 설정이나 알려지지 않은 필드를 유지합니다.
    """

    home: HomeSettings = Field(default_factory=HomeSettings)
    format_style: FormatStyleGroup = Field(default_factory=FormatStyleGroup)
    parsing_content: ParsingContentGroup = Field(default_factory=ParsingContentGroup)
    advanced_group: AdvancedGroup = Field(default_factory=AdvancedGroup)
    _schema_version: int = 2


# ══════════════════════════════════════════════
# 헬퍼 함수: flatten / unflatten
# ══════════════════════════════════════════════

# ── 매핑 테이블 ──
# (flat_key, group_path) 형식.
# group_path 는 AppSettings 내 dotted path (예: "home.platform").
# colors와 margins는 특수 처리.

_FIELD_MAP: list[tuple[str, str]] = [
    # --- HomeSettings ---
    ("platform", "home.platform"),
    ("title", "home.title"),
    ("author", "home.author"),
    ("output_dir", "home.output_dir"),
    ("narrators", "home.narrators"),
    ("language", "home.language"),
    ("convert_mode", "home.convert_mode"),
    ("output_format", "home.output_format"),
    # --- StyleSettings ---
    ("style_body_bg", "format_style.style.style_body_bg"),
    ("style_body_text", "format_style.style.style_body_text"),
    ("style_font_size", "format_style.style.style_font_size"),
    ("style_line_height", "format_style.style.style_line_height"),
    ("style_name_color", "format_style.style.style_name_color"),
    ("style_name_bold", "format_style.style.style_name_bold"),
    ("style_separator", "format_style.style.style_separator"),
    ("custom_separator_text", "format_style.style.custom_separator_text"),
    ("character_colors", "format_style.style.character_colors"),
    ("custom_theme_presets", "format_style.style.custom_theme_presets"),
    # colors는 별도 처리 (nested dict)
    # --- FontSettings ---
    ("epub_body_font", "format_style.font.epub_body_font"),
    ("epub_name_font", "format_style.font.epub_name_font"),
    ("embed_body_font", "format_style.font.embed_body_font"),
    ("embed_name_font", "format_style.font.embed_name_font"),
    ("docx_body_font", "format_style.font.docx_body_font"),
    ("docx_name_font", "format_style.font.docx_name_font"),
    ("docx_embed_body", "format_style.font.docx_embed_body"),
    ("docx_embed_name", "format_style.font.docx_embed_name"),
    ("body_line_height", "format_style.font.body_line_height"),
    ("dialogue_line_height", "format_style.font.dialogue_line_height"),
    ("narration_line_height", "format_style.font.narration_line_height"),
    ("base_font_size", "format_style.font.base_font_size"),
    # --- CoverSettings ---
    ("include_cover", "format_style.cover.include_cover"),
    ("title_on_cover", "format_style.cover.title_on_cover"),
    ("author_on_cover", "format_style.cover.author_on_cover"),
    ("cover_subtitle", "format_style.cover.cover_subtitle"),
    ("cover_bg", "format_style.cover.cover_bg"),
    ("cover_title_color", "format_style.cover.cover_title_color"),
    ("cover_image", "format_style.cover.cover_image"),
    ("include_toc", "format_style.cover.include_toc"),
    ("toc_title", "format_style.cover.toc_title"),
    # --- DecorationSettings ---
    ("divider_type", "format_style.decoration.divider_type"),
    ("divider_text", "format_style.decoration.divider_text"),
    ("divider_color", "format_style.decoration.divider_color"),
    ("divider_image", "format_style.decoration.divider_image"),
    ("divider_img_height", "format_style.decoration.divider_img_height"),
    ("line_style", "format_style.decoration.line_style"),
    ("line_thickness", "format_style.decoration.line_thickness"),
    ("line_color", "format_style.decoration.line_color"),
    ("line_width", "format_style.decoration.line_width"),
    ("scene_marker", "format_style.decoration.scene_marker"),
    ("chapter_ornament", "format_style.decoration.chapter_ornament"),
    ("scene_separator", "format_style.decoration.scene_separator"),
    ("narration_prefix", "format_style.decoration.narration_prefix"),
    ("narration_indent", "format_style.decoration.narration_indent"),
    ("header_style", "format_style.decoration.header_style"),
    ("header_size", "format_style.decoration.header_size"),
    ("header_color", "format_style.decoration.header_color"),
    ("header_bold", "format_style.decoration.header_bold"),
    ("header_prefix", "format_style.decoration.header_prefix"),
    ("header_suffix", "format_style.decoration.header_suffix"),
    ("header_underline", "format_style.decoration.header_underline"),
    ("header_box", "format_style.decoration.header_box"),
    ("header_box_color", "format_style.decoration.header_box_color"),
    ("quote_style", "format_style.decoration.quote_style"),
    ("quote_bg", "format_style.decoration.quote_bg"),
    ("quote_border", "format_style.decoration.quote_border"),
    ("dice_style", "format_style.decoration.dice_style"),
    ("dice_icon", "format_style.decoration.dice_icon"),
    ("dice_color", "format_style.decoration.dice_color"),
    # --- ContentFilterSettings ---
    ("include_dice", "parsing_content.content_filter.include_dice"),
    ("include_effects", "parsing_content.content_filter.include_effects"),
    ("include_system", "parsing_content.content_filter.include_system"),
    ("include_ooc", "parsing_content.content_filter.include_ooc"),
    ("merge_dialogue", "parsing_content.content_filter.merge_dialogue"),
    ("merge_separator", "parsing_content.content_filter.merge_separator"),
    ("merge_max", "parsing_content.content_filter.merge_max"),
    ("empty_dialogue", "parsing_content.content_filter.empty_dialogue"),
    # --- SceneSplitSettings ---
    ("split_mode", "parsing_content.scene_split.split_mode"),
    ("scene_patterns", "parsing_content.scene_split.scene_patterns"),
    ("entries_per_chapter", "parsing_content.scene_split.entries_per_chapter"),
    ("min_scene_entries", "parsing_content.scene_split.min_scene_entries"),
    ("title_format", "parsing_content.scene_split.title_format"),
    # --- ParsingRulesSettings ---
    ("custom_separator_type", "parsing_content.parsing_rules.custom_separator_type"),
    ("custom_name_position", "parsing_content.parsing_rules.custom_name_position"),
    ("custom_name_max", "parsing_content.parsing_rules.custom_name_max"),
    ("narration_no_name", "parsing_content.parsing_rules.narration_no_name"),
    ("scene_separator_pattern", "parsing_content.parsing_rules.scene_separator_pattern"),
    ("dice_keywords", "parsing_content.parsing_rules.dice_keywords"),
    ("system_prefix", "parsing_content.parsing_rules.system_prefix"),
    # --- OutputSettings ---
    ("epub_page_format", "advanced_group.output.epub_page_format"),
    ("page_format", "advanced_group.output.page_format"),
    ("custom_page_width", "advanced_group.output.custom_page_width"),
    ("custom_page_height", "advanced_group.output.custom_page_height"),
    # margins는 별도 처리 (nested dict)
    # --- AdvancedOptions ---
    ("name_max_length", "advanced_group.advanced.name_max_length"),
    ("skip_channels", "advanced_group.advanced.skip_channels"),
    ("normalize_punct", "advanced_group.advanced.normalize_punct"),
    ("session_gap", "advanced_group.advanced.session_gap"),
    ("emote_style", "advanced_group.advanced.emote_style"),
    ("include_whisper", "advanced_group.advanced.include_whisper"),
    ("images_enable", "advanced_group.advanced.images_enable"),
    ("show_caption", "advanced_group.advanced.show_caption"),
    ("image_align", "advanced_group.advanced.image_align"),
    ("image_max_width", "advanced_group.advanced.image_max_width"),
    ("image_max_resolution", "advanced_group.advanced.image_max_resolution"),
    ("image_jpeg_quality", "advanced_group.advanced.image_jpeg_quality"),
    ("image_convert_webp", "advanced_group.advanced.image_convert_webp"),
    ("campaign_enable", "advanced_group.advanced.campaign_enable"),
    ("campaign_title", "advanced_group.advanced.campaign_title"),
    ("session_title_format", "advanced_group.advanced.session_title_format"),
    ("custom_css", "advanced_group.advanced.custom_css"),
]


def _get_nested(obj: Any, path: str) -> Any:
    """도트 경로로 중첩된 속성값을 가져옵니다."""
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


def _set_nested(data: dict, path: str, value: Any) -> None:
    """도트 경로로 중첩된 dict에 값을 설정합니다."""
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def flatten_settings(app: AppSettings) -> dict:
    """AppSettings 계층 모델을 플랫 dict로 변환합니다.

    기존 config_manager.gui_settings와 동일한 구조를 반환하므로
    하위 호환성이 보장됩니다.

    Args:
        app: AppSettings 인스턴스

    Returns:
        플랫 dict (DEFAULT_GUI_SETTINGS와 동일한 키 구조)
    """
    flat: dict = {}

    for flat_key, dotted_path in _FIELD_MAP:
        value = _get_nested(app, dotted_path)
        if value is not None:
            flat[flat_key] = value

    # colors: ColorPalette → dict
    palette = app.format_style.style.colors
    flat["colors"] = palette.model_dump()

    # margins: MarginsSettings → dict
    margins = app.advanced_group.output.margins
    flat["margins"] = margins.model_dump()

    # _schema_version
    flat["_schema_version"] = 2

    # ContentFilterSettings의 이미지/나레이션 필드는 decoration과 중복되지만
    # 플랫 dict에서는 단일 키로 존재하므로 별도 처리 불필요
    # (이미 _FIELD_MAP에서 마지막에 쓴 값이 우선)

    # extra 필드 유지
    if hasattr(app, "model_extra") and app.model_extra:
        for key, value in app.model_extra.items():
            if key not in flat and key != "_schema_version":
                flat[key] = value

    return flat


def unflatten_settings(flat: dict) -> AppSettings:
    """플랫 dict를 AppSettings 계층 모델로 변환합니다.

    Pydantic 검증을 통해 잘못된 값이 기본값으로 대체됩니다.

    Args:
        flat: DEFAULT_GUI_SETTINGS 형태의 플랫 dict

    Returns:
        검증된 AppSettings 인스턴스
    """
    nested: dict = {
        "home": {},
        "format_style": {
            "style": {},
            "font": {},
            "cover": {},
            "decoration": {},
        },
        "parsing_content": {
            "content_filter": {},
            "scene_split": {},
            "parsing_rules": {},
        },
        "advanced_group": {
            "output": {},
            "advanced": {},
        },
    }

    # 매핑 테이블을 사용하여 플랫 키를 중첩 구조로 배치
    for flat_key, dotted_path in _FIELD_MAP:
        if flat_key in flat:
            _set_nested(nested, dotted_path, flat[flat_key])

    # colors: dict → ColorPalette (별도 처리)
    if "colors" in flat and isinstance(flat["colors"], dict):
        nested["format_style"]["style"]["colors"] = flat["colors"]

    # margins: dict → MarginsSettings (별도 처리)
    if "margins" in flat and isinstance(flat["margins"], dict):
        nested["advanced_group"]["output"]["margins"] = flat["margins"]

    # character_colors (이미 _FIELD_MAP에 포함되어 있지만 dict인 경우 보정)
    if "character_colors" in flat and isinstance(flat["character_colors"], dict):
        nested["format_style"]["style"]["character_colors"] = flat["character_colors"]

    # custom_theme_presets
    if "custom_theme_presets" in flat and isinstance(flat["custom_theme_presets"], dict):
        nested["format_style"]["style"]["custom_theme_presets"] = flat["custom_theme_presets"]

    # 중복 필드 교차 배치: 플랫 dict에서는 단일 키이지만
    # 여러 sub-model에 존재하는 필드를 양쪽에 모두 채워줍니다.
    _cross_populate = {
        # flat_key -> additional dotted paths (primary path는 이미 _FIELD_MAP에서 처리됨)
        "images_enable": "parsing_content.content_filter.images_enable",
        "show_caption": "parsing_content.content_filter.show_caption",
        "image_align": "parsing_content.content_filter.image_align",
        "image_max_width": "parsing_content.content_filter.image_max_width",
        "narration_prefix": "parsing_content.content_filter.narration_prefix",
        "narration_indent": "parsing_content.content_filter.narration_indent",
    }
    for flat_key, extra_path in _cross_populate.items():
        if flat_key in flat:
            _set_nested(nested, extra_path, flat[flat_key])

    # 알려지지 않은 키들은 extra 필드로 전달
    known_flat_keys = {fk for fk, _ in _FIELD_MAP}
    known_flat_keys.update({"colors", "margins", "_schema_version"})
    extra_fields = {k: v for k, v in flat.items() if k not in known_flat_keys}
    nested.update(extra_fields)

    try:
        return AppSettings(**nested)
    except Exception:
        # 검증 실패 시 기본값 반환
        return AppSettings()
