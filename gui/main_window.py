"""
TRPG Log Converter Pro - 메인 윈도우
QFluentWidgets 기반 현대적 UI
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QMessageBox,
    QSplitter, QFileDialog, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QShortcut, QKeySequence
from pathlib import Path
import os
import json
import logging

logger = logging.getLogger(__name__)

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    setTheme, Theme, setThemeColor, InfoBar, InfoBarPosition
)
from qfluentwidgets import FluentIcon as FIF

from .pages import (
    ConvertPage, BasicPage, StylePage, FontPage,
    ContentPage, CoverPage, OutputPage, AdvancedPage, PresetPage, DecorationPage,
    ParsingRulePage
)
from .components import InspectorBar, DocumentPreview
from core.services import CacheService, CharacterColorService


class RecentFilesManager:
    """최근 파일 관리자"""
    MAX_RECENT = 10

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._recent_files = []
        self._load()

    def _load(self):
        """최근 파일 목록 로드"""
        settings = self.config_manager.get_gui_settings()
        self._recent_files = settings.get('recent_files', [])

    def _save(self):
        """최근 파일 목록 저장"""
        settings = self.config_manager.get_gui_settings()
        settings['recent_files'] = self._recent_files
        self.config_manager.save_gui_settings(settings)

    def add_file(self, file_path: str):
        """파일 추가"""
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        self._recent_files.insert(0, file_path)
        self._recent_files = self._recent_files[:self.MAX_RECENT]
        self._save()

    def add_files(self, file_paths: list):
        """여러 파일 추가"""
        for path in file_paths:
            self.add_file(path)

    def get_files(self) -> list:
        """최근 파일 목록 반환 (존재하는 파일만)"""
        valid = [f for f in self._recent_files if os.path.exists(f)]
        if len(valid) != len(self._recent_files):
            self._recent_files = valid
            self._save()
        return valid

    def clear(self):
        """목록 초기화"""
        self._recent_files = []
        self._save()


class ConversionWorker(QThread):
    """변환 작업 스레드"""
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, config_manager, files, title, mode, output_format,
                 preset_config=None, character_colors=None, cache_service=None):
        super().__init__()
        self.config_manager = config_manager
        self.files = files
        self.title = title
        self.mode = mode
        self.output_format = output_format
        self.preset_config = preset_config
        self.character_colors = character_colors or {}
        self.cache_service = cache_service

    def run(self):
        """변환 실행"""
        try:
            from core.engine import ConversionEngine, deep_merge

            self.progress.emit(5, "설정 준비 중...")
            config = self.config_manager.build_engine_config()
            config['output_format'] = self.output_format

            if self.preset_config:
                config = deep_merge(config, self.preset_config)

            if self.character_colors:
                if 'custom_styles' not in config:
                    config['custom_styles'] = {}
                config['custom_styles']['character_colors'] = self.character_colors

            output_dir = config.get('paths', {}).get('output_dir', './export')
            os.makedirs(output_dir, exist_ok=True)

            engine = ConversionEngine(config)
            author = config.get('metadata', {}).get('author', 'GM')
            results = []

            # engine progress_callback → Qt signal 변환
            def engine_progress(current, total, message):
                if total > 0:
                    pct = int(current * 100 / total)
                else:
                    pct = 0
                self.progress.emit(min(pct, 99), message)

            def parse_with_cache(file_path):
                if self.cache_service:
                    cached = self.cache_service.get(file_path, config)
                    if cached:
                        return cached[0]

                entries = engine.parse_file(file_path)

                if self.cache_service and entries:
                    characters = list(set(e.get('name', '') for e in entries if e.get('name')))
                    self.cache_service.set(file_path, config, entries, characters)

                return entries

            if self.mode == 'merge':
                self.progress.emit(10, "파일 병합 중...")
                all_entries = []

                for i, file_path in enumerate(self.files):
                    progress = int(10 + (40 * (i / len(self.files))))
                    self.progress.emit(progress, f"파싱 중: {Path(file_path).name}")
                    entries = parse_with_cache(file_path)
                    all_entries.extend(entries)

                if all_entries:
                    self.progress.emit(60, "변환 중...")
                    base = Path(self.files[0]).stem + "_merged"

                    if self.output_format in ['both', 'all', 'epub']:
                        results.append(engine.create_epub(all_entries, os.path.join(output_dir, f"{base}.epub"), self.title, author, progress_callback=engine_progress))
                    if self.output_format in ['both', 'all', 'docx']:
                        results.append(engine.create_docx(all_entries, os.path.join(output_dir, f"{base}.docx"), self.title, author, progress_callback=engine_progress))
                    if self.output_format in ['all', 'pdf']:
                        pdf_result = engine.create_pdf(all_entries, os.path.join(output_dir, f"{base}.pdf"), self.title, author)
                        if pdf_result:
                            results.append(pdf_result)

            elif self.mode == 'batch':
                total_files = len(self.files)
                for i, file_path in enumerate(self.files):
                    progress = int(10 + (80 * (i / total_files)))
                    file_name = Path(file_path).name
                    self.progress.emit(progress, f"변환 중: {file_name}")

                    entries = parse_with_cache(file_path)
                    if entries:
                        base = Path(file_path).stem
                        file_title = self.title or base

                        if self.output_format in ['both', 'all', 'epub']:
                            results.append(engine.create_epub(entries, os.path.join(output_dir, f"{base}.epub"), file_title, author, progress_callback=engine_progress))
                        if self.output_format in ['both', 'all', 'docx']:
                            results.append(engine.create_docx(entries, os.path.join(output_dir, f"{base}.docx"), file_title, author, progress_callback=engine_progress))
                        if self.output_format in ['all', 'pdf']:
                            pdf_result = engine.create_pdf(entries, os.path.join(output_dir, f"{base}.pdf"), file_title, author)
                            if pdf_result:
                                results.append(pdf_result)

            else:
                if self.files:
                    file_path = self.files[0]
                    self.progress.emit(20, f"파싱 중: {Path(file_path).name}")
                    entries = parse_with_cache(file_path)

                    if entries:
                        self.progress.emit(60, "변환 중...")
                        base = Path(file_path).stem

                        if self.output_format in ['both', 'all', 'epub']:
                            results.append(engine.create_epub(entries, os.path.join(output_dir, f"{base}.epub"), self.title, author, progress_callback=engine_progress))
                        if self.output_format in ['both', 'all', 'docx']:
                            results.append(engine.create_docx(entries, os.path.join(output_dir, f"{base}.docx"), self.title, author, progress_callback=engine_progress))
                        if self.output_format in ['all', 'pdf']:
                            pdf_result = engine.create_pdf(entries, os.path.join(output_dir, f"{base}.pdf"), self.title, author)
                            if pdf_result:
                                results.append(pdf_result)

            self.progress.emit(100, "완료!")

            success_count = sum(1 for r in results if r)
            self.finished.emit(True, f"변환 완료!\n{success_count}개 파일 생성\n출력 위치: {output_dir}")

        except UnicodeDecodeError as e:
            logger.error("인코딩 오류: %s", e)
            self.finished.emit(False, f"파일 인코딩 오류: 지원되지 않는 인코딩입니다. UTF-8, EUC-KR, CP949 형식의 파일을 사용해주세요.")
        except Exception as e:
            logger.error("변환 실패: %s", e, exc_info=True)
            self.finished.emit(False, f"변환 실패: {str(e)}")


class MainWindow(FluentWindow):
    """메인 애플리케이션 윈도우 - Fluent Design"""

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.pages = {}
        self._worker = None
        self._conversion_log = []  # 변환 로그 저장
        self._current_page = None  # 현재 페이지 추적 (on_page_leave 호출용)

        # 캐시 서비스 초기화
        gui_settings = config_manager.get_gui_settings()
        cache_enabled = gui_settings.get('cache_enabled', True)
        self.cache_service = CacheService(enabled=cache_enabled)

        # 최근 파일 관리자
        self.recent_files_manager = RecentFilesManager(config_manager)

        # 윈도우 설정
        self.setWindowTitle("TRPG Log Converter Pro")
        self.setMinimumSize(900, 600)  # 최소 크기 축소로 유연성 확보
        self.resize(1300, 800)

        # 테마 설정 (시스템 테마 따라감)
        setTheme(Theme.AUTO)
        setThemeColor('#0A84FF')  # Apple 블루

        self._setup_navigation()
        self._setup_main_layout()
        self._connect_signals()
        self._setup_shortcuts()
        self._load_recent_files()

    def _setup_navigation(self):
        """네비게이션 설정"""
        # 페이지 생성
        self.convert_page = ConvertPage(self.config_manager)
        self.basic_page = BasicPage(self.config_manager)
        self.style_page = StylePage(self.config_manager)
        self.font_page = FontPage(self.config_manager)
        self.content_page = ContentPage(self.config_manager)
        self.cover_page = CoverPage(self.config_manager)
        self.decoration_page = DecorationPage(self.config_manager)
        self.output_page = OutputPage(self.config_manager)
        self.advanced_page = AdvancedPage(self.config_manager)
        self.preset_page = PresetPage(self.config_manager)
        self.parsing_rules_page = ParsingRulePage(self.config_manager)

        # 페이지 저장
        self.pages = {
            'convert': self.convert_page,
            'basic': self.basic_page,
            'style': self.style_page,
            'font': self.font_page,
            'content': self.content_page,
            'cover': self.cover_page,
            'decoration': self.decoration_page,
            'output': self.output_page,
            'advanced': self.advanced_page,
            'preset': self.preset_page,
            'parsing_rules': self.parsing_rules_page,
        }

        # 네비게이션 아이템 추가
        self.addSubInterface(self.convert_page, FIF.PLAY_SOLID, '변환')
        self.addSubInterface(self.basic_page, FIF.SETTING, '기본')

        self.navigationInterface.addSeparator()

        self.addSubInterface(self.style_page, FIF.PALETTE, '스타일')
        self.addSubInterface(self.font_page, FIF.FONT_SIZE, '폰트')
        self.addSubInterface(self.content_page, FIF.DOCUMENT, '콘텐츠')
        self.addSubInterface(self.cover_page, FIF.PHOTO, '표지')
        self.addSubInterface(self.decoration_page, FIF.BRUSH, '장식')

        self.navigationInterface.addSeparator()

        self.addSubInterface(self.output_page, FIF.FOLDER, '출력')
        self.addSubInterface(self.preset_page, FIF.BOOK_SHELF, '프리셋')
        self.addSubInterface(self.parsing_rules_page, FIF.CODE, '파싱 규칙')

        self.navigationInterface.addSeparator(NavigationItemPosition.BOTTOM)

        self.addSubInterface(self.advanced_page, FIF.DEVELOPER_TOOLS, '고급',
                            position=NavigationItemPosition.BOTTOM)

        # 종료 버튼 추가
        self.navigationInterface.addItem(
            routeKey='quit',
            icon=FIF.POWER_BUTTON,
            text='종료',
            onClick=self.close,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )

        # 네비게이션 확장 모드로 설정 (종료 버튼 표시 보장)
        self.navigationInterface.setExpandWidth(200)
        self.navigationInterface.setMinimumExpandWidth(200)

    def _setup_main_layout(self):
        """전역 문서 미리보기 패널을 포함한 메인 레이아웃 설정"""
        self._preview_visible = True

        # 미리보기 컨테이너 생성
        self.preview_container = QFrame()
        self.preview_container.setObjectName("GlobalPreviewContainer")
        self.preview_container.setMinimumWidth(300)
        self.preview_container.setMaximumWidth(600)

        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        self.document_preview = DocumentPreview()
        preview_layout.addWidget(self.document_preview)

        # 스플리터 생성 및 설정
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: rgba(128, 128, 128, 0.12);
            }
            QSplitter::handle:hover {
                background-color: rgba(10, 132, 255, 0.4);
            }
        """)
        self.main_splitter.setChildrenCollapsible(False)

        # FluentWindow 내부 구조를 안전하게 조작
        stacked_parent = self.stackedWidget.parent()
        if stacked_parent and stacked_parent.layout():
            parent_layout = stacked_parent.layout()

            # stackedWidget의 현재 인덱스 위치 찾기
            index = -1
            for i in range(parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item and item.widget() == self.stackedWidget:
                    index = i
                    break

            if index >= 0:
                parent_layout.removeWidget(self.stackedWidget)
                self.main_splitter.addWidget(self.stackedWidget)
                self.main_splitter.addWidget(self.preview_container)
                parent_layout.insertWidget(index, self.main_splitter)

                # 비율 설정 (약 55:45)
                self.main_splitter.setSizes([550, 450])
                self.main_splitter.setStretchFactor(0, 3)
                self.main_splitter.setStretchFactor(1, 2)
            else:
                # 폴백: 인덱스를 못 찾은 경우에도 작동하도록
                parent_layout.addWidget(self.main_splitter)
                self.main_splitter.addWidget(self.stackedWidget)
                self.main_splitter.addWidget(self.preview_container)
                self.main_splitter.setSizes([550, 450])

    def toggle_preview(self):
        """미리보기 패널 토글"""
        self._preview_visible = not self._preview_visible
        self.preview_container.setVisible(self._preview_visible)
        if self._preview_visible:
            self.main_splitter.setSizes([550, 450])


    def _connect_signals(self):
        """시그널 연결"""
        if hasattr(self.convert_page, 'conversion_started'):
            self.convert_page.conversion_started.connect(self._start_conversion)

        # 파일 추가 시 최근 파일 목록 업데이트 및 미리보기 동기화
        if hasattr(self.convert_page, 'files_updated'):
            self.convert_page.files_updated.connect(self._on_files_updated)

        # 엔트리 파싱 시 미리보기 업데이트
        if hasattr(self.convert_page, 'entries_parsed'):
            self.convert_page.entries_parsed.connect(self._on_entries_parsed)

        # 각 페이지의 설정 변경 시 미리보기 업데이트
        pages_with_settings = [
            self.style_page, self.font_page, self.content_page,
            self.cover_page, self.decoration_page
        ]
        for page in pages_with_settings:
            if hasattr(page, 'settings_changed'):
                page.settings_changed.connect(self._update_document_preview)

        # 페이지 전환 시 on_page_enter 호출 (설정 동기화)
        self.stackedWidget.currentChanged.connect(self._on_page_changed)

    def _on_page_changed(self, index: int):
        """페이지 전환 시 호출"""
        # 이전 페이지의 on_page_leave 호출 (설정 저장)
        if self._current_page and hasattr(self._current_page, 'on_page_leave'):
            self._current_page.on_page_leave()

        # 현재 페이지 업데이트
        current_widget = self.stackedWidget.widget(index)
        self._current_page = current_widget

        # 새 페이지의 on_page_enter 호출 (설정 동기화)
        if current_widget and hasattr(current_widget, 'on_page_enter'):
            current_widget.on_page_enter()

    def _setup_shortcuts(self):
        """키보드 단축키 설정"""
        # ⌘+O: 파일 열기
        open_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        open_shortcut.activated.connect(self._shortcut_open_files)

        # ⌘+R: 변환 시작
        convert_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        convert_shortcut.activated.connect(self._start_conversion)

        # ⌘+E: 설정 내보내기
        export_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        export_shortcut.activated.connect(self.export_settings)

        # ⌘+I: 설정 가져오기
        import_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        import_shortcut.activated.connect(self.import_settings)

        # ⌘+L: 로그 보기
        log_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        log_shortcut.activated.connect(self.show_conversion_log)

        # ⌘+P: 미리보기 토글
        preview_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        preview_shortcut.activated.connect(self.toggle_preview)

        # ⌘+1~9: 페이지 전환
        page_keys = ['convert', 'basic', 'style', 'font', 'content', 'cover', 'decoration', 'output', 'preset', 'parsing_rules']
        for i, key in enumerate(page_keys[:9], 1):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda k=key: self._switch_to_page(k))

    def _shortcut_open_files(self):
        """단축키로 파일 열기"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "로그 파일 선택",
            "",
            "지원 형식 (*.html *.htm *.txt);;모든 파일 (*.*)"
        )
        if files and hasattr(self.convert_page, '_on_files_dropped'):
            self.convert_page._on_files_dropped(files)
            self._switch_to_page('convert')

    def _switch_to_page(self, page_key: str):
        """특정 페이지로 전환"""
        if page_key in self.pages:
            self.stackedWidget.setCurrentWidget(self.pages[page_key])

    def _on_files_updated(self, files: list):
        """파일 목록 업데이트 시"""
        if files:
            # 최근 파일에 추가
            self.recent_files_manager.add_files(files)
            # UI 갱신
            self._load_recent_files()
        else:
            # 파일이 비어있으면 엔트리 초기화
            if hasattr(self.convert_page, '_parsed_entries'):
                self.convert_page._parsed_entries = []

    def _on_entries_parsed(self, entries: list):
        """엔트리 파싱 완료 시 - 미리보기 업데이트"""
        if self.document_preview and entries:
            settings = self._collect_preview_settings()
            self.document_preview.update_preview(entries=entries, settings=settings)

    def _update_document_preview(self):
        """문서 미리보기 업데이트 (설정 변경 시)"""
        if not self.document_preview:
            return

        # 파싱된 엔트리가 있으면 설정만 업데이트
        if hasattr(self.convert_page, '_parsed_entries') and self.convert_page._parsed_entries:
            settings = self._collect_preview_settings()
            self.document_preview.update_settings(**settings)

    def _collect_preview_settings(self) -> dict:
        """미리보기용 설정 수집"""
        settings = self.config_manager.get_gui_settings()

        # 스타일 페이지 설정
        if hasattr(self.style_page, 'bg_picker'):
            settings['style_body_bg'] = self.style_page.bg_picker.get_color()
        if hasattr(self.style_page, 'text_picker'):
            settings['dialogue_color'] = self.style_page.text_picker.get_color()

        # 폰트 페이지 설정
        if hasattr(self.font_page, 'font_combo'):
            settings['font_family'] = self.font_page.font_combo.currentText()
        if hasattr(self.font_page, 'size_slider'):
            settings['font_size'] = self.font_page.size_slider.value()

        # 장식 페이지 설정
        if hasattr(self.decoration_page, 'divider_text'):
            settings['scene_marker'] = self.decoration_page.divider_text.text()

        return settings

    def export_settings(self):
        """설정 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "설정 내보내기",
            "trpg_converter_settings.json",
            "JSON 파일 (*.json)"
        )

        if not file_path:
            return

        try:
            settings = self.config_manager.get_gui_settings()

            # base64 이미지 데이터는 제외 (파일 크기 문제)
            export_settings = {k: v for k, v in settings.items()
                              if not (isinstance(v, str) and len(v) > 10000)}

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_settings, f, ensure_ascii=False, indent=2)

            InfoBar.success(
                title='내보내기 완료',
                content=f'설정이 저장되었습니다: {Path(file_path).name}',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
        except Exception as e:
            InfoBar.error(
                title='내보내기 실패',
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )

    def import_settings(self):
        """설정 가져오기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "설정 가져오기",
            "",
            "JSON 파일 (*.json)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported = json.load(f)

            # 현재 설정과 병합
            current = self.config_manager.get_gui_settings()
            current.update(imported)
            self.config_manager.save_gui_settings(current)

            # 각 페이지 다시 로드
            for page in self.pages.values():
                if hasattr(page, 'load_settings'):
                    page.load_settings()

            InfoBar.success(
                title='가져오기 완료',
                content='설정이 적용되었습니다. 일부 설정은 앱 재시작 후 적용됩니다.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
        except Exception as e:
            InfoBar.error(
                title='가져오기 실패',
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )

    def add_conversion_log(self, message: str):
        """변환 로그 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._conversion_log.append(f"[{timestamp}] {message}")
        # 최대 1000줄 유지
        if len(self._conversion_log) > 1000:
            self._conversion_log = self._conversion_log[-500:]

    def show_conversion_log(self):
        """변환 로그 표시"""
        from qfluentwidgets import MessageBox

        if not self._conversion_log:
            log_text = "아직 변환 로그가 없습니다."
        else:
            log_text = "\n".join(self._conversion_log[-50:])  # 최근 50줄
            if len(self._conversion_log) > 50:
                log_text = f"... (최근 50줄만 표시, 총 {len(self._conversion_log)}줄)\n\n" + log_text

        w = MessageBox(
            "변환 로그",
            log_text,
            self
        )
        w.exec()

    def get_recent_files(self) -> list:
        """최근 파일 목록 반환"""
        return self.recent_files_manager.get_files()

    def _load_recent_files(self):
        """최근 파일 목록을 convert_page에 로드"""
        recent = self.recent_files_manager.get_files()
        if hasattr(self.convert_page, 'load_recent_files'):
            self.convert_page.load_recent_files(recent)

    def _start_conversion(self):
        """변환 시작"""
        files = self.convert_page.get_files()
        if not files:
            InfoBar.warning(
                title='파일 없음',
                content='변환할 파일을 추가해주세요.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        title = self.convert_page.get_title()
        mode = self.convert_page.get_convert_mode()
        output_format = self.convert_page.get_output_format()
        preset_config = self.convert_page.get_preset_config()

        character_colors = {}
        if hasattr(self.style_page, 'get_character_colors'):
            character_colors = self.style_page.get_character_colors()

        # 모든 페이지 설정 저장 (먼저 각 페이지 위젯을 settings에서 동기화)
        for page in self.pages.values():
            # 공유 설정(output_dir 등)을 다른 페이지와 동기화
            if hasattr(page, 'on_page_enter'):
                page.on_page_enter()
            if hasattr(page, 'save_settings'):
                page.save_settings()

        # 변환 워커 시작
        self._worker = ConversionWorker(
            self.config_manager, files, title, mode, output_format,
            preset_config=preset_config,
            character_colors=character_colors,
            cache_service=self.cache_service
        )
        self._worker.progress.connect(self._on_conversion_progress)
        self._worker.finished.connect(self._on_conversion_finished)
        self._worker.start()

    def _on_conversion_progress(self, value: int, message: str):
        """변환 진행 상태 업데이트"""
        if hasattr(self.convert_page, 'update_progress'):
            self.convert_page.update_progress(value, message)

        # 로그 기록
        self.add_conversion_log(f"[{value}%] {message}")

    def _on_conversion_finished(self, success: bool, message: str):
        """변환 완료 처리"""
        if hasattr(self.convert_page, 'conversion_complete'):
            self.convert_page.conversion_complete(success, message)

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

    def closeEvent(self, event):
        """윈도우 닫기 이벤트"""
        for page in self.pages.values():
            if hasattr(page, 'save_settings'):
                page.save_settings()

        if self._worker and self._worker.isRunning():
            reply = QMessageBox.question(
                self,
                "변환 중",
                "변환이 진행 중입니다. 정말 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

            self._worker.terminate()
            self._worker.wait()

        event.accept()

