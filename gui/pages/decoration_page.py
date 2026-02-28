"""
TRPG Log Converter Pro - 장식 요소 페이지
장면 구분선, 챕터 헤더, CSS 등 시각적 장식 요소 편집
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QFileDialog, QLabel, QSizePolicy, QTabWidget, QPlainTextEdit,
    QSpinBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QFont

from qfluentwidgets import (
    BodyLabel, PushButton, LineEdit, ComboBox, CheckBox,
    Slider, InfoBar, InfoBarPosition, CardWidget, TextEdit,
    TabWidget, PrimaryPushButton
)

from .base_page import BasePage
from ..components import ContentCard, ColorPicker
import os
import base64


class ImagePreview(QFrame):
    """이미지 미리보기 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ImagePreview")
        self.setMinimumSize(200, 60)
        self.setMaximumHeight(100)
        self.setStyleSheet("""
            #ImagePreview {
                background: palette(base);
                border: 2px dashed rgba(128, 128, 128, 0.3);
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.image_label = QLabel("이미지 없음")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("color: palette(mid); font-size: 12px;")
        layout.addWidget(self.image_label)

        self._image_path = ""
        self._image_data = ""  # base64 encoded

    def set_image(self, path: str = None, data: str = None):
        """이미지 설정 (파일 경로 또는 base64 데이터)"""
        if path and os.path.exists(path):
            self._image_path = path
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setText("")

                # base64로 변환하여 저장
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
        """이미지 제거"""
        self._image_path = ""
        self._image_data = ""
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("이미지 없음")

    def get_image_data(self) -> str:
        """base64 인코딩된 이미지 데이터 반환"""
        return self._image_data

    def get_image_path(self) -> str:
        """이미지 경로 반환"""
        return self._image_path


class DecorationPreview(QFrame):
    """장식 요소 실시간 미리보기"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DecorationPreview")
        self.setMinimumHeight(150)  # 높이 축소
        self.setMaximumHeight(180)  # 최대 높이 제한
        self.setStyleSheet("""
            #DecorationPreview {
                background: palette(base);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)  # 마진 축소
        layout.setSpacing(6)  # 간격 축소

        # 미리보기 제목
        title = BodyLabel("미리보기")
        title.setStyleSheet("color: palette(mid); font-size: 11px; font-weight: 600;")
        layout.addWidget(title)

        # 샘플 콘텐츠
        self.sample_before = QLabel("캐릭터A: 이전 대사입니다.")
        self.sample_before.setStyleSheet("font-size: 13px; color: palette(text);")
        self.sample_before.setWordWrap(True)
        layout.addWidget(self.sample_before)

        # 장식 요소 (구분선)
        self.divider_label = QLabel("─────────────")
        self.divider_label.setAlignment(Qt.AlignCenter)
        self.divider_label.setStyleSheet("font-size: 14px; color: palette(mid); padding: 8px 0;")
        self.divider_label.setWordWrap(True)
        layout.addWidget(self.divider_label)

        # 샘플 콘텐츠
        self.sample_after = QLabel("캐릭터B: 이후 대사입니다.")
        self.sample_after.setStyleSheet("font-size: 13px; color: palette(text);")
        self.sample_after.setWordWrap(True)
        layout.addWidget(self.sample_after)

        layout.addSpacing(8)

        # 주사위 굴림 미리보기
        self.dice_label = QLabel("🎲 1D100 → 42 (성공)")
        self.dice_label.setStyleSheet("font-size: 13px; color: #0066cc;")
        self.dice_label.setWordWrap(True)
        self.dice_label.setMinimumHeight(30)
        layout.addWidget(self.dice_label)

        layout.addStretch()

    def update_dice(self, show_icon: bool = True, color: str = "#0066cc",
                    style: str = "인라인"):
        """주사위 굴림 미리보기 업데이트"""
        icon = "🎲 " if show_icon else ""
        sample_text = f"{icon}1D100 → 42 (성공)"

        if style == "숨김":
            self.dice_label.setVisible(False)
        else:
            self.dice_label.setVisible(True)
            self.dice_label.setText(sample_text)

            if style == "별도 블록":
                self.dice_label.setStyleSheet(f"""
                    font-size: 13px;
                    color: {color};
                    background: rgba(0, 0, 0, 0.03);
                    padding: 6px 10px;
                    border-radius: 4px;
                """)
            elif style == "하이라이트":
                self.dice_label.setStyleSheet(f"""
                    font-size: 13px;
                    color: white;
                    background: {color};
                    padding: 4px 8px;
                    border-radius: 4px;
                """)
            else:  # 인라인
                self.dice_label.setStyleSheet(f"font-size: 13px; color: {color};")

    def update_divider(self, text: str = None, image_data: str = None,
                       color: str = "#999", style: str = "solid"):
        """구분선 미리보기 업데이트"""
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
            if style == "solid":
                border_style = "none"
            elif style == "dashed":
                border_style = "border-bottom: 2px dashed " + color + ";"
            elif style == "dotted":
                border_style = "border-bottom: 2px dotted " + color + ";"

            self.divider_label.setStyleSheet(f"""
                font-size: 14px;
                color: {color};
                padding: 8px 0;
                {border_style}
            """)


class DecorationPage(BasePage):
    """장식 요소 페이지 - 시각적 요소 커스터마이징"""

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._setup_page()
        self.load_settings()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("장식 요소", "장면 구분선, 헤더, CSS 등 시각적 요소를 편집합니다")

        # 탭 위젯으로 구성
        self.tab_widget = TabWidget()

        # 탭 1: 장면 구분선
        divider_tab = self._create_divider_tab()
        self.tab_widget.addTab(divider_tab, "장면 구분선")

        # 탭 2: 챕터 헤더
        header_tab = self._create_header_tab()
        self.tab_widget.addTab(header_tab, "챕터 헤더")

        # 탭 3: CSS 편집기
        css_tab = self._create_css_tab()
        self.tab_widget.addTab(css_tab, "CSS 편집")

        # 탭 4: 기타 장식
        misc_tab = self._create_misc_tab()
        self.tab_widget.addTab(misc_tab, "기타 장식")

        self.content_layout.addWidget(self.tab_widget)

        # 미리보기 패널
        preview_card = ContentCard("실시간 미리보기")
        self.preview_panel = DecorationPreview()
        preview_card.add_widget(self.preview_panel)
        self.content_layout.addWidget(preview_card)

        self.add_stretch()

    def _create_divider_tab(self) -> QWidget:
        """장면 구분선 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(16)

        # 구분선 유형 선택
        type_card = ContentCard("구분선 유형")

        self.divider_type = type_card.add_dropdown(
            "유형", "divider_type",
            options=["텍스트/기호", "이미지", "선 스타일", "사용 안 함"],
            default="텍스트/기호",
            help_text="장면 전환 시 표시되는 구분선의 유형을 선택합니다."
        )
        self.divider_type.currentTextChanged.connect(self._on_divider_type_changed)

        layout.addWidget(type_card)

        # 텍스트/기호 설정
        self.text_card = ContentCard("텍스트/기호 설정")

        self.divider_text = self.text_card.add_text_field(
            "구분 기호", "divider_text",
            placeholder="* * *",
            default="* * *",
            help_text="장면 구분에 사용할 텍스트나 기호입니다. 예: * * *, ───, ◆◆◆",
            clear_button=False
        )
        self.divider_text.textChanged.connect(self._update_preview)

        # 색상 선택
        self.divider_color = ColorPicker(self.settings.get('divider_color', '#888888'))
        self.divider_color.color_changed.connect(self._update_preview)
        self.text_card.add_field("색상", self.divider_color, "divider_color")

        layout.addWidget(self.text_card)

        # 이미지 설정
        self.image_card = ContentCard("이미지 설정")
        self.image_card.setVisible(False)

        # 이미지 미리보기
        self.divider_image_preview = ImagePreview()
        self.image_card.add_widget(self.divider_image_preview)

        # 이미지 버튼
        img_btn_row = QHBoxLayout()
        img_btn_row.setSpacing(8)

        upload_btn = PushButton("이미지 업로드")
        upload_btn.clicked.connect(self._upload_divider_image)
        img_btn_row.addWidget(upload_btn)

        clear_img_btn = PushButton("이미지 제거")
        clear_img_btn.clicked.connect(self._clear_divider_image)
        img_btn_row.addWidget(clear_img_btn)

        img_btn_row.addStretch()
        self.image_card.add_layout(img_btn_row)

        # 이미지 크기
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)

        self.divider_img_height = QSpinBox()
        self.divider_img_height.setRange(20, 200)
        self.divider_img_height.setValue(40)
        self.divider_img_height.setSuffix(" px")
        size_layout.addWidget(self.divider_img_height)
        size_layout.addStretch()

        self.image_card.add_field("이미지 높이", size_widget, help_text="구분선 이미지의 높이를 설정합니다.")

        layout.addWidget(self.image_card)

        # 선 스타일 설정
        self.line_card = ContentCard("선 스타일 설정")
        self.line_card.setVisible(False)

        self.line_style = self.line_card.add_dropdown(
            "선 종류", "line_style",
            options=["실선", "점선", "파선", "이중선"],
            default="실선",
            help_text="구분선의 선 스타일입니다."
        )
        self.line_style.currentTextChanged.connect(self._update_preview)

        # 선 두께
        thickness_widget = QWidget()
        thickness_layout = QHBoxLayout(thickness_widget)
        thickness_layout.setContentsMargins(0, 0, 0, 0)

        self.line_thickness = QSpinBox()
        self.line_thickness.setRange(1, 10)
        self.line_thickness.setValue(1)
        self.line_thickness.setSuffix(" px")
        self.line_thickness.valueChanged.connect(self._update_preview)
        thickness_layout.addWidget(self.line_thickness)
        thickness_layout.addStretch()

        self.line_card.add_field("선 두께", thickness_widget)

        # 선 색상
        self.line_color = ColorPicker("#cccccc")
        self.line_color.color_changed.connect(self._update_preview)
        self.line_card.add_field("선 색상", self.line_color)

        # 선 너비
        width_widget = QWidget()
        width_layout = QHBoxLayout(width_widget)
        width_layout.setContentsMargins(0, 0, 0, 0)

        self.line_width = Slider(Qt.Horizontal)
        self.line_width.setRange(20, 100)
        self.line_width.setValue(60)
        self.line_width.valueChanged.connect(self._update_preview)
        width_layout.addWidget(self.line_width, 1)

        self.line_width_label = BodyLabel("60%")
        self.line_width_label.setFixedWidth(40)
        width_layout.addWidget(self.line_width_label)

        self.line_card.add_field("선 너비", width_widget)

        layout.addWidget(self.line_card)

        layout.addStretch()
        return tab

    def _create_header_tab(self) -> QWidget:
        """챕터 헤더 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(16)

        # 챕터 헤더 스타일
        header_card = ContentCard("챕터 헤더 스타일")

        self.header_style = header_card.add_dropdown(
            "스타일", "header_style",
            options=["기본", "중앙 정렬", "장식 포함", "이미지 헤더", "사용 안 함"],
            default="기본",
            help_text="챕터/씬 제목의 표시 스타일입니다."
        )

        # 헤더 폰트 크기
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)

        self.header_size = Slider(Qt.Horizontal)
        self.header_size.setRange(14, 32)
        self.header_size.setValue(20)
        size_layout.addWidget(self.header_size, 1)

        self.header_size_label = BodyLabel("20px")
        self.header_size_label.setFixedWidth(50)
        self.header_size.valueChanged.connect(
            lambda v: self.header_size_label.setText(f"{v}px")
        )
        size_layout.addWidget(self.header_size_label)

        header_card.add_field("폰트 크기", size_widget)

        # 헤더 색상
        self.header_color = ColorPicker("#1a1a1a")
        header_card.add_field("헤더 색상", self.header_color)

        # 헤더 굵게
        self.header_bold = header_card.add_checkbox(
            "굵게 표시", "header_bold", checked=True
        )

        layout.addWidget(header_card)

        # 장식 요소
        deco_card = ContentCard("헤더 장식")

        # 전후 장식 기호
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

        # 밑줄 표시
        self.header_underline = deco_card.add_checkbox(
            "밑줄 표시", "header_underline", checked=False,
            help_text="챕터 제목 아래에 밑줄을 표시합니다."
        )

        # 배경 박스
        self.header_box = deco_card.add_checkbox(
            "배경 박스", "header_box", checked=False,
            help_text="챕터 제목에 배경 박스를 표시합니다."
        )

        self.header_box_color = ColorPicker("#f5f5f5")
        deco_card.add_field("박스 배경색", self.header_box_color)

        layout.addWidget(deco_card)

        layout.addStretch()
        return tab

    def _create_css_tab(self) -> QWidget:
        """CSS 편집기 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(16)

        # CSS 편집기 설명
        info_card = ContentCard("사용자 정의 CSS")

        info_label = BodyLabel(
            "고급 사용자를 위한 CSS 직접 편집 기능입니다.\n"
            "EPUB 출력에 적용될 추가 CSS 스타일을 입력하세요."
        )
        info_label.setWordWrap(True)
        info_card.add_widget(info_label)

        layout.addWidget(info_card)

        # CSS 편집기
        css_card = ContentCard("CSS 코드")

        self.css_editor = QPlainTextEdit()
        self.css_editor.setMinimumHeight(180)  # 높이 축소
        self.css_editor.setMaximumHeight(250)  # 최대 높이 제한
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
        import sys as _sys
        self.css_editor.setFont(QFont("Consolas" if _sys.platform == "win32" else "Menlo", 12))
        self.css_editor.setStyleSheet("""
            QPlainTextEdit {
                background: palette(base);
                color: palette(text);
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 8px;
                padding: 12px;
            }
        """)
        css_card.add_widget(self.css_editor)

        # CSS 변경 시 문서 미리보기 업데이트
        self.css_editor.textChanged.connect(self._on_css_changed)

        # CSS 프리셋
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)

        preset_label = BodyLabel("프리셋:")
        preset_row.addWidget(preset_label)

        self.css_preset_combo = ComboBox()
        self.css_preset_combo.addItems([
            "선택...",
            "기본 스타일",
            "소설풍",
            "시나리오풍",
            "미니멀",
            "다크 테마"
        ])
        self.css_preset_combo.currentTextChanged.connect(self._apply_css_preset)
        preset_row.addWidget(self.css_preset_combo)

        preset_row.addStretch()

        reset_btn = PushButton("초기화")
        reset_btn.clicked.connect(lambda: self.css_editor.clear())
        preset_row.addWidget(reset_btn)

        css_card.add_layout(preset_row)

        layout.addWidget(css_card)

        # CSS 클래스 참조
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

        layout.addWidget(ref_card)

        layout.addStretch()
        return tab

    def _create_misc_tab(self) -> QWidget:
        """기타 장식 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(16)

        # 인용 박스 스타일
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

        layout.addWidget(quote_card)

        # 주사위 굴림 스타일
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
            help_text="주사위 굴림 앞에 🎲 아이콘을 표시합니다."
        )
        self.dice_icon.stateChanged.connect(self._update_dice_preview)

        self.dice_color = ColorPicker("#0066cc")
        self.dice_color.color_changed.connect(self._update_dice_preview)
        dice_card.add_field("주사위 색상", self.dice_color)

        layout.addWidget(dice_card)

        # 페이지 여백
        margin_card = ContentCard("페이지 여백")

        margin_grid = QGridLayout()
        margin_grid.setSpacing(12)

        # 상단 여백
        self.margin_top = QSpinBox()
        self.margin_top.setRange(0, 100)
        self.margin_top.setValue(20)
        self.margin_top.setSuffix(" px")
        margin_grid.addWidget(BodyLabel("상단"), 0, 0)
        margin_grid.addWidget(self.margin_top, 0, 1)

        # 하단 여백
        self.margin_bottom = QSpinBox()
        self.margin_bottom.setRange(0, 100)
        self.margin_bottom.setValue(20)
        self.margin_bottom.setSuffix(" px")
        margin_grid.addWidget(BodyLabel("하단"), 0, 2)
        margin_grid.addWidget(self.margin_bottom, 0, 3)

        # 좌측 여백
        self.margin_left = QSpinBox()
        self.margin_left.setRange(0, 100)
        self.margin_left.setValue(15)
        self.margin_left.setSuffix(" px")
        margin_grid.addWidget(BodyLabel("좌측"), 1, 0)
        margin_grid.addWidget(self.margin_left, 1, 1)

        # 우측 여백
        self.margin_right = QSpinBox()
        self.margin_right.setRange(0, 100)
        self.margin_right.setValue(15)
        self.margin_right.setSuffix(" px")
        margin_grid.addWidget(BodyLabel("우측"), 1, 2)
        margin_grid.addWidget(self.margin_right, 1, 3)

        margin_card.add_layout(margin_grid)

        layout.addWidget(margin_card)

        # 특수 효과
        effect_card = ContentCard("특수 효과")

        self.first_letter = effect_card.add_checkbox(
            "드롭캡 (첫 글자 크게)", "first_letter", checked=False,
            help_text="각 챕터의 첫 글자를 크게 표시합니다."
        )

        self.page_break = effect_card.add_checkbox(
            "챕터마다 페이지 나눔", "page_break", checked=True,
            help_text="각 챕터가 새 페이지에서 시작됩니다."
        )

        layout.addWidget(effect_card)

        layout.addStretch()
        return tab

    def _on_divider_type_changed(self, type_name: str):
        """구분선 유형 변경 시"""
        self.text_card.setVisible(type_name == "텍스트/기호")
        self.image_card.setVisible(type_name == "이미지")
        self.line_card.setVisible(type_name == "선 스타일")
        self._update_preview()

    def _upload_divider_image(self):
        """구분선 이미지 업로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 선택",
            "",
            "이미지 (*.png *.jpg *.jpeg *.gif *.svg);;모든 파일 (*.*)"
        )

        if file_path:
            if self.divider_image_preview.set_image(path=file_path):
                self._update_preview()
                InfoBar.success(
                    title='완료',
                    content='이미지가 업로드되었습니다.',
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000
                )
            else:
                InfoBar.error(
                    title='오류',
                    content='이미지를 로드할 수 없습니다.',
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )

    def _clear_divider_image(self):
        """구분선 이미지 제거"""
        self.divider_image_preview.clear_image()
        self._update_preview()

    def _update_preview(self, *args):
        """미리보기 업데이트"""
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
            # 선 스타일로 미리보기 업데이트
            width = self.line_width.value()
            self.line_width_label.setText(f"{width}%")

            line_char = "─" * (width // 10)
            self.preview_panel.update_divider(
                text=line_char,
                color=self.line_color.get_color(),
                style=style_map.get(self.line_style.currentText(), "solid")
            )
        else:
            self.preview_panel.update_divider(text="")

        self.settings_changed.emit()

    def _on_css_changed(self):
        """CSS 편집기 내용 변경 시 문서 미리보기 업데이트"""
        self.settings_changed.emit()

    def _update_dice_preview(self, *args):
        """주사위 굴림 미리보기 업데이트"""
        self.preview_panel.update_dice(
            show_icon=self.dice_icon.isChecked(),
            color=self.dice_color.get_color(),
            style=self.dice_style.currentText()
        )
        self.settings_changed.emit()

    def _apply_css_preset(self, preset_name: str):
        """CSS 프리셋 적용"""
        presets = {
            "기본 스타일": """/* 기본 스타일 */
.dialogue {
    margin-bottom: 0.8em;
    line-height: 1.7;
}

.character-name {
    font-weight: bold;
    color: #333;
}

.scene-break {
    text-align: center;
    margin: 2em 0;
    color: #888;
}""",
            "소설풍": """/* 소설풍 스타일 */
body {
    font-family: 'Noto Serif KR', serif;
    text-align: justify;
}

.dialogue {
    text-indent: 1em;
    margin-bottom: 0;
}

.dialogue-text::before {
    content: '「';
}

.dialogue-text::after {
    content: '」';
}

.narration {
    font-style: italic;
    color: #555;
}

.scene-break {
    margin: 3em 0;
    text-align: center;
}

.chapter-title {
    font-size: 1.5em;
    text-align: center;
    margin: 2em 0;
    border-bottom: 1px solid #ddd;
    padding-bottom: 0.5em;
}""",
            "시나리오풍": """/* 시나리오풍 스타일 */
.dialogue {
    margin-left: 2em;
    margin-bottom: 1em;
}

.character-name {
    display: block;
    margin-left: -2em;
    font-weight: bold;
    margin-bottom: 0.3em;
}

.narration {
    margin-left: 4em;
    font-style: italic;
    color: #666;
}

.scene-break {
    border-top: 2px solid #333;
    margin: 2em 0;
    padding-top: 1em;
}

.chapter-title {
    font-size: 1.3em;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}""",
            "미니멀": """/* 미니멀 스타일 */
body {
    max-width: 600px;
    margin: 0 auto;
}

.dialogue, .narration {
    margin-bottom: 1em;
}

.character-name {
    font-weight: 500;
}

.scene-break {
    height: 2em;
}

.chapter-title {
    font-size: 1.2em;
    margin: 1.5em 0;
}""",
            "다크 테마": """/* 다크 테마 (EPUB 뷰어 지원 시) */
@media (prefers-color-scheme: dark) {
    body {
        background: #1a1a1a;
        color: #e0e0e0;
    }

    .character-name {
        color: #fff;
    }

    .narration {
        color: #aaa;
    }

    .scene-break {
        color: #666;
    }

    .dice-roll {
        color: #6db3f2;
    }
}"""
        }

        if preset_name in presets:
            current = self.css_editor.toPlainText()
            if current:
                self.css_editor.setPlainText(current + "\n\n" + presets[preset_name])
            else:
                self.css_editor.setPlainText(presets[preset_name])

    def save_settings(self):
        """설정 저장"""
        # 장면 구분선 설정
        self.settings['divider_type'] = self.divider_type.currentText()
        self.settings['divider_text'] = self.divider_text.text()
        self.settings['divider_color'] = self.divider_color.get_color()
        self.settings['divider_image'] = self.divider_image_preview.get_image_data()
        self.settings['divider_img_height'] = self.divider_img_height.value()

        # 선 스타일
        self.settings['line_style'] = self.line_style.currentText()
        self.settings['line_thickness'] = self.line_thickness.value()
        self.settings['line_color'] = self.line_color.get_color()
        self.settings['line_width'] = self.line_width.value()

        # 챕터 헤더 설정
        self.settings['header_style'] = self.header_style.currentText()
        self.settings['header_size'] = self.header_size.value()
        self.settings['header_color'] = self.header_color.get_color()
        self.settings['header_bold'] = self.header_bold.isChecked()
        self.settings['header_prefix'] = self.header_prefix.text()
        self.settings['header_suffix'] = self.header_suffix.text()
        self.settings['header_underline'] = self.header_underline.isChecked()
        self.settings['header_box'] = self.header_box.isChecked()
        self.settings['header_box_color'] = self.header_box_color.get_color()

        # CSS
        self.settings['custom_css'] = self.css_editor.toPlainText()

        # 기타 장식
        self.settings['quote_style'] = self.quote_style.currentText()
        self.settings['quote_bg'] = self.quote_bg.get_color()
        self.settings['quote_border'] = self.quote_border.get_color()
        self.settings['dice_style'] = self.dice_style.currentText()
        self.settings['dice_icon'] = self.dice_icon.isChecked()
        self.settings['dice_color'] = self.dice_color.get_color()

        # 여백
        self.settings['margin_top'] = self.margin_top.value()
        self.settings['margin_bottom'] = self.margin_bottom.value()
        self.settings['margin_left'] = self.margin_left.value()
        self.settings['margin_right'] = self.margin_right.value()

        # 특수 효과
        self.settings['first_letter'] = self.first_letter.isChecked()
        self.settings['page_break'] = self.page_break.isChecked()

        self.config_manager.save_gui_settings(self.settings)
        self.settings_changed.emit()

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()

        # 장면 구분선
        self.divider_type.setCurrentText(self.settings.get('divider_type', '텍스트/기호'))
        self.divider_text.setText(self.settings.get('divider_text', '* * *'))
        self.divider_color.set_color(self.settings.get('divider_color', '#888888'))

        if self.settings.get('divider_image'):
            self.divider_image_preview.set_image(data=self.settings.get('divider_image'))

        self.divider_img_height.setValue(self.settings.get('divider_img_height', 40))

        # 선 스타일
        self.line_style.setCurrentText(self.settings.get('line_style', '실선'))
        self.line_thickness.setValue(self.settings.get('line_thickness', 1))
        self.line_color.set_color(self.settings.get('line_color', '#cccccc'))
        self.line_width.setValue(self.settings.get('line_width', 60))

        # 챕터 헤더
        self.header_style.setCurrentText(self.settings.get('header_style', '기본'))
        self.header_size.setValue(self.settings.get('header_size', 20))
        self.header_color.set_color(self.settings.get('header_color', '#1a1a1a'))
        self.header_bold.setChecked(self.settings.get('header_bold', True))
        self.header_prefix.setText(self.settings.get('header_prefix', ''))
        self.header_suffix.setText(self.settings.get('header_suffix', ''))
        self.header_underline.setChecked(self.settings.get('header_underline', False))
        self.header_box.setChecked(self.settings.get('header_box', False))
        self.header_box_color.set_color(self.settings.get('header_box_color', '#f5f5f5'))

        # CSS
        self.css_editor.setPlainText(self.settings.get('custom_css', ''))

        # 기타 장식
        self.quote_style.setCurrentText(self.settings.get('quote_style', '왼쪽 테두리'))
        self.quote_bg.set_color(self.settings.get('quote_bg', '#f9f9f9'))
        self.quote_border.set_color(self.settings.get('quote_border', '#e0e0e0'))
        self.dice_style.setCurrentText(self.settings.get('dice_style', '인라인'))
        self.dice_icon.setChecked(self.settings.get('dice_icon', True))
        self.dice_color.set_color(self.settings.get('dice_color', '#0066cc'))

        # 여백
        self.margin_top.setValue(self.settings.get('margin_top', 20))
        self.margin_bottom.setValue(self.settings.get('margin_bottom', 20))
        self.margin_left.setValue(self.settings.get('margin_left', 15))
        self.margin_right.setValue(self.settings.get('margin_right', 15))

        # 특수 효과
        self.first_letter.setChecked(self.settings.get('first_letter', False))
        self.page_break.setChecked(self.settings.get('page_break', True))

        # 초기 UI 상태 설정
        self._on_divider_type_changed(self.divider_type.currentText())
        self._update_preview()
        self._update_dice_preview()
