import yaml
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

from core.utils import deep_merge, safe_int, safe_float
from core.config.defaults import (
    CONFIG_SCHEMA_VERSION,
    DEFAULT_ENGINE_CONFIG,
    default_engine_config,
)
from core.config.migrations import migrate_gui_settings

logger = logging.getLogger(__name__)


def _default_gui_settings() -> dict:
    """Pydantic AppSettings 기본값을 플랫 dict로 변환해 반환.

    Why: GUI 설정의 유일한 스키마 소스는 gui.config_models.AppSettings이다.
         이 함수는 기본값을 동적으로 생성해 상수 중복을 제거한다.
    """
    # 지연 import: core → gui 방향 계층 역전을 피함
    from gui.config_models import AppSettings, flatten_settings
    return flatten_settings(AppSettings())


def _load_bundled_default(app_dir: Path) -> Optional[dict]:
    """배포에 동봉된 default_settings.json 을 읽는다.

    배포자가 미리 정한 디폴트(폰트, 판형, scene_patterns, custom_css 등)를
    첫 실행 시 자동 적용하기 위한 용도. 사용자가 한 번이라도 설정을 저장하면
    gui_settings.json 이 우선이고 이 파일은 무시된다.

    탐색 위치:
      1. app_dir / "default_settings.json"  (배포 폴더 또는 dev 디렉토리)
      2. PyInstaller _MEIPASS / "default_settings.json"  (frozen 번들 내)
    """
    candidates = [app_dir / "default_settings.json"]
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "default_settings.json")
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data.pop("_meta", None)
                logger.info("배포 기본 설정 로드: %s (%d 키)", p.name, len(data))
                return data
            except Exception as e:
                logger.warning("default_settings.json 로드 실패: %s", e)
    return None


