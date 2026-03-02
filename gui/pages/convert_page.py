"""
TRPG Log Converter Pro - 변환 페이지
파일 선택 및 기본 변환 설정
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QFileDialog, QFrame, QButtonGroup
)
from PySide6.QtCore import Signal, Qt
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

from qfluentwidgets import (
    BodyLabel, PushButton, PrimaryPushButton, LineEdit, ComboBox, RadioButton,
    ProgressBar, InfoBar, InfoBarPosition, MessageBox
)

from .base_page import BasePage
from ..components import ContentCard, FileDropArea, DocumentPreview
from core.services import PresetService


class ConvertPage(BasePage):
    """변환 페이지 - 파일 선택 및 변환 실행"""
    conversion_started = Signal()
    conversion_finished = Signal(bool, str)
    files_updated = Signal(list)  # 파일 목록 변경 시그널
    entries_parsed = Signal(list)  # 엔트리 파싱 완료 시그널

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self.files = []
        self.preset_service = PresetService()
        self._parsed_entries = []  # 파싱된 엔트리 캐시
        self._setup_page()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("로그 변환", "TRPG 채팅 로그를 EPUB/DOCX/PDF 형식으로 변환합니다")

        # === 파일 선택 카드 ===
        file_card = ContentCard("소스 파일", "변환할 로그 파일을 추가하세요")

        # 드래그 앤 드롭 영역
        self.drop_area = FileDropArea()
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        file_card.add_widget(self.drop_area)

        file_card.add_spacing(8)

        # 파일 목록
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(80)
        self.file_list.setMaximumHeight(200)
        self.file_list.setDragDropMode(QListWidget.InternalMove)
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        file_card.add_widget(self.file_list)

        # 파일 관리 버튼
        file_buttons = QHBoxLayout()
        file_buttons.setSpacing(8)

        add_btn = PushButton("파일 추가")
        add_btn.setMinimumHeight(34)
        add_btn.clicked.connect(self._add_files)
        file_buttons.addWidget(add_btn)

        folder_btn = PushButton("폴더 추가")
        folder_btn.setMinimumHeight(34)
        folder_btn.clicked.connect(self._add_folder)
        file_buttons.addWidget(folder_btn)

        file_buttons.addStretch()

        remove_btn = PushButton("선택 제거")
        remove_btn.setMinimumHeight(34)
        remove_btn.clicked.connect(self._remove_selected)
        file_buttons.addWidget(remove_btn)

        clear_btn = PushButton("전체 삭제")
        clear_btn.setMinimumHeight(34)
        clear_btn.clicked.connect(self._clear_files)
        file_buttons.addWidget(clear_btn)

        file_card.add_layout(file_buttons)

        self.content_layout.addWidget(file_card)

        # === 최근 파일 카드 ===
        recent_card = ContentCard("최근 파일", "최근에 작업한 파일을 빠르게 열기")

        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(60)
        self.recent_list.setMaximumHeight(120)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_file_clicked)
        self.recent_list.setSelectionMode(QListWidget.ExtendedSelection)
        recent_card.add_widget(self.recent_list)

        # 최근 파일 버튼
        recent_buttons = QHBoxLayout()
        recent_buttons.setSpacing(8)

        load_recent_btn = PushButton("선택 항목 추가")
        load_recent_btn.clicked.connect(self._add_selected_recent)
        recent_buttons.addWidget(load_recent_btn)

        clear_recent_btn = PushButton("목록 지우기")
        clear_recent_btn.clicked.connect(self._clear_recent_files)
        recent_buttons.addWidget(clear_recent_btn)

        recent_buttons.addStretch()
        recent_card.add_layout(recent_buttons)

        self.content_layout.addWidget(recent_card)

        # === 기본 설정 카드 ===
        settings_card = ContentCard("기본 설정", "제목, 저자 및 플랫폼 설정")

        # 제목
        self.title_entry = settings_card.add_text_field(
            "제목", "title",
            placeholder="TRPG 리플레이",
            help_text="EPUB/DOCX 파일에 표시될 제목"
        )

        # 저자
        self.author_entry = settings_card.add_text_field(
            "저자", "author",
            placeholder="GM",
            help_text="메타데이터에 기록될 저자명"
        )

        # 플랫폼
        self.platform_combo = settings_card.add_dropdown(
            "플랫폼", "platform",
            options=["cocofolia", "roll20", "auto"],
            default="cocofolia",
            help_text="로그 출처 플랫폼 (auto는 자동 감지)"
        )

        # 출력 폴더
        self.output_entry = LineEdit()
        self.output_entry.setText("./export")
        self.output_entry.setMinimumHeight(38)
        browse_btn = PushButton("찾아보기")
        browse_btn.clicked.connect(self._browse_output)
        browse_btn.setFixedWidth(100)
        browse_btn.setMinimumHeight(38)

        output_widget = QWidget()
        output_layout = QHBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(8)
        output_layout.addWidget(self.output_entry)
        output_layout.addWidget(browse_btn)

        settings_card.add_field("출력 폴더", output_widget, help_text="변환된 파일이 저장될 폴더")

        self.content_layout.addWidget(settings_card)

        # === 변환 옵션 카드 ===
        options_card = ContentCard("변환 옵션", "변환 모드 및 출력 형식 선택")

        # 변환 모드
        mode_label = BodyLabel("변환 모드")
        options_card.add_widget(mode_label)

        self.mode_group = QButtonGroup(self)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(16)

        modes = [
            ("단일 파일", "single", "각 파일을 별도로 변환"),
            ("병합", "merge", "모든 파일을 하나로 병합"),
            ("일괄 변환", "batch", "여러 파일을 각각 변환")
        ]

        for text, value, tooltip in modes:
            radio = RadioButton(text)
            radio.setProperty("value", value)
            radio.setToolTip(tooltip)
            if value == "single":
                radio.setChecked(True)
            self.mode_group.addButton(radio)
            mode_layout.addWidget(radio)

        mode_layout.addStretch()
        options_card.add_layout(mode_layout)

        options_card.add_spacing(12)

        # 출력 형식
        format_label = BodyLabel("출력 형식")
        options_card.add_widget(format_label)

        self.format_group = QButtonGroup(self)
        format_layout = QHBoxLayout()
        format_layout.setSpacing(16)

        formats = [
            ("EPUB + DOCX", "both"),
            ("EPUB만", "epub"),
            ("DOCX만", "docx"),
            ("모두 (PDF 포함)", "all")
        ]

        for text, value in formats:
            radio = RadioButton(text)
            radio.setProperty("value", value)
            if value == "both":
                radio.setChecked(True)
            self.format_group.addButton(radio)
            format_layout.addWidget(radio)

        format_layout.addStretch()
        options_card.add_layout(format_layout)

        self.content_layout.addWidget(options_card)

        # === 프리셋 카드 ===
        preset_card = ContentCard("프리셋", "저장된 설정 프리셋을 빠르게 적용")

        presets = self.preset_service.list_presets()
        preset_items = [("없음 (기본 설정)", None)]
        preset_items.extend([(p.name, p.name) for p in presets])

        self.preset_combo = ComboBox()
        for text, value in preset_items:
            self.preset_combo.addItem(text, value)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)

        preset_card.add_field("프리셋 선택", self.preset_combo, help_text="저장된 스타일 프리셋 적용")

        self.preset_desc = BodyLabel("")
        self.preset_desc.setWordWrap(True)
        self.preset_desc.setVisible(False)
        self.preset_desc.setStyleSheet("color: palette(dark); padding: 8px; background: rgba(128, 128, 128, 0.05); border-radius: 6px;")
        preset_card.add_widget(self.preset_desc)

        self.content_layout.addWidget(preset_card)

        # === 변환 실행 카드 ===
        convert_card = ContentCard("변환 실행")

        # 파일 상태 표시 영역
        self.file_count_label = BodyLabel("파일을 선택해주세요")
        self.file_count_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: palette(mid);
        """)
        convert_card.add_widget(self.file_count_label)

        self.file_size_label = BodyLabel("")
        self.file_size_label.setStyleSheet("font-size: 12px; color: palette(mid);")
        convert_card.add_widget(self.file_size_label)

        convert_card.add_spacing(8)

        # 진행 상태
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        self.progress_frame.setStyleSheet("""
            QFrame {
                background: rgba(10, 132, 255, 0.06);
                border: 1px solid rgba(10, 132, 255, 0.15);
                border-radius: 10px;
            }
        """)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(16, 12, 16, 12)
        progress_layout.setSpacing(8)

        self.progress_label = BodyLabel("변환 준비 중...")
        self.progress_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #0A84FF;")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimumHeight(6)
        self.progress_bar.setMaximumHeight(6)
        progress_layout.addWidget(self.progress_bar)

        convert_card.add_widget(self.progress_frame)

        convert_card.add_spacing(12)

        # 변환 버튼 영역
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        btn_layout.addStretch()

        # 변환 시작 버튼 - 세련된 프라이머리 액션
        self.convert_btn = PrimaryPushButton("변환 시작")
        self.convert_btn.setMinimumHeight(46)
        self.convert_btn.setMinimumWidth(180)
        self.convert_btn.setCursor(Qt.PointingHandCursor)
        self.convert_btn.setStyleSheet("""
            PrimaryPushButton {
                font-size: 15px;
                font-weight: 600;
                border-radius: 10px;
                padding: 0 32px;
                background: #0A84FF;
                color: white;
                border: none;
            }
            PrimaryPushButton:hover {
                background: #0070E0;
            }
            PrimaryPushButton:pressed {
                background: #005BBB;
            }
            PrimaryPushButton:disabled {
                background: rgba(128, 128, 128, 0.2);
                color: rgba(128, 128, 128, 0.5);
            }
        """)
        self.convert_btn.clicked.connect(self._start_conversion)
        btn_layout.addWidget(self.convert_btn)

        convert_card.add_layout(btn_layout)

        self.content_layout.addWidget(convert_card)

        self.add_stretch()
        self.load_settings()



    def _update_document_preview(self, files: list = None):
        """문서 미리보기 업데이트"""
        if files is None:
            files = self.files

        if not files or not hasattr(self, 'document_preview'):
            return

        try:
            # 첫 번째 파일만 파싱하여 미리보기 (성능을 위해)
            file_path = files[0]
            platform = self.platform_combo.currentText()

            # text_parser.parse_file 사용
            from core.text_parser import parse_file

            # 플랫폼 매핑 (ccfolia는 cocofolia와 동일)
            log_source = platform if platform != 'ccfolia' else 'cocofolia'
            narrators = self.settings.get('narrators', 'GM, KP, DM')
            narrator_list = [n.strip() for n in narrators.split(',') if n.strip()]

            config = {
                'log_source': log_source,
                'narration': {'users': narrator_list}
            }

            entries = parse_file(file_path, config)
            self._parsed_entries = entries
            self.entries_parsed.emit(entries)

            # GUI 설정 가져오기
            settings = {
                'font_family': self.settings.get('font_family', 'Noto Serif KR'),
                'font_size': self.settings.get('font_size', 11),
                'line_height': self.settings.get('line_height', 1.8),
                'dialogue_color': self.settings.get('dialogue_color', '#333333'),
                'narration_color': self.settings.get('narration_color', '#555555'),
                'scene_marker': self.settings.get('scene_marker', '■'),
                'narration_prefix': self.settings.get('narration_prefix', '＿'),
                'narrators': self.settings.get('narrators', 'GM, KP, DM'),
            }

            self.document_preview.update_preview(entries=entries, settings=settings)

        except Exception as e:
            logger.warning("미리보기 업데이트 오류: %s", e, exc_info=True)

    def _show_preview(self):
        """미리보기 패널 표시 및 업데이트"""
        parent = self.window()
        # 미리보기 패널이 숨겨져 있으면 보여주기
        if hasattr(parent, '_preview_visible') and not parent._preview_visible:
            parent.toggle_preview()
        # 파일이 있으면 미리보기 업데이트
        if self.files:
            self._update_document_preview(self.files)
        if hasattr(parent, 'document_preview'):
            parent.document_preview.setFocus()

    def _update_file_count(self):
        """파일 개수 및 크기 라벨 업데이트"""
        count = len(self.files)
        if count == 0:
            self.file_count_label.setText("파일을 선택해주세요")
            self.file_count_label.setStyleSheet("font-size: 14px; font-weight: 500; color: palette(mid);")
            self.file_size_label.setText("")
        else:
            self.file_count_label.setText(f"파일 {count}개 준비됨")
            self.file_count_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #0A84FF;")
            total_size = 0
            for f in self.files:
                try:
                    total_size += os.path.getsize(f)
                except OSError:
                    pass
            if total_size > 0:
                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    size_str = f"{total_size / (1024 * 1024):.1f} MB"
                self.file_size_label.setText(f"총 {size_str}")
            else:
                self.file_size_label.setText("")

    def _on_files_dropped(self, files: list):
        """파일 드롭 이벤트"""
        added = False
        large_files = []
        for path in files:
            if path not in self.files:
                self.files.append(path)
                item = QListWidgetItem(f"  {Path(path).name}")
                item.setData(Qt.UserRole, path)
                item.setToolTip(path)
                self.file_list.addItem(item)
                added = True
                try:
                    if os.path.getsize(path) > 10 * 1024 * 1024:
                        large_files.append(Path(path).name)
                except OSError:
                    pass

        if large_files:
            InfoBar.warning(
                title='대용량 파일 경고',
                content=f'10MB 이상 파일이 포함되어 있습니다: {", ".join(large_files)}. 변환에 시간이 걸릴 수 있습니다.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )

        if added:
            self._update_file_count()
            self.files_updated.emit(self.files)
            self._update_document_preview(self.files)

    def _add_files(self):
        """파일 추가 대화상자"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "로그 파일 선택",
            "",
            "지원 형식 (*.html *.htm *.txt);;HTML (*.html *.htm);;텍스트 (*.txt);;모든 파일 (*.*)"
        )
        if files:
            self._on_files_dropped(files)

    def _add_folder(self):
        """폴더의 모든 파일 추가"""
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            files = []
            for ext in ['*.html', '*.htm', '*.txt']:
                files.extend([str(p) for p in Path(folder).glob(ext)])
            if files:
                self._on_files_dropped(sorted(files))
            else:
                InfoBar.warning(
                    title='알림',
                    content='폴더에 지원되는 파일이 없습니다.',
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )

    def _remove_selected(self):
        """선택한 파일 제거"""
        for item in self.file_list.selectedItems():
            path = item.data(Qt.UserRole)
            if path in self.files:
                self.files.remove(path)
            self.file_list.takeItem(self.file_list.row(item))
        self._update_file_count()

    def _clear_files(self):
        """모든 파일 제거"""
        self.files.clear()
        self.file_list.clear()
        self.drop_area.clear_files()
        self._parsed_entries = []
        self._update_file_count()
        self.files_updated.emit([])
        if hasattr(self, 'document_preview'):
            self.document_preview.clear_preview()

    def _browse_output(self):
        """출력 폴더 선택"""
        folder = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if folder:
            self.output_entry.setText(folder)

    def _import_roll20_html(self):
        """Roll20 HTML 파일 가져오기 (다운로드 폴더에서 시작)"""
        # 다운로드 폴더 경로 찾기
        downloads_folder = str(Path.home() / "Downloads")
        if not os.path.exists(downloads_folder):
            downloads_folder = str(Path.home())

        # 파일 선택 대화상자 (다운로드 폴더에서 시작, HTML 필터)
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Roll20 HTML 파일 선택",
            downloads_folder,
            "HTML 파일 (*.html *.htm);;모든 파일 (*.*)"
        )

        if files:
            self._on_files_dropped(files)
            InfoBar.success(
                title='완료',
                content=f'Roll20 로그 {len(files)}개 파일을 가져왔습니다!',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _on_preset_changed(self, index: int):
        """프리셋 변경 시"""
        preset_name = self.preset_combo.currentData()
        if preset_name:
            preset = self.preset_service.get_preset(preset_name)
            if preset:
                self.preset_desc.setText(preset.description)
                self.preset_desc.setVisible(True)

                # 플랫폼 자동 설정
                platform_map = {
                    "ccfolia": "cocofolia",
                    "roll20": "roll20",
                    "discord": "auto",
                    "text": "auto",
                }
                platform = platform_map.get(preset.platform, "auto")
                idx = self.platform_combo.findText(platform)
                if idx >= 0:
                    self.platform_combo.setCurrentIndex(idx)
        else:
            self.preset_desc.setVisible(False)

    def _on_secondary_action(self, action: str):
        """보조 액션 처리"""
        if action == "preview":
            # 미리보기 패널로 포커스
            pass
        elif action == "settings":
            # 설정 페이지로 이동
            parent = self.window()
            if hasattr(parent, '_switch_to_page'):
                parent._switch_to_page('basic')

    def _start_conversion(self):
        """변환 시작"""
        files = self.get_files()
        if not files:
            InfoBar.warning(
                title='파일 없음',
                content='변환할 파일을 추가해주세요.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        self.save_settings()
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("준비 중...")
        self.convert_btn.setEnabled(False)

        # 실제 변환은 메인 윈도우에서 처리
        self.conversion_started.emit()

    def update_progress(self, value: int, message: str = ""):
        """진행 상태 업데이트"""
        self.progress_bar.setValue(value)
        if message:
            self.progress_label.setText(message)

    def conversion_complete(self, success: bool, message: str):
        """변환 완료 처리"""
        self.progress_frame.setVisible(False)
        self.convert_btn.setEnabled(True)

        if success:
            InfoBar.success(
                title='변환 완료',
                content=message,
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )
        else:
            InfoBar.error(
                title='변환 실패',
                content=message,
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )

        self.conversion_finished.emit(success, message)

    def save_settings(self):
        """설정 저장"""
        if hasattr(self, 'title_entry'):
            self.settings['title'] = self.title_entry.text()
        if hasattr(self, 'author_entry'):
            self.settings['author'] = self.author_entry.text()
        if hasattr(self, 'platform_combo'):
            self.settings['platform'] = self.platform_combo.currentText()
        if hasattr(self, 'output_entry'):
            self.settings['output_dir'] = self.output_entry.text()

        # 변환 모드
        if hasattr(self, 'mode_group'):
            mode_checked = self.mode_group.checkedButton()
            if mode_checked:
                self.settings['convert_mode'] = mode_checked.property('value')

        # 출력 형식
        if hasattr(self, 'format_group'):
            format_checked = self.format_group.checkedButton()
            if format_checked:
                self.settings['output_format'] = format_checked.property('value')

        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()
        if hasattr(self, 'title_entry'):
            self.title_entry.setText(self.settings.get('title', ''))
        if hasattr(self, 'author_entry'):
            self.author_entry.setText(self.settings.get('author', ''))
        if hasattr(self, 'platform_combo'):
            self.platform_combo.setCurrentText(self.settings.get('platform', 'cocofolia'))
        if hasattr(self, 'output_entry'):
            self.output_entry.setText(self.settings.get('output_dir', './export'))

    def on_page_enter(self):
        """페이지 진입 시 호출 - 출력 폴더 동기화"""
        # 다른 페이지에서 변경된 output_dir을 동기화
        if hasattr(self, 'output_entry'):
            current_output_dir = self.config_manager.get_gui_settings().get('output_dir', './export')
            if self.output_entry.text() != current_output_dir:
                self.output_entry.setText(current_output_dir)

    def get_files(self) -> list:
        """파일 목록 반환 (드래그로 재정렬된 순서)"""
        # QListWidget에서 파일 순서대로 반환
        files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            path = item.data(Qt.UserRole)
            if path:
                files.append(path)
        return files

    def get_title(self) -> str:
        """제목 반환"""
        if hasattr(self, 'title_entry'):
            return self.title_entry.text() or "TRPG 리플레이"
        return "TRPG 리플레이"

    def get_convert_mode(self) -> str:
        """변환 모드 반환"""
        checked = self.mode_group.checkedButton()
        return checked.property('value') if checked else 'single'

    def get_output_format(self) -> str:
        """출력 형식 반환"""
        checked = self.format_group.checkedButton()
        return checked.property('value') if checked else 'both'

    def get_preset_name(self) -> str:
        """선택된 프리셋 이름 반환"""
        return self.preset_combo.currentData() or ""

    def get_preset_config(self):
        """선택된 프리셋 설정 반환"""
        preset_name = self.get_preset_name()
        if preset_name:
            return self.preset_service.get_preset_config(preset_name)
        return None

    def load_recent_files(self, recent_files: list):
        """최근 파일 목록 로드 (외부에서 호출)"""
        if not hasattr(self, 'recent_list'):
            return

        self.recent_list.clear()
        for file_path in recent_files:
            if os.path.exists(file_path):
                item = QListWidgetItem(f"  {Path(file_path).name}")
                item.setData(Qt.UserRole, file_path)
                item.setToolTip(file_path)
                self.recent_list.addItem(item)

    def _on_recent_file_clicked(self, item: QListWidgetItem):
        """최근 파일 더블클릭 시 추가"""
        file_path = item.data(Qt.UserRole)
        if file_path and os.path.exists(file_path):
            self._on_files_dropped([file_path])

    def _add_selected_recent(self):
        """선택된 최근 파일 추가"""
        selected = self.recent_list.selectedItems()
        if not selected:
            InfoBar.warning(
                title='알림',
                content='추가할 파일을 선택해주세요.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        files = []
        for item in selected:
            file_path = item.data(Qt.UserRole)
            if file_path and os.path.exists(file_path):
                files.append(file_path)

        if files:
            self._on_files_dropped(files)

    def _clear_recent_files(self):
        """최근 파일 목록 지우기"""
        # MainWindow의 recent_files_manager를 통해 지우기
        parent = self.window()
        if hasattr(parent, 'recent_files_manager'):
            parent.recent_files_manager.clear()
        self.recent_list.clear()

        InfoBar.info(
            title='완료',
            content='최근 파일 목록이 지워졌습니다.',
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )
