"""
TRPG Log Converter Pro - 미리보기 컴포넌트
InspectorBar, CoverPreview, DocumentPreview 등
"""

from PySide6.QtWidgets import (
    QFrame, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPlainTextEdit, QSizePolicy, QScrollArea, QTextEdit,
    QPushButton, QSpinBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextDocument, QColor


class InspectorBar(QFrame):
    """하단 인스펙터 바 - 3열 미리보기"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InspectorBar")
        self.setMinimumHeight(140)  # 최소 높이 축소
        self.setMaximumHeight(180)  # 최대 높이 축소

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)  # 마진 축소
        layout.setSpacing(16)  # 간격 축소

        # 폰트 미리보기
        self.font_section = self._create_section("폰트")
        self.font_preview_label = QLabel("가나다라마바사\nABC abc 123")
        self.font_preview_label.setObjectName("FontPreviewLabel")
        self.font_section.layout().addWidget(self.font_preview_label, 1)
        layout.addWidget(self.font_section, 1)

        # 콘텐츠 미리보기
        self.content_section = self._create_section("콘텐츠")
        self.content_preview = QPlainTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setPlaceholderText("파일을 추가하면 미리보기가 표시됩니다")
        self.content_preview.setMaximumHeight(100)
        self.content_preview.setObjectName("ContentPreviewText")
        self.content_section.layout().addWidget(self.content_preview, 1)
        layout.addWidget(self.content_section, 2)

        # 표지 미리보기
        self.cover_section = self._create_section("표지")
        self.cover_preview = CoverPreview()
        self.cover_section.layout().addWidget(self.cover_preview, 1)
        layout.addWidget(self.cover_section, 1)

    def _create_section(self, title: str) -> QFrame:
        """미리보기 섹션 생성"""
        frame = QFrame()
        frame.setObjectName("PreviewSection")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        header = QLabel(title)
        header.setObjectName("PreviewTitle")
        header.setMinimumHeight(22)
        layout.addWidget(header)

        return frame

    def update_font_preview(self, font_family: str = None, font_size: int = None, sample_text: str = None):
        """폰트 미리보기 업데이트"""
        if sample_text:
            self.font_preview_label.setText(sample_text)

        # Use QFont for font family/size changes (preserves palette colors)
        if font_family or font_size:
            font = self.font_preview_label.font()
            if font_family:
                font.setFamily(font_family)
            if font_size:
                font.setPointSize(font_size)
            self.font_preview_label.setFont(font)

    def update_content_preview(self, text: str):
        """콘텐츠 미리보기 업데이트"""
        # 첫 5줄만 표시
        lines = text.split('\n')[:5]
        preview_text = '\n'.join(lines)
        if len(text.split('\n')) > 5:
            preview_text += '\n...'
        self.content_preview.setPlainText(preview_text)

    def update_cover_preview(self, title: str = None, author: str = None,
                             bg_color: str = None, title_color: str = None):
        """표지 미리보기 업데이트"""
        self.cover_preview.update_preview(title, author, bg_color, title_color)

    def set_visible(self, visible: bool):
        """인스펙터 바 표시/숨김"""
        self.setVisible(visible)
        if visible:
            self.setFixedHeight(160)
        else:
            self.setFixedHeight(0)


class CoverPreview(QFrame):
    """표지 미리보기 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CoverPreview")

        self._bg_color = "#1a1a1a"
        self._title_color = "#ffffff"
        self._title = "TRPG 리플레이"
        self._author = "GM"

        self.setMinimumSize(80, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # 제목
        self.title_label = QLabel(self._title)
        self.title_label.setObjectName("CoverPreviewTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        layout.addStretch()

        # 저자
        self.author_label = QLabel(self._author)
        self.author_label.setObjectName("CoverPreviewAuthor")
        self.author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.author_label)

        self._update_style()

    def update_preview(self, title: str = None, author: str = None,
                       bg_color: str = None, title_color: str = None):
        """미리보기 업데이트"""
        if title is not None:
            self._title = title
            self.title_label.setText(title)

        if author is not None:
            self._author = author
            self.author_label.setText(author)

        if bg_color is not None:
            self._bg_color = bg_color

        if title_color is not None:
            self._title_color = title_color

        self._update_style()

    def _update_style(self):
        """스타일 업데이트 - 표지 색상은 사용자 선택값 사용"""
        self.setStyleSheet(f"""
            #CoverPreview {{
                background: {self._bg_color};
                border-radius: 4px;
            }}
            #CoverPreviewTitle {{
                font-size: 11px;
                font-weight: 600;
                color: {self._title_color};
            }}
            #CoverPreviewAuthor {{
                font-size: 9px;
                color: {self._title_color};
            }}
        """)


class DocumentPreview(QFrame):
    """문서 미리보기 패널 - 엔터프라이즈급 PDF 뷰어 스타일"""

    ENTRIES_PER_PAGE = 30  # 페이지당 항목 수

    # 문서 형식별 비율 (너비, 높이) - mm 단위
    DOCUMENT_FORMATS = {
        "A4 (210×297mm)": (210, 297),
        "A5 (148×210mm)": (148, 210),
        "B5 (182×257mm)": (182, 257),
        "신국판 (152×225mm)": (152, 225),
        "국판 (148×210mm)": (148, 210),
        "46배판 (128×188mm)": (128, 188),
        "문고판 (105×148mm)": (105, 148),
        "Letter (216×279mm)": (216, 279),
        "EPUB (6×9)": (152, 229),
        "EPUB (5×8)": (127, 203),
    }

    # 줌 프리셋
    ZOOM_PRESETS = [50, 75, 90, 100, 125, 150, 200]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DocumentPreview")
        self.setMinimumWidth(280)

        self._entries = []
        self._settings = {}
        self._current_page = 1
        self._total_pages = 1
        self._current_format = "A5 (148×210mm)"
        self._page_width = 240
        self._zoom_level = 100
        self._fit_mode = "width"  # width, height, page

        self._setup_ui()

    def _setup_ui(self):
        """UI 구성 - 엔터프라이즈급 도구 모음"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === 상단 툴바 ===
        toolbar = QFrame()
        toolbar.setObjectName("PreviewToolbar")
        toolbar.setStyleSheet("""
            #PreviewToolbar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 palette(window), stop:1 rgba(128, 128, 128, 0.05));
                border-bottom: 1px solid rgba(128, 128, 128, 0.15);
            }
        """)

        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)

        # 1행: 제목 + 판형
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        title = QLabel("미리보기")
        title.setStyleSheet("font-size: 13px; font-weight: 600; padding: 0; margin: 0; min-height: 0;")
        row1.addWidget(title)
        row1.addStretch()

        self.format_combo = QComboBox()
        self.format_combo.addItems(list(self.DOCUMENT_FORMATS.keys()))
        self.format_combo.setCurrentText(self._current_format)
        self.format_combo.setMaximumWidth(160)
        self.format_combo.setStyleSheet("""
            QComboBox {
                background: palette(base);
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down { border: none; width: 18px; }
        """)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        row1.addWidget(self.format_combo)

        toolbar_layout.addLayout(row1)

        # 2행: 줌 + 페이지
        row2 = QHBoxLayout()
        row2.setSpacing(4)

        # 축소
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedSize(26, 26)
        self.zoom_out_btn.setCursor(Qt.PointingHandCursor)
        self.zoom_out_btn.setStyleSheet(self._get_tool_button_style())
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        row2.addWidget(self.zoom_out_btn)

        # 줌 레벨
        self.zoom_combo = QComboBox()
        for z in self.ZOOM_PRESETS:
            self.zoom_combo.addItem(f"{z}%", z)
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.setFixedWidth(62)
        self.zoom_combo.setStyleSheet("""
            QComboBox { background: transparent; border: none; font-size: 11px; font-weight: 500; padding: 2px 4px; }
            QComboBox::drop-down { border: none; width: 14px; }
        """)
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_preset_changed)
        row2.addWidget(self.zoom_combo)

        # 확대
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(26, 26)
        self.zoom_in_btn.setCursor(Qt.PointingHandCursor)
        self.zoom_in_btn.setStyleSheet(self._get_tool_button_style())
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        row2.addWidget(self.zoom_in_btn)

        row2.addStretch()

        # 이전 페이지
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(26, 26)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet(self._get_nav_button_style())
        self.prev_btn.clicked.connect(self._prev_page)
        row2.addWidget(self.prev_btn)

        # 페이지 번호
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setFixedSize(44, 26)
        self.page_spin.setAlignment(Qt.AlignCenter)
        self.page_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.page_spin.setStyleSheet("""
            QSpinBox {
                background: palette(base);
                border: 1px solid rgba(0, 122, 255, 0.3);
                border-radius: 4px;
                padding: 2px;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        self.page_spin.valueChanged.connect(self._on_page_changed)
        row2.addWidget(self.page_spin)

        self.page_label = QLabel("/ 1")
        self.page_label.setStyleSheet("color: palette(dark); font-size: 11px; font-weight: 500; padding: 0; margin: 0; min-height: 0;")
        row2.addWidget(self.page_label)

        # 다음 페이지
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(26, 26)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet(self._get_nav_button_style())
        self.next_btn.clicked.connect(self._next_page)
        row2.addWidget(self.next_btn)

        toolbar_layout.addLayout(row2)

        layout.addWidget(toolbar)

        # 맞춤 버튼 (숨김 - 기능은 유지)
        self.fit_width_btn = QPushButton()
        self.fit_width_btn.hide()
        self.fit_page_btn = QPushButton()
        self.fit_page_btn.hide()

        # 문서 영역 설정
        self._setup_document_area(layout)

        # 줌 레벨 초기화
        self.zoom_combo.setCurrentText(f"{self._zoom_level}%")

    def _get_tool_button_style(self, active=False):
        """도구 버튼 스타일"""
        if active:
            return """
                QPushButton {
                    background: rgba(0, 122, 255, 0.15);
                    border: none; border-radius: 4px; padding: 0;
                    font-size: 13px; font-weight: bold; color: #007AFF;
                }
                QPushButton:hover { background: rgba(0, 122, 255, 0.25); }
            """
        return """
            QPushButton {
                background: transparent;
                border: none; border-radius: 4px; padding: 0;
                font-size: 13px; font-weight: bold; color: palette(dark);
            }
            QPushButton:hover { background: rgba(128, 128, 128, 0.15); }
        """

    def _get_nav_button_style(self):
        """네비게이션 버튼 스타일"""
        return """
            QPushButton {
                background: rgba(0, 122, 255, 0.1);
                border: none; border-radius: 4px; padding: 0;
                font-size: 11px; color: #007AFF;
            }
            QPushButton:hover { background: rgba(0, 122, 255, 0.2); }
            QPushButton:disabled { background: transparent; color: rgba(128,128,128,0.4); }
        """

    def _on_zoom_preset_changed(self, index):
        """줌 프리셋 변경"""
        zoom = self.zoom_combo.currentData()
        if zoom:
            self._zoom_level = zoom
            self._update_page_size()

    def _set_fit_mode(self, mode: str):
        """맞춤 모드 설정"""
        self._fit_mode = mode
        # 버튼 스타일 업데이트
        self.fit_width_btn.setStyleSheet(self._get_tool_button_style(active=(mode == "width")))
        self.fit_page_btn.setStyleSheet(self._get_tool_button_style(active=(mode == "page")))

        # 맞춤 모드에 따라 줌 레벨 조정
        if mode == "width":
            self._zoom_level = 100
            self.zoom_combo.setCurrentText("100%")
        elif mode == "page":
            self._zoom_level = 75
            self.zoom_combo.setCurrentText("75%")

        self._update_page_size()

    def _setup_document_area(self, layout):
        """문서 영역 설정 - _setup_ui에서 호출"""
        # 문서 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: rgba(128, 128, 128, 0.15);
            }
        """)

        # 페이지 컨테이너
        self.page_container = QWidget()
        self.page_container.setStyleSheet("background: rgba(128, 128, 128, 0.15);")
        page_layout = QVBoxLayout(self.page_container)
        page_layout.setContentsMargins(16, 16, 16, 16)
        page_layout.setSpacing(16)
        page_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # 페이지 (문서 내용) - 실제 문서 비율 적용
        self.page_widget = QFrame()
        self.page_widget.setObjectName("PreviewPage")
        self._update_page_size()
        self.page_widget.setStyleSheet("""
            #PreviewPage {
                background: palette(base);
                border-radius: 6px;
                border: none;
            }
        """)
        # 그림자 효과
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self.page_widget)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.page_widget.setGraphicsEffect(shadow)

        page_inner_layout = QVBoxLayout(self.page_widget)
        page_inner_layout.setContentsMargins(28, 36, 28, 36)
        page_inner_layout.setSpacing(12)

        # 문서 내용
        self.content_view = QTextEdit()
        self.content_view.setReadOnly(True)
        self.content_view.setFrameShape(QFrame.NoFrame)
        self.content_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_view.setStyleSheet("""
            QTextEdit {
                background: palette(base);
                color: palette(text);
                font-size: 10px;
                line-height: 1.5;
            }
        """)

        # 기본 안내 텍스트
        self._show_placeholder()

        page_inner_layout.addWidget(self.content_view)

        page_layout.addWidget(self.page_widget)

        scroll.setWidget(self.page_container)
        layout.addWidget(scroll)

    def _show_placeholder(self):
        """플레이스홀더 표시"""
        placeholder_html = """
        <div style="text-align: center; color: gray; padding: 40px 20px;">
            <p style="font-size: 14px; margin-bottom: 8px; color: silver;">---</p>
            <p style="font-size: 12px;">파일을 추가하고 설정을 변경하면<br>여기에 미리보기가 표시됩니다</p>
        </div>
        """
        self.content_view.setHtml(placeholder_html)

    def _prev_page(self):
        """이전 페이지"""
        if self._current_page > 1:
            self._current_page -= 1
            self.page_spin.setValue(self._current_page)

    def _next_page(self):
        """다음 페이지"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self.page_spin.setValue(self._current_page)

    def _on_page_changed(self, value):
        """페이지 번호 변경됨"""
        self._current_page = value
        self._update_nav_buttons()
        self._render_document()

    def _update_nav_buttons(self):
        """네비게이션 버튼 상태 업데이트"""
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)

    def _on_format_changed(self, format_name: str):
        """문서 형식 변경"""
        self._current_format = format_name
        self._update_page_size()

    def _zoom_in(self):
        """확대"""
        # 다음 프리셋으로 이동
        current_idx = self.zoom_combo.currentIndex()
        if current_idx < self.zoom_combo.count() - 1:
            self.zoom_combo.setCurrentIndex(current_idx + 1)

    def _zoom_out(self):
        """축소"""
        # 이전 프리셋으로 이동
        current_idx = self.zoom_combo.currentIndex()
        if current_idx > 0:
            self.zoom_combo.setCurrentIndex(current_idx - 1)

    def _update_page_size(self):
        """문서 형식에 맞게 페이지 크기 업데이트"""
        if self._current_format not in self.DOCUMENT_FORMATS:
            return

        width, height = self.DOCUMENT_FORMATS[self._current_format]
        aspect_ratio = height / width

        # 컨테이너 너비 기준으로 계산 (패딩 48px 제외 - 양쪽 24px씩)
        container_width = self.width() - 48 if self.width() > 150 else 250

        # 100%일 때 컨테이너에 정확히 맞추기 (오버플로 방지)
        if self._zoom_level == 100:
            # 100%에서는 컨테이너 너비의 95%로 맞춤 (스크롤바 공간 확보)
            base_width = int(container_width * 0.95)
        else:
            # 다른 줌 레벨에서는 비율 계산
            base_width = int(container_width * self._zoom_level / 100)

        base_width = max(180, min(base_width, 650))  # 최소 180, 최대 650
        calculated_height = int(base_width * aspect_ratio)

        # page_widget이 있을 때만 크기 설정
        if hasattr(self, 'page_widget'):
            self.page_widget.setFixedWidth(base_width)
            self.page_widget.setMinimumHeight(calculated_height)
            self.page_widget.setMaximumHeight(calculated_height + 150)

        # content_view가 있을 때만 스타일 설정
        if hasattr(self, 'content_view'):
            font_size = max(9, int(11 * self._zoom_level / 100))  # 최소 9px
            self.content_view.setStyleSheet(f"""
                QTextEdit {{
                    background: palette(base);
                    color: palette(text);
                    font-size: {font_size}px;
                    line-height: 1.4;
                }}
            """)

    def _update_pagination(self):
        """페이지네이션 업데이트"""
        total_entries = len(self._entries)
        self._total_pages = max(1, (total_entries + self.ENTRIES_PER_PAGE - 1) // self.ENTRIES_PER_PAGE)
        self._current_page = min(self._current_page, self._total_pages)

        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(self._total_pages)
        self.page_spin.setValue(self._current_page)
        self.page_spin.blockSignals(False)

        self.page_label.setText(f"/ {self._total_pages}")
        self._update_nav_buttons()

    def update_preview(self, entries: list = None, settings: dict = None):
        """미리보기 업데이트"""
        if entries is not None:
            self._entries = entries
            self._current_page = 1  # 새 데이터면 첫 페이지로
        if settings is not None:
            self._settings = settings

        if not self._entries:
            self._show_placeholder()
            self._total_pages = 1
            self._update_pagination()
            return

        self._update_pagination()
        self._render_document()

    def _render_document(self):
        """문서 렌더링"""
        settings = self._settings

        # 현재 페이지의 항목들만 가져오기
        start_idx = (self._current_page - 1) * self.ENTRIES_PER_PAGE
        end_idx = start_idx + self.ENTRIES_PER_PAGE
        entries = self._entries[start_idx:end_idx]

        # 스타일 설정 가져오기
        dialogue_color = settings.get('dialogue_color', '#333333')
        narration_color = settings.get('narration_color', '#555555')
        scene_marker = settings.get('scene_marker', '■')
        narration_prefix = settings.get('narration_prefix', '＿')
        narration_users = settings.get('narrators', 'GM, KP, DM').split(',')
        narration_users = [u.strip() for u in narration_users]

        font_family = settings.get('font_family', 'Noto Serif KR')
        font_size = int(settings.get('font_size', 11))
        line_height = float(settings.get('line_height', 1.8))

        # HTML 시작 - 모든 요소에 일관된 폰트 크기 적용
        html_parts = [f"""
        <div style="font-family: '{font_family}', 'Malgun Gothic', serif; font-size: {font_size}pt; line-height: {line_height}; color: {dialogue_color};">
        """]

        current_scene = 0

        for entry in entries:
            entry_type = entry.get('type', 'dialogue')
            name = entry.get('name', '')
            content = entry.get('content', '')

            # 장면 전환 감지
            if content.startswith(scene_marker) or content.startswith('씬') or content.startswith('Scene'):
                current_scene += 1
                html_parts.append(f'<p style="font-size: {font_size + 2}pt; font-weight: bold; margin: 16px 0 12px 0; color: #222;">{content}</p>')
                continue

            if entry_type == 'dice':
                html_parts.append(f'<p style="color: #0066cc; font-size: {font_size}pt; margin: 4px 0;">[Dice] {content}</p>')
            elif entry_type == 'system':
                html_parts.append(f'<p style="color: #666; font-size: {font_size}pt; margin: 4px 0;">[System] {content}</p>')
            elif name in narration_users or entry_type == 'narration':
                html_parts.append(f'<p style="margin: 8px 0; padding-left: 1.5em; color: {narration_color}; font-style: italic; font-size: {font_size}pt;">{narration_prefix}{content}</p>')
            else:
                # 대사
                if name:
                    html_parts.append(f'<p style="margin: 4px 0; color: {dialogue_color}; font-size: {font_size}pt;"><b>{name}</b>: {content}</p>')
                else:
                    html_parts.append(f'<p style="margin: 4px 0; color: {dialogue_color}; font-size: {font_size}pt;">{content}</p>')

        # 페이지 정보 표시
        if self._total_pages > 1:
            html_parts.append(f'<p style="text-align: center; color: gray; margin: 16px 0; font-size: {font_size}pt;">— {self._current_page} / {self._total_pages} 페이지 —</p>')

        # HTML 닫기
        html_parts.append('</div>')

        self.content_view.setHtml(''.join(html_parts))

    def clear_preview(self):
        """미리보기 초기화"""
        self._entries = []
        self._settings = {}
        self._current_page = 1
        self._total_pages = 1
        self._update_pagination()
        self._show_placeholder()

    def set_visible(self, visible: bool):
        """미리보기 패널 표시/숨김"""
        self.setVisible(visible)

    def update_settings(self, **kwargs):
        """설정 업데이트 및 재렌더링"""
        self._settings.update(kwargs)
        if self._entries:
            self._render_document()

    def set_document_format(self, format_name: str):
        """외부에서 문서 형식 설정"""
        # 출력 설정의 판형을 미리보기 형식으로 매핑
        format_mapping = {
            "A4 (210×297mm)": "A4 (210×297mm)",
            "A5 (148×210mm)": "A5 (148×210mm)",
            "B5 (182×257mm)": "B5 (182×257mm)",
            "신국판 (152×225mm)": "신국판 (152×225mm)",
            "국판 (148×210mm)": "국판 (148×210mm)",
            "46배판 (128×188mm)": "46배판 (128×188mm)",
            "문고판 (105×148mm)": "문고판 (105×148mm)",
            "Letter (8.5×11in)": "Letter (216×279mm)",
        }

        mapped_format = format_mapping.get(format_name)
        if mapped_format and mapped_format in self.DOCUMENT_FORMATS:
            self._current_format = mapped_format
            self.format_combo.setCurrentText(mapped_format)
            self._update_page_size()

    def resizeEvent(self, event):
        """창 크기 변경 시 페이지 크기 업데이트"""
        super().resizeEvent(event)
        self._update_page_size()

    def set_custom_size(self, width_mm: int, height_mm: int):
        """사용자 정의 문서 크기 설정"""
        # 사용자 정의 크기를 동적으로 추가
        custom_name = f"사용자 정의 ({width_mm}×{height_mm}mm)"
        self.DOCUMENT_FORMATS[custom_name] = (width_mm, height_mm)

        # 콤보박스에 추가 (없는 경우만)
        if self.format_combo.findText(custom_name) == -1:
            self.format_combo.addItem(custom_name)

        self._current_format = custom_name
        self.format_combo.setCurrentText(custom_name)
        self._update_page_size()
