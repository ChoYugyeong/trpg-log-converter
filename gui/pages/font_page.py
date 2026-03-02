"""
TRPG Log Converter Pro - 폰트 페이지
EPUB/DOCX 폰트 설정
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from pathlib import Path

from qfluentwidgets import (
    BodyLabel, LineEdit, PushButton, ComboBox
)

from .base_page import BasePage
from ..components import ContentCard


class FontPage(BasePage):
    """폰트 페이지 - 폰트 설정"""

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._system_fonts = self._get_system_fonts()
        self._setup_page()
        self.load_settings()

    def _get_system_fonts(self) -> list:
        """시스템에 설치된 폰트 목록 가져오기"""
        fonts = QFontDatabase.families()
        # 한글 폰트를 우선으로 정렬
        korean_fonts = []
        other_fonts = []
        for font in fonts:
            # 한글이 포함된 폰트명 또는 주요 한글 폰트
            if any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in font) or \
               any(kw in font.lower() for kw in ['nanum', 'malgun', 'batang', 'gulim', 'dotum', 'gungsuh', 'pretendard', 'noto sans kr', 'noto serif kr']):
                korean_fonts.append(font)
            else:
                other_fonts.append(font)
        korean_fonts.sort()
        other_fonts.sort()
        return korean_fonts + other_fonts

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("폰트 설정", "EPUB/DOCX 출력물의 폰트를 설정합니다")

        # EPUB 폰트 카드
        epub_card = ContentCard("EPUB 폰트", "웹 폰트 또는 임베드 폰트 사용")

        # EPUB 본문 폰트 드롭다운
        self.epub_body_combo = ComboBox()
        self.epub_body_combo.addItems(self._system_fonts)
        self.epub_body_combo.setMinimumWidth(220)
        self.epub_body_combo.setCurrentText(self.settings.get('epub_body_font', '나눔명조'))
        self.epub_body_combo.currentTextChanged.connect(self._on_font_changed)
        epub_card.add_field("본문 폰트", self.epub_body_combo, help_text="EPUB 본문에 사용할 폰트를 선택하세요.")

        # EPUB 이름 폰트 드롭다운
        self.epub_name_combo = ComboBox()
        self.epub_name_combo.addItems(self._system_fonts)
        self.epub_name_combo.setMinimumWidth(220)
        self.epub_name_combo.setCurrentText(self.settings.get('epub_name_font', 'Pretendard'))
        self.epub_name_combo.currentTextChanged.connect(self._on_font_changed)
        epub_card.add_field("이름 폰트", self.epub_name_combo, help_text="캐릭터 이름에 사용할 폰트. 산세리프 계열 권장.")

        epub_card.add_spacing(8)

        # 폰트 임베드 섹션
        embed_label = BodyLabel("폰트 파일 임베드 (선택사항)")
        embed_label.setStyleSheet("font-weight: 600;")
        epub_card.add_widget(embed_label)

        # 본문 폰트 파일
        body_embed_row = QHBoxLayout()
        body_embed_row.setSpacing(8)

        self.embed_body_entry = LineEdit()
        self.embed_body_entry.setPlaceholderText("본문 폰트 파일 (.ttf, .otf)")
        self.embed_body_entry.setText(self.settings.get('embed_body_font', ''))
        body_embed_row.addWidget(self.embed_body_entry, 1)

        body_browse = PushButton("찾기")
        body_browse.clicked.connect(lambda: self._browse_font('body'))
        body_embed_row.addWidget(body_browse)

        epub_card.add_field("본문 파일", QWidget())
        epub_card.add_layout(body_embed_row)

        # 이름 폰트 파일
        name_embed_row = QHBoxLayout()
        name_embed_row.setSpacing(8)

        self.embed_name_entry = LineEdit()
        self.embed_name_entry.setPlaceholderText("이름 폰트 파일 (.ttf, .otf)")
        self.embed_name_entry.setText(self.settings.get('embed_name_font', ''))
        name_embed_row.addWidget(self.embed_name_entry, 1)

        name_browse = PushButton("찾기")
        name_browse.clicked.connect(lambda: self._browse_font('name'))
        name_embed_row.addWidget(name_browse)

        epub_card.add_field("이름 파일", QWidget())
        epub_card.add_layout(name_embed_row)

        self.content_layout.addWidget(epub_card)

        # DOCX 폰트 카드
        docx_card = ContentCard("DOCX 폰트", "시스템 폰트 또는 폰트 파일 사용")

        # DOCX 본문 폰트 드롭다운
        self.docx_body_combo = ComboBox()
        self.docx_body_combo.addItems(self._system_fonts)
        self.docx_body_combo.setMinimumWidth(220)
        self.docx_body_combo.setCurrentText(self.settings.get('docx_body_font', '맑은 고딕'))
        self.docx_body_combo.currentTextChanged.connect(self._on_font_changed)
        docx_card.add_field("본문 폰트", self.docx_body_combo, help_text="시스템에 설치된 폰트를 선택하세요.")

        # DOCX 이름 폰트 드롭다운
        self.docx_name_combo = ComboBox()
        self.docx_name_combo.addItems(self._system_fonts)
        self.docx_name_combo.setMinimumWidth(220)
        self.docx_name_combo.setCurrentText(self.settings.get('docx_name_font', '맑은 고딕'))
        self.docx_name_combo.currentTextChanged.connect(self._on_font_changed)
        docx_card.add_field("이름 폰트", self.docx_name_combo, help_text="캐릭터 이름 표시용 폰트.")

        docx_card.add_spacing(8)

        # DOCX 폰트 파일 임베드 섹션
        docx_embed_label = BodyLabel("폰트 파일 지정 (선택사항)")
        docx_embed_label.setStyleSheet("font-weight: 600;")
        docx_card.add_widget(docx_embed_label)

        docx_embed_help = BodyLabel("폰트 파일을 지정하면 해당 폰트 이름이 자동으로 적용됩니다.")
        docx_embed_help.setStyleSheet("color: palette(mid); font-size: 11px;")
        docx_card.add_widget(docx_embed_help)

        # DOCX 본문 폰트 파일
        docx_body_row = QHBoxLayout()
        docx_body_row.setSpacing(8)

        self.docx_embed_body = LineEdit()
        self.docx_embed_body.setPlaceholderText("본문 폰트 파일 (.ttf, .otf)")
        self.docx_embed_body.setText(self.settings.get('docx_embed_body', ''))
        docx_body_row.addWidget(self.docx_embed_body, 1)

        docx_body_browse = PushButton("찾기")
        docx_body_browse.clicked.connect(lambda: self._browse_docx_font('body'))
        docx_body_row.addWidget(docx_body_browse)

        docx_card.add_field("본문 파일", QWidget())
        docx_card.add_layout(docx_body_row)

        # DOCX 이름 폰트 파일
        docx_name_row = QHBoxLayout()
        docx_name_row.setSpacing(8)

        self.docx_embed_name = LineEdit()
        self.docx_embed_name.setPlaceholderText("이름 폰트 파일 (.ttf, .otf)")
        self.docx_embed_name.setText(self.settings.get('docx_embed_name', ''))
        docx_name_row.addWidget(self.docx_embed_name, 1)

        docx_name_browse = PushButton("찾기")
        docx_name_browse.clicked.connect(lambda: self._browse_docx_font('name'))
        docx_name_row.addWidget(docx_name_browse)

        docx_card.add_field("이름 파일", QWidget())
        docx_card.add_layout(docx_name_row)

        self.content_layout.addWidget(docx_card)

        # 타이포그래피 상세 카드
        typo_card = ContentCard("타이포그래피 설정")

        self.body_height = typo_card.add_text_field(
            "본문 줄 간격", "body_line_height",
            placeholder="1.6",
            default=self.settings.get('body_line_height', '1.6'),
            help_text="일반 본문의 line-height. 1.5~1.8 권장."
        )

        self.dialogue_height = typo_card.add_text_field(
            "대사 줄 간격", "dialogue_line_height",
            placeholder="1.5",
            default=self.settings.get('dialogue_line_height', '1.5'),
            help_text="캐릭터 대사 부분의 line-height. 본문보다 약간 좁게 설정."
        )

        self.narration_height = typo_card.add_text_field(
            "나레이션 줄 간격", "narration_line_height",
            placeholder="1.7",
            default=self.settings.get('narration_line_height', '1.7'),
            help_text="GM 나레이션의 line-height. 본문보다 넓게 설정하면 구분됨."
        )

        self.base_font_size = typo_card.add_text_field(
            "기본 폰트 배율", "base_font_size",
            placeholder="1.0",
            default=self.settings.get('base_font_size', '1.0'),
            help_text="전체 폰트 크기 배율. 1.0=100%, 1.2=120%"
        )

        self.content_layout.addWidget(typo_card)

        self.add_stretch()

    def _browse_font(self, font_type: str):
        """폰트 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "폰트 파일 선택",
            "",
            "폰트 파일 (*.ttf *.otf *.woff *.woff2);;모든 파일 (*.*)"
        )
        if file_path:
            if font_type == 'body':
                self.embed_body_entry.setText(file_path)
            else:
                self.embed_name_entry.setText(file_path)
            self.save_settings()

    def _browse_docx_font(self, font_type: str):
        """DOCX 폰트 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "폰트 파일 선택",
            "",
            "폰트 파일 (*.ttf *.otf);;모든 파일 (*.*)"
        )
        if file_path:
            # 폰트 파일명에서 폰트 이름 추출
            font_name = Path(file_path).stem
            # 일반적인 접미사 제거
            for suffix in ['-Regular', '-Bold', '-Light', '-Medium', '-SemiBold', '_Regular']:
                font_name = font_name.replace(suffix, '')

            if font_type == 'body':
                self.docx_embed_body.setText(file_path)
                # 시스템 폰트 목록에서 찾아서 선택
                if font_name in self._system_fonts:
                    self.docx_body_combo.setCurrentText(font_name)
            else:
                self.docx_embed_name.setText(file_path)
                if font_name in self._system_fonts:
                    self.docx_name_combo.setCurrentText(font_name)
            self.save_settings()

    def _on_font_changed(self):
        """폰트 선택 변경 시"""
        self._update_preview()
        self.save_settings()

    def _update_preview(self):
        """미리보기 업데이트"""
        body_font = self.epub_body_combo.currentText() or "나눔명조"
        self.update_inspector(font_family=body_font)
        self.settings_changed.emit()

    def save_settings(self):
        """설정 저장"""
        self.settings['epub_body_font'] = self.epub_body_combo.currentText()
        self.settings['epub_name_font'] = self.epub_name_combo.currentText()
        self.settings['embed_body_font'] = self.embed_body_entry.text()
        self.settings['embed_name_font'] = self.embed_name_entry.text()
        self.settings['docx_body_font'] = self.docx_body_combo.currentText()
        self.settings['docx_name_font'] = self.docx_name_combo.currentText()
        self.settings['docx_embed_body'] = self.docx_embed_body.text()
        self.settings['docx_embed_name'] = self.docx_embed_name.text()
        self.settings['body_line_height'] = self.body_height.text()
        self.settings['dialogue_line_height'] = self.dialogue_height.text()
        self.settings['narration_line_height'] = self.narration_height.text()
        self.settings['base_font_size'] = self.base_font_size.text()

        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()

        # 저장된 폰트가 시스템에 있으면 선택, 없으면 기본값
        epub_body = self.settings.get('epub_body_font', '나눔명조')
        if epub_body in self._system_fonts:
            self.epub_body_combo.setCurrentText(epub_body)

        epub_name = self.settings.get('epub_name_font', 'Pretendard')
        if epub_name in self._system_fonts:
            self.epub_name_combo.setCurrentText(epub_name)

        self.embed_body_entry.setText(self.settings.get('embed_body_font', ''))
        self.embed_name_entry.setText(self.settings.get('embed_name_font', ''))

        docx_body = self.settings.get('docx_body_font', '맑은 고딕')
        if docx_body in self._system_fonts:
            self.docx_body_combo.setCurrentText(docx_body)

        docx_name = self.settings.get('docx_name_font', '맑은 고딕')
        if docx_name in self._system_fonts:
            self.docx_name_combo.setCurrentText(docx_name)

        self.docx_embed_body.setText(self.settings.get('docx_embed_body', ''))
        self.docx_embed_name.setText(self.settings.get('docx_embed_name', ''))
        self.body_height.setText(self.settings.get('body_line_height', '1.6'))
        self.dialogue_height.setText(self.settings.get('dialogue_line_height', '1.5'))
        self.narration_height.setText(self.settings.get('narration_line_height', '1.7'))
        self.base_font_size.setText(self.settings.get('base_font_size', '1.0'))
