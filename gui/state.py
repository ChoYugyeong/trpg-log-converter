"""
TRPG Log Converter Pro - 중앙 반응형 상태 관리

Pydantic V2 모델 기반 설정을 관리하며,
값 변경 시 Qt Signal을 방출하여 UI가 자동 업데이트됩니다.

아키텍처:
    ConfigManager (JSON I/O)
         ↕ load/save
    AppState (QObject)  ← 중앙 상태 소스
         ↓ changed / group_changed Signal
    DocumentPreview, InspectorBar, Pages ...

사용 패턴:
    # 값 설정 (Signal 자동 방출)
    state.set('style_font_size', 14)

    # 값 읽기
    size = state.get('style_font_size')

    # 개별 키 변경 감지
    state.changed.connect(lambda key, val: print(f'{key} = {val}'))

    # 그룹 변경 감지 (미리보기 갱신 등)
    state.group_changed.connect(lambda group: preview.refresh())

    # 일괄 업데이트 (Signal 한 번만 방출)
    with state.batch_update():
        state.set('style_font_size', 14)
        state.set('style_line_height', 1.6)
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from PySide6.QtCore import QMutex, QMutexLocker, QObject, Signal

from .config_models import AppSettings, flatten_settings, unflatten_settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# 키 → 그룹 매핑
# ══════════════════════════════════════════════
# 각 flat key가 어떤 UI 그룹에 속하는지를 정의합니다.
# group_changed Signal은 이 매핑을 기준으로 방출됩니다.

_KEY_GROUP_MAP: dict[str, str] = {
    # ── basic (홈) ──
    "platform": "basic",
    "title": "basic",
    "author": "basic",
    "output_dir": "basic",
    "narrators": "basic",
    "language": "basic",
    "convert_mode": "basic",
    "output_format": "basic",

    # ── style (서식 - 비주얼 스타일) ──
    "style_body_bg": "style",
    "style_body_text": "style",
    "style_font_size": "style",
    "style_line_height": "style",
    "style_name_color": "style",
    "style_name_bold": "style",
    "style_separator": "style",
    "custom_separator_text": "style",
    "character_colors": "style",
    "custom_theme_presets": "style",

    # ── style - colors (요소별 색상 팔레트) ──
    "colors": "style",

    # ── font (폰트) ──
    "epub_body_font": "font",
    "epub_name_font": "font",
    "embed_body_font": "font",
    "embed_name_font": "font",
    "docx_body_font": "font",
    "docx_name_font": "font",
    "docx_embed_body": "font",
    "docx_embed_name": "font",
    "body_line_height": "font",
    "dialogue_line_height": "font",
    "narration_line_height": "font",
    "base_font_size": "font",

    # ── cover (표지) ──
    "include_cover": "cover",
    "title_on_cover": "cover",
    "author_on_cover": "cover",
    "cover_subtitle": "cover",
    "cover_bg": "cover",
    "cover_title_color": "cover",
    "cover_image": "cover",
    "include_toc": "cover",
    "toc_title": "cover",

    # ── decoration (장식) ──
    "divider_type": "decoration",
    "divider_text": "decoration",
    "divider_color": "decoration",
    "divider_image": "decoration",
    "divider_img_height": "decoration",
    "line_style": "decoration",
    "line_thickness": "decoration",
    "line_color": "decoration",
    "line_width": "decoration",
    "scene_marker": "decoration",
    "chapter_ornament": "decoration",
    "scene_separator": "decoration",
    "narration_prefix": "decoration",
    "narration_indent": "decoration",
    "header_style": "decoration",
    "header_size": "decoration",
    "header_color": "decoration",
    "header_bold": "decoration",
    "header_prefix": "decoration",
    "header_suffix": "decoration",
    "header_underline": "decoration",
    "header_box": "decoration",
    "header_box_color": "decoration",
    "quote_style": "decoration",
    "quote_bg": "decoration",
    "quote_border": "decoration",
    "dice_style": "decoration",
    "dice_icon": "decoration",
    "dice_color": "decoration",

    # ── content (콘텐츠 필터) ──
    "include_dice": "content",
    "include_effects": "content",
    "include_system": "content",
    "include_ooc": "content",
    "merge_dialogue": "content",
    "merge_separator": "content",
    "merge_max": "content",
    "empty_dialogue": "content",

    # ── scene (장면 분할) ──
    "split_mode": "scene",
    "scene_patterns": "scene",
    "entries_per_chapter": "scene",
    "min_scene_entries": "scene",
    "title_format": "scene",

    # ── parsing (파싱 규칙) ──
    "custom_separator_type": "parsing",
    "custom_name_position": "parsing",
    "custom_name_max": "parsing",
    "narration_no_name": "parsing",
    "scene_separator_pattern": "parsing",
    "dice_keywords": "parsing",
    "system_prefix": "parsing",

    # ── output (출력 레이아웃) ──
    "epub_page_format": "output",
    "page_format": "output",
    "custom_page_width": "output",
    "custom_page_height": "output",
    "margins": "output",

    # ── advanced (고급 옵션) ──
    "name_max_length": "advanced",
    "skip_channels": "advanced",
    "normalize_punct": "advanced",
    "session_gap": "advanced",
    "emote_style": "advanced",
    "include_whisper": "advanced",
    "images_enable": "advanced",
    "show_caption": "advanced",
    "image_align": "advanced",
    "image_max_width": "advanced",
    "image_max_resolution": "advanced",
    "image_jpeg_quality": "advanced",
    "image_convert_webp": "advanced",
    "campaign_enable": "advanced",
    "campaign_title": "advanced",
    "session_title_format": "advanced",
    "custom_css": "advanced",
}

# 미리보기 갱신이 필요한 그룹 목록
_PREVIEW_GROUPS: frozenset[str] = frozenset(
    {"style", "font", "decoration", "cover", "basic"}
)


class AppState(QObject):
    """중앙 반응형 상태 관리자.

    Pydantic 모델(AppSettings) 기반으로 모든 GUI 설정을 관리하며,
    값 변경 시 Signal을 방출하여 UI 컴포넌트가 자동 업데이트됩니다.

    Signals:
        changed(key, value)       — 개별 키가 변경되었을 때
        group_changed(group_name) — 그룹 내 하나 이상의 키가 변경되었을 때
        reset()                   — 전체 설정이 초기화되었을 때
    """

    # 개별 키 변경: (key: str, value: Any)
    changed = Signal(str, object)

    # 그룹 변경: (group_name: str) — 'style', 'font', 'cover' 등
    group_changed = Signal(str)

    # 전체 초기화 완료
    reset = Signal()

    def __init__(self, config_manager, parent: QObject | None = None):
        super().__init__(parent)

        self._config_manager = config_manager

        # 뮤텍스: batch_update 컨텍스트 매니저의 스레드 안전 보장
        self._mutex = QMutex()

        # 배치 모드 상태
        self._batch_mode: bool = False
        self._pending_groups: set[str] = set()
        self._pending_keys: list[tuple[str, Any]] = []

        # Pydantic 모델 + 플랫 dict 초기화
        self._model: AppSettings = AppSettings()
        self._flat: dict[str, Any] = {}

        # 저장 차단 플래그.
        # 앱 시작 시 페이지 __init__ 에서 위젯을 채우는 도중 changed 시그널이
        # save_settings → state.save() 로 이어져 아직 세팅 안 된 다른 위젯의
        # 기본값이 디스크로 내려가면 import 값이 지워진다.
        # MainWindow 가 모든 페이지 초기화 전에 True 로 잠그고, 끝난 뒤 해제한다.
        self._suspend_save: bool = False
        # set() 차단 플래그.
        # load_settings 중 위젯.setText/setCurrentText 가 textChanged 시그널을
        # 거쳐 save_settings() 를 트리거하면, 아직 세팅 안 된 다른 위젯의
        # 기본값이 state.set() 으로 AppState 에 유입되어 내부 메모리까지 오염된다.
        # load 작업 구간에서 _suspend_set=True 로 막아 단방향(AppState→UI)만 흐르게 한다.
        self._suspend_set: bool = False

        # ConfigManager에서 초기 설정 로드
        self.load()

    # ──────────────────────────────────────────
    # 읽기
    # ──────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """설정 값을 읽어옵니다.

        Args:
            key: 플랫 설정 키 (예: 'style_font_size')
            default: 키가 없을 때 반환할 기본값

        Returns:
            설정 값 또는 default
        """
        return self._flat.get(key, default)

    def get_all(self) -> dict[str, Any]:
        """전체 설정을 플랫 dict로 반환합니다.

        ConfigManager.save_gui_settings() 또는 엔진 빌드에 전달할 때 사용합니다.
        """
        return dict(self._flat)

    def get_model(self) -> AppSettings:
        """현재 Pydantic 모델 인스턴스를 반환합니다 (읽기 전용 권장)."""
        return self._model

    # ──────────────────────────────────────────
    # 쓰기
    # ──────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        """설정 값을 변경하고 Signal을 방출합니다.

        동일한 값을 다시 설정하면 Signal이 방출되지 않습니다 (불필요한 갱신 방지).

        Args:
            key: 플랫 설정 키
            value: 새로운 값
        """
        # load_settings 중에 위젯 시그널을 타고 들어오는 set 은 AppState 를
        # 오염시키므로 차단한다 (AppState→UI 단방향 보장).
        if self._suspend_set:
            return

        # 동일 값이면 무시 (얕은 비교)
        old = self._flat.get(key)
        if old == value:
            return

        self._flat[key] = value

        group = _KEY_GROUP_MAP.get(key, "unknown")

        locker = QMutexLocker(self._mutex)
        is_batch = self._batch_mode
        if is_batch:
            self._pending_groups.add(group)
            self._pending_keys.append((key, value))
        del locker  # 뮤텍스 해제

        if not is_batch:
            # 즉시 방출
            self.changed.emit(key, value)
            self.group_changed.emit(group)

    def update(self, data: dict[str, Any]) -> None:
        """여러 키를 한번에 설정합니다 (자동으로 batch_update 사용).

        Args:
            data: {key: value, ...} 형태의 딕셔너리
        """
        with self.batch_update():
            for key, value in data.items():
                self.set(key, value)

    # ──────────────────────────────────────────
    # 배치 업데이트
    # ──────────────────────────────────────────

    @contextmanager
    def batch_update(self) -> Iterator[None]:
        """일괄 업데이트 컨텍스트 매니저.

        블록 내에서 set()을 여러 번 호출하더라도
        group_changed Signal은 블록 종료 시 그룹당 한 번만 방출됩니다.
        changed Signal은 개별 키마다 블록 종료 시 일괄 방출됩니다.

        사용 예:
            with state.batch_update():
                state.set('style_font_size', 14)
                state.set('style_line_height', 1.6)
            # → group_changed('style') 1회만 방출
        """
        locker = QMutexLocker(self._mutex)
        self._batch_mode = True
        self._pending_groups = set()
        self._pending_keys = []
        del locker

        try:
            yield
        finally:
            locker = QMutexLocker(self._mutex)
            self._batch_mode = False
            pending_groups = set(self._pending_groups)
            pending_keys = list(self._pending_keys)
            self._pending_groups.clear()
            self._pending_keys.clear()
            del locker

            # 개별 changed Signal 방출
            for key, value in pending_keys:
                self.changed.emit(key, value)

            # 그룹 changed Signal 방출 (그룹당 1회)
            for group in pending_groups:
                self.group_changed.emit(group)

    # ──────────────────────────────────────────
    # 영속화 (ConfigManager 연동)
    # ──────────────────────────────────────────

    def save(self) -> None:
        """현재 상태를 ConfigManager를 통해 gui_settings.json에 저장합니다.

        ``_suspend_save`` 가 True 이면 저장을 건너뜁니다. 앱 시작 시 페이지
        초기화 중 발생하는 side-effect save 로 디스크의 값이 기본값으로
        덮여쓰이는 문제를 방지합니다.
        """
        if self._suspend_save:
            logger.debug("AppState 저장 보류 (suspend)")
            return
        self._sync_model_from_flat()
        self._config_manager.save_gui_settings(self._flat)
        logger.debug("AppState 저장 완료 (%d 키)", len(self._flat))

    def load(self) -> None:
        """ConfigManager에서 설정을 다시 읽어옵니다.

        기존 상태를 완전히 덮어씁니다.
        """
        raw: dict = self._config_manager.get_gui_settings()

        # Pydantic 모델로 검증
        self._model = unflatten_settings(raw)

        # 모델에서 플랫 dict 재생성 (검증된 값 사용)
        self._flat = flatten_settings(self._model)

        # 원본에는 있지만 모델에 없는 키도 유지 (하위 호환)
        for key, value in raw.items():
            if key not in self._flat:
                self._flat[key] = value

        logger.debug("AppState 로드 완료 (%d 키)", len(self._flat))

    def reset_to_defaults(self) -> None:
        """모든 설정을 기본값으로 초기화합니다.

        reset Signal이 방출됩니다.
        """
        self._model = AppSettings()
        self._flat = flatten_settings(self._model)
        self.reset.emit()
        logger.info("AppState 기본값으로 초기화 완료")

    # ──────────────────────────────────────────
    # 미리보기 설정 생성
    # ──────────────────────────────────────────

    def get_preview_settings(self) -> dict[str, Any]:
        """DocumentPreview가 필요로 하는 설정 dict를 반환합니다.

        MainWindow._collect_preview_settings()를 대체합니다.
        DocumentPreview._render_document()가 기대하는 키 이름에 맞춰
        변환하여 반환합니다.

        Returns:
            dict: DocumentPreview.update_settings(**settings) 에 전달할 수 있는 dict
        """
        f = self._flat

        # 색상 팔레트
        colors = f.get("colors", {})
        if not isinstance(colors, dict):
            colors = {}

        return {
            # 텍스트/배경 색상
            "dialogue_color": f.get("style_body_text", colors.get("text_color", "#1a1a1a")),
            "narration_color": colors.get("system_color", "#555555"),

            # 폰트
            "font_family": self._extract_font_family(
                f.get("epub_body_font", "'Nanum Myeongjo', 'Batang', serif")
            ),
            "font_size": f.get("style_font_size", 14),
            "line_height": f.get("style_line_height", 1.6),

            # 장식/마커
            "scene_marker": f.get("scene_marker", "■"),
            "narration_prefix": f.get("narration_prefix", "＿"),

            # 나레이터 목록
            "narrators": f.get("narrators", "GM, KP, DM"),

            # 배경색 (DocumentPreview 스타일에 사용 가능)
            "body_bg": f.get("style_body_bg", "#ffffff"),

            # 이름 스타일
            "name_color": f.get("style_name_color", colors.get("name_color", "#2d2d2d")),
            "name_bold": f.get("style_name_bold", True),

            # 대사 구분자
            "separator": f.get("style_separator", "「 」 (꺾쇠)"),
        }

    @staticmethod
    def _extract_font_family(font_str: str) -> str:
        """CSS 폰트 스택에서 첫 번째 폰트 이름을 추출합니다.

        "'Nanum Myeongjo', 'Batang', serif" → "Nanum Myeongjo"
        """
        if not font_str:
            return "Noto Serif KR"
        first = font_str.split(",")[0].strip()
        # 따옴표 제거
        return first.strip("'\"")

    # ──────────────────────────────────────────
    # 그룹 조회 유틸
    # ──────────────────────────────────────────

    @staticmethod
    def get_group_for_key(key: str) -> str:
        """키가 속한 그룹 이름을 반환합니다."""
        return _KEY_GROUP_MAP.get(key, "unknown")

    @staticmethod
    def is_preview_group(group: str) -> bool:
        """해당 그룹의 변경이 미리보기 갱신을 필요로 하는지 반환합니다."""
        return group in _PREVIEW_GROUPS

    def get_keys_for_group(self, group: str) -> dict[str, Any]:
        """특정 그룹에 속하는 키-값 쌍을 반환합니다.

        Args:
            group: 그룹 이름 (예: 'style', 'font')

        Returns:
            해당 그룹의 {key: value} dict
        """
        return {
            key: self._flat.get(key)
            for key, grp in _KEY_GROUP_MAP.items()
            if grp == group and key in self._flat
        }

    # ──────────────────────────────────────────
    # 내부 헬퍼
    # ──────────────────────────────────────────

    def _sync_model_from_flat(self) -> None:
        """플랫 dict에서 Pydantic 모델을 재구성합니다 (저장 전 호출)."""
        try:
            self._model = unflatten_settings(self._flat)
        except Exception as e:
            logger.warning("Pydantic 모델 동기화 실패, 플랫 dict만 저장합니다: %s", e)

    def __repr__(self) -> str:
        return f"<AppState keys={len(self._flat)} groups={len(set(_KEY_GROUP_MAP.values()))}>"
