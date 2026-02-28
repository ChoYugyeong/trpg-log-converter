"""
TRPG Log Converter Pro - 표지 페이지
EPUB 표지 설정
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from pathlib import Path

from qfluentwidgets import BodyLabel, PushButton

from .base_page import BasePage
from ..components import ContentCard, ColorPicker


class CoverPage(BasePage):
    """표지 페이지 - EPUB 표지 설정"""

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._setup_page()
        self.load_settings()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("표지 설정", "EPUB 표지 디자인을 설정합니다")

        # 표지 포함 설정 카드
        include_card = ContentCard("표지 옵션")

        self.include_cover = include_card.add_checkbox(
            "표지 페이지 포함",
            "include_cover",
            checked=self.settings.get('include_cover', True),
            help_text="EPUB 시작 부분에 표지 페이지를 추가합니다."
        )
        self.include_cover.stateChanged.connect(self._on_cover_toggle)

        self.title_on_cover = include_card.add_checkbox(
            "표지에 제목 표시",
            "title_on_cover",
            checked=self.settings.get('title_on_cover', True),
            help_text="표지 페이지에 작품 제목을 표시합니다."
        )
        self.title_on_cover.stateChanged.connect(self._update_cover_preview)

        self.author_on_cover = include_card.add_checkbox(
            "표지에 저자 표시",
            "author_on_cover",
            checked=self.settings.get('author_on_cover', True),
            help_text="표지 페이지에 저자(GM) 이름을 표시합니다."
        )
        self.author_on_cover.stateChanged.connect(self._update_cover_preview)

        self.content_layout.addWidget(include_card)

        # 표지 텍스트 카드
        text_card = ContentCard("표지 텍스트")

        self.cover_subtitle = text_card.add_text_field(
            "부제목", "cover_subtitle",
            placeholder="선택사항",
            default=self.settings.get('cover_subtitle', ''),
            help_text="제목 아래에 표시될 부제목입니다. 시나리오 이름 등을 넣을 수 있습니다."
        )
        self.cover_subtitle.textChanged.connect(self._update_cover_preview)

        self.content_layout.addWidget(text_card)

        # 표지 색상 카드
        color_card = ContentCard("표지 색상")

        self.bg_picker = ColorPicker(self.settings.get('cover_bg', '#1a1a1a'))
        self.bg_picker.color_changed.connect(self._on_bg_color_changed)
        color_card.add_field("배경색", self.bg_picker, "cover_bg",
                            help_text="표지 배경색. 어두운 색상이 세련된 느낌을 줍니다.")

        self.title_color_picker = ColorPicker(self.settings.get('cover_title_color', '#ffffff'))
        self.title_color_picker.color_changed.connect(self._on_title_color_changed)
        color_card.add_field("제목 색상", self.title_color_picker, "cover_title_color",
                            help_text="표지 제목 글씨 색상. 배경색과 대비되는 색상 권장.")

        self.content_layout.addWidget(color_card)

        # 표지 이미지 카드
        image_card = ContentCard("표지 이미지", "선택사항 - 커스텀 표지 이미지 사용")

        # 이미지 미리보기 - 유연한 크기
        self.image_preview_frame = QFrame()
        self.image_preview_frame.setMinimumSize(150, 200)
        self.image_preview_frame.setMaximumSize(180, 250)  # 크기 축소
        self.image_preview_frame.setObjectName("ImagePreviewFrame")

        preview_layout = QVBoxLayout(self.image_preview_frame)
        preview_layout.setAlignment(Qt.AlignCenter)

        self.image_preview_label = BodyLabel("이미지 없음")
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.image_preview_label)

        image_card.add_widget(self.image_preview_frame)

        # 이미지 경로
        image_row = QHBoxLayout()
        image_row.setSpacing(8)

        self.cover_image_entry = image_card.add_text_field(
            "", "cover_image",
            placeholder="이미지 파일 경로",
            default=self.settings.get('cover_image', '')
        )
        self.cover_image_entry.textChanged.connect(self._on_image_path_changed)
        image_row.addWidget(self.cover_image_entry, 1)

        browse_btn = PushButton("찾기")
        browse_btn.clicked.connect(self._browse_image)
        image_row.addWidget(browse_btn)

        clear_btn = PushButton("삭제")
        clear_btn.clicked.connect(self._clear_image)
        image_row.addWidget(clear_btn)

        image_card.add_field("이미지", QWidget())
        image_card.add_layout(image_row)

        self.content_layout.addWidget(image_card)

        # 목차 설정 카드
        toc_card = ContentCard("목차 설정")

        self.include_toc = toc_card.add_checkbox(
            "목차 포함",
            "include_toc",
            checked=self.settings.get('include_toc', True),
            help_text="EPUB에 목차(Table of Contents) 페이지를 추가합니다."
        )

        self.toc_title = toc_card.add_text_field(
            "목차 제목", "toc_title",
            placeholder="목차",
            default=self.settings.get('toc_title', '목차'),
            help_text="목차 페이지의 제목입니다. 기본값은 '목차'입니다."
        )

        self.content_layout.addWidget(toc_card)

        self.add_stretch()

        # 초기 미리보기 업데이트
        self._update_cover_preview()
        self._load_image_preview()

    def _on_cover_toggle(self, state: int):
        """표지 포함 토글"""
        enabled = state == Qt.Checked
        self.title_on_cover.setEnabled(enabled)
        self.author_on_cover.setEnabled(enabled)
        self.save_settings()

    def _on_bg_color_changed(self, color: str):
        """배경색 변경"""
        self._update_cover_preview()
        self.save_settings()

    def _on_title_color_changed(self, color: str):
        """제목 색상 변경"""
        self._update_cover_preview()
        self.save_settings()

    def _update_cover_preview(self):
        """인스펙터 바 표지 미리보기 업데이트"""
        self.update_inspector(
            cover_title="TRPG 리플레이",  # 실제 제목은 ConvertPage에서
            cover_author="GM",
            cover_bg_color=self.bg_picker.get_color(),
            cover_title_color=self.title_color_picker.get_color()
        )

    def _browse_image(self):
        """이미지 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "표지 이미지 선택",
            "",
            "이미지 파일 (*.png *.jpg *.jpeg *.webp);;모든 파일 (*.*)"
        )
        if file_path:
            self.cover_image_entry.setText(file_path)
            self._load_image_preview()
            self.save_settings()

    def _clear_image(self):
        """이미지 삭제"""
        self.cover_image_entry.clear()
        self.image_preview_label.setPixmap(QPixmap())
        self.image_preview_label.setText("이미지 없음")
        self.save_settings()

    def _on_image_path_changed(self, path: str):
        """이미지 경로 변경"""
        self._load_image_preview()

    def _load_image_preview(self):
        """이미지 미리보기 로드"""
        path = self.cover_image_entry.text()
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    180, 260,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_preview_label.setPixmap(scaled)
                self.image_preview_label.setText("")
                return

        self.image_preview_label.setPixmap(QPixmap())
        self.image_preview_label.setText("이미지 없음")

    def save_settings(self):
        """설정 저장"""
        self.settings['include_cover'] = self.include_cover.isChecked()
        self.settings['title_on_cover'] = self.title_on_cover.isChecked()
        self.settings['author_on_cover'] = self.author_on_cover.isChecked()
        self.settings['cover_subtitle'] = self.cover_subtitle.text()
        self.settings['cover_bg'] = self.bg_picker.get_color()
        self.settings['cover_title_color'] = self.title_color_picker.get_color()
        self.settings['cover_image'] = self.cover_image_entry.text()
        self.settings['include_toc'] = self.include_toc.isChecked()
        self.settings['toc_title'] = self.toc_title.text()

        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()

        self.include_cover.setChecked(self.settings.get('include_cover', True))
        self.title_on_cover.setChecked(self.settings.get('title_on_cover', True))
        self.author_on_cover.setChecked(self.settings.get('author_on_cover', True))
        self.cover_subtitle.setText(self.settings.get('cover_subtitle', ''))
        self.bg_picker.set_color(self.settings.get('cover_bg', '#1a1a1a'))
        self.title_color_picker.set_color(self.settings.get('cover_title_color', '#ffffff'))
        self.cover_image_entry.setText(self.settings.get('cover_image', ''))
        self.include_toc.setChecked(self.settings.get('include_toc', True))
        self.toc_title.setText(self.settings.get('toc_title', '목차'))
