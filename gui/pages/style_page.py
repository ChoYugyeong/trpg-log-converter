"""
TRPG Log Converter Pro - 스타일 페이지
시각적 스타일 설정 (색상, 테마 등)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from qfluentwidgets import (
    BodyLabel, PushButton, Slider, MessageBox, InfoBar, InfoBarPosition
)

from .base_page import BasePage
from ..components import ContentCard, ColorPicker
from ..styles import Theme
from core.services import CharacterColorService


class StylePage(BasePage):
    """스타일 페이지 - 색상 및 테마 설정"""

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self.color_service = CharacterColorService(
            self.settings.get('character_colors', {})
        )
        self.character_color_widgets = {}
        self._setup_page()
        self.load_settings()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("스타일 설정", "EPUB 출력물의 시각적 스타일을 설정합니다")

        # 테마 프리셋 카드
        preset_card = ContentCard("테마 프리셋", "미리 정의된 스타일 조합을 선택하거나 직접 만들 수 있습니다")

        # 내장 프리셋 + 사용자 프리셋 목록 구성
        self._custom_theme_presets = self.settings.get('custom_theme_presets', {})
        preset_options = list(Theme.PRESETS.keys()) + list(self._custom_theme_presets.keys())

        self.preset_combo = preset_card.add_dropdown(
            "프리셋", "preset",
            options=preset_options if preset_options else ["Classic Light"],
            default="Classic Light",
            help_text="미리 정의된 색상/스타일 조합. 선택 후 개별 설정 수정 가능."
        )
        self.preset_combo.currentTextChanged.connect(self._apply_preset)

        # 프리셋 미리보기 스와치
        self.preset_preview = QWidget()
        preview_layout = QHBoxLayout(self.preset_preview)
        preview_layout.setContentsMargins(0, 4, 0, 8)
        preview_layout.setSpacing(6)

        self.swatch_bg = QWidget()
        self.swatch_bg.setFixedSize(32, 32)
        self.swatch_bg.setStyleSheet("border-radius: 6px; border: 1px solid rgba(128,128,128,0.2);")
        preview_layout.addWidget(self.swatch_bg)

        self.swatch_text = QWidget()
        self.swatch_text.setFixedSize(32, 32)
        self.swatch_text.setStyleSheet("border-radius: 6px; border: 1px solid rgba(128,128,128,0.2);")
        preview_layout.addWidget(self.swatch_text)

        self.swatch_name = QWidget()
        self.swatch_name.setFixedSize(32, 32)
        self.swatch_name.setStyleSheet("border-radius: 6px; border: 1px solid rgba(128,128,128,0.2);")
        preview_layout.addWidget(self.swatch_name)

        self.swatch_label = BodyLabel("")
        self.swatch_label.setStyleSheet("font-size: 12px; color: palette(mid);")
        preview_layout.addWidget(self.swatch_label)

        preview_layout.addStretch()
        preset_card.add_widget(self.preset_preview)

        # 프리셋 관리 버튼
        preset_btn_row = QHBoxLayout()
        preset_btn_row.setSpacing(8)

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

        self.content_layout.addWidget(preset_card)

        # 본문 스타일 카드
        body_card = ContentCard("본문 스타일")

        # 배경색
        self.bg_picker = ColorPicker(self.settings.get('style_body_bg', '#ffffff'))
        self.bg_picker.color_changed.connect(self._on_style_changed)
        body_card.add_field("배경색", self.bg_picker, "style_body_bg",
                           help_text="EPUB 본문의 배경색입니다. 흰색(#ffffff) 또는 세피아(#f4ecd8) 권장.")

        # 텍스트 색상
        self.text_picker = ColorPicker(self.settings.get('style_body_text', '#1a1a1a'))
        self.text_picker.color_changed.connect(self._on_style_changed)
        body_card.add_field("텍스트", self.text_picker, "style_body_text",
                           help_text="본문 텍스트 색상입니다. 배경색과 대비가 좋은 색상을 선택하세요.")

        # 폰트 크기 슬라이더
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(12)

        self.size_slider = Slider(Qt.Horizontal)
        self.size_slider.setRange(10, 24)
        self.size_slider.setValue(int(self.settings.get('style_font_size', 14)))
        self.size_slider.valueChanged.connect(self._on_font_size_changed)
        size_layout.addWidget(self.size_slider, 1)

        self.size_label = BodyLabel(f"{self.size_slider.value()}px")
        self.size_label.setFixedWidth(50)
        size_layout.addWidget(self.size_label)

        body_card.add_field("폰트 크기", size_widget, "style_font_size",
                           help_text="EPUB 본문의 기본 폰트 크기입니다. 14-16px 권장.")

        # 줄 간격 슬라이더
        height_widget = QWidget()
        height_layout = QHBoxLayout(height_widget)
        height_layout.setContentsMargins(0, 0, 0, 0)
        height_layout.setSpacing(12)

        self.height_slider = Slider(Qt.Horizontal)
        self.height_slider.setRange(12, 24)  # 1.2 ~ 2.4
        self.height_slider.setValue(int(float(self.settings.get('style_line_height', 1.6)) * 10))
        self.height_slider.valueChanged.connect(self._on_line_height_changed)
        height_layout.addWidget(self.height_slider, 1)

        self.height_label = BodyLabel(f"{self.height_slider.value() / 10:.1f}")
        self.height_label.setFixedWidth(50)
        height_layout.addWidget(self.height_label)

        body_card.add_field("줄 간격", height_widget, "style_line_height",
                           help_text="줄과 줄 사이의 간격입니다. 1.6~1.8 권장.")

        self.content_layout.addWidget(body_card)

        # 캐릭터 스타일 카드
        char_card = ContentCard("캐릭터 이름 스타일")

        # 이름 색상
        self.name_picker = ColorPicker(self.settings.get('style_name_color', '#2d2d2d'))
        self.name_picker.color_changed.connect(self._on_style_changed)
        char_card.add_field("이름 색상", self.name_picker, "style_name_color",
                           help_text="캐릭터 이름의 기본 색상입니다. 캐릭터별 색상이 우선 적용됩니다.")

        # 이름 굵게
        self.name_bold = char_card.add_checkbox(
            "이름을 굵게 표시",
            "style_name_bold",
            checked=self.settings.get('style_name_bold', True),
            help_text="캐릭터 이름을 굵은 글씨로 표시합니다."
        )
        self.name_bold.stateChanged.connect(self._on_style_changed)

        # 대사 구분자
        self.separator_combo = char_card.add_dropdown(
            "대사 구분자", "style_separator",
            options=["「 」 (꺾쇠)", "\" \" (따옴표)", "' ' (작은따옴표)", "없음"],
            default=self.settings.get('style_separator', '「 」 (꺾쇠)'),
            help_text="대사를 감싸는 기호입니다. 일본식 꺾쇠「」가 가장 많이 사용됩니다."
        )
        self.separator_combo.currentTextChanged.connect(self._on_style_changed)

        self.content_layout.addWidget(char_card)

        # 캐릭터별 색상 카드
        char_color_card = ContentCard("캐릭터별 색상", "각 캐릭터에 고유한 색상 자동 할당")

        # 자동 할당 버튼
        auto_btn_row = QHBoxLayout()
        auto_btn_row.setSpacing(8)

        auto_assign_btn = PushButton("파일에서 캐릭터 추출")
        auto_assign_btn.clicked.connect(self._auto_assign_colors)
        auto_btn_row.addWidget(auto_assign_btn)

        reset_colors_btn = PushButton("색상 초기화")
        reset_colors_btn.clicked.connect(self._reset_character_colors)
        auto_btn_row.addWidget(reset_colors_btn)

        auto_btn_row.addStretch()
        char_color_card.add_layout(auto_btn_row)

        # 캐릭터 색상 목록
        self.char_color_container = QWidget()
        self.char_color_layout = QVBoxLayout(self.char_color_container)
        self.char_color_layout.setContentsMargins(0, 8, 0, 0)
        self.char_color_layout.setSpacing(8)

        # 기존 캐릭터 색상 로드
        char_colors = self.settings.get('character_colors', {})
        for name, color in char_colors.items():
            self._add_character_color_row(name, color)

        if not char_colors:
            no_char_label = BodyLabel("아직 캐릭터가 없습니다. '파일에서 캐릭터 추출'을 사용하거나 변환 시 자동 할당됩니다.")
            no_char_label.setWordWrap(True)
            self.char_color_layout.addWidget(no_char_label)

        char_color_card.add_widget(self.char_color_container)
        self.content_layout.addWidget(char_color_card)

        # 색상 팔레트 카드
        palette_card = ContentCard("색상 팔레트", "요소별 색상 설정")

        colors = self.settings.get('colors', {})

        # 색상 그리드
        color_grid = QGridLayout()
        color_grid.setSpacing(16)

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
            item_layout.setSpacing(8)

            lbl = BodyLabel(label)
            lbl.setFixedWidth(100)
            item_layout.addWidget(lbl)

            picker = ColorPicker(colors.get(key, default))
            picker.color_changed.connect(lambda c, k=key: self._on_color_changed(k, c))
            self.color_pickers[key] = picker
            item_layout.addWidget(picker)

            color_grid.addWidget(item_widget, row, col)

        palette_card.add_layout(color_grid)
        self.content_layout.addWidget(palette_card)

        self.add_stretch()

    def _apply_preset(self, name: str):
        """프리셋 적용"""
        # 내장 프리셋 확인
        if name in Theme.PRESETS:
            preset = Theme.PRESETS[name]
        # 사용자 프리셋 확인
        elif name in self._custom_theme_presets:
            preset = self._custom_theme_presets[name]
        else:
            return

        bg = preset.get('body_bg', '#ffffff')
        text = preset.get('body_text', '#1a1a1a')
        name_c = preset.get('name_color', '#2d2d2d')

        self.bg_picker.set_color(bg)
        self.text_picker.set_color(text)
        self.name_picker.set_color(name_c)

        # 스와치 업데이트
        self._update_preset_swatch(bg, text, name_c, name)

        self._on_style_changed()

    def _update_preset_swatch(self, bg: str, text: str, name_c: str, preset_name: str = ""):
        """프리셋 미리보기 스와치 업데이트"""
        self.swatch_bg.setStyleSheet(f"background: {bg}; border-radius: 6px; border: 1px solid rgba(128,128,128,0.3);")
        self.swatch_text.setStyleSheet(f"background: {text}; border-radius: 6px; border: 1px solid rgba(128,128,128,0.3);")
        self.swatch_name.setStyleSheet(f"background: {name_c}; border-radius: 6px; border: 1px solid rgba(128,128,128,0.3);")
        is_builtin = preset_name in Theme.PRESETS
        tag = "[Built-in]" if is_builtin else "[Custom]"
        self.swatch_label.setText(f"{tag}  배경 / 텍스트 / 이름")

    def _save_current_as_preset(self):
        """현재 스타일을 프리셋으로 저장"""
        from PySide6.QtWidgets import QInputDialog

        # 이름 입력 대화상자
        name, ok = QInputDialog.getText(
            self,
            "테마 프리셋 저장",
            "새 프리셋 이름을 입력하세요:",
            text="내 테마"
        )

        if ok:
            name = name.strip()
            if not name:
                InfoBar.warning(
                    title="입력 오류",
                    content="프리셋 이름을 입력하세요.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return

            if name in Theme.PRESETS:
                InfoBar.warning(
                    title="중복",
                    content="내장 프리셋 이름과 동일합니다. 다른 이름을 사용하세요.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return

            # 현재 스타일 저장
            self._custom_theme_presets[name] = {
                'body_bg': self.bg_picker.get_color(),
                'body_text': self.text_picker.get_color(),
                'name_color': self.name_picker.get_color(),
            }

            # 설정에 저장
            self.settings['custom_theme_presets'] = self._custom_theme_presets
            self.config_manager.save_gui_settings(self.settings)

            # 콤보박스 업데이트
            self._refresh_preset_combo()
            self.preset_combo.setCurrentText(name)

            InfoBar.success(
                title="저장 완료",
                content=f"'{name}' 프리셋이 저장되었습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _delete_preset(self):
        """선택된 프리셋 삭제"""
        name = self.preset_combo.currentText()

        if name in Theme.PRESETS:
            InfoBar.warning(
                title="삭제 불가",
                content="내장 프리셋은 삭제할 수 없습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        if name not in self._custom_theme_presets:
            InfoBar.warning(
                title="알림",
                content="삭제할 사용자 프리셋을 선택하세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        w = MessageBox(
            "프리셋 삭제",
            f"'{name}' 프리셋을 삭제하시겠습니까?",
            self.window()
        )

        if w.exec():
            del self._custom_theme_presets[name]
            self.settings['custom_theme_presets'] = self._custom_theme_presets
            self.config_manager.save_gui_settings(self.settings)

            self._refresh_preset_combo()

            InfoBar.success(
                title="삭제 완료",
                content="프리셋이 삭제되었습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _refresh_preset_combo(self):
        """프리셋 콤보박스 새로고침"""
        current = self.preset_combo.currentText()
        self.preset_combo.clear()

        preset_options = list(Theme.PRESETS.keys()) + list(self._custom_theme_presets.keys())
        self.preset_combo.addItems(preset_options)

        if current in preset_options:
            self.preset_combo.setCurrentText(current)
        else:
            self.preset_combo.setCurrentText("Classic Light")

    def _on_style_changed(self, *args):
        """스타일 변경 시"""
        self.save_settings()
        self.settings_changed.emit()

    def _on_font_size_changed(self, value: int):
        """폰트 크기 변경"""
        self.size_label.setText(f"{value}px")
        self.save_settings()
        self.update_inspector(font_size=value)
        self.settings_changed.emit()

    def _on_line_height_changed(self, value: int):
        """줄 간격 변경"""
        self.height_label.setText(f"{value / 10:.1f}")
        self.save_settings()
        self.settings_changed.emit()

    def _on_color_changed(self, key: str, color: str):
        """개별 색상 변경"""
        if 'colors' not in self.settings:
            self.settings['colors'] = {}
        self.settings['colors'][key] = color
        self.config_manager.save_gui_settings(self.settings)
        self.settings_changed.emit()

    def save_settings(self):
        """설정 저장"""
        self.settings['style_body_bg'] = self.bg_picker.get_color()
        self.settings['style_body_text'] = self.text_picker.get_color()
        self.settings['style_font_size'] = self.size_slider.value()
        self.settings['style_line_height'] = self.height_slider.value() / 10
        self.settings['style_name_color'] = self.name_picker.get_color()
        self.settings['style_name_bold'] = self.name_bold.isChecked()
        self.settings['style_separator'] = self.separator_combo.currentText()

        # 색상 팔레트
        if 'colors' not in self.settings:
            self.settings['colors'] = {}
        for key, picker in self.color_pickers.items():
            self.settings['colors'][key] = picker.get_color()

        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()

        bg = self.settings.get('style_body_bg', '#ffffff')
        text = self.settings.get('style_body_text', '#1a1a1a')
        name_c = self.settings.get('style_name_color', '#2d2d2d')

        self.bg_picker.set_color(bg)
        self.text_picker.set_color(text)
        self.size_slider.setValue(int(self.settings.get('style_font_size', 14)))
        self.height_slider.setValue(int(float(self.settings.get('style_line_height', 1.6)) * 10))
        self.name_picker.set_color(name_c)
        self.name_bold.setChecked(self.settings.get('style_name_bold', True))
        self.separator_combo.setCurrentText(self.settings.get('style_separator', '「 」 (꺾쇠)'))

        # 스와치 초기화
        current_preset = self.preset_combo.currentText()
        self._update_preset_swatch(bg, text, name_c, current_preset)

        colors = self.settings.get('colors', {})
        for key, picker in self.color_pickers.items():
            default_colors = {
                'text_color': '#1a1a1a', 'name_color': '#2d2d2d',
                'dice_color': '#888888', 'system_color': '#666666',
                'effect_bg': '#f5f5f5', 'effect_border': '#cccccc'
            }
            picker.set_color(colors.get(key, default_colors.get(key, '#000000')))

    def _add_character_color_row(self, name: str, color: str):
        """캐릭터 색상 행 추가"""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        # 캐릭터 이름
        name_label = BodyLabel(name)
        name_label.setMinimumWidth(80)
        name_label.setMaximumWidth(200)
        row_layout.addWidget(name_label)

        # 색상 선택
        picker = ColorPicker(color)
        picker.color_changed.connect(lambda c, n=name: self._on_character_color_changed(n, c))
        row_layout.addWidget(picker)

        row_layout.addStretch()

        self.char_color_layout.addWidget(row_widget)
        self.character_color_widgets[name] = (row_widget, picker)

    def _on_character_color_changed(self, name: str, color: str):
        """캐릭터 색상 변경"""
        self.color_service.set_custom_color(name, color)
        self._save_character_colors()

    def _save_character_colors(self):
        """캐릭터 색상 저장"""
        self.settings['character_colors'] = self.color_service.get_all_colors()
        self.config_manager.save_gui_settings(self.settings)

    def _auto_assign_colors(self):
        """파일에서 캐릭터 추출 및 색상 자동 할당"""
        from PySide6.QtWidgets import QFileDialog
        from core.text_parser import parse_file
        from core.engine import load_config

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "캐릭터 추출용 로그 파일 선택",
            "",
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
                    title='알림',
                    content='파일에서 캐릭터를 찾을 수 없습니다.',
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return

            # 색상 자동 할당
            char_colors = self.color_service.auto_assign(all_entries)

            # 기존 UI 제거
            self._clear_character_color_ui()

            # 새 캐릭터 색상 UI 추가
            for name, color in char_colors.items():
                self._add_character_color_row(name, color)

            self._save_character_colors()

            InfoBar.success(
                title='완료',
                content=f'{len(char_colors)}명의 캐릭터에 색상이 할당되었습니다.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

        except Exception as e:
            InfoBar.error(
                title='오류',
                content=f'캐릭터 추출 실패: {str(e)}',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )

    def _reset_character_colors(self):
        """캐릭터 색상 초기화"""
        w = MessageBox(
            "확인",
            "모든 캐릭터 색상을 초기화하시겠습니까?",
            self.window()
        )

        if w.exec():
            self.color_service.reset()
            self._clear_character_color_ui()
            self.settings['character_colors'] = {}
            self.config_manager.save_gui_settings(self.settings)

            # 안내 메시지 추가
            no_char_label = BodyLabel("아직 캐릭터가 없습니다. '파일에서 캐릭터 추출'을 사용하거나 변환 시 자동 할당됩니다.")
            no_char_label.setWordWrap(True)
            self.char_color_layout.addWidget(no_char_label)

    def _clear_character_color_ui(self):
        """캐릭터 색상 UI 제거"""
        while self.char_color_layout.count():
            child = self.char_color_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.character_color_widgets.clear()

    def get_character_colors(self):
        """캐릭터 색상 딕셔너리 반환"""
        return self.color_service.get_all_colors()
