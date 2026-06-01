"""
설정 데이터 검증 스키마 (Pydantic)
설정 파일이 깨져도 안전한 기본값으로 동작하도록 보장
"""

import logging

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class PathsConfig(BaseModel):
    input_dir: str = "./input"
    output_dir: str = "./export"
    fonts_dir: str = "./fonts"
    images_dir: str = "./images"


class CoverConfig(BaseModel):
    image: str = ""
    include: bool = True
    title_on_cover: bool = True
    author_on_cover: bool = True
    background_color: str = "#1a1a1a"
    title_color: str = "#ffffff"
    subtitle: str = ""

    @field_validator("background_color", "title_color")
    @classmethod
    def validate_color(cls, v):
        if not v.startswith("#") or len(v) not in (4, 7):
            return "#1a1a1a"
        return v


class TocConfig(BaseModel):
    include: bool = True
    title: str = "목차"
    mode: str = "auto"
    entries: list = Field(default_factory=list)
    style: str = "simple"


class FontsConfig(BaseModel):
    name_font: str = "'Pretendard', sans-serif"
    body_font: str = "'Nanum Myeongjo', serif"
    pretendard_cdn: str = (
        "https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css"
    )
    embed: dict = Field(default_factory=dict)
    docx_fallback: dict = Field(default_factory=lambda: {"body": "맑은 고딕", "name": "맑은 고딕"})


class StyleConfig(BaseModel):
    narration_prefix: str = "＿"
    scene_marker: str = "■"
    dialogue_margin: float = 0.12
    narration_margin: float = 0.8
    narration_indent: float = 1.5
    dice_color: str = "#888"

    @field_validator("dialogue_margin", "narration_margin", "narration_indent")
    @classmethod
    def validate_margin(cls, v):
        if v < 0:
            return 0.0
        if v > 10:
            return 10.0
        return v


class NarrationConfig(BaseModel):
    users: list[str] = Field(default_factory=lambda: ["GM", "KP", "DM", "Keeper", "Narrator"])
    style: str = "indent"


class ContentConfig(BaseModel):
    include_dice: bool = True
    include_system: bool = True
    include_effects: bool = True


class DialogueConfig(BaseModel):
    merge_consecutive: bool = False
    merge_separator: str = "\n"
    merge_max: int = 5

    @field_validator("merge_max")
    @classmethod
    def validate_merge_max(cls, v):
        return max(0, min(v, 100))


class ImagesConfig(BaseModel):
    enable: bool = True
    markers: list[str] = Field(default_factory=lambda: [r"\[IMG:\s*(.+?)\]", r"\[삽화:\s*(.+?)\]"])
    show_caption: bool = True
    max_resolution: int = 0
    jpeg_quality: int = 85
    convert_webp: bool = True

    @field_validator("jpeg_quality")
    @classmethod
    def validate_quality(cls, v):
        return max(10, min(v, 100))

    @field_validator("max_resolution")
    @classmethod
    def validate_resolution(cls, v):
        return max(0, v)


class ChapterConfig(BaseModel):
    split_mode: str = "scene"
    entries_per_chapter: int = 300
    extract_scene_title: bool = True
    title_format: str = "장면 {n}"
    min_scene_entries: int = 10
    scene_patterns: list[str] = Field(
        default_factory=lambda: [
            "^■",
            "^●",
            "^▶",
            "^씬\\s*\\d+",
            "^장면\\s*\\d+",
        ]
    )

    @field_validator("entries_per_chapter")
    @classmethod
    def validate_entries(cls, v):
        return max(10, min(v, 10000))

    @field_validator("min_scene_entries")
    @classmethod
    def validate_min_entries(cls, v):
        return max(1, min(v, 1000))


class ParsingConfig(BaseModel):
    name_max_length: int = 50
    skip_channels: list[str] = Field(default_factory=list)
    normalize_punctuation: bool = True

    @field_validator("name_max_length")
    @classmethod
    def validate_name_length(cls, v):
        return max(5, min(v, 200))


class PerformanceConfig(BaseModel):
    """런타임 성능 옵션."""

    parse_max_workers: int = 4
    max_html_bytes: int = 50 * 1024 * 1024  # 50 MiB

    @field_validator("parse_max_workers")
    @classmethod
    def validate_workers(cls, v):
        return max(1, min(int(v), 32))

    @field_validator("max_html_bytes")
    @classmethod
    def validate_max_bytes(cls, v):
        # 1 MiB ~ 1 GiB
        return max(1 * 1024 * 1024, min(int(v), 1024 * 1024 * 1024))


class EngineConfig(BaseModel):
    """엔진 설정 전체 스키마"""

    paths: PathsConfig = Field(default_factory=PathsConfig)
    output_format: str = "both"
    log_source: str = "auto"
    cover: CoverConfig = Field(default_factory=CoverConfig)
    toc: TocConfig = Field(default_factory=TocConfig)
    fonts: FontsConfig = Field(default_factory=FontsConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)
    narration: NarrationConfig = Field(default_factory=NarrationConfig)
    content: ContentConfig = Field(default_factory=ContentConfig)
    dialogue: DialogueConfig = Field(default_factory=DialogueConfig)
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    custom_styles: dict = Field(default_factory=dict)
    chapter: ChapterConfig = Field(default_factory=ChapterConfig)
    parsing: ParsingConfig = Field(default_factory=ParsingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    @field_validator("output_format")
    @classmethod
    def validate_format(cls, v):
        valid = {"epub", "docx", "both", "all", "pdf"}
        return v if v in valid else "both"

    @field_validator("log_source")
    @classmethod
    def validate_source(cls, v):
        valid = {"auto", "cocofolia", "roll20"}
        return v if v in valid else "auto"


def validate_engine_config(config_dict: dict) -> dict:
    """엔진 설정을 검증하고 안전한 값으로 반환.

    잘못된 값은 기본값으로 대체되며, 앱이 비정상 종료되지 않도록 보장.
    """
    try:
        validated = EngineConfig(**config_dict).model_dump()
        # 검증은 '알려진 필드'를 교정/클램프하되, 스키마에 정의되지 않은 (중첩)
        # 키까지 버리면 안 된다. Pydantic 기본 extra="ignore" 는 style.first_letter,
        # parsing.dice_keywords, toc.scene_only, style.body_line_height/색상 등
        # GUI 가 실제로 사용하는 수많은 키를 조용히 떨어뜨려, 해당 설정들이 출력에
        # 반영되지 않는 버그를 유발했다. 원본 위에 검증값을 deep_merge 해서
        # 알려진 필드는 교정된 값으로 덮되 그 외 키는 보존한다(비파괴 검증).
        from core.utils import deep_merge

        return deep_merge(config_dict, validated)
    except Exception as e:
        logger.warning("설정 검증 실패, 기본값 사용: %s", e)
        return EngineConfig().model_dump()


# GUI 설정 스키마는 gui.config_models.AppSettings가 SSOT이다.
# GUISettings 클래스는 중복이었기에 제거되었다. 필요 시
# `from gui.config_models import AppSettings, unflatten_settings, flatten_settings`
# 를 사용할 것.
