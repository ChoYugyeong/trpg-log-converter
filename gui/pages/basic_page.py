"""
TRPG Log Converter Pro - 기본 페이지
GM 이름, 언어, 장면 분할 설정
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt

from .base_page import BasePage
from ..components import ContentCard


class BasicPage(BasePage):
    """기본 페이지 - GM 이름, 언어, 장면 분할 설정"""

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._setup_page()
        self.load_settings()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("기본 설정", "GM 이름, 언어, 장면 분할 옵션")

        # GM / 나레이터 이름 카드
        gm_card = ContentCard(
            "GM / 나레이터 이름",
            "이 이름들의 대사는 나레이션으로 처리됩니다"
        )

        self.narrators = gm_card.add_text_field(
            "이름 목록", "narrators",
            placeholder="GM, KP, DM, Keeper, 나레이터, 진행자",
            default=self.settings.get('narrators', 'GM, KP, DM, Keeper, 나레이터, 진행자'),
            help_text="쉼표로 구분하여 입력"
        )

        self.content_layout.addWidget(gm_card)

        # 메타데이터 카드
        meta_card = ContentCard("메타데이터")

        self.language = meta_card.add_dropdown(
            "언어", "language",
            options=["ko", "en", "ja"],
            default=self.settings.get('language', 'ko'),
            help_text="EPUB 메타데이터 언어 코드"
        )

        self.content_layout.addWidget(meta_card)

        # 장면 분할 카드
        scene_card = ContentCard(
            "장면 분할",
            "로그를 여러 챕터로 나누는 방식"
        )

        self.split_mode = scene_card.add_dropdown(
            "분할 모드", "split_mode",
            options=["scene", "count", "none"],
            default=self.settings.get('split_mode', 'scene'),
            help_text="scene: 장면 패턴으로 분할, count: 항목 수로 분할, none: 분할 안함"
        )

        self.scene_patterns = scene_card.add_text_field(
            "장면 패턴", "scene_patterns",
            placeholder="■, 씬, Scene, 장면, Act",
            default=self.settings.get('scene_patterns', '■, 씬, Scene, 장면, Act'),
            help_text="이 텍스트로 시작하는 메시지에서 챕터 분할"
        )

        self.entries_per_chapter = scene_card.add_text_field(
            "챕터당 항목 수", "entries_per_chapter",
            placeholder="300",
            default=self.settings.get('entries_per_chapter', '300'),
            help_text="count 모드에서 사용"
        )
        self.entries_per_chapter.setMaximumWidth(100)

        self.min_scene_entries = scene_card.add_text_field(
            "최소 항목 수", "min_scene_entries",
            placeholder="10",
            default=self.settings.get('min_scene_entries', '10'),
            help_text="이보다 적은 항목의 장면은 이전 장면에 병합"
        )
        self.min_scene_entries.setMaximumWidth(100)

        self.title_format = scene_card.add_text_field(
            "챕터 제목 형식", "title_format",
            placeholder="장면 {n}",
            default=self.settings.get('title_format', '장면 {n}'),
            help_text="{n}은 장면 번호로 대체됨"
        )

        self.content_layout.addWidget(scene_card)

        self.add_stretch()

    def save_settings(self):
        """설정 저장"""
        self.settings['narrators'] = self.narrators.text()
        self.settings['language'] = self.language.currentText()
        self.settings['split_mode'] = self.split_mode.currentText()
        self.settings['scene_patterns'] = self.scene_patterns.text()
        self.settings['entries_per_chapter'] = self.entries_per_chapter.text()
        self.settings['min_scene_entries'] = self.min_scene_entries.text()
        self.settings['title_format'] = self.title_format.text()

        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()

        self.narrators.setText(self.settings.get('narrators', 'GM, KP, DM, Keeper, 나레이터, 진행자'))
        self.language.setCurrentText(self.settings.get('language', 'ko'))
        self.split_mode.setCurrentText(self.settings.get('split_mode', 'scene'))
        self.scene_patterns.setText(self.settings.get('scene_patterns', '■, 씬, Scene, 장면, Act'))
        self.entries_per_chapter.setText(self.settings.get('entries_per_chapter', '300'))
        self.min_scene_entries.setText(self.settings.get('min_scene_entries', '10'))
        self.title_format.setText(self.settings.get('title_format', '장면 {n}'))
