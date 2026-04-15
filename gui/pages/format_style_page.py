"""
TRPG Log Converter Pro - 서식 및 스타일 통합 페이지
스타일, 폰트, 표지, 장식 설정을 아코디언 섹션으로 통합
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QSpinBox, QDoubleSpinBox, QFileDialog, QLabel,
    QPlainTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont, QFontDatabase, QImage

from qfluentwidgets import (
    BodyLabel, StrongBodyLabel, CaptionLabel, PushButton, LineEdit, ComboBox,
    CheckBox, Slider, InfoBar, InfoBarPosition, MessageBox
)

from pathlib import Path
import os
import sys
import base64

from .base_page import BasePage
from ..components import ContentCard, ColorPicker, CollapsibleSection
from ..styles import Theme
from ..theme import Colors, Sizes, Spacing, Typography
from core.services import CharacterColorService


# ---------------------------------------------------------------------------
# Helper widgets (from decoration_page)
# ---------------------------------------------------------------------------

class ImagePreview(QFrame):
    """Image preview widget for divider images."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ImagePreview")
        self.setMinimumSize(200, 60)
        self.setMaximumHeight(100)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.image_label = QLabel("이미지 없음")
        self.image_label.setObjectName("ImagePreviewLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        self._image_path = ""
        self._image_data = ""

    def set_image(self, path: str = None, data: str = None):
        if path and os.path.exists(path):
            self._image_path = path
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setText("")
                with open(path, 'rb') as f:
                    self._image_data = base64.b64encode(f.read()).decode('utf-8')
                return True
        elif data:
            self._image_data = data
            try:
                img_bytes = base64.b64decode(data)
                img = QImage()
                img.loadFromData(img_bytes)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img)
                    scaled = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
                    self.image_label.setPixmap(scaled)
                    self.image_label.setText("")
                    return True
            except Exception:
                pass
        self.clear_image()
        return False

    def clear_image(self):
        self._image_path = ""
        self._image_data = ""
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("이미지 없음")

    def get_image_data(self) -> str:
        return self._image_data

    def get_image_path(self) -> str:
        return self._image_path