class ConfigManager:
    """GUI 설정과 엔진 설정을 관리하는 클래스.

    엔진용 기본값은 ``core.config.defaults.DEFAULT_ENGINE_CONFIG`` 단일 소스에서 가져옵니다.
    ``ConfigManager.DEFAULT_CONFIG`` 는 외부 코드 호환용 alias 입니다.
    """

    # Backwards-compatible alias — 새 코드는 core.config.default_engine_config() 사용
    DEFAULT_CONFIG = DEFAULT_ENGINE_CONFIG

    def __init__(self, app_dir: Optional[Path] = None) -> None:
        if app_dir is None:
            self.app_dir = Path(__file__).parent.parent
        else:
            self.app_dir = Path(app_dir)

        self.config_path: Path = self.app_dir / "config.yaml"
        self.settings_path: Path = self.app_dir / "gui_settings.json"

        self.yaml_config: Dict = self._load_yaml_config()
        self.gui_settings: Dict = self._load_gui_settings()

        # 서비스 초기화 (지연 로딩)
        self._history_manager = None
        self._profile_manager = None

    @property
    def history(self):
        """변환 이력 관리자 (지연 로딩)"""
        if self._history_manager is None:
            try:
                from core.services.history import HistoryManager
                self._history_manager = HistoryManager(self.app_dir)
            except ImportError:
                logger.warning("HistoryManager를 로드할 수 없습니다")
        return self._history_manager

    @property
    def profiles(self):
        """프로필 관리자 (지연 로딩)"""
        if self._profile_manager is None:
            try:
                from core.services.profiles import ProfileManager
                self._profile_manager = ProfileManager(self.app_dir)
            except ImportError:
                logger.warning("ProfileManager를 로드할 수 없습니다")
        return self._profile_manager

    def _load_yaml_config(self) -> Dict:
        """config.yaml 로드"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except (IOError, yaml.YAMLError) as e:
                logger.warning("config.yaml 로드 실패: %s", e)
        return {}

    def _load_gui_settings(self) -> Dict:
        """GUI 설정 로드 — 파일을 읽고 스키마 마이그레이션만 수행한다.

        우선순위:
          1) 사용자 ``gui_settings.json`` (있으면 항상 우선)
          2) 배포 동봉 ``default_settings.json`` (없으면 단계 3)
          3) Pydantic ``AppSettings`` 기본값
        """
        if self.settings_path.exists():
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                loaded = migrate_gui_settings(loaded)
                # 기본값과 병합: 사용자 파일에 없는 신규 키에 기본값을 채워준다
                merged = _default_gui_settings()
                merged.update(loaded)
                return merged
            except Exception as e:
                logger.warning("GUI 설정 파일 로드 실패, 기본값 사용: %s", e)

        # 사용자 설정 없음 — 배포에 동봉된 default_settings.json 으로 fallback
        bundled = _load_bundled_default(self.app_dir)
        if bundled is not None:
            merged = _default_gui_settings()
            merged.update(migrate_gui_settings(bundled))
            return merged

        return _default_gui_settings()

    def save_gui_settings(self, settings: Dict) -> None:
        """GUI 설정 저장"""
        self.gui_settings = settings
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    def get_gui_settings(self) -> Dict:
        """GUI 설정 반환"""
        return self.gui_settings

    def get_default_gui_settings(self) -> Dict:
        """기본 GUI 설정 반환 (Pydantic AppSettings 기반)"""
        return _default_gui_settings()

    def build_engine_config(self, gui_settings: Optional[Dict] = None) -> Dict:
        """GUI 설정을 엔진이 이해하는 config 형식으로 변환"""
        if gui_settings is None:
            gui_settings = self.gui_settings

        sep_map = {'newline': '\n', 'space': ' ', 'dash': ' — '}

        # 기본 설정과 병합
        config = deep_merge(default_engine_config(), self.yaml_config)

        # GUI 설정 적용
        gui_config = {
            'log_source': gui_settings.get('platform', 'auto'),
            'output_format': gui_settings.get('output_format', 'both'),
            'metadata': {
                'author': gui_settings.get('author', 'GM'),
                'language': gui_settings.get('language', 'ko'),
            },
            'paths': {
                'output_dir': gui_settings.get('output_dir', str(self.app_dir / 'export')),
                'images_dir': str(self.app_dir / 'images'),
                'fonts_dir': str(self.app_dir / 'fonts'),
            },
            'narration': {
                'users': (
                    gui_settings.get('narrators')
                    if isinstance(gui_settings.get('narrators'), list)
                    else [n.strip() for n in str(gui_settings.get('narrators', 'GM')).split(',')]
                ),
            },
            'style': {
                'narration_prefix': gui_settings.get('narration_prefix', '＿'),
                'scene_marker': gui_settings.get('scene_marker', '■'),
                'chapter_ornament': gui_settings.get('chapter_ornament', '─────  ✦  ─────'),
                'scene_separator': gui_settings.get('scene_separator', '＊　＊　＊'),
                'base_font_size': safe_float(gui_settings.get('base_font_size', '1.0'), 1.0),
                'body_line_height': safe_float(gui_settings.get('body_line_height', '1.6'), 1.6),
                'dialogue_line_height': safe_float(gui_settings.get('dialogue_line_height', '1.5'), 1.5),
                'narration_line_height': safe_float(gui_settings.get('narration_line_height', '1.7'), 1.7),
                'narration_indent': safe_float(gui_settings.get('narration_indent', '1.5'), 1.5),
            },
            'fonts': {
                'body_font': gui_settings.get('epub_body_font', "'Nanum Myeongjo', serif"),
                'name_font': gui_settings.get('epub_name_font', "'Pretendard', sans-serif"),
                'embed': {
                    'body': gui_settings.get('embed_body_font', ''),
                    'name': gui_settings.get('embed_name_font', ''),
                },
                'docx_fallback': {
                    'body': gui_settings.get('docx_body_font', '맑은 고딕'),
                    'name': gui_settings.get('docx_name_font', '맑은 고딕'),
                },
            },
            'content': {
                'include_dice': gui_settings.get('include_dice', True),
                'include_effects': gui_settings.get('include_effects', True),
                'include_system': gui_settings.get('include_system', True),
                'include_ooc': gui_settings.get('include_ooc', False),
            },
            'dialogue': {
                'merge_consecutive': gui_settings.get('merge_dialogue', False),
                'merge_separator': sep_map.get(gui_settings.get('merge_separator', 'newline'), '\n'),
                'merge_max': safe_int(gui_settings.get('merge_max', '5'), 5),
                'empty_dialogue': gui_settings.get('empty_dialogue', '……'),
            },
            'images': {
                'enable': gui_settings.get('images_enable', True),
                'show_caption': gui_settings.get('show_caption', True),
                'alignment': gui_settings.get('image_align', 'center'),
                'max_width': safe_int(gui_settings.get('image_max_width', '100'), 100),
                'max_resolution': safe_int(gui_settings.get('image_max_resolution', '1600'), 1600),
                'jpeg_quality': safe_int(gui_settings.get('image_jpeg_quality', '85 (권장)'), 85),
                'convert_webp': gui_settings.get('image_convert_webp', True),
            },
            'cover': {
                'include': gui_settings.get('include_cover', True),
                'title_on_cover': gui_settings.get('title_on_cover', True),
                'author_on_cover': gui_settings.get('author_on_cover', True),
                'image': gui_settings.get('cover_image', ''),
                'subtitle': gui_settings.get('cover_subtitle', ''),
                'background_color': gui_settings.get('cover_bg', '#1a1a1a'),
                'title_color': gui_settings.get('cover_title_color', '#ffffff'),
            },
            'toc': {
                'include': gui_settings.get('include_toc', True),
                'title': gui_settings.get('toc_title', '목차'),
            },
            'chapter': {
                'split_mode': gui_settings.get('split_mode', 'scene'),
                # GUI 에서는 쉼표로 구분된 키워드 문자열("■, ▶Scene, 씬, ...")을 받는다.
                # 그대로 re.search 에 넣으면 본문 중간 'Scene' 같은 단어도 매칭되어 오탐이
                # 된다. 이미 '^' 로 시작하지 않는 항목은 자동으로 선두 앵커를 붙인다.
                'scene_patterns': (
                    gui_settings.get('scene_patterns')
                    if isinstance(gui_settings.get('scene_patterns'), list)
                    else [
                        (p if p.startswith('^') else '^' + p)
                        for p in (
                            s.strip()
                            for s in str(gui_settings.get('scene_patterns', '■')).split(',')
                        )
                        if p
                    ]
                ),
                'entries_per_chapter': safe_int(gui_settings.get('entries_per_chapter', '300'), 300),
                'min_scene_entries': safe_int(gui_settings.get('min_scene_entries', '10'), 10),
                'title_format': gui_settings.get('title_format', '장면 {n}'),
            },
            'layout': {
                'docx_margin': (lambda m: {
                    k: safe_float(m.get(k, '1.0'), 1.0)
                    for k in ('top', 'bottom', 'left', 'right')
                })(gui_settings.get('margins') if isinstance(gui_settings.get('margins'), dict) else {}),
            },
            # DOCX 와 PDF 가 공유하는 판형 정보 (core.layout 헬퍼로 파싱)
            'page_format': gui_settings.get('page_format', 'A5 (148x210mm)'),
            'epub_page_format': gui_settings.get('epub_page_format', 'EPUB (6x9)'),
            # 챕터(씬) 제목 헤더 설정 — DOCX/EPUB/PDF 가 공유
            'header': {
                'size': safe_int(gui_settings.get('header_size', 24), 24),
                'color': gui_settings.get('header_color', '#1a1a1a'),
                'bold': gui_settings.get('header_bold', True),
                'underline': gui_settings.get('header_underline', False),
                'prefix': gui_settings.get('header_prefix', ''),
                'suffix': gui_settings.get('header_suffix', ''),
                'box': gui_settings.get('header_box', False),
                'box_color': gui_settings.get('header_box_color', '#f5f5f5'),
                'style': gui_settings.get('header_style', '기본'),
            },
            'parsing': {
                'name_max_length': safe_int(gui_settings.get('name_max_length', '50'), 50),
                'skip_channels': [c.strip() for c in gui_settings.get('skip_channels', '').split(',') if c.strip()],
                'normalize_punctuation': gui_settings.get('normalize_punct', True),
            },
            'roll20': {
                'session_gap_minutes': safe_int(gui_settings.get('session_gap', '60'), 60),
                'emote_style': gui_settings.get('emote_style', 'italic'),
                'include_whisper': gui_settings.get('include_whisper', False),
            },
            'campaign': {
                'enable': gui_settings.get('campaign_enable', False),
                'title': gui_settings.get('campaign_title', '캠페인 리플레이'),
                'session_title_format': gui_settings.get('session_title_format', 'Session {n}: {filename}'),
            },
        }

        # 색상 설정 적용
        colors = gui_settings.get('colors', {})
        if colors:
            gui_config['style'].update({
                'text_color': colors.get('text_color', '#1a1a1a'),
                'name_color': colors.get('name_color', '#2d2d2d'),
                'dice_color': colors.get('dice_color', '#888888'),
                'system_color': colors.get('system_color', '#666666'),
                'effect_bg': colors.get('effect_bg', '#f5f5f5'),
                'effect_border': colors.get('effect_border', '#cccccc'),
            })

        # 비주얼 에디터 스타일 설정 적용 (ContentPage에서 설정)
        gui_config['style'].update({
            'body_bg': gui_settings.get('style_body_bg', '#ffffff'),
            'body_text': gui_settings.get('style_body_text', '#1a1a1a'),
            'body_font_size': safe_int(gui_settings.get('style_font_size', 14), 14),
            'name_color': gui_settings.get('style_name_color', '#2d2d2d'),
            'name_bold': gui_settings.get('style_name_bold', True),
            'visual_line_height': safe_float(gui_settings.get('style_line_height', 1.6), 1.6),
            'dialogue_separator': gui_settings.get('style_separator', '「 」 (꺾쇠)'),
        })

        # 커스텀 CSS
        gui_config['custom_css'] = gui_settings.get('custom_css', '')

        merged = deep_merge(config, gui_config)

        # Pydantic으로 최종 설정 검증
        try:
            from core.services.config_schema import validate_engine_config
            validated = validate_engine_config(merged)
            # validate_engine_config가 인식하지 못하는 필드 유지
            for key in merged:
                if key not in validated:
                    validated[key] = merged[key]
            return validated
        except ImportError:
            return merged

    def get_config(self):
        """엔진 config 반환 (호환성 유지)"""
        return self.build_engine_config()

    def build_engine_config_with_profile(self, gui_settings=None, profile_id: str = None) -> Dict:
        """프로필을 적용한 엔진 config 생성"""
        config = self.build_engine_config(gui_settings)

        if self.profiles and profile_id:
            config = self.profiles.apply_profile_to_config(config, profile_id)

        return config

    def record_conversion(self, input_file: str, output_files: list,
                          output_format: str, title: str, author: str,
                          entry_count: int, scene_count: int,
                          success: bool, error_message: str = None,
                          duration_ms: int = 0, profile_used: str = None):
        """변환 기록 추가"""
        if self.history:
            return self.history.add_record(
                input_file=input_file,
                output_files=output_files,
                output_format=output_format,
                title=title,
                author=author,
                entry_count=entry_count,
                scene_count=scene_count,
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
                profile_used=profile_used,
            )
        return None

    def get_recent_files(self, limit: int = 10) -> list:
        """최근 변환 파일 목록"""
        if self.history:
            return self.history.get_recent_files(limit)
        return []

    def get_conversion_stats(self) -> Dict:
        """변환 통계"""
        if self.history:
            return self.history.get_stats()
        return {}
