"""
TRPG Log Converter Pro - 고급 페이지
고급 설정 및 커스텀 CSS
"""

import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from qfluentwidgets import (
    BodyLabel, PushButton, InfoBar, InfoBarPosition, MessageBox
)

from .base_page import BasePage
from ..components import ContentCard, HelpButton


class AdvancedPage(BasePage):
    """고급 페이지 - 고급 설정 및 커스텀 CSS"""

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._setup_page()
        self.load_settings()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("고급 설정", "상세 변환 옵션 및 커스텀 스타일")

        # 파싱 설정 카드
        parsing_card = ContentCard("파싱 설정")

        self.name_max_length = parsing_card.add_text_field(
            "이름 최대 길이", "name_max_length",
            placeholder="50",
            default=self.settings.get('name_max_length', '50'),
            help_text="캐릭터 이름의 최대 문자 수입니다. 이보다 긴 이름은 잘립니다."
        )

        self.skip_channels = parsing_card.add_text_field(
            "제외할 채널", "skip_channels",
            placeholder="[main], [잡담], [ooc]",
            default=self.settings.get('skip_channels', '[main], [잡담], [ooc]'),
            help_text="변환에서 제외할 채널 이름을 쉼표로 구분하여 입력합니다."
        )

        self.normalize_punct = parsing_card.add_checkbox(
            "구두점 정규화",
            "normalize_punct",
            checked=self.settings.get('normalize_punct', True),
            help_text="전각/반각 구두점을 일관되게 변환합니다."
        )

        self.content_layout.addWidget(parsing_card)

        # Roll20 특화 설정 카드
        roll20_card = ContentCard("Roll20 설정", "Roll20 로그 전용 옵션")

        self.session_gap = roll20_card.add_text_field(
            "세션 간격 (분)", "session_gap",
            placeholder="60",
            default=self.settings.get('session_gap', '60'),
            help_text="메시지 간격이 이 시간을 초과하면 새 세션으로 구분합니다."
        )

        self.emote_style = roll20_card.add_dropdown(
            "이모트 스타일", "emote_style",
            options=["italic", "normal", "bold"],
            default=self.settings.get('emote_style', 'italic'),
            help_text="이모트(/em, /me) 텍스트의 스타일을 지정합니다."
        )

        self.include_whisper = roll20_card.add_checkbox(
            "귓속말 포함",
            "include_whisper",
            checked=self.settings.get('include_whisper', False),
            help_text="Roll20 귓속말(whisper) 메시지를 변환에 포함합니다."
        )

        self.content_layout.addWidget(roll20_card)

        # 이미지 설정 카드
        image_card = ContentCard("이미지 설정")

        self.images_enable = image_card.add_checkbox(
            "이미지 포함",
            "images_enable",
            checked=self.settings.get('images_enable', True),
            help_text="로그에 포함된 이미지를 EPUB/DOCX에 삽입합니다."
        )

        self.show_caption = image_card.add_checkbox(
            "이미지 캡션 표시",
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

        self.image_max_resolution = image_card.add_text_field(
            "최대 해상도 (px)", "image_max_resolution",
            placeholder="1600",
            default=self.settings.get('image_max_resolution', '1600'),
            help_text="이미지의 긴 변이 이 값을 초과하면 자동으로 축소합니다. 0이면 리사이즈하지 않습니다."
        )

        self.image_jpeg_quality = image_card.add_dropdown(
            "JPEG 품질", "image_jpeg_quality",
            options=["95 (최고)", "85 (권장)", "75 (보통)", "60 (낮음)"],
            default=self.settings.get('image_jpeg_quality', '85 (권장)'),
            help_text="JPEG/WEBP 이미지의 압축 품질입니다. 낮을수록 파일이 작아집니다."
        )

        self.image_convert_webp = image_card.add_checkbox(
            "WebP → JPEG 변환",
            "image_convert_webp",
            checked=self.settings.get('image_convert_webp', True),
            help_text="WebP 이미지를 JPEG로 변환합니다. EPUB 리더 호환성이 향상됩니다."
        )

        self.content_layout.addWidget(image_card)

        # DOCX 레이아웃 카드
        layout_card = ContentCard("DOCX 레이아웃", "DOCX 여백 설정 (인치)")

        margins = self.settings.get('margins', {})

        margin_row = QHBoxLayout()
        margin_row.setSpacing(16)

        for key, label in [('top', '상'), ('bottom', '하'), ('left', '좌'), ('right', '우')]:
            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)

            lbl = BodyLabel(label)
            item_layout.addWidget(lbl)

            entry = layout_card.add_text_field(
                "", f"margin_{key}",
                placeholder="1.0",
                default=margins.get(key, '1.0')
            )
            entry.setMaximumWidth(60)
            setattr(self, f"margin_{key}", entry)
            item_layout.addWidget(entry)

            margin_row.addWidget(item)

        margin_row.addStretch()
        layout_card.add_layout(margin_row)

        self.content_layout.addWidget(layout_card)

        # 캠페인 모드 카드
        campaign_card = ContentCard("캠페인 모드", "여러 세션을 하나의 EPUB으로 병합")

        self.campaign_enable = campaign_card.add_checkbox(
            "캠페인 모드 활성화",
            "campaign_enable",
            checked=self.settings.get('campaign_enable', False),
            help_text="여러 로그 파일을 하나의 EPUB으로 병합합니다."
        )

        self.campaign_title = campaign_card.add_text_field(
            "캠페인 제목", "campaign_title",
            placeholder="캠페인 리플레이",
            default=self.settings.get('campaign_title', '캠페인 리플레이'),
            help_text="병합된 EPUB의 전체 제목입니다."
        )

        self.session_title_format = campaign_card.add_text_field(
            "세션 제목 형식", "session_title_format",
            placeholder="Session {n}: {filename}",
            default=self.settings.get('session_title_format', 'Session {n}: {filename}'),
            help_text="{n}은 세션 번호, {filename}은 파일명으로 대체됩니다."
        )

        self.content_layout.addWidget(campaign_card)

        # 커스텀 CSS 카드
        css_card = ContentCard("커스텀 CSS", "EPUB에 추가할 CSS 스타일")

        self.css_editor = QPlainTextEdit()
        self.css_editor.setPlaceholderText("/* 커스텀 CSS를 입력하세요 */\n\n.dialogue {\n    color: #333;\n}")
        self.css_editor.setMinimumHeight(200)
        self.css_editor.setFont(QFont("Consolas" if sys.platform == "win32" else "Monaco", 12))
        self.css_editor.setObjectName("CodeEditor")
        self.css_editor.setPlainText(self.settings.get('custom_css', ''))

        css_card.add_widget(self.css_editor)

        # CSS 버튼
        css_buttons = QHBoxLayout()
        css_buttons.setSpacing(8)

        apply_btn = PushButton("적용")
        apply_btn.clicked.connect(self._apply_css)
        css_buttons.addWidget(apply_btn)

        reset_btn = PushButton("초기화")
        reset_btn.clicked.connect(self._reset_css)
        css_buttons.addWidget(reset_btn)

        css_buttons.addStretch()
        css_card.add_layout(css_buttons)

        self.content_layout.addWidget(css_card)

        # 설정 백업/복원 카드
        backup_card = ContentCard("설정 백업/복원", "설정을 파일로 내보내거나 가져오기")

        backup_buttons = QHBoxLayout()
        backup_buttons.setSpacing(8)

        export_btn = PushButton("설정 내보내기 (Ctrl+E)")
        export_btn.clicked.connect(self._export_settings)
        backup_buttons.addWidget(export_btn)

        import_btn = PushButton("설정 가져오기 (Ctrl+I)")
        import_btn.clicked.connect(self._import_settings)
        backup_buttons.addWidget(import_btn)

        backup_buttons.addStretch()
        backup_card.add_layout(backup_buttons)

        # 단축키 안내
        mod = "⌘" if sys.platform == "darwin" else "Ctrl+"
        shortcut_label = BodyLabel(
            f"단축키: {mod}O 파일열기, {mod}R 변환시작, {mod}P 미리보기, {mod}E 설정내보내기, {mod}I 설정가져오기, {mod}L 로그보기, {mod}1~9 페이지전환"
        )
        shortcut_label.setWordWrap(True)
        shortcut_label.setStyleSheet("color: palette(mid); font-size: 11px; margin-top: 8px;")
        backup_card.add_widget(shortcut_label)

        self.content_layout.addWidget(backup_card)

        # 설정 초기화 버튼
        reset_all_btn = PushButton("모든 설정 초기화")
        reset_all_btn.setObjectName("danger")
        reset_all_btn.clicked.connect(self._reset_all_settings)
        self.content_layout.addWidget(reset_all_btn)

        self.add_stretch()

    def _apply_css(self):
        """커스텀 CSS 적용"""
        self.save_settings()
        InfoBar.success(
            title="적용됨",
            content="커스텀 CSS가 저장되었습니다.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _reset_css(self):
        """CSS 초기화"""
        self.css_editor.clear()
        self.save_settings()

    def _export_settings(self):
        """설정 내보내기 (MainWindow 호출)"""
        main_window = self.window()
        if hasattr(main_window, 'export_settings'):
            main_window.export_settings()

    def _import_settings(self):
        """설정 가져오기 (MainWindow 호출)"""
        main_window = self.window()
        if hasattr(main_window, 'import_settings'):
            main_window.import_settings()

    def _reset_all_settings(self):
        """모든 설정 초기화"""
        w = MessageBox(
            "설정 초기화",
            "모든 설정을 기본값으로 초기화하시겠습니까?",
            self
        )
        w.yesButton.setText("초기화")
        w.cancelButton.setText("취소")

        if w.exec():
            default_settings = self.config_manager.get_default_gui_settings()
            self.config_manager.save_gui_settings(default_settings)
            self.load_settings()
            InfoBar.success(
                title="초기화 완료",
                content="모든 설정이 기본값으로 초기화되었습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )

    def save_settings(self):
        """설정 저장"""
        self.settings['name_max_length'] = self.name_max_length.text()
        self.settings['skip_channels'] = self.skip_channels.text()
        self.settings['normalize_punct'] = self.normalize_punct.isChecked()

        self.settings['session_gap'] = self.session_gap.text()
        self.settings['emote_style'] = self.emote_style.currentText()
        self.settings['include_whisper'] = self.include_whisper.isChecked()

        self.settings['images_enable'] = self.images_enable.isChecked()
        self.settings['show_caption'] = self.show_caption.isChecked()
        self.settings['image_align'] = self.image_align.currentText()
        self.settings['image_max_width'] = self.image_max_width.text()
        self.settings['image_max_resolution'] = self.image_max_resolution.text()
        self.settings['image_jpeg_quality'] = self.image_jpeg_quality.currentText()
        self.settings['image_convert_webp'] = self.image_convert_webp.isChecked()

        self.settings['margins'] = {
            'top': self.margin_top.text(),
            'bottom': self.margin_bottom.text(),
            'left': self.margin_left.text(),
            'right': self.margin_right.text(),
        }

        self.settings['campaign_enable'] = self.campaign_enable.isChecked()
        self.settings['campaign_title'] = self.campaign_title.text()
        self.settings['session_title_format'] = self.session_title_format.text()

        self.settings['custom_css'] = self.css_editor.toPlainText()

        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()

        self.name_max_length.setText(self.settings.get('name_max_length', '50'))
        self.skip_channels.setText(self.settings.get('skip_channels', '[main], [잡담], [ooc]'))
        self.normalize_punct.setChecked(self.settings.get('normalize_punct', True))

        self.session_gap.setText(self.settings.get('session_gap', '60'))
        self.emote_style.setCurrentText(self.settings.get('emote_style', 'italic'))
        self.include_whisper.setChecked(self.settings.get('include_whisper', False))

        self.images_enable.setChecked(self.settings.get('images_enable', True))
        self.show_caption.setChecked(self.settings.get('show_caption', True))
        self.image_align.setCurrentText(self.settings.get('image_align', 'center'))
        self.image_max_width.setText(self.settings.get('image_max_width', '100'))
        self.image_max_resolution.setText(self.settings.get('image_max_resolution', '1600'))
        self.image_jpeg_quality.setCurrentText(self.settings.get('image_jpeg_quality', '85 (권장)'))
        self.image_convert_webp.setChecked(self.settings.get('image_convert_webp', True))

        margins = self.settings.get('margins', {})
        self.margin_top.setText(margins.get('top', '1.0'))
        self.margin_bottom.setText(margins.get('bottom', '1.0'))
        self.margin_left.setText(margins.get('left', '1.0'))
        self.margin_right.setText(margins.get('right', '1.0'))

        self.campaign_enable.setChecked(self.settings.get('campaign_enable', False))
        self.campaign_title.setText(self.settings.get('campaign_title', '캠페인 리플레이'))
        self.session_title_format.setText(self.settings.get('session_title_format', 'Session {n}: {filename}'))

        self.css_editor.setPlainText(self.settings.get('custom_css', ''))