class DecorationPreview(QFrame):
    """Decoration live preview panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DecorationPreview")
        self.setMinimumHeight(150)
        self.setMaximumHeight(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        title = BodyLabel("미리보기")
        title.setObjectName("DecoPreviewTitle")
        layout.addWidget(title)

        self.sample_before = QLabel("캐릭터A: 이전 대사입니다.")
        self.sample_before.setObjectName("DecoSampleBefore")
        self.sample_before.setWordWrap(True)
        layout.addWidget(self.sample_before)

        self.divider_label = QLabel("─────────────")
        self.divider_label.setObjectName("DecoDivider")
        self.divider_label.setAlignment(Qt.AlignCenter)
        self.divider_label.setWordWrap(True)
        layout.addWidget(self.divider_label)

        self.sample_after = QLabel("캐릭터B: 이후 대사입니다.")
        self.sample_after.setObjectName("DecoSampleAfter")
        self.sample_after.setWordWrap(True)
        layout.addWidget(self.sample_after)

        layout.addSpacing(8)

        self.dice_label = QLabel("\U0001f3b2 1D100 \u2192 42 (\uc131\uacf5)")
        self.dice_label.setObjectName("DecoDiceLabel")
        self.dice_label.setWordWrap(True)
        self.dice_label.setMinimumHeight(30)
        layout.addWidget(self.dice_label)

        layout.addStretch()

    def update_dice(self, show_icon=True, color="#0066cc", style="인라인"):
        icon = "\U0001f3b2 " if show_icon else ""
        sample_text = f"{icon}1D100 \u2192 42 (\uc131\uacf5)"
        if style == "숨김":
            self.dice_label.setVisible(False)
        else:
            self.dice_label.setVisible(True)
            self.dice_label.setText(sample_text)
            if style == "별도 블록":
                # Dynamic: 사용자 선택에 따라 변경됨
                self.dice_label.setStyleSheet(f"""
                    font-size: 13px; color: {color};
                    background: rgba(0,0,0,0.03); padding: 6px 10px; border-radius: 4px;
                """)
            elif style == "하이라이트":
                # Dynamic: 사용자 선택에 따라 변경됨
                self.dice_label.setStyleSheet(f"""
                    font-size: 13px; color: white;
                    background: {color}; padding: 4px 8px; border-radius: 4px;
                """)
            else:
                # Dynamic: 사용자 선택에 따라 변경됨
                self.dice_label.setStyleSheet(f"font-size: 13px; color: {color};")

    def update_divider(self, text=None, image_data=None, color="#999", style="solid"):
        if image_data:
            try:
                img_bytes = base64.b64decode(image_data)
                img = QImage()
                img.loadFromData(img_bytes)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img)
                    scaled = pixmap.scaledToHeight(40, Qt.SmoothTransformation)
                    self.divider_label.setPixmap(scaled)
                    self.divider_label.setText("")
                    return
            except Exception:
                pass
        if text:
            self.divider_label.setPixmap(QPixmap())
            self.divider_label.setText(text)
            border_style = "none"
            if style == "dashed":
                border_style = "border-bottom: 2px dashed " + color + ";"
            elif style == "dotted":
                border_style = "border-bottom: 2px dotted " + color + ";"
            # Dynamic: 사용자 선택에 따라 변경됨
            self.divider_label.setStyleSheet(f"""
                font-size: 14px; color: {color}; padding: 8px 0; {border_style}
            """)


# ===========================================================================
# Main page
# ===========================================================================

class FormatStylePage(BasePage):
    """
    서식 및 스타일 통합 페이지
    Style + Font + Cover + Decoration settings combined with accordion sections.
    """

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self.color_service = CharacterColorService(
            self.settings.get('character_colors', {})
        )
        self.character_color_widgets = {}
        self._system_fonts = self._get_system_fonts()
        self._setup_page()
        self.load_settings()

    # ------------------------------------------------------------------
    # System fonts helper (from FontPage)
    # ------------------------------------------------------------------

    def _get_system_fonts(self) -> list:
        fonts = QFontDatabase.families()
        korean_fonts = []
        other_fonts = []
        for font in fonts:
            if any(0xAC00 <= ord(c) <= 0xD7A3 for c in font) or \
               any(kw in font.lower() for kw in [
                   'nanum', 'malgun', 'batang', 'gulim', 'dotum',
                   'gungsuh', 'pretendard', 'noto sans kr', 'noto serif kr'
               ]):
                korean_fonts.append(font)
            else:
                other_fonts.append(font)
        korean_fonts.sort()
        other_fonts.sort()
        return korean_fonts + other_fonts

    # ==================================================================
    # Page setup
    # ==================================================================

    def _setup_page(self):
        self.add_header("서식 및 스타일", "스타일, 폰트, 표지, 장식 요소를 설정합니다")

        # --- Section 1: 스타일 설정 (expanded) ---
        self.style_section = CollapsibleSection(
            "스타일 설정", expanded=True
        )
        self._build_style_section(self.style_section)
        self.content_layout.addWidget(self.style_section)

        # --- Section 2: 폰트 설정 (collapsed) ---
        self.font_section = CollapsibleSection(
            "폰트 설정", expanded=False
        )
        self._build_font_section(self.font_section)
        self.content_layout.addWidget(self.font_section)

        # --- Section 3: 표지 설정 (collapsed) ---
        self.cover_section = CollapsibleSection(
            "표지 설정", expanded=False
        )
        self._build_cover_section(self.cover_section)
        self.content_layout.addWidget(self.cover_section)

        # --- Section 4: 장식 요소 (collapsed) ---
        self.deco_section = CollapsibleSection(
            "장식 요소", expanded=False
        )
        self._build_decoration_section(self.deco_section)
        self.content_layout.addWidget(self.deco_section)

        self.add_stretch()

    # ==================================================================
    # Section 1 - 스타일 설정
    # ==================================================================

    def _build_style_section(self, section: CollapsibleSection):
        # ---- 테마 프리셋 카드 ----
        preset_card = ContentCard("테마 프리셋", "미리 정의된 스타일 조합을 선택하거나 직접 만들 수 있습니다")

        self._custom_theme_presets = self.settings.get('custom_theme_presets', {})
        preset_options = list(Theme.PRESETS.keys()) + list(self._custom_theme_presets.keys())

        self.preset_combo = preset_card.add_dropdown(
            "프리셋", "preset",
            options=preset_options if preset_options else ["Classic Light"],
            default="Classic Light",
            help_text="미리 정의된 색상/스타일 조합. 선택 후 개별 설정 수정 가능."
        )
        self.preset_combo.currentTextChanged.connect(self._apply_preset)

        # Preset swatch preview
        self.preset_preview = QWidget()
        preview_layout = QHBoxLayout(self.preset_preview)
        preview_layout.setContentsMargins(0, 4, 0, 8)
        preview_layout.setSpacing(6)

        self.swatch_bg = QWidget()
        self.swatch_bg.setObjectName("PresetSwatchBg")
        self.swatch_bg.setFixedSize(32, 32)
        preview_layout.addWidget(self.swatch_bg)

        self.swatch_text = QWidget()
        self.swatch_text.setObjectName("PresetSwatchText")
        self.swatch_text.setFixedSize(32, 32)
        preview_layout.addWidget(self.swatch_text)

        self.swatch_name = QWidget()
        self.swatch_name.setObjectName("PresetSwatchName")
        self.swatch_name.setFixedSize(32, 32)
        preview_layout.addWidget(self.swatch_name)

        self.swatch_label = BodyLabel("")
        self.swatch_label.setObjectName("PresetSwatchLabel")
        preview_layout.addWidget(self.swatch_label)
        preview_layout.addStretch()

        preset_card.add_widget(self.preset_preview)

        # Preset management buttons
        preset_btn_row = QHBoxLayout()
        preset_btn_row.setSpacing(Spacing.SM)

        save_preset_btn = PushButton("현재 스타일 저장")
        save_preset_btn.setMinimumHeight(36)
        save_preset_btn.setCursor(Qt.PointingHandCursor)
        save_preset_btn.clicked.connect(self._save_current_as_preset)
        preset_btn_row.addWidget(save_preset_btn)

        delete_preset_btn = PushButton("프리셋 삭제")
        delete_preset_btn.setMinimumHeight(36)
        delete_preset_btn.setCursor(Qt.PointingHandCursor)
        delete_preset_btn.clicked.connect(self._delete_preset)
        preset_btn_row.addWidget(delete_preset_btn)

        preset_btn_row.addStretch()
        preset_card.add_layout(preset_btn_row)

        section.add_widget(preset_card)

        # ---- 본문 스타일 카드 ----
        body_card = ContentCard("본문 스타일")

        # Background color
        self.style_bg_picker = ColorPicker(self.settings.get('style_body_bg', '#ffffff'))
        self.style_bg_picker.color_changed.connect(self._on_style_changed)
        body_card.add_field("배경색", self.style_bg_picker, "style_body_bg",
                           help_text="EPUB 본문의 배경색입니다. 흰색(#ffffff) 또는 세피아(#f4ecd8) 권장.")

        # Text color
        self.style_text_picker = ColorPicker(self.settings.get('style_body_text', '#1a1a1a'))
        self.style_text_picker.color_changed.connect(self._on_style_changed)
        body_card.add_field("텍스트", self.style_text_picker, "style_body_text",
                           help_text="본문 텍스트 색상입니다. 배경색과 대비가 좋은 색상을 선택하세요.")

        # Font size slider + spinbox
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(Spacing.SM)

        self.size_slider = Slider(Qt.Horizontal)
        self.size_slider.setRange(10, 24)
        try:
            _font_size = int(self.settings.get('style_font_size', 14))
        except (ValueError, TypeError):
            _font_size = 14
        self.size_slider.setValue(_font_size)
        size_layout.addWidget(self.size_slider, 1)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 24)
        self.size_spin.setValue(self.size_slider.value())
        self.size_spin.setSuffix("px")
        self.size_spin.setFixedWidth(70)
        self.size_spin.setFixedHeight(32)
        size_layout.addWidget(self.size_spin)

        self.size_slider.valueChanged.connect(self._on_font_size_changed)
        self.size_spin.valueChanged.connect(self._on_font_size_spin_changed)

        body_card.add_field("폰트 크기", size_widget, "style_font_size",
                           help_text="EPUB 본문의 기본 폰트 크기입니다. 14-16px 권장.")

        # Line height slider + spinbox
        height_widget = QWidget()
        height_layout = QHBoxLayout(height_widget)
        height_layout.setContentsMargins(0, 0, 0, 0)
        height_layout.setSpacing(Spacing.SM)

        self.height_slider = Slider(Qt.Horizontal)
        self.height_slider.setRange(12, 24)
        try:
            _line_height = int(float(self.settings.get('style_line_height', 1.6)) * 10)
        except (ValueError, TypeError):
            _line_height = 16
        self.height_slider.setValue(_line_height)
        height_layout.addWidget(self.height_slider, 1)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1.2, 2.4)
        self.height_spin.setSingleStep(0.1)
        self.height_spin.setDecimals(1)
        self.height_spin.setValue(self.height_slider.value() / 10)
        self.height_spin.setFixedWidth(70)
        self.height_spin.setFixedHeight(32)
        height_layout.addWidget(self.height_spin)

        self.height_slider.valueChanged.connect(self._on_line_height_changed)
        self.height_spin.valueChanged.connect(self._on_line_height_spin_changed)

        body_card.add_field("줄 간격", height_widget, "style_line_height",
                           help_text="줄과 줄 사이의 간격입니다. 1.6~1.8 권장.")

        section.add_widget(body_card)

        # ---- 캐릭터 이름 스타일 카드 ----
        char_card = ContentCard("캐릭터 이름 스타일")

        self.name_picker = ColorPicker(self.settings.get('style_name_color', '#2d2d2d'))
        self.name_picker.color_changed.connect(self._on_style_changed)
        char_card.add_field("이름 색상", self.name_picker, "style_name_color",
                           help_text="캐릭터 이름의 기본 색상입니다. 캐릭터별 색상이 우선 적용됩니다.")

        self.name_bold = char_card.add_checkbox(
            "이름을 굵게 표시", "style_name_bold",
            checked=self.settings.get('style_name_bold', True),
            help_text="캐릭터 이름을 굵은 글씨로 표시합니다."
        )
        self.name_bold.stateChanged.connect(self._on_style_changed)

        self.separator_combo = char_card.add_dropdown(
            "대사 구분자", "style_separator",
            options=["「 」 (꺾쇠)", "\" \" (따옴표)", "' ' (작은따옴표)", "없음", "직접 입력"],
            default=self.settings.get('style_separator', '「 」 (꺾쇠)'),
            help_text="대사를 감싸는 기호입니다. 일본식 꺾쇠「」가 가장 많이 사용됩니다."
        )
        self.separator_combo.currentTextChanged.connect(self._on_separator_changed)

        self.custom_separator = LineEdit()
        self.custom_separator.setPlaceholderText("예: [ ] 또는 < >")
        self.custom_separator.setMinimumHeight(36)
        self.custom_separator.setVisible(False)
        self.custom_separator.textChanged.connect(self._on_style_changed)
        char_card.add_field("", self.custom_separator,
                           help_text="열림/닫힘 기호를 공백으로 구분하여 입력 (예: [ ])")

        saved_sep = self.settings.get('style_separator', '「 」 (꺾쇠)')
        if saved_sep == '직접 입력':
            self.custom_separator.setVisible(True)
            self.custom_separator.setText(self.settings.get('custom_separator_text', ''))

        section.add_widget(char_card)

        # ---- 캐릭터별 색상 카드 ----
        char_color_card = ContentCard("캐릭터별 색상", "각 캐릭터에 고유한 색상 자동 할당")

        auto_btn_row = QHBoxLayout()
        auto_btn_row.setSpacing(Spacing.SM)

        auto_assign_btn = PushButton("파일에서 캐릭터 추출")
        auto_assign_btn.clicked.connect(self._auto_assign_colors)
        auto_btn_row.addWidget(auto_assign_btn)

        reset_colors_btn = PushButton("색상 초기화")
        reset_colors_btn.clicked.connect(self._reset_character_colors)
        auto_btn_row.addWidget(reset_colors_btn)

        auto_btn_row.addStretch()
        char_color_card.add_layout(auto_btn_row)

        self.char_color_container = QWidget()
        self.char_color_layout = QVBoxLayout(self.char_color_container)
        self.char_color_layout.setContentsMargins(0, 8, 0, 0)
        self.char_color_layout.setSpacing(Spacing.SM)

        char_colors = self.settings.get('character_colors', {})
        for name, color in char_colors.items():
            self._add_character_color_row(name, color)

        if not char_colors:
            no_char_label = BodyLabel(
                "아직 캐릭터가 없습니다. '파일에서 캐릭터 추출'을 사용하거나 변환 시 자동 할당됩니다."
            )
            no_char_label.setWordWrap(True)
            self.char_color_layout.addWidget(no_char_label)

        char_color_card.add_widget(self.char_color_container)
        section.add_widget(char_color_card)

        # ---- 색상 팔레트 카드 ----
        palette_card = ContentCard("색상 팔레트", "요소별 색상 설정")

        colors = self.settings.get('colors', {})
        color_grid = QGridLayout()
        color_grid.setSpacing(Spacing.LG)

        self.color_pickers = {}
        color_items = [
            ('text_color', '본문 텍스트', '#1a1a1a'),
            ('name_color', '캐릭터 이름', '#2d2d2d'),
            ('dice_color', '주사위', '#888888'),
            ('system_color', '시스템 메시지', '#666666'),
            ('effect_bg', '효과 배경', '#f5f5f5'),
            ('effect_border', '효과 테두리', '#cccccc'),
        ]

        for i, (key, label, default) in enumerate(color_items):
            row, col = divmod(i, 2)
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(Spacing.SM)

            lbl = BodyLabel(label)
            lbl.setFixedWidth(100)
            item_layout.addWidget(lbl)

            picker = ColorPicker(colors.get(key, default))
            picker.color_changed.connect(lambda c, k=key: self._on_palette_color_changed(k, c))
            self.color_pickers[key] = picker
            item_layout.addWidget(picker)

            color_grid.addWidget(item_widget, row, col)

        palette_card.add_layout(color_grid)
        section.add_widget(palette_card)

    # ==================================================================
    # Section 2 - 폰트 설정
    # ==================================================================

    def _build_font_section(self, section: CollapsibleSection):
        # ---- EPUB 폰트 카드 ----
        epub_card = ContentCard("EPUB 폰트", "웹 폰트 또는 임베드 폰트 사용")

        self.epub_body_combo = ComboBox()
        self.epub_body_combo.addItems(self._system_fonts)
        self.epub_body_combo.setMinimumWidth(220)
        self.epub_body_combo.setCurrentText(self.settings.get('epub_body_font', '나눔명조'))
        self.epub_body_combo.currentTextChanged.connect(self._on_font_changed)
        epub_card.add_field("본문 폰트", self.epub_body_combo,
                           help_text="EPUB 본문에 사용할 폰트를 선택하세요.")

        self.epub_name_combo = ComboBox()
        self.epub_name_combo.addItems(self._system_fonts)
        self.epub_name_combo.setMinimumWidth(220)
        self.epub_name_combo.setCurrentText(self.settings.get('epub_name_font', 'Pretendard'))
        self.epub_name_combo.currentTextChanged.connect(self._on_font_changed)
        epub_card.add_field("이름 폰트", self.epub_name_combo,
                           help_text="캐릭터 이름에 사용할 폰트. 산세리프 계열 권장.")

        epub_card.add_spacing(8)

        embed_label = StrongBodyLabel("폰트 파일 임베드 (선택사항)")
        epub_card.add_widget(embed_label)

        # Body font file
        body_embed_row = QHBoxLayout()
        body_embed_row.setSpacing(Spacing.SM)

        self.embed_body_entry = LineEdit()
        self.embed_body_entry.setPlaceholderText("본문 폰트 파일 (.ttf, .otf)")
        self.embed_body_entry.setText(self.settings.get('embed_body_font', ''))
        body_embed_row.addWidget(self.embed_body_entry, 1)

        body_browse = PushButton("찾기")
        body_browse.clicked.connect(lambda: self._browse_font('body'))
        body_embed_row.addWidget(body_browse)

        epub_card.add_field("본문 파일", QWidget())
        epub_card.add_layout(body_embed_row)

        # Name font file
        name_embed_row = QHBoxLayout()
        name_embed_row.setSpacing(Spacing.SM)

        self.embed_name_entry = LineEdit()
        self.embed_name_entry.setPlaceholderText("이름 폰트 파일 (.ttf, .otf)")
        self.embed_name_entry.setText(self.settings.get('embed_name_font', ''))
        name_embed_row.addWidget(self.embed_name_entry, 1)

        name_browse = PushButton("찾기")
        name_browse.clicked.connect(lambda: self._browse_font('name'))
        name_embed_row.addWidget(name_browse)

        epub_card.add_field("이름 파일", QWidget())
        epub_card.add_layout(name_embed_row)

        section.add_widget(epub_card)

        # ---- DOCX 폰트 카드 ----
        docx_card = ContentCard("DOCX 폰트", "시스템 폰트 또는 폰트 파일 사용")

        self.docx_body_combo = ComboBox()
        self.docx_body_combo.addItems(self._system_fonts)
        self.docx_body_combo.setMinimumWidth(220)
        self.docx_body_combo.setCurrentText(self.settings.get('docx_body_font', '맑은 고딕'))
        self.docx_body_combo.currentTextChanged.connect(self._on_font_changed)
        docx_card.add_field("본문 폰트", self.docx_body_combo,
                           help_text="시스템에 설치된 폰트를 선택하세요.")

        self.docx_name_combo = ComboBox()
        self.docx_name_combo.addItems(self._system_fonts)
        self.docx_name_combo.setMinimumWidth(220)
        self.docx_name_combo.setCurrentText(self.settings.get('docx_name_font', '맑은 고딕'))
        self.docx_name_combo.currentTextChanged.connect(self._on_font_changed)
        docx_card.add_field("이름 폰트", self.docx_name_combo,
                           help_text="캐릭터 이름 표시용 폰트.")

        docx_card.add_spacing(8)

        docx_embed_label = StrongBodyLabel("폰트 파일 지정 (선택사항)")
        docx_card.add_widget(docx_embed_label)

        docx_embed_help = BodyLabel("폰트 파일을 지정하면 해당 폰트 이름이 자동으로 적용됩니다.")
        docx_embed_help.setObjectName("FontEmbedHelp")
        docx_card.add_widget(docx_embed_help)

        # DOCX body font file
        docx_body_row = QHBoxLayout()
        docx_body_row.setSpacing(Spacing.SM)

        self.docx_embed_body = LineEdit()
        self.docx_embed_body.setPlaceholderText("본문 폰트 파일 (.ttf, .otf)")
        self.docx_embed_body.setText(self.settings.get('docx_embed_body', ''))
        docx_body_row.addWidget(self.docx_embed_body, 1)

        docx_body_browse = PushButton("찾기")
        docx_body_browse.clicked.connect(lambda: self._browse_docx_font('body'))
        docx_body_row.addWidget(docx_body_browse)

        docx_card.add_field("본문 파일", QWidget())
        docx_card.add_layout(docx_body_row)

        # DOCX name font file
        docx_name_row = QHBoxLayout()
        docx_name_row.setSpacing(Spacing.SM)

        self.docx_embed_name = LineEdit()
        self.docx_embed_name.setPlaceholderText("이름 폰트 파일 (.ttf, .otf)")
        self.docx_embed_name.setText(self.settings.get('docx_embed_name', ''))
        docx_name_row.addWidget(self.docx_embed_name, 1)

        docx_name_browse = PushButton("찾기")
        docx_name_browse.clicked.connect(lambda: self._browse_docx_font('name'))
        docx_name_row.addWidget(docx_name_browse)

        docx_card.add_field("이름 파일", QWidget())
        docx_card.add_layout(docx_name_row)

        section.add_widget(docx_card)

        # ---- 타이포그래피 카드 ----
        typo_card = ContentCard("타이포그래피 설정")

        self.body_height_input = typo_card.add_text_field(
            "본문 줄 간격", "body_line_height",
            placeholder="1.6",
            default=self.settings.get('body_line_height', '1.6'),
            help_text="일반 본문의 line-height. 1.5~1.8 권장."
        )

        self.dialogue_height_input = typo_card.add_text_field(
            "대사 줄 간격", "dialogue_line_height",
            placeholder="1.5",
            default=self.settings.get('dialogue_line_height', '1.5'),
            help_text="캐릭터 대사 부분의 line-height. 본문보다 약간 좁게 설정."
        )

        self.narration_height_input = typo_card.add_text_field(
            "나레이션 줄 간격", "narration_line_height",
            placeholder="1.7",
            default=self.settings.get('narration_line_height', '1.7'),
            help_text="GM 나레이션의 line-height. 본문보다 넓게 설정하면 구분됨."
        )

        self.base_font_size_input = typo_card.add_text_field(
            "기본 폰트 배율", "base_font_size",
            placeholder="1.0",
            default=self.settings.get('base_font_size', '1.0'),
            help_text="전체 폰트 크기 배율. 1.0=100%, 1.2=120%"
        )

        section.add_widget(typo_card)

    # ==================================================================
    # Section 3 - 표지 설정
    # ==================================================================

    def _build_cover_section(self, section: CollapsibleSection):
        # ---- 표지 옵션 카드 ----
        include_card = ContentCard("표지 옵션")

        self.include_cover = include_card.add_checkbox(
            "표지 페이지 포함", "include_cover",
            checked=self.settings.get('include_cover', True),
            help_text="EPUB 시작 부분에 표지 페이지를 추가합니다."
        )
        self.include_cover.stateChanged.connect(self._on_cover_toggle)

        self.title_on_cover = include_card.add_checkbox(
            "표지에 제목 표시", "title_on_cover",
            checked=self.settings.get('title_on_cover', True),
            help_text="표지 페이지에 작품 제목을 표시합니다."
        )
        self.title_on_cover.stateChanged.connect(self._update_cover_preview)

        self.author_on_cover = include_card.add_checkbox(
            "표지에 저자 표시", "author_on_cover",
            checked=self.settings.get('author_on_cover', True),
            help_text="표지 페이지에 저자(GM) 이름을 표시합니다."
        )
        self.author_on_cover.stateChanged.connect(self._update_cover_preview)

        section.add_widget(include_card)

        # ---- 표지 텍스트 카드 ----
        text_card = ContentCard("표지 텍스트")

        self.cover_subtitle = text_card.add_text_field(
            "부제목", "cover_subtitle",
            placeholder="선택사항",
            default=self.settings.get('cover_subtitle', ''),
            help_text="제목 아래에 표시될 부제목입니다. 시나리오 이름 등을 넣을 수 있습니다."
        )
        self.cover_subtitle.textChanged.connect(self._update_cover_preview)

        section.add_widget(text_card)

        # ---- 표지 색상 카드 ----
        color_card = ContentCard("표지 색상")

        self.cover_bg_picker = ColorPicker(self.settings.get('cover_bg', '#1a1a1a'))
        self.cover_bg_picker.color_changed.connect(self._on_cover_bg_color_changed)
        color_card.add_field("배경색", self.cover_bg_picker, "cover_bg",
                            help_text="표지 배경색. 어두운 색상이 세련된 느낌을 줍니다.")

        self.cover_title_color_picker = ColorPicker(self.settings.get('cover_title_color', '#ffffff'))
        self.cover_title_color_picker.color_changed.connect(self._on_cover_title_color_changed)
        color_card.add_field("제목 색상", self.cover_title_color_picker, "cover_title_color",
                            help_text="표지 제목 글씨 색상. 배경색과 대비되는 색상 권장.")

        section.add_widget(color_card)

        # ---- 표지 이미지 카드 ----
        image_card = ContentCard("표지 이미지", "선택사항 - 커스텀 표지 이미지 사용")

        self.cover_image_preview_frame = QFrame()
        self.cover_image_preview_frame.setMinimumSize(150, 200)
        self.cover_image_preview_frame.setMaximumSize(180, 250)
        self.cover_image_preview_frame.setObjectName("ImagePreviewFrame")

        cover_preview_layout = QVBoxLayout(self.cover_image_preview_frame)
        cover_preview_layout.setAlignment(Qt.AlignCenter)

        self.cover_image_preview_label = BodyLabel("이미지 없음")
        self.cover_image_preview_label.setAlignment(Qt.AlignCenter)
        cover_preview_layout.addWidget(self.cover_image_preview_label)

        image_card.add_widget(self.cover_image_preview_frame)

        # Image path + buttons
        self.cover_image_entry = image_card.add_text_field(
            "", "cover_image",
            placeholder="이미지 파일 경로",
            default=self.settings.get('cover_image', '')
        )
        self.cover_image_entry.textChanged.connect(self._on_cover_image_path_changed)

        image_row = QHBoxLayout()
        image_row.setSpacing(Spacing.SM)
        image_row.addWidget(self.cover_image_entry, 1)

        browse_btn = PushButton("찾기")
        browse_btn.clicked.connect(self._browse_cover_image)
        image_row.addWidget(browse_btn)

        clear_btn = PushButton("삭제")
        clear_btn.clicked.connect(self._clear_cover_image)
        image_row.addWidget(clear_btn)

        image_card.add_field("이미지", QWidget())
        image_card.add_layout(image_row)

        section.add_widget(image_card)

        # ---- 목차 설정 카드 ----
        toc_card = ContentCard("목차 설정")

        self.include_toc = toc_card.add_checkbox(
            "목차 포함", "include_toc",
            checked=self.settings.get('include_toc', True),
            help_text="EPUB에 목차(Table of Contents) 페이지를 추가합니다."
        )

        self.toc_title = toc_card.add_text_field(
            "목차 제목", "toc_title",
            placeholder="목차",
            default=self.settings.get('toc_title', '목차'),
            help_text="목차 페이지의 제목입니다. 기본값은 '목차'입니다."
        )

        section.add_widget(toc_card)

    # ==================================================================
    # Section 4 - 장식 요소
    # ==================================================================

    def _build_decoration_section(self, section: CollapsibleSection):
        # ---- 장면 구분선 카드 ----
        divider_type_card = ContentCard("장면 구분선")

        self.divider_type = divider_type_card.add_dropdown(
            "유형", "divider_type",
            options=["텍스트/기호", "이미지", "선 스타일", "사용 안 함"],
            default="텍스트/기호",
            help_text="장면 전환 시 표시되는 구분선의 유형을 선택합니다."
        )
        self.divider_type.currentTextChanged.connect(self._on_divider_type_changed)

        section.add_widget(divider_type_card)

        # ---- 텍스트/기호 설정 ----
        self.text_card = ContentCard("텍스트/기호 설정")

        self.divider_text = self.text_card.add_text_field(
            "구분 기호", "divider_text",
            placeholder="* * *",
            default="* * *",
            help_text="장면 구분에 사용할 텍스트나 기호입니다. 예: * * *, ───, ◆◆◆",
            clear_button=False
        )
        self.divider_text.textChanged.connect(self._update_deco_preview)

        self.divider_color = ColorPicker(self.settings.get('divider_color', '#888888'))
        self.divider_color.color_changed.connect(self._update_deco_preview)
        self.text_card.add_field("색상", self.divider_color, "divider_color")

        section.add_widget(self.text_card)

        # ---- 이미지 설정 ----
        self.image_card = ContentCard("이미지 설정")
        self.image_card.setVisible(False)

        self.divider_image_preview = ImagePreview()
        self.image_card.add_widget(self.divider_image_preview)

        img_btn_row = QHBoxLayout()
        img_btn_row.setSpacing(Spacing.SM)

        upload_btn = PushButton("이미지 업로드")
        upload_btn.clicked.connect(self._upload_divider_image)
        img_btn_row.addWidget(upload_btn)

        clear_img_btn = PushButton("이미지 제거")
        clear_img_btn.clicked.connect(self._clear_divider_image)
        img_btn_row.addWidget(clear_img_btn)

        img_btn_row.addStretch()
        self.image_card.add_layout(img_btn_row)

        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)

        self.divider_img_height = QSpinBox()
        self.divider_img_height.setRange(20, 200)
        self.divider_img_height.setValue(40)
        self.divider_img_height.setSuffix(" px")
        size_layout.addWidget(self.divider_img_height)
        size_layout.addStretch()

        self.image_card.add_field("이미지 높이", size_widget,
                                 help_text="구분선 이미지의 높이를 설정합니다.")

        section.add_widget(self.image_card)

        # ---- 선 스타일 설정 ----
        self.line_card = ContentCard("선 스타일 설정")
        self.line_card.setVisible(False)

        self.line_style = self.line_card.add_dropdown(
            "선 종류", "line_style",
            options=["실선", "점선", "파선", "이중선"],
            default="실선",
            help_text="구분선의 선 스타일입니다."
        )
        self.line_style.currentTextChanged.connect(self._update_deco_preview)

        thickness_widget = QWidget()
        thickness_layout = QHBoxLayout(thickness_widget)
        thickness_layout.setContentsMargins(0, 0, 0, 0)

        self.line_thickness = QSpinBox()
        self.line_thickness.setRange(1, 10)
        self.line_thickness.setValue(1)
        self.line_thickness.setSuffix(" px")
        self.line_thickness.valueChanged.connect(self._update_deco_preview)
        thickness_layout.addWidget(self.line_thickness)
        thickness_layout.addStretch()

        self.line_card.add_field("선 두께", thickness_widget)

        self.line_color = ColorPicker("#cccccc")
        self.line_color.color_changed.connect(self._update_deco_preview)
        self.line_card.add_field("선 색상", self.line_color)

        # Line width slider + spinbox
        width_widget = QWidget()
        width_layout = QHBoxLayout(width_widget)
        width_layout.setContentsMargins(0, 0, 0, 0)
        width_layout.setSpacing(Spacing.SM)

        self.line_width = Slider(Qt.Horizontal)
        self.line_width.setRange(20, 100)
        self.line_width.setValue(60)
        self.line_width.valueChanged.connect(self._update_deco_preview)
        width_layout.addWidget(self.line_width, 1)

        self.line_width_spin = QSpinBox()
        self.line_width_spin.setRange(20, 100)
        self.line_width_spin.setValue(60)
        self.line_width_spin.setSuffix("%")
        self.line_width_spin.setFixedWidth(70)
        self.line_width_spin.setFixedHeight(32)
        self.line_width_spin.valueChanged.connect(lambda v: (
            self.line_width.blockSignals(True),
            self.line_width.setValue(v),
            self.line_width.blockSignals(False),
            self._update_deco_preview(),
        ))
        self.line_width.valueChanged.connect(lambda v: (
            self.line_width_spin.blockSignals(True),
            self.line_width_spin.setValue(v),
            self.line_width_spin.blockSignals(False),
        ))
        width_layout.addWidget(self.line_width_spin)

        self.line_card.add_field("선 너비", width_widget)

        section.add_widget(self.line_card)

        # ---- 챕터 헤더 스타일 카드 ----
        header_card = ContentCard("챕터 헤더 스타일")

        self.header_style = header_card.add_dropdown(
            "스타일", "header_style",
            options=["기본", "중앙 정렬", "장식 포함", "이미지 헤더", "사용 안 함"],
            default="기본",
            help_text="챕터/씬 제목의 표시 스타일입니다."
        )

        # Header font size slider + spinbox
        hdr_size_widget = QWidget()
        hdr_size_layout = QHBoxLayout(hdr_size_widget)
        hdr_size_layout.setContentsMargins(0, 0, 0, 0)
        hdr_size_layout.setSpacing(Spacing.SM)

        self.header_size = Slider(Qt.Horizontal)
        self.header_size.setRange(14, 32)
        self.header_size.setValue(20)
        hdr_size_layout.addWidget(self.header_size, 1)

        self.header_size_spin = QSpinBox()
        self.header_size_spin.setRange(14, 32)
        self.header_size_spin.setValue(20)
        self.header_size_spin.setSuffix("px")
        self.header_size_spin.setFixedWidth(70)
        self.header_size_spin.setFixedHeight(32)
        hdr_size_layout.addWidget(self.header_size_spin)

        self.header_size.valueChanged.connect(lambda v: (
            self.header_size_spin.blockSignals(True),
            self.header_size_spin.setValue(v),
            self.header_size_spin.blockSignals(False),
        ))
        self.header_size_spin.valueChanged.connect(lambda v: (
            self.header_size.blockSignals(True),
            self.header_size.setValue(v),
            self.header_size.blockSignals(False),
        ))

        header_card.add_field("폰트 크기", hdr_size_widget)

        self.header_color = ColorPicker("#1a1a1a")
        header_card.add_field("헤더 색상", self.header_color)

        self.header_bold = header_card.add_checkbox(
            "굵게 표시", "header_bold", checked=True
        )

        section.add_widget(header_card)

        # ---- 헤더 장식 카드 ----
        deco_card = ContentCard("헤더 장식")

        self.header_prefix = deco_card.add_text_field(
            "앞 장식", "header_prefix",
            placeholder="【",
            default="",
            help_text="챕터 제목 앞에 붙는 장식 기호",
            clear_button=False
        )

        self.header_suffix = deco_card.add_text_field(
            "뒤 장식", "header_suffix",
            placeholder="】",
            default="",
            help_text="챕터 제목 뒤에 붙는 장식 기호",
            clear_button=False
        )

        self.header_underline = deco_card.add_checkbox(
            "밑줄 표시", "header_underline", checked=False,
            help_text="챕터 제목 아래에 밑줄을 표시합니다."
        )

        self.header_box = deco_card.add_checkbox(
            "배경 박스", "header_box", checked=False,
            help_text="챕터 제목에 배경 박스를 표시합니다."
        )

        self.header_box_color = ColorPicker("#f5f5f5")
        deco_card.add_field("박스 배경색", self.header_box_color)

        section.add_widget(deco_card)

        # ---- CSS 편집기 카드 ----
        css_info_card = ContentCard("사용자 정의 CSS")

        info_label = BodyLabel(
            "고급 사용자를 위한 CSS 직접 편집 기능입니다.\n"
            "EPUB 출력에 적용될 추가 CSS 스타일을 입력하세요."
        )
        info_label.setWordWrap(True)
        css_info_card.add_widget(info_label)

        self.css_editor = QPlainTextEdit()
        self.css_editor.setMinimumHeight(180)
        self.css_editor.setMaximumHeight(250)
        self.css_editor.setPlaceholderText(
            "/* 사용자 정의 CSS */\n"
            ".dialogue {\n"
            "    margin-bottom: 0.5em;\n"
            "}\n\n"
            ".character-name {\n"
            "    font-weight: bold;\n"
            "}\n\n"
            ".scene-break {\n"
            "    text-align: center;\n"
            "    margin: 2em 0;\n"
            "}"
        )
        self.css_editor.setObjectName("CssEditor")
        self.css_editor.setFont(QFont("Consolas" if sys.platform == "win32" else "Menlo", 12))
        css_info_card.add_widget(self.css_editor)

        self.css_editor.textChanged.connect(self._on_css_changed)

        # CSS preset row
        preset_row = QHBoxLayout()
        preset_row.setSpacing(Spacing.SM)

        preset_label = BodyLabel("프리셋:")
        preset_row.addWidget(preset_label)

        css_preset_options = [
            "선택...", "기본 스타일", "소설풍", "시나리오풍", "미니멀", "다크 테마"
        ]
        self.css_preset_combo = ComboBox()
        self.css_preset_combo.addItems(css_preset_options)
        self.css_preset_combo.setMinimumHeight(Sizes.BUTTON_MD_H)
        fm = self.css_preset_combo.fontMetrics()
        max_w = max(fm.horizontalAdvance(opt) for opt in css_preset_options)
        self.css_preset_combo.setMinimumWidth(max(160, max_w + 80))
        self.css_preset_combo.currentTextChanged.connect(self._apply_css_preset)
        preset_row.addWidget(self.css_preset_combo)

        preset_row.addStretch()

        reset_btn = PushButton("초기화")
        reset_btn.clicked.connect(lambda: self.css_editor.clear())
        preset_row.addWidget(reset_btn)

        css_info_card.add_layout(preset_row)

        section.add_widget(css_info_card)

        # CSS class reference
        ref_card = ContentCard("사용 가능한 CSS 클래스")

        ref_text = BodyLabel(
            "<b>.dialogue</b> - 대사 컨테이너\n"
            "<b>.character-name</b> - 캐릭터 이름\n"
            "<b>.dialogue-text</b> - 대사 내용\n"
            "<b>.narration</b> - 나레이션/지문\n"
            "<b>.scene-break</b> - 장면 구분선\n"
            "<b>.chapter-title</b> - 챕터 제목\n"
            "<b>.dice-roll</b> - 주사위 굴림\n"
            "<b>.system-message</b> - 시스템 메시지"
        )
        ref_text.setWordWrap(True)
        ref_text.setTextFormat(Qt.RichText)
        ref_card.add_widget(ref_text)

        section.add_widget(ref_card)

        # ---- 인용/효과 박스 카드 ----
        quote_card = ContentCard("인용/효과 박스")

        self.quote_style = quote_card.add_dropdown(
            "스타일", "quote_style",
            options=["없음", "왼쪽 테두리", "둥근 박스", "그림자 박스", "인용 기호"],
            default="왼쪽 테두리",
            help_text="특수 효과나 인용문 표시 스타일"
        )

        self.quote_bg = ColorPicker("#f9f9f9")
        quote_card.add_field("배경색", self.quote_bg)

        self.quote_border = ColorPicker("#e0e0e0")
        quote_card.add_field("테두리색", self.quote_border)

        section.add_widget(quote_card)

        # ---- 주사위 굴림 카드 ----
        dice_card = ContentCard("주사위 굴림 표시")

        self.dice_style = dice_card.add_dropdown(
            "스타일", "dice_style",
            options=["인라인", "별도 블록", "하이라이트", "숨김"],
            default="인라인",
            help_text="주사위 굴림 결과 표시 방식"
        )
        self.dice_style.currentTextChanged.connect(self._update_dice_preview)

        self.dice_icon = dice_card.add_checkbox(
            "주사위 아이콘 표시", "dice_icon", checked=True,
            help_text="주사위 굴림 앞에 \U0001f3b2 아이콘을 표시합니다."
        )
        self.dice_icon.stateChanged.connect(self._update_dice_preview)

        self.dice_color = ColorPicker("#0066cc")
        self.dice_color.color_changed.connect(self._update_dice_preview)
        dice_card.add_field("주사위 색상", self.dice_color)

        section.add_widget(dice_card)

        # ---- 페이지 여백 카드 ----
        margin_card = ContentCard("페이지 여백")

        margin_grid = QGridLayout()
        margin_grid.setSpacing(Spacing.MD)

        self.margin_top = QSpinBox()
        self.margin_top.setRange(0, 100)
        self.margin_top.setValue(20)
        self.margin_top.setSuffix(" px")
        margin_grid.addWidget(BodyLabel("상단"), 0, 0)
        margin_grid.addWidget(self.margin_top, 0, 1)

        self.margin_bottom = QSpinBox()
        self.margin_bottom.setRange(0, 100)
        self.margin_bottom.setValue(20)
        self.margin_bottom.setSuffix(" px")
        margin_grid.addWidget(BodyLabel("하단"), 0, 2)
        margin_grid.addWidget(self.margin_bottom, 0, 3)

        self.margin_left = QSpinBox()
        self.margin_left.setRange(0, 100)
        self.margin_left.setValue(15)
        self.margin_left.setSuffix(" px")
        margin_grid.addWidget(BodyLabel("좌측"), 1, 0)
        margin_grid.addWidget(self.margin_left, 1, 1)

        self.margin_right = QSpinBox()
        self.margin_right.setRange(0, 100)
        self.margin_right.setValue(15)
        self.margin_right.setSuffix(" px")
        margin_grid.addWidget(BodyLabel("우측"), 1, 2)
        margin_grid.addWidget(self.margin_right, 1, 3)

        margin_card.add_layout(margin_grid)

        section.add_widget(margin_card)

        # ---- 특수 효과 카드 ----
        effect_card = ContentCard("특수 효과")

        self.first_letter = effect_card.add_checkbox(
            "드롭캡 (첫 글자 크게)", "first_letter", checked=False,
            help_text="각 챕터의 첫 글자를 크게 표시합니다."
        )

        self.page_break = effect_card.add_checkbox(
            "챕터마다 페이지 나눔", "page_break", checked=True,
            help_text="각 챕터가 새 페이지에서 시작됩니다."
        )

        section.add_widget(effect_card)

        # ---- 미리보기 패널 ----
        preview_card = ContentCard("실시간 미리보기")
        self.preview_panel = DecorationPreview()
        preview_card.add_widget(self.preview_panel)
        section.add_widget(preview_card)

    # ==================================================================
    # Style section handlers
    # ==================================================================

    def _apply_preset(self, name: str):
        if name in Theme.PRESETS:
            preset = Theme.PRESETS[name]
        elif name in self._custom_theme_presets:
            preset = self._custom_theme_presets[name]
        else:
            return

        bg = preset.get('body_bg', '#ffffff')
        text = preset.get('body_text', '#1a1a1a')
        name_c = preset.get('name_color', '#2d2d2d')

        self.style_bg_picker.set_color(bg)
        self.style_text_picker.set_color(text)
        self.name_picker.set_color(name_c)

        self._update_preset_swatch(bg, text, name_c, name)
        self._on_style_changed()

    def _update_preset_swatch(self, bg: str, text: str, name_c: str, preset_name: str = ""):
        # Dynamic: 사용자 선택에 따라 변경됨
        self.swatch_bg.setStyleSheet(
            f"background: {bg}; border-radius: 6px; border: 1px solid rgba(128,128,128,0.3);"
        )
        self.swatch_text.setStyleSheet(
            f"background: {text}; border-radius: 6px; border: 1px solid rgba(128,128,128,0.3);"
        )
        self.swatch_name.setStyleSheet(
            f"background: {name_c}; border-radius: 6px; border: 1px solid rgba(128,128,128,0.3);"
        )
        is_builtin = preset_name in Theme.PRESETS
        tag = "[Built-in]" if is_builtin else "[Custom]"
        self.swatch_label.setText(f"{tag}  배경 / 텍스트 / 이름")

    def _save_current_as_preset(self):
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "테마 프리셋 저장", "새 프리셋 이름을 입력하세요:", text="내 테마"
        )
        if ok:
            name = name.strip()
            if not name:
                InfoBar.warning(
                    title="입력 오류", content="프리셋 이름을 입력하세요.",
                    parent=self, position=InfoBarPosition.TOP, duration=3000
                )
                return
            if name in Theme.PRESETS:
                InfoBar.warning(
                    title="중복",
                    content="내장 프리셋 이름과 동일합니다. 다른 이름을 사용하세요.",
                    parent=self, position=InfoBarPosition.TOP, duration=3000
                )
                return

            self._custom_theme_presets[name] = {
                'body_bg': self.style_bg_picker.get_color(),
                'body_text': self.style_text_picker.get_color(),
                'name_color': self.name_picker.get_color(),
            }
            self.settings['custom_theme_presets'] = self._custom_theme_presets
            self.config_manager.save_gui_settings(self.settings)

            self._refresh_preset_combo()
            self.preset_combo.setCurrentText(name)

            InfoBar.success(
                title="저장 완료", content=f"'{name}' 프리셋이 저장되었습니다.",
                parent=self, position=InfoBarPosition.TOP, duration=3000
            )

    def _delete_preset(self):
        name = self.preset_combo.currentText()
        if name in Theme.PRESETS:
            InfoBar.warning(
                title="삭제 불가", content="내장 프리셋은 삭제할 수 없습니다.",
                parent=self, position=InfoBarPosition.TOP, duration=3000
            )
            return
        if name not in self._custom_theme_presets:
            InfoBar.warning(
                title="알림", content="삭제할 사용자 프리셋을 선택하세요.",
                parent=self, position=InfoBarPosition.TOP, duration=3000
            )
            return

        w = MessageBox("프리셋 삭제", f"'{name}' 프리셋을 삭제하시겠습니까?", self.window())
        if w.exec():
            del self._custom_theme_presets[name]
            self.settings['custom_theme_presets'] = self._custom_theme_presets
            self.config_manager.save_gui_settings(self.settings)
            self._refresh_preset_combo()
            InfoBar.success(
                title="삭제 완료", content="프리셋이 삭제되었습니다.",
                parent=self, position=InfoBarPosition.TOP, duration=3000
            )

    def _refresh_preset_combo(self):
        current = self.preset_combo.currentText()
        self.preset_combo.clear()
        preset_options = list(Theme.PRESETS.keys()) + list(self._custom_theme_presets.keys())
        self.preset_combo.addItems(preset_options)
        if current in preset_options:
            self.preset_combo.setCurrentText(current)
        else:
            self.preset_combo.setCurrentText("Classic Light")

    def _on_separator_changed(self, text: str):
        self.custom_separator.setVisible(text == '직접 입력')
        self._on_style_changed()

    def _on_style_changed(self, *args):
        self.save_settings()
        self.settings_changed.emit()

    def _on_font_size_changed(self, value: int):
        self.size_spin.blockSignals(True)
        self.size_spin.setValue(value)
        self.size_spin.blockSignals(False)
        self.save_settings()
        self.update_inspector(font_size=value)
        self.settings_changed.emit()

    def _on_font_size_spin_changed(self, value: int):
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(value)
        self.size_slider.blockSignals(False)
        self.save_settings()
        self.update_inspector(font_size=value)
        self.settings_changed.emit()

    def _on_line_height_changed(self, value: int):
        self.height_spin.blockSignals(True)
        self.height_spin.setValue(value / 10)
        self.height_spin.blockSignals(False)
        self.save_settings()
        self.settings_changed.emit()

    def _on_line_height_spin_changed(self, value: float):
        self.height_slider.blockSignals(True)
        self.height_slider.setValue(int(value * 10))
        self.height_slider.blockSignals(False)
        self.save_settings()
        self.settings_changed.emit()

    def _on_palette_color_changed(self, key: str, color: str):
        if 'colors' not in self.settings:
            self.settings['colors'] = {}
        self.settings['colors'][key] = color
        self.config_manager.save_gui_settings(self.settings)
        self.settings_changed.emit()

    # Character color helpers
    def _add_character_color_row(self, name: str, color: str):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(Spacing.SM)

        name_label = BodyLabel(name)
        name_label.setMinimumWidth(80)
        name_label.setMaximumWidth(200)
        row_layout.addWidget(name_label)

        picker = ColorPicker(color)
        picker.color_changed.connect(lambda c, n=name: self._on_character_color_changed(n, c))
        row_layout.addWidget(picker)

        row_layout.addStretch()

        self.char_color_layout.addWidget(row_widget)
        self.character_color_widgets[name] = (row_widget, picker)

    def _on_character_color_changed(self, name: str, color: str):
        self.color_service.set_custom_color(name, color)
        self._save_character_colors()

    def _save_character_colors(self):
        self.settings['character_colors'] = self.color_service.get_all_colors()
        self.config_manager.save_gui_settings(self.settings)

    def _auto_assign_colors(self):
        from PySide6.QtWidgets import QFileDialog as _QFD
        from core.text_parser import parse_file
        from core.engine import load_config

        files, _ = _QFD.getOpenFileNames(
            self, "캐릭터 추출용 로그 파일 선택", "",
            "지원 형식 (*.html *.htm *.txt);;모든 파일 (*.*)"
        )
        if not files:
            return

        try:
            config = load_config()
            all_entries = []
            for file_path in files:
                entries = parse_file(file_path, config)
                all_entries.extend(entries)

            if not all_entries:
                InfoBar.warning(
                    title='알림', content='파일에서 캐릭터를 찾을 수 없습니다.',
                    parent=self, position=InfoBarPosition.TOP, duration=3000
                )
                return

            char_colors = self.color_service.auto_assign(all_entries)
            self._clear_character_color_ui()

            for name, color in char_colors.items():
                self._add_character_color_row(name, color)

            self._save_character_colors()
            InfoBar.success(
                title='완료',
                content=f'{len(char_colors)}명의 캐릭터에 색상이 할당되었습니다.',
                parent=self, position=InfoBarPosition.TOP, duration=3000
            )
        except Exception as e:
            InfoBar.error(
                title='오류', content=f'캐릭터 추출 실패: {str(e)}',
                parent=self, position=InfoBarPosition.TOP, duration=5000
            )

    def _reset_character_colors(self):
        w = MessageBox("확인", "모든 캐릭터 색상을 초기화하시겠습니까?", self.window())
        if w.exec():
            self.color_service.reset()
            self._clear_character_color_ui()
            self.settings['character_colors'] = {}
            self.config_manager.save_gui_settings(self.settings)

            no_char_label = BodyLabel(
                "아직 캐릭터가 없습니다. '파일에서 캐릭터 추출'을 사용하거나 변환 시 자동 할당됩니다."
            )
            no_char_label.setWordWrap(True)
            self.char_color_layout.addWidget(no_char_label)

    def _clear_character_color_ui(self):
        while self.char_color_layout.count():
            child = self.char_color_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.character_color_widgets.clear()

    def get_character_colors(self):
        return self.color_service.get_all_colors()

    # ==================================================================
    # Font section handlers
    # ==================================================================

    def _browse_font(self, font_type: str):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "폰트 파일 선택", "",
            "폰트 파일 (*.ttf *.otf *.woff *.woff2);;모든 파일 (*.*)"
        )
        if file_path:
            if font_type == 'body':
                self.embed_body_entry.setText(file_path)
            else:
                self.embed_name_entry.setText(file_path)
            self.save_settings()

    def _browse_docx_font(self, font_type: str):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "폰트 파일 선택", "",
            "폰트 파일 (*.ttf *.otf);;모든 파일 (*.*)"
        )
        if file_path:
            font_name = Path(file_path).stem
            for suffix in ['-Regular', '-Bold', '-Light', '-Medium', '-SemiBold', '_Regular']:
                font_name = font_name.replace(suffix, '')

            if font_type == 'body':
                self.docx_embed_body.setText(file_path)
                if font_name in self._system_fonts:
                    self.docx_body_combo.setCurrentText(font_name)
            else:
                self.docx_embed_name.setText(file_path)
                if font_name in self._system_fonts:
                    self.docx_name_combo.setCurrentText(font_name)
            self.save_settings()

    def _on_font_changed(self):
        body_font = self.epub_body_combo.currentText() or "나눔명조"
        self.update_inspector(font_family=body_font)
        self.save_settings()
        self.settings_changed.emit()

    # ==================================================================
    # Cover section handlers
    # ==================================================================

    def _on_cover_toggle(self, state: int):
        enabled = state == Qt.Checked
        self.title_on_cover.setEnabled(enabled)
        self.author_on_cover.setEnabled(enabled)
        self.save_settings()

    def _on_cover_bg_color_changed(self, color: str):
        self._update_cover_preview()
        self.save_settings()

    def _on_cover_title_color_changed(self, color: str):
        self._update_cover_preview()
        self.save_settings()

    def _update_cover_preview(self, *args):
        self.update_inspector(
            cover_title="TRPG 리플레이",
            cover_author="GM",
            cover_bg_color=self.cover_bg_picker.get_color(),
            cover_title_color=self.cover_title_color_picker.get_color()
        )

    def _browse_cover_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "표지 이미지 선택", "",
            "이미지 파일 (*.png *.jpg *.jpeg *.webp);;모든 파일 (*.*)"
        )
        if file_path:
            self.cover_image_entry.setText(file_path)
            self._load_cover_image_preview()
            self.save_settings()

    def _clear_cover_image(self):
        self.cover_image_entry.clear()
        self.cover_image_preview_label.setPixmap(QPixmap())
        self.cover_image_preview_label.setText("이미지 없음")
        self.save_settings()

    def _on_cover_image_path_changed(self, path: str):
        self._load_cover_image_preview()

    def _load_cover_image_preview(self):
        path = self.cover_image_entry.text()
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.cover_image_preview_label.setPixmap(scaled)
                self.cover_image_preview_label.setText("")
                return
        self.cover_image_preview_label.setPixmap(QPixmap())
        self.cover_image_preview_label.setText("이미지 없음")

    # ==================================================================
    # Decoration section handlers
    # ==================================================================

    def _on_divider_type_changed(self, type_name: str):
        self.text_card.setVisible(type_name == "텍스트/기호")
        self.image_card.setVisible(type_name == "이미지")
        self.line_card.setVisible(type_name == "선 스타일")
        self._update_deco_preview()

    def _upload_divider_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "",
            "이미지 (*.png *.jpg *.jpeg *.gif *.svg);;모든 파일 (*.*)"
        )
        if file_path:
            if self.divider_image_preview.set_image(path=file_path):
                self._update_deco_preview()
                InfoBar.success(
                    title='완료', content='이미지가 업로드되었습니다.',
                    parent=self, position=InfoBarPosition.TOP, duration=2000
                )
            else:
                InfoBar.error(
                    title='오류', content='이미지를 로드할 수 없습니다.',
                    parent=self, position=InfoBarPosition.TOP, duration=3000
                )

    def _clear_divider_image(self):
        self.divider_image_preview.clear_image()
        self._update_deco_preview()

    def _update_deco_preview(self, *args):
        divider_type = self.divider_type.currentText()
        if divider_type == "텍스트/기호":
            self.preview_panel.update_divider(
                text=self.divider_text.text() or "* * *",
                color=self.divider_color.get_color()
            )
        elif divider_type == "이미지":
            self.preview_panel.update_divider(
                image_data=self.divider_image_preview.get_image_data()
            )
        elif divider_type == "선 스타일":
            style_map = {
                "실선": "solid", "점선": "dotted",
                "파선": "dashed", "이중선": "double"
            }
            width = self.line_width.value()
            line_char = "\u2500" * (width // 10)
            self.preview_panel.update_divider(
                text=line_char,
                color=self.line_color.get_color(),
                style=style_map.get(self.line_style.currentText(), "solid")
            )
        else:
            self.preview_panel.update_divider(text="")

        self.settings_changed.emit()

    def _on_css_changed(self):
        self.settings_changed.emit()

    def _update_dice_preview(self, *args):
        self.preview_panel.update_dice(
            show_icon=self.dice_icon.isChecked(),
            color=self.dice_color.get_color(),
            style=self.dice_style.currentText()
        )
        self.settings_changed.emit()

    def _apply_css_preset(self, preset_name: str):
        presets = {
            "기본 스타일": (
                "/* 기본 스타일 */\n"
                ".dialogue {\n"
                "    margin-bottom: 0.8em;\n"
                "    line-height: 1.7;\n"
                "}\n\n"
                ".character-name {\n"
                "    font-weight: bold;\n"
                "    color: #333;\n"
                "}\n\n"
                ".scene-break {\n"
                "    text-align: center;\n"
                "    margin: 2em 0;\n"
                "    color: #888;\n"
                "}"
            ),
            "소설풍": (
                "/* 소설풍 스타일 */\n"
                "body {\n"
                "    font-family: 'Noto Serif KR', serif;\n"
                "    text-align: justify;\n"
                "}\n\n"
                ".dialogue {\n"
                "    text-indent: 1em;\n"
                "    margin-bottom: 0;\n"
                "}\n\n"
                ".dialogue-text::before {\n"
                "    content: '\u300c';\n"
                "}\n\n"
                ".dialogue-text::after {\n"
                "    content: '\u300d';\n"
                "}\n\n"
                ".narration {\n"
                "    font-style: italic;\n"
                "    color: #555;\n"
                "}\n\n"
                ".scene-break {\n"
                "    margin: 3em 0;\n"
                "    text-align: center;\n"
                "}\n\n"
                ".chapter-title {\n"
                "    font-size: 1.5em;\n"
                "    text-align: center;\n"
                "    margin: 2em 0;\n"
                "    border-bottom: 1px solid #ddd;\n"
                "    padding-bottom: 0.5em;\n"
                "}"
            ),
            "시나리오풍": (
                "/* 시나리오풍 스타일 */\n"
                ".dialogue {\n"
                "    margin-left: 2em;\n"
                "    margin-bottom: 1em;\n"
                "}\n\n"
                ".character-name {\n"
                "    display: block;\n"
                "    margin-left: -2em;\n"
                "    font-weight: bold;\n"
                "    margin-bottom: 0.3em;\n"
                "}\n\n"
                ".narration {\n"
                "    margin-left: 4em;\n"
                "    font-style: italic;\n"
                "    color: #666;\n"
                "}\n\n"
                ".scene-break {\n"
                "    border-top: 2px solid #333;\n"
                "    margin: 2em 0;\n"
                "    padding-top: 1em;\n"
                "}\n\n"
                ".chapter-title {\n"
                "    font-size: 1.3em;\n"
                "    text-transform: uppercase;\n"
                "    letter-spacing: 0.1em;\n"
                "}"
            ),
            "미니멀": (
                "/* 미니멀 스타일 */\n"
                "body {\n"
                "    max-width: 600px;\n"
                "    margin: 0 auto;\n"
                "}\n\n"
                ".dialogue, .narration {\n"
                "    margin-bottom: 1em;\n"
                "}\n\n"
                ".character-name {\n"
                "    font-weight: 500;\n"
                "}\n\n"
                ".scene-break {\n"
                "    height: 2em;\n"
                "}\n\n"
                ".chapter-title {\n"
                "    font-size: 1.2em;\n"
                "    margin: 1.5em 0;\n"
                "}"
            ),
            "다크 테마": (
                "/* 다크 테마 (EPUB 뷰어 지원 시) */\n"
                "@media (prefers-color-scheme: dark) {\n"
                "    body {\n"
                "        background: #1a1a1a;\n"
                "        color: #e0e0e0;\n"
                "    }\n\n"
                "    .character-name {\n"
                "        color: #fff;\n"
                "    }\n\n"
                "    .narration {\n"
                "        color: #aaa;\n"
                "    }\n\n"
                "    .scene-break {\n"
                "        color: #666;\n"
                "    }\n\n"
                "    .dice-roll {\n"
                "        color: #6db3f2;\n"
                "    }\n"
                "}"
            ),
        }

        if preset_name in presets:
            current = self.css_editor.toPlainText()
            if current:
                self.css_editor.setPlainText(current + "\n\n" + presets[preset_name])
            else:
                self.css_editor.setPlainText(presets[preset_name])

    # ==================================================================
    # save_settings / load_settings
    # ==================================================================

    def save_settings(self):
        """Save all settings from all four sections to AppState."""
        state = self.app_state
        _s = state.set

        # Style
        _s('style_body_bg', self.style_bg_picker.get_color())
        _s('style_body_text', self.style_text_picker.get_color())
        _s('style_font_size', self.size_slider.value())
        _s('style_line_height', self.height_slider.value() / 10)
        _s('style_name_color', self.name_picker.get_color())
        _s('style_name_bold', self.name_bold.isChecked())
        _s('style_separator', self.separator_combo.currentText())
        if self.separator_combo.currentText() == '직접 입력':
            _s('custom_separator_text', self.custom_separator.text())

        # Color palette
        _s('colors', {key: picker.get_color() for key, picker in self.color_pickers.items()})

        # Font
        _s('epub_body_font', self.epub_body_combo.currentText())
        _s('epub_name_font', self.epub_name_combo.currentText())
        _s('embed_body_font', self.embed_body_entry.text())
        _s('embed_name_font', self.embed_name_entry.text())
        _s('docx_body_font', self.docx_body_combo.currentText())
        _s('docx_name_font', self.docx_name_combo.currentText())
        _s('docx_embed_body', self.docx_embed_body.text())
        _s('docx_embed_name', self.docx_embed_name.text())
        _s('body_line_height', self.body_height_input.text())
        _s('dialogue_line_height', self.dialogue_height_input.text())
        _s('narration_line_height', self.narration_height_input.text())
        _s('base_font_size', self.base_font_size_input.text())

        # Cover
        _s('include_cover', self.include_cover.isChecked())
        _s('title_on_cover', self.title_on_cover.isChecked())
        _s('author_on_cover', self.author_on_cover.isChecked())
        _s('cover_subtitle', self.cover_subtitle.text())
        _s('cover_bg', self.cover_bg_picker.get_color())
        _s('cover_title_color', self.cover_title_color_picker.get_color())
        _s('cover_image', self.cover_image_entry.text())
        _s('include_toc', self.include_toc.isChecked())
        _s('toc_title', self.toc_title.text())

        # Decoration - Divider
        _s('divider_type', self.divider_type.currentText())
        _s('divider_text', self.divider_text.text())
        _s('divider_color', self.divider_color.get_color())
        _s('divider_image', self.divider_image_preview.get_image_data())
        _s('divider_img_height', self.divider_img_height.value())

        # Line style
        _s('line_style', self.line_style.currentText())
        _s('line_thickness', self.line_thickness.value())
        _s('line_color', self.line_color.get_color())
        _s('line_width', self.line_width.value())

        # Chapter header
        _s('header_style', self.header_style.currentText())
        _s('header_size', self.header_size.value())
        _s('header_color', self.header_color.get_color())
        _s('header_bold', self.header_bold.isChecked())
        _s('header_prefix', self.header_prefix.text())
        _s('header_suffix', self.header_suffix.text())
        _s('header_underline', self.header_underline.isChecked())
        _s('header_box', self.header_box.isChecked())
        _s('header_box_color', self.header_box_color.get_color())

        # CSS
        _s('custom_css', self.css_editor.toPlainText())

        # Misc decoration
        _s('quote_style', self.quote_style.currentText())
        _s('quote_bg', self.quote_bg.get_color())
        _s('quote_border', self.quote_border.get_color())
        _s('dice_style', self.dice_style.currentText())
        _s('dice_icon', self.dice_icon.isChecked())
        _s('dice_color', self.dice_color.get_color())

        # Margins
        _s('margin_top', self.margin_top.value())
        _s('margin_bottom', self.margin_bottom.value())
        _s('margin_left', self.margin_left.value())
        _s('margin_right', self.margin_right.value())

        # Effects
        _s('first_letter', self.first_letter.isChecked())
        _s('page_break', self.page_break.isChecked())

        state.save()

    def load_settings(self):
        """Load all settings for all four sections."""
        # ----------------------------------------------------------
        # Block signals during bulk load
        # ----------------------------------------------------------
        signal_widgets = [
            self.size_slider, self.size_spin, self.height_slider, self.height_spin,
            self.separator_combo, self.name_bold,
            self.epub_body_combo, self.epub_name_combo,
            self.docx_body_combo, self.docx_name_combo,
            self.include_cover, self.title_on_cover, self.author_on_cover,
            self.include_toc,
            self.divider_type, self.divider_text, self.line_style,
            self.line_thickness, self.line_width, self.line_width_spin,
            self.header_size, self.header_size_spin, self.header_style,
            self.header_bold, self.header_underline, self.header_box,
            self.quote_style, self.dice_style, self.dice_icon,
            self.margin_top, self.margin_bottom, self.margin_left, self.margin_right,
            self.first_letter, self.page_break, self.divider_img_height,
        ]
        for w in signal_widgets:
            w.blockSignals(True)

        _g = self.app_state.get

        # === Style ===
        bg = _g('style_body_bg', '#ffffff')
        text = _g('style_body_text', '#1a1a1a')
        name_c = _g('style_name_color', '#2d2d2d')

        self.style_bg_picker.set_color(bg)
        self.style_text_picker.set_color(text)
        self.name_picker.set_color(name_c)

        try:
            font_size = int(_g('style_font_size', 14))
        except (ValueError, TypeError):
            font_size = 14
        self.size_slider.setValue(font_size)
        self.size_spin.setValue(font_size)

        try:
            line_height = float(_g('style_line_height', 1.6))
        except (ValueError, TypeError):
            line_height = 1.6
        self.height_slider.setValue(int(line_height * 10))
        self.height_spin.setValue(line_height)

        self.name_bold.setChecked(_g('style_name_bold', True))
        self.safe_set_combo(self.separator_combo, _g('style_separator', '「 」 (꺾쇠)'))

        saved_sep = _g('style_separator', '「 」 (꺾쇠)')
        if saved_sep == '직접 입력':
            self.custom_separator.setVisible(True)
            self.custom_separator.setText(_g('custom_separator_text', ''))

        current_preset = self.preset_combo.currentText()
        self._update_preset_swatch(bg, text, name_c, current_preset)

        # Color palette
        colors = _g('colors', {})
        default_colors = {
            'text_color': '#1a1a1a', 'name_color': '#2d2d2d',
            'dice_color': '#888888', 'system_color': '#666666',
            'effect_bg': '#f5f5f5', 'effect_border': '#cccccc'
        }
        if isinstance(colors, dict):
            for key, picker in self.color_pickers.items():
                picker.set_color(colors.get(key, default_colors.get(key, '#000000')))

        # === Font ===
        epub_body = _g('epub_body_font', '나눔명조')
        if epub_body in self._system_fonts:
            self.epub_body_combo.setCurrentText(epub_body)

        epub_name = _g('epub_name_font', 'Pretendard')
        if epub_name in self._system_fonts:
            self.epub_name_combo.setCurrentText(epub_name)

        self.embed_body_entry.setText(_g('embed_body_font', ''))
        self.embed_name_entry.setText(_g('embed_name_font', ''))

        docx_body = _g('docx_body_font', '맑은 고딕')
        if docx_body in self._system_fonts:
            self.docx_body_combo.setCurrentText(docx_body)

        docx_name = _g('docx_name_font', '맑은 고딕')
        if docx_name in self._system_fonts:
            self.docx_name_combo.setCurrentText(docx_name)

        self.docx_embed_body.setText(_g('docx_embed_body', ''))
        self.docx_embed_name.setText(_g('docx_embed_name', ''))
        self.body_height_input.setText(str(_g('body_line_height', '1.6')))
        self.dialogue_height_input.setText(str(_g('dialogue_line_height', '1.5')))
        self.narration_height_input.setText(str(_g('narration_line_height', '1.7')))
        self.base_font_size_input.setText(str(_g('base_font_size', '1.0')))

        # === Cover ===
        self.include_cover.setChecked(_g('include_cover', True))
        self.title_on_cover.setChecked(_g('title_on_cover', True))
        self.author_on_cover.setChecked(_g('author_on_cover', True))
        self.cover_subtitle.setText(str(_g('cover_subtitle', '')))
        self.cover_bg_picker.set_color(_g('cover_bg', '#1a1a1a'))
        self.cover_title_color_picker.set_color(_g('cover_title_color', '#ffffff'))
        self.cover_image_entry.setText(str(_g('cover_image', '')))
        self.include_toc.setChecked(_g('include_toc', True))
        self.toc_title.setText(str(_g('toc_title', '목차')))

        # === Decoration ===
        self.safe_set_combo(self.divider_type, _g('divider_type', '텍스트/기호'))
        self.divider_text.setText(str(_g('divider_text', '* * *')))
        self.divider_color.set_color(_g('divider_color', '#888888'))

        divider_img = _g('divider_image', '')
        if divider_img:
            self.divider_image_preview.set_image(data=divider_img)

        self.divider_img_height.setValue(_g('divider_img_height', 40))

        # Line style
        self.safe_set_combo(self.line_style, _g('line_style', '실선'))
        self.line_thickness.setValue(_g('line_thickness', 1))
        self.line_color.set_color(_g('line_color', '#cccccc'))
        lw = _g('line_width', 60)
        self.line_width.setValue(lw)
        self.line_width_spin.setValue(lw)

        # Chapter header
        self.safe_set_combo(self.header_style, _g('header_style', '기본'))
        header_sz = _g('header_size', 20)
        self.header_size.setValue(header_sz)
        self.header_size_spin.setValue(header_sz)
        self.header_color.set_color(_g('header_color', '#1a1a1a'))
        self.header_bold.setChecked(_g('header_bold', True))
        self.header_prefix.setText(str(_g('header_prefix', '')))
        self.header_suffix.setText(str(_g('header_suffix', '')))
        self.header_underline.setChecked(_g('header_underline', False))
        self.header_box.setChecked(_g('header_box', False))
        self.header_box_color.set_color(_g('header_box_color', '#f5f5f5'))

        # CSS
        self.css_editor.setPlainText(str(_g('custom_css', '')))

        # Misc decoration
        self.safe_set_combo(self.quote_style, _g('quote_style', '왼쪽 테두리'))
        self.quote_bg.set_color(_g('quote_bg', '#f9f9f9'))
        self.quote_border.set_color(_g('quote_border', '#e0e0e0'))
        self.safe_set_combo(self.dice_style, _g('dice_style', '인라인'))
        self.dice_icon.setChecked(_g('dice_icon', True))
        self.dice_color.set_color(_g('dice_color', '#0066cc'))

        # Margins
        self.margin_top.setValue(_g('margin_top', 20))
        self.margin_bottom.setValue(_g('margin_bottom', 20))
        self.margin_left.setValue(_g('margin_left', 15))
        self.margin_right.setValue(_g('margin_right', 15))

        # Effects
        self.first_letter.setChecked(_g('first_letter', False))
        self.page_break.setChecked(_g('page_break', True))

        # ----------------------------------------------------------
        # Unblock signals
        # ----------------------------------------------------------
        for w in signal_widgets:
            w.blockSignals(False)

        # Initial UI state for decoration visibility
        self._on_divider_type_changed(self.divider_type.currentText())
        self._update_deco_preview()
        self._update_dice_preview()

        # Cover image preview
        self._load_cover_image_preview()
        self._update_cover_preview()
