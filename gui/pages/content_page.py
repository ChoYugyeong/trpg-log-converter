"""
TRPG Log Converter Pro - 콘텐츠 페이지
콘텐츠 포함/제외 및 포맷 설정
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit
)
from PySide6.QtCore import Qt

from .base_page import BasePage
from ..components import ContentCard, TagInput


class ContentPage(BasePage):
    """콘텐츠 페이지 - 콘텐츠 필터 및 포맷 설정"""

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._setup_page()
        self.load_settings()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("콘텐츠 설정", "변환에 포함할 콘텐츠 유형을 설정합니다")

        # 콘텐츠 포함 설정 카드
        include_card = ContentCard("포함 설정")

        self.include_dice = include_card.add_checkbox(
            "주사위 굴림 결과 포함",
            "include_dice",
            checked=self.settings.get('include_dice', True),
            help_text="1d20 = 15 같은 주사위 결과를 변환에 포함합니다."
        )

        self.include_effects = include_card.add_checkbox(
            "연출 효과 포함 (SE, BGM 등)",
            "include_effects",
            checked=self.settings.get('include_effects', True),
            help_text="[SE:효과음] [BGM:배경음악] 같은 연출 태그를 포함합니다."
        )

        self.include_system = include_card.add_checkbox(
            "시스템 메시지 포함",
            "include_system",
            checked=self.settings.get('include_system', True),
            help_text="입장/퇴장, 알림 등 시스템 메시지를 포함합니다."
        )

        self.include_ooc = include_card.add_checkbox(
            "OOC(Out of Character) 포함",
            "include_ooc",
            checked=self.settings.get('include_ooc', False),
            help_text="(( )) 또는 OOC: 로 시작하는 비RP 대화를 포함합니다."
        )

        self.content_layout.addWidget(include_card)

        # 나레이션 설정 카드
        narration_card = ContentCard("나레이션 설정", "나레이터로 인식할 사용자 설정")

        self.narrators_entry = narration_card.add_text_field(
            "나레이터 목록", "narrators",
            placeholder="GM, KP, DM, Keeper (쉼표로 구분)",
            default=self.settings.get('narrators', 'GM, KP, DM, Keeper, 나레이터, 진행자'),
            help_text="쉼표로 구분. 이 이름들의 대사는 나레이션으로 처리됩니다."
        )

        self.narration_prefix = narration_card.add_text_field(
            "나레이션 접두사", "narration_prefix",
            placeholder="＿",
            default=self.settings.get('narration_prefix', '＿'),
            help_text="나레이션 시작 부분에 붙는 기호입니다."
        )

        self.narration_indent = narration_card.add_text_field(
            "나레이션 들여쓰기 (em)", "narration_indent",
            placeholder="1.5",
            default=self.settings.get('narration_indent', '1.5'),
            help_text="나레이션의 들여쓰기 정도(em 단위). 1.5~2.0 권장."
        )

        self.content_layout.addWidget(narration_card)

        # 대화 병합 설정 카드
        merge_card = ContentCard("대화 병합", "연속된 대사를 하나로 병합")

        self.merge_dialogue = merge_card.add_checkbox(
            "연속 대화 병합",
            "merge_dialogue",
            checked=self.settings.get('merge_dialogue', False),
            help_text="같은 캐릭터의 연속 대사를 하나로 합칩니다."
        )

        self.merge_separator_combo = merge_card.add_dropdown(
            "병합 구분자", "merge_separator",
            options=["newline", "space", "dash"],
            default=self.settings.get('merge_separator', 'newline'),
            help_text="병합된 대사들 사이에 들어갈 구분자입니다."
        )

        self.merge_max = merge_card.add_text_field(
            "최대 병합 수", "merge_max",
            placeholder="5",
            default=self.settings.get('merge_max', '5'),
            help_text="한 번에 병합할 수 있는 최대 대사 수입니다."
        )

        self.empty_dialogue = merge_card.add_text_field(
            "빈 대사 대체", "empty_dialogue",
            placeholder="……",
            default=self.settings.get('empty_dialogue', '……'),
            help_text="내용이 없는 대사를 대체할 텍스트입니다."
        )

        self.content_layout.addWidget(merge_card)

        # 챕터 구분 설정 카드
        chapter_card = ContentCard("챕터 구분", "EPUB 챕터 분할 방식")

        self.split_mode_group = chapter_card.add_radio_group(
            [("장면 기반", "scene"), ("항목 수 기반", "count"), ("단일 챕터", "none")],
            "split_mode",
            default=self.settings.get('split_mode', 'scene')
        )

        self.scene_patterns = chapter_card.add_text_field(
            "장면 패턴", "scene_patterns",
            placeholder="■, 씬, Scene, 장면",
            default=self.settings.get('scene_patterns', '■, 씬, Scene, 장면, Act'),
            help_text="이 텍스트로 시작하는 메시지에서 새 챕터가 시작됩니다."
        )

        self.entries_per_chapter = chapter_card.add_text_field(
            "챕터당 항목 수", "entries_per_chapter",
            placeholder="300",
            default=self.settings.get('entries_per_chapter', '300'),
            help_text="'항목 수 기반' 모드에서 사용. 이 수만큼 항목이 쌓이면 새 챕터."
        )

        self.min_scene_entries = chapter_card.add_text_field(
            "최소 장면 항목", "min_scene_entries",
            placeholder="10",
            default=self.settings.get('min_scene_entries', '10'),
            help_text="이보다 적은 항목의 장면은 이전 장면에 병합됩니다."
        )

        self.title_format = chapter_card.add_text_field(
            "챕터 제목 형식", "title_format",
            placeholder="장면 {n}",
            default=self.settings.get('title_format', '장면 {n}'),
            help_text="{n}은 장면 번호로 대체됩니다. 예: '제 {n} 장', 'Scene {n}'"
        )

        self.content_layout.addWidget(chapter_card)

        # 장식 요소 카드
        decoration_card = ContentCard("장식 요소")

        self.scene_marker = decoration_card.add_text_field(
            "장면 마커", "scene_marker",
            placeholder="■",
            default=self.settings.get('scene_marker', '■'),
            help_text="장면 제목 앞에 붙는 마커입니다."
        )

        self.chapter_ornament = decoration_card.add_text_field(
            "챕터 장식", "chapter_ornament",
            placeholder="─────  ✦  ─────",
            default=self.settings.get('chapter_ornament', '─────  ✦  ─────'),
            help_text="챕터 시작 부분의 장식 문양입니다."
        )

        self.scene_separator = decoration_card.add_text_field(
            "장면 구분선", "scene_separator",
            placeholder="＊　＊　＊",
            default=self.settings.get('scene_separator', '＊　＊　＊'),
            help_text="장면과 장면 사이의 구분선입니다."
        )

        self.content_layout.addWidget(decoration_card)

        # 이미지 삽입 설정 카드
        image_card = ContentCard("이미지 삽입", "로그에 포함된 이미지 처리 설정")

        self.images_enable = image_card.add_checkbox(
            "이미지 삽입 활성화",
            "images_enable",
            checked=self.settings.get('images_enable', True),
            help_text="로그에 포함된 이미지를 EPUB/DOCX에 삽입합니다."
        )

        self.show_caption = image_card.add_checkbox(
            "캡션 표시",
            "show_caption",
            checked=self.settings.get('show_caption', True),
            help_text="이미지 아래에 캡션(설명)을 표시합니다."
        )

        self.image_align = image_card.add_dropdown(
            "이미지 정렬", "image_align",
            options=["center", "left", "right"],
            default=self.settings.get('image_align', 'center'),
            help_text="이미지의 가로 정렬 위치입니다."
        )

        self.image_max_width = image_card.add_text_field(
            "최대 너비 (%)", "image_max_width",
            placeholder="100",
            default=self.settings.get('image_max_width', '100'),
            help_text="이미지의 최대 너비를 페이지 너비의 백분율로 지정합니다."
        )

        self.content_layout.addWidget(image_card)

        # 설정 변경 시 저장 연결
        for checkbox in [self.include_dice, self.include_effects,
                        self.include_system, self.include_ooc, self.merge_dialogue,
                        self.images_enable, self.show_caption]:
            checkbox.stateChanged.connect(self.save_settings)

        self.add_stretch()

    def save_settings(self):
        """설정 저장"""
        self.settings['include_dice'] = self.include_dice.isChecked()
        self.settings['include_effects'] = self.include_effects.isChecked()
        self.settings['include_system'] = self.include_system.isChecked()
        self.settings['include_ooc'] = self.include_ooc.isChecked()

        self.settings['narrators'] = self.narrators_entry.text()
        self.settings['narration_prefix'] = self.narration_prefix.text()
        self.settings['narration_indent'] = self.narration_indent.text()

        self.settings['merge_dialogue'] = self.merge_dialogue.isChecked()
        self.settings['merge_separator'] = self.merge_separator_combo.currentText()
        self.settings['merge_max'] = self.merge_max.text()
        self.settings['empty_dialogue'] = self.empty_dialogue.text()

        # 라디오 그룹
        checked = self.split_mode_group.checkedButton()
        if checked:
            self.settings['split_mode'] = checked.property('value')

        self.settings['scene_patterns'] = self.scene_patterns.text()
        self.settings['entries_per_chapter'] = self.entries_per_chapter.text()
        self.settings['min_scene_entries'] = self.min_scene_entries.text()
        self.settings['title_format'] = self.title_format.text()

        self.settings['scene_marker'] = self.scene_marker.text()
        self.settings['chapter_ornament'] = self.chapter_ornament.text()
        self.settings['scene_separator'] = self.scene_separator.text()

        # 이미지 설정
        self.settings['images_enable'] = self.images_enable.isChecked()
        self.settings['show_caption'] = self.show_caption.isChecked()
        self.settings['image_align'] = self.image_align.currentText()
        self.settings['image_max_width'] = self.image_max_width.text()

        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()

        self.include_dice.setChecked(self.settings.get('include_dice', True))
        self.include_effects.setChecked(self.settings.get('include_effects', True))
        self.include_system.setChecked(self.settings.get('include_system', True))
        self.include_ooc.setChecked(self.settings.get('include_ooc', False))

        self.narrators_entry.setText(self.settings.get('narrators', 'GM, KP, DM, Keeper, 나레이터, 진행자'))
        self.narration_prefix.setText(self.settings.get('narration_prefix', '＿'))
        self.narration_indent.setText(self.settings.get('narration_indent', '1.5'))

        self.merge_dialogue.setChecked(self.settings.get('merge_dialogue', False))
        self.merge_separator_combo.setCurrentText(self.settings.get('merge_separator', 'newline'))
        self.merge_max.setText(self.settings.get('merge_max', '5'))
        self.empty_dialogue.setText(self.settings.get('empty_dialogue', '……'))

        self.scene_patterns.setText(self.settings.get('scene_patterns', '■, 씬, Scene, 장면, Act'))
        self.entries_per_chapter.setText(self.settings.get('entries_per_chapter', '300'))
        self.min_scene_entries.setText(self.settings.get('min_scene_entries', '10'))
        self.title_format.setText(self.settings.get('title_format', '장면 {n}'))

        self.scene_marker.setText(self.settings.get('scene_marker', '■'))
        self.chapter_ornament.setText(self.settings.get('chapter_ornament', '─────  ✦  ─────'))
        self.scene_separator.setText(self.settings.get('scene_separator', '＊　＊　＊'))

        # 이미지 설정
        self.images_enable.setChecked(self.settings.get('images_enable', True))
        self.show_caption.setChecked(self.settings.get('show_caption', True))
        self.image_align.setCurrentText(self.settings.get('image_align', 'center'))
        self.image_max_width.setText(self.settings.get('image_max_width', '100'))
