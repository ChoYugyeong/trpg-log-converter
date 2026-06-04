"""
TRPG Log Converter Pro - 메인 윈도우
QFluentWidgets 기반 현대적 UI
"""

import contextlib
import json
import logging
import os
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFileDialog, QFrame, QMessageBox, QSplitter, QVBoxLayout
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
    Theme,
    setTheme,
    setThemeColor,
)

from core.constants import (
    CONVERT_WORKER_SHUTDOWN_TIMEOUT_MS,
    INFOBAR_DURATION_ATTENTION_MS,
    INFOBAR_DURATION_INFO_MS,
    INFOBAR_DURATION_TRANSIENT_MS,
    INFOBAR_DURATION_WARNING_MS,
    INFOBAR_STICKY,
    THREAD_TERMINATE_GRACE_MS,
    UPDATE_CHECK_HARD_TIMEOUT_MS,
    UPDATE_CHECK_STARTUP_DELAY_MS,
    UPDATE_THREAD_SHUTDOWN_TIMEOUT_MS,
    WELCOME_DIALOG_DELAY_MS,
)
from core.services import CacheService

from .components import DocumentPreview
from .pages.advanced_settings_page import AdvancedSettingsPage
from .pages.format_style_page import FormatStylePage
from .pages.home_page import HomePage
from .pages.parsing_content_page import ParsingContentPage
from .state import AppState

logger = logging.getLogger(__name__)


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
        self._recent_files = settings.get("recent_files", [])

    def _save(self):
        """최근 파일 목록 저장"""
        settings = self.config_manager.get_gui_settings()
        settings["recent_files"] = self._recent_files
        self.config_manager.save_gui_settings(settings)

    def add_file(self, file_path: str):
        """파일 추가"""
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        self._recent_files.insert(0, file_path)
        self._recent_files = self._recent_files[: self.MAX_RECENT]
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


class _UpdateCheckWorker(QObject):
    """GitHub Releases API 호출을 백그라운드 스레드에서 수행.

    QThread 직접 상속 대신 QObject + moveToThread 패턴 — Qt 권장 방식.
    """

    finished = Signal(object)  # UpdateInfo | None

    def __init__(self, service) -> None:
        super().__init__()
        self._service = service

    def run(self) -> None:
        logger.info("[update-worker] run() entry on thread %s", id(self.thread()))
        try:
            info = self._service.check()
        except Exception:
            logger.exception("[update-worker] check() raised")
            info = None
        logger.info(
            "[update-worker] check() returned %s; emitting finished",
            "None" if info is None else f"v{info.version}",
        )
        self.finished.emit(info)


class ConversionWorker(QThread):
    """변환 작업 스레드"""

    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(
        self,
        config_manager,
        files,
        title,
        mode,
        output_format,
        preset_config=None,
        character_colors=None,
        cache_service=None,
    ):
        super().__init__()
        self.config_manager = config_manager
        self.files = files
        self.title = title
        self.mode = mode
        self.output_format = output_format
        self.preset_config = preset_config
        self.character_colors = character_colors or {}
        self.cache_service = cache_service
        self._stop_event = threading.Event()
        # 변환 끝났을 때 main_window 가 HistoryManager 에 기록하기 위해 보관.
        # finished signal 직후 self._worker.last_records 로 접근 가능.
        # 한 번의 변환이 여러 파일을 만들 수 있으니 dict 리스트.
        self.last_records: list[dict] = []

    def run(self):
        """변환 실행"""
        import time as _time

        start_ts = _time.monotonic()
        try:
            from core.engine import ConversionEngine, deep_merge

            self.progress.emit(5, "설정 준비 중...")
            config = self.config_manager.build_engine_config()
            config["output_format"] = self.output_format

            if self.preset_config:
                config = deep_merge(config, self.preset_config)

            if self.character_colors:
                if "custom_styles" not in config:
                    config["custom_styles"] = {}
                config["custom_styles"]["character_colors"] = self.character_colors

            output_dir = config.get("paths", {}).get("output_dir", "./export")
            os.makedirs(output_dir, exist_ok=True)

            engine = ConversionEngine(config)
            author = config.get("metadata", {}).get("author", "GM")
            results = []

            # engine progress_callback → Qt signal 변환
            def engine_progress(current, total, message):
                if total > 0:
                    pct = int(current * 100 / total)
                else:
                    pct = 0
                self.progress.emit(min(pct, 99), message)

            def parse_with_cache(file_path):
                if self._stop_event.is_set():
                    raise InterruptedError("작업이 중단되었습니다.")

                if self.cache_service:
                    cached = self.cache_service.get(file_path, config)
                    if cached:
                        return cached[0]

                entries = engine.parse_file(file_path)

                if self.cache_service and entries:
                    characters = list({e.get("name", "") for e in entries if e.get("name")})
                    self.cache_service.set(file_path, config, entries, characters)

                return entries

            if self.mode == "merge":
                self.progress.emit(10, "파일 병합 중...")
                all_entries = []

                # 캠페인 모드: 각 파일(세션) 앞에 세션 제목 scene 을 삽입해 하나의
                # 합본을 세션별 챕터로 구성한다.
                campaign_cfg = config.get("campaign", {}) or {}
                campaign_on = bool(campaign_cfg.get("enable", False))
                session_fmt = campaign_cfg.get(
                    "session_title_format", "Session {n}: {filename}"
                )

                for i, file_path in enumerate(self.files):
                    if self._stop_event.is_set():
                        raise InterruptedError("작업이 중단되었습니다.")

                    progress = int(10 + (40 * (i / len(self.files))))
                    self.progress.emit(progress, f"파싱 중: {Path(file_path).name}")
                    entries = parse_with_cache(file_path)
                    if campaign_on:
                        from core.engine import make_session_scene_entry

                        all_entries.append(
                            make_session_scene_entry(
                                session_fmt, i + 1, Path(file_path).stem
                            )
                        )
                    all_entries.extend(entries)

                if all_entries:
                    self.progress.emit(60, "변환 중...")
                    base = Path(self.files[0]).stem + "_merged"
                    # 캠페인 모드이고 사용자가 제목을 비워뒀으면 campaign.title 을 사용.
                    if campaign_on and not self.title:
                        self.title = campaign_cfg.get("title") or self.title
                    merged_outputs: list[str] = []

                    if self.output_format in ["both", "all", "epub"]:
                        out = engine.create_epub(
                            all_entries,
                            os.path.join(output_dir, f"{base}.epub"),
                            self.title,
                            author,
                            progress_callback=engine_progress,
                        )
                        results.append(out)
                        if out:
                            merged_outputs.append(str(out))
                    if self.output_format in ["both", "all", "docx"]:
                        out = engine.create_docx(
                            all_entries,
                            os.path.join(output_dir, f"{base}.docx"),
                            self.title,
                            author,
                            progress_callback=engine_progress,
                        )
                        results.append(out)
                        if out:
                            merged_outputs.append(str(out))
                    if self.output_format in ["all", "pdf"]:
                        pdf_result = engine.create_pdf(
                            all_entries, os.path.join(output_dir, f"{base}.pdf"), self.title, author
                        )
                        if pdf_result:
                            results.append(pdf_result)
                            merged_outputs.append(str(pdf_result))

                    # 병합 변환은 입력 파일 N개를 한 record 로 기록.
                    scene_count = sum(1 for e in all_entries if e.get("type") == "scene")
                    self.last_records.append(
                        {
                            "input_file": self.files[0],  # 첫 파일을 대표로
                            "output_files": merged_outputs,
                            "output_format": self.output_format,
                            "title": self.title or base,
                            "author": author,
                            "entry_count": len(all_entries),
                            "scene_count": scene_count,
                            "success": bool(merged_outputs),
                        }
                    )

            elif self.mode == "batch":
                total_files = len(self.files)

                # 파싱 단계 병렬화 (I/O 바운드). config.performance.parse_max_workers 사용.
                from concurrent.futures import ThreadPoolExecutor

                parsed_files = {}
                self.progress.emit(10, "파일 파싱 중 (병렬)...")

                def _parse_one(fp):
                    return fp, parse_with_cache(fp)

                worker_cap = int(config.get("performance", {}).get("parse_max_workers", 4))
                worker_count = max(1, min(worker_cap, total_files))
                with ThreadPoolExecutor(max_workers=worker_count) as pool:
                    if self._stop_event.is_set():
                        raise InterruptedError("작업이 중단되었습니다.")
                    for fp, entries in pool.map(_parse_one, self.files):
                        parsed_files[fp] = entries

                # 변환 단계 (순차 - 파일 쓰기)
                for i, file_path in enumerate(self.files):
                    progress = int(30 + (60 * (i / total_files)))
                    file_name = Path(file_path).name
                    if self._stop_event.is_set():
                        raise InterruptedError("작업이 중단되었습니다.")

                    self.progress.emit(progress, f"변환 중: {file_name}")

                    entries = parsed_files.get(file_path, [])
                    if entries:
                        base = Path(file_path).stem
                        file_title = self.title or base
                        file_outputs: list[str] = []

                        if self.output_format in ["both", "all", "epub"]:
                            out = engine.create_epub(
                                entries,
                                os.path.join(output_dir, f"{base}.epub"),
                                file_title,
                                author,
                                progress_callback=engine_progress,
                            )
                            results.append(out)
                            if out:
                                file_outputs.append(str(out))
                        if self.output_format in ["both", "all", "docx"]:
                            out = engine.create_docx(
                                entries,
                                os.path.join(output_dir, f"{base}.docx"),
                                file_title,
                                author,
                                progress_callback=engine_progress,
                            )
                            results.append(out)
                            if out:
                                file_outputs.append(str(out))
                        if self.output_format in ["all", "pdf"]:
                            pdf_result = engine.create_pdf(
                                entries, os.path.join(output_dir, f"{base}.pdf"), file_title, author
                            )
                            if pdf_result:
                                results.append(pdf_result)
                                file_outputs.append(str(pdf_result))

                        # batch 모드: 파일마다 별도 record.
                        scene_count = sum(1 for e in entries if e.get("type") == "scene")
                        self.last_records.append(
                            {
                                "input_file": file_path,
                                "output_files": file_outputs,
                                "output_format": self.output_format,
                                "title": file_title,
                                "author": author,
                                "entry_count": len(entries),
                                "scene_count": scene_count,
                                "success": bool(file_outputs),
                            }
                        )

            else:
                if self.files:
                    file_path = self.files[0]
                    self.progress.emit(20, f"파싱 중: {Path(file_path).name}")
                    entries = parse_with_cache(file_path)

                    if entries:
                        self.progress.emit(60, "변환 중...")
                        base = Path(file_path).stem
                        single_outputs: list[str] = []

                        if self.output_format in ["both", "all", "epub"]:
                            out = engine.create_epub(
                                entries,
                                os.path.join(output_dir, f"{base}.epub"),
                                self.title,
                                author,
                                progress_callback=engine_progress,
                            )
                            results.append(out)
                            if out:
                                single_outputs.append(str(out))
                        if self.output_format in ["both", "all", "docx"]:
                            out = engine.create_docx(
                                entries,
                                os.path.join(output_dir, f"{base}.docx"),
                                self.title,
                                author,
                                progress_callback=engine_progress,
                            )
                            results.append(out)
                            if out:
                                single_outputs.append(str(out))
                        if self.output_format in ["all", "pdf"]:
                            pdf_result = engine.create_pdf(
                                entries, os.path.join(output_dir, f"{base}.pdf"), self.title, author
                            )
                            if pdf_result:
                                results.append(pdf_result)
                                single_outputs.append(str(pdf_result))

                        scene_count = sum(1 for e in entries if e.get("type") == "scene")
                        self.last_records.append(
                            {
                                "input_file": file_path,
                                "output_files": single_outputs,
                                "output_format": self.output_format,
                                "title": self.title or base,
                                "author": author,
                                "entry_count": len(entries),
                                "scene_count": scene_count,
                                "success": bool(single_outputs),
                            }
                        )

            self.progress.emit(100, "완료!")

            success_count = sum(1 for r in results if r)
            # last_records 에 duration_ms 추가 — 사용자가 변환마다 걸린 시간을
            # history 에서 확인 가능.
            duration_ms = int((_time.monotonic() - start_ts) * 1000)
            for rec in self.last_records:
                rec["duration_ms"] = duration_ms
            if success_count == 0:
                # 콘텐츠 필터로 항목이 모두 제거되는 등으로 출력이 0개면 '완료'가 아니라
                # 경고로 알린다(과거엔 '0개 파일 생성' 을 성공으로 표시).
                self.finished.emit(
                    False,
                    "생성된 파일이 없습니다.\n포함 설정(주사위/시스템/OOC 등)이나 "
                    "장면 분할로 모든 내용이 제외되지 않았는지 확인해 주세요.",
                )
            else:
                self.finished.emit(
                    True, f"변환 완료!\n{success_count}개 파일 생성\n출력 위치: {output_dir}"
                )

        except InterruptedError:
            logger.info("변환 작업이 사용자에 의해 중단되었습니다.")
            self.finished.emit(False, "작업이 중단되었습니다.")
        except UnicodeDecodeError as e:
            logger.error("인코딩 오류: %s", e)
            self.finished.emit(
                False,
                "파일 인코딩 오류: 지원되지 않는 인코딩입니다. "
                "UTF-8, EUC-KR, CP949 형식의 파일을 사용해주세요.",
            )
        except Exception as e:
            from core.exceptions import ConverterError

            logger.error("변환 실패: %s", e, exc_info=True)
            if isinstance(e, ConverterError):
                self.finished.emit(False, e.user_message)
            else:
                self.finished.emit(False, f"변환 실패: {e}")

    def stop(self):
        """스레드에 중지 신호를 보냅니다 (스레드 안전)."""
        self._stop_event.set()


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
        cache_enabled = gui_settings.get("cache_enabled", True)
        self.cache_service = CacheService(enabled=cache_enabled)

        # 중앙 반응형 상태 관리자
        self.app_state = AppState(config_manager, parent=self)

        # 모든 페이지에서 AppState에 접근할 수 있도록 주입
        from .pages.base_page import BasePage

        BasePage.set_app_state(self.app_state)

        # 최근 파일 관리자
        self.recent_files_manager = RecentFilesManager(config_manager)

        # 윈도우 설정
        self.setWindowTitle("TRPG Log Converter Pro")
        self.setMinimumSize(900, 600)
        self.resize(1300, 800)
        # 창 전체에서 파일 드래그 앤 드롭을 받는다. FluentWindow(프레임리스)에서는
        # 자식 드롭 영역까지 이벤트가 잘 전달되지 않는 경우가 있어, 윈도우 레벨에서
        # 받아 어디에 떨궈도 추가되게 한다(드롭 영역 밖에 떨궈도 동작).
        self.setAcceptDrops(True)

        # 테마 설정 (시스템 테마 따라감)
        setTheme(Theme.AUTO)
        setThemeColor("#0A84FF")

        # 페이지 생성 중 side-effect save 로 gui_settings.json 이 기본값으로
        # 덮여쓰이는 버그를 막기 위해 초기화 구간 동안 AppState 저장/set 을 잠근다.
        # (widget.setText → textChanged → save_settings → state.set(..) 경로로
        #  아직 초기화 안 된 다른 위젯의 기본값이 AppState 에 유입되는 것을 차단)
        self.app_state._suspend_save = True
        self.app_state._suspend_set = True
        try:
            self._setup_navigation()
            self._setup_main_layout()
            self._connect_signals()
            self._setup_shortcuts()
            self._load_recent_files()
        finally:
            self.app_state._suspend_set = False
            self.app_state._suspend_save = False

        # 타이틀바를 최상위로 올려서 드래그 이동 보장
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.raise_()

        # 백그라운드 silent 업데이트 체크 — 첫 paint 가 끝난 뒤 5초 지연.
        # dev (frozen=False) 에서는 적용 스크립트가 의미 없으므로 frozen 빌드에서만 실행.
        # 설정에서 끄려면 gui_settings['updates_check_on_startup'] = False.
        import sys

        from core.version import __update_repo__

        # repo 자체가 바뀌었으면 (private→public 마이그레이션 등) 이전에
        # 자동으로 꺼놨던 updates_check_on_startup 을 한 번 복구한다.
        # _on_update_check_result 가 private 감지 시 무음으로 끄는 안전장치를
        # 가지고 있는데, 그 결정의 전제(=옛 repo URL)가 깨졌으니 사용자가
        # 명시적으로 끄지 않은 한 다시 켜는 게 옳음.
        last_seen_repo = gui_settings.get("_updates_repo_seen")
        if last_seen_repo != __update_repo__:
            if last_seen_repo is not None and not gui_settings.get(
                "updates_check_on_startup",
                True,
            ):
                gui_settings["updates_check_on_startup"] = True
                logger.info(
                    "Update repo changed (%s → %s); re-enabling startup check.",
                    last_seen_repo,
                    __update_repo__,
                )
            gui_settings["_updates_repo_seen"] = __update_repo__
            try:
                self.config_manager.save_gui_settings(gui_settings)
            except Exception:
                logger.exception("Failed to persist _updates_repo_seen marker")

        if getattr(sys, "frozen", False) and gui_settings.get("updates_check_on_startup", True):
            QTimer.singleShot(
                UPDATE_CHECK_STARTUP_DELAY_MS,
                lambda: self._check_for_updates(silent=True),
            )

        # 첫 실행 환영 다이얼로그 — gui_settings 에 _welcome_seen 플래그가
        # 없는 사용자에게만 노출. 첫 paint 후 일정 지연으로 메인 윈도우
        # 렌더가 끝난 다음 자연스럽게 뜨도록 (WELCOME_DIALOG_DELAY_MS).
        if not gui_settings.get("_welcome_seen"):
            QTimer.singleShot(WELCOME_DIALOG_DELAY_MS, self._show_welcome_dialog)

    def _setup_navigation(self):
        """네비게이션 설정 - 4탭 구조 (홈, 서식, 파싱, 고급)"""
        # 4개 메인 페이지 생성
        self.home_page = HomePage(self.config_manager)
        self.format_style_page = FormatStylePage(self.config_manager)
        self.parsing_content_page = ParsingContentPage(self.config_manager)
        self.advanced_settings_page = AdvancedSettingsPage(self.config_manager)

        # 페이지 저장
        self.pages = {
            "home": self.home_page,
            "format_style": self.format_style_page,
            "parsing_content": self.parsing_content_page,
            "advanced": self.advanced_settings_page,
        }

        # 네비게이션 아이템 추가 (4개 탭)
        self.addSubInterface(self.home_page, FIF.PLAY_SOLID, "홈")
        self.addSubInterface(self.format_style_page, FIF.PALETTE, "서식 및 스타일")
        self.addSubInterface(self.parsing_content_page, FIF.DOCUMENT, "파싱 및 콘텐츠")

        self.navigationInterface.addSeparator(NavigationItemPosition.BOTTOM)

        self.addSubInterface(
            self.advanced_settings_page,
            FIF.DEVELOPER_TOOLS,
            "고급 설정",
            position=NavigationItemPosition.BOTTOM,
        )

        # 변환 이력
        self.navigationInterface.addItem(
            routeKey="history",
            icon=FIF.HISTORY,
            text="변환 이력",
            onClick=self._show_history_dialog,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )

        # 업데이트 확인
        self.navigationInterface.addItem(
            routeKey="check_update",
            icon=FIF.UPDATE,
            text="업데이트 확인",
            onClick=self._check_for_updates,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )

        # 정보
        self.navigationInterface.addItem(
            routeKey="about",
            icon=FIF.INFO,
            text="정보",
            onClick=self._show_about_dialog,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )

        # 종료 버튼
        self.navigationInterface.addItem(
            routeKey="quit",
            icon=FIF.POWER_BUTTON,
            text="종료",
            onClick=self.close,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )

        # 네비게이션 확장 모드
        self.navigationInterface.setExpandWidth(200)
        self.navigationInterface.setMinimumExpandWidth(200)

    def _setup_main_layout(self):
        """전역 문서 미리보기 패널을 포함한 메인 레이아웃 설정"""
        self._preview_visible = True

        # 미리보기 컨테이너 생성.
        # 최소폭은 "판형" 라벨 + 콤보(가장 긴 항목 픽셀 폭) + 줌/페이지 위젯이 한 줄에
        # 모두 들어가도록 ~340px 로 잡는다. 이보다 좁아지면 콤보가 잘려서 사용자가
        # 무슨 판형을 골랐는지 확인하기 어려워진다.
        self.preview_container = QFrame()
        self.preview_container.setObjectName("GlobalPreviewContainer")
        self.preview_container.setMinimumWidth(340)
        self.preview_container.setMaximumWidth(600)

        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        self.document_preview = DocumentPreview()
        preview_layout.addWidget(self.document_preview)

        # 스플리터 생성 및 설정
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName("MainSplitter")
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setChildrenCollapsible(False)

        # FluentWindow의 widgetLayout에 직접 삽입 (48px 상단 여백 보장)
        if hasattr(self, "widgetLayout"):
            self.widgetLayout.removeWidget(self.stackedWidget)
            self.main_splitter.addWidget(self.stackedWidget)
            self.main_splitter.addWidget(self.preview_container)
            self.widgetLayout.addWidget(self.main_splitter)
        else:
            # 폴백
            stacked_parent = self.stackedWidget.parent()
            if stacked_parent and stacked_parent.layout():
                stacked_parent.layout().addWidget(self.main_splitter)
            self.main_splitter.addWidget(self.stackedWidget)
            self.main_splitter.addWidget(self.preview_container)

        # 비율 설정 (약 55:45)
        self.main_splitter.setSizes([550, 450])
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)

        # 타이틀바가 레이아웃 변경 후에도 최상위에 오도록 보장
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.raise_()

    def resizeEvent(self, e):
        """창 크기 변경 시 타이틀바 정렬 보장"""
        super().resizeEvent(e)
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.raise_()

    def toggle_preview(self):
        """미리보기 패널 토글"""
        self._preview_visible = not self._preview_visible
        self.preview_container.setVisible(self._preview_visible)
        if self._preview_visible:
            self.main_splitter.setSizes([550, 450])

    def _connect_signals(self):
        """시그널 연결"""
        self.home_page.conversion_started.connect(self._start_conversion)
        self.home_page.files_updated.connect(self._on_files_updated)
        self.home_page.entries_parsed.connect(self._on_entries_parsed)

        # 각 페이지의 설정 변경 시 미리보기 업데이트
        for page in (
            self.format_style_page,
            self.parsing_content_page,
            self.advanced_settings_page,
        ):
            page.settings_changed.connect(self._update_document_preview)

        # AppState 그룹 변경 시 미리보기 자동 갱신
        self.app_state.group_changed.connect(self._on_state_group_changed)

        # 페이지 전환 시 on_page_enter 호출 (설정 동기화)
        self.stackedWidget.currentChanged.connect(self._on_page_changed)

    def _on_page_changed(self, index: int):
        """페이지 전환 시 호출"""
        if self._current_page is not None:
            self._current_page.on_page_leave()

        current_widget = self.stackedWidget.widget(index)
        self._current_page = current_widget

        if current_widget is not None:
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

        # ⌘+H: 변환 이력 다이얼로그
        history_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        history_shortcut.activated.connect(self._show_history_dialog)

        # ⌘+P: 미리보기 토글
        preview_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        preview_shortcut.activated.connect(self.toggle_preview)

        # ⌘+1~4: 4탭 페이지 전환
        page_keys = ["home", "format_style", "parsing_content", "advanced"]
        for i, key in enumerate(page_keys, 1):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda k=key: self._switch_to_page(k))

    def _shortcut_open_files(self):
        """단축키로 파일 열기"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "로그 파일 선택", "", "지원 형식 (*.html *.htm *.txt);;모든 파일 (*.*)"
        )
        if files:
            self.home_page._on_files_dropped(files)
            self._switch_to_page("home")

    def _switch_to_page(self, page_key: str):
        """특정 페이지로 전환"""
        if page_key in self.pages:
            self.stackedWidget.setCurrentWidget(self.pages[page_key])

    def _on_files_updated(self, files: list):
        """파일 목록 업데이트 시"""
        if files:
            self.recent_files_manager.add_files(files)
            self._load_recent_files()
        else:
            self.home_page._parsed_entries = []

    def _on_entries_parsed(self, entries: list):
        """엔트리 파싱 완료 시 - 미리보기 업데이트"""
        if self.document_preview and entries:
            settings = self.app_state.get_preview_settings()
            self.document_preview.update_preview(entries=entries, settings=settings)

    def _update_document_preview(self):
        """문서 미리보기 업데이트 (설정 변경 시)"""
        if self.document_preview and self.home_page._parsed_entries:
            settings = self.app_state.get_preview_settings()
            self.document_preview.update_settings(**settings)

    def _on_state_group_changed(self, group: str):
        """AppState 그룹 변경 시 미리보기 자동 갱신.

        style, font, decoration, cover, basic 그룹이 변경되면
        DocumentPreview를 업데이트합니다.
        """
        if not AppState.is_preview_group(group):
            return
        if self.document_preview and self.home_page._parsed_entries:
            settings = self.app_state.get_preview_settings()
            self.document_preview.update_settings(**settings)

    def _collect_preview_settings(self) -> dict:
        """미리보기용 설정 수집 - AppState에서 통합 설정 반환.

        하위 호환성을 위해 유지합니다.
        새로운 코드에서는 self.app_state.get_preview_settings()를 직접 사용하세요.
        """
        return self.app_state.get_preview_settings()

    def export_settings(self):
        """설정 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "설정 내보내기", "trpg_converter_settings.json", "JSON 파일 (*.json)"
        )

        if not file_path:
            return

        try:
            settings = self.config_manager.get_gui_settings()

            # base64 이미지 데이터는 제외 (파일 크기 문제)
            export_settings = {
                k: v for k, v in settings.items() if not (isinstance(v, str) and len(v) > 10000)
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_settings, f, ensure_ascii=False, indent=2)

            InfoBar.success(
                title="내보내기 완료",
                content=f"설정이 저장되었습니다: {Path(file_path).name}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_INFO_MS,
            )
        except Exception as e:
            InfoBar.error(
                title="내보내기 실패",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_WARNING_MS,
            )

    def import_settings(self):
        """설정 가져오기"""
        file_path, _ = QFileDialog.getOpenFileName(self, "설정 가져오기", "", "JSON 파일 (*.json)")

        if not file_path:
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                imported = json.load(f)
            imported.pop("_meta", None)

            # 현재 설정과 병합
            current = self.config_manager.get_gui_settings()
            current.update(imported)
            self.config_manager.save_gui_settings(current)

            # AppState 다시 로드
            self.app_state.load()

            # 페이지 리로드 중 widget signal 이 save_settings 를 거쳐 기본값으로
            # AppState/디스크를 오염시키는 것을 막기 위해 set/save 를 잠근다.
            original_save = self.config_manager.save_gui_settings
            self.config_manager.save_gui_settings = lambda _s: None
            self.app_state._suspend_set = True
            try:
                for page in self.pages.values():
                    page.load_settings()
            finally:
                self.app_state._suspend_set = False
                self.config_manager.save_gui_settings = original_save

            # 리로드 완료 후 import 값을 최종 확정
            self.config_manager.save_gui_settings(current)
            self.app_state.load()

            InfoBar.success(
                title="가져오기 완료",
                content="설정이 적용되었습니다. 일부 설정은 앱 재시작 후 적용됩니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_INFO_MS,
            )
        except Exception as e:
            InfoBar.error(
                title="가져오기 실패",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_WARNING_MS,
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
                log_text = (
                    f"... (최근 50줄만 표시, 총 {len(self._conversion_log)}줄)\n\n" + log_text
                )

        w = MessageBox("변환 로그", log_text, self)
        w.exec()

    def get_recent_files(self) -> list:
        """최근 파일 목록 반환"""
        return self.recent_files_manager.get_files()

    def _load_recent_files(self):
        """최근 파일 목록을 홈 페이지에 로드"""
        recent = self.recent_files_manager.get_files()
        self.home_page.load_recent_files(recent)

    def _start_conversion(self):
        """변환 시작"""
        if self._worker is not None and self._worker.isRunning():
            InfoBar.warning(
                title="변환 진행 중",
                content="이전 변환이 끝난 뒤 다시 시도해주세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_INFO_MS,
            )
            return

        files = self.home_page.get_files()
        if not files:
            InfoBar.warning(
                title="파일 없음",
                content="변환할 파일을 추가해주세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_INFO_MS,
            )
            return

        title = self.home_page.get_title()
        mode = self.home_page.get_convert_mode()
        output_format = self.home_page.get_output_format()
        preset_config = self.home_page.get_preset_config()

        character_colors = self.format_style_page.get_character_colors()

        # 모든 페이지 설정 저장 (위젯 값을 AppState로 동기화)
        for page in self.pages.values():
            page.on_page_enter()
            page.save_settings()

        self._cleanup_worker()

        self._worker = ConversionWorker(
            self.config_manager,
            files,
            title,
            mode,
            output_format,
            preset_config=preset_config,
            character_colors=character_colors,
            cache_service=self.cache_service,
        )
        self._worker.progress.connect(self._on_conversion_progress)
        self._worker.finished.connect(self._on_conversion_finished)
        self._worker.start()

    def _cleanup_worker(self) -> None:
        """이전 워커의 시그널을 명시적으로 해제하고 참조를 비웁니다."""
        worker = self._worker
        if worker is None:
            return
        with contextlib.suppress(TypeError, RuntimeError):
            worker.progress.disconnect(self._on_conversion_progress)
        with contextlib.suppress(TypeError, RuntimeError):
            worker.finished.disconnect(self._on_conversion_finished)
        if not worker.isRunning():
            worker.deleteLater()
            self._worker = None

    def _on_conversion_progress(self, value: int, message: str):
        """변환 진행 상태 업데이트"""
        self.home_page.update_progress(value, message)
        self.add_conversion_log(f"[{value}%] {message}")

    def _on_conversion_finished(self, success: bool, message: str):
        """변환 완료 처리 — HistoryManager 자동 기록.

        완료/실패 토스트(InfoBar)는 home_page.conversion_complete() 가 띄운다.
        여기서 또 띄우면 '변환 완료'가 두 번 떠서, 이 함수에서는 띄우지 않는다.
        """
        self.home_page.conversion_complete(success, message)

        # Worker 가 보관한 각 파일의 결과 → HistoryManager 에 영구 저장.
        # 실패 (worker 예외) 시 last_records 가 비어 있을 수 있어 대비.
        worker = self._worker
        if worker is not None and self.config_manager.history is not None:
            records = getattr(worker, "last_records", [])
            for rec in records:
                try:
                    self.config_manager.history.add_record(
                        input_file=rec["input_file"],
                        output_files=rec.get("output_files", []),
                        output_format=rec.get("output_format", ""),
                        title=rec.get("title", ""),
                        author=rec.get("author", ""),
                        entry_count=rec.get("entry_count", 0),
                        scene_count=rec.get("scene_count", 0),
                        success=rec.get("success", success),
                        error_message=None if rec.get("success") else message,
                        duration_ms=rec.get("duration_ms", 0),
                    )
                except Exception:
                    logger.exception("Failed to record conversion to history")

        # 완료/실패 토스트는 home_page.conversion_complete() 가 이미 띄웠다.
        # (중복 InfoBar 제거 — '변환 완료'가 두 번 뜨던 문제)

    _SHUTDOWN_WORKER_TIMEOUT_MS = CONVERT_WORKER_SHUTDOWN_TIMEOUT_MS

    # ------------------------------------------------------------------
    # About / Update
    # ------------------------------------------------------------------

    def _show_about_dialog(self) -> None:
        """앱 정보 다이얼로그 표시."""
        from gui.dialogs import AboutDialog

        AboutDialog(self).exec()

    def _show_history_dialog(self) -> None:
        """변환 이력 다이얼로그 표시."""
        from gui.dialogs import HistoryDialog

        hm = self.config_manager.history
        if hm is None:
            InfoBar.warning(
                title="이력 기능 불가",
                content="이력 관리자 로드에 실패했습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_INFO_MS,
            )
            return
        HistoryDialog(hm, self).exec()

    def _open_releases_page(self) -> None:
        """시스템 브라우저로 GitHub Releases 페이지 열기.

        Private 저장소 운영 시 자동 업데이트가 동작하지 않으므로 사용자가
        브라우저 (GitHub 로그인) 에서 직접 새 버전 다운받게 하는 fallback.
        """
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from core.version import __homepage__

        QDesktopServices.openUrl(QUrl(f"{__homepage__}/releases/latest"))

    def _show_welcome_dialog(self) -> None:
        """첫 실행 환영 다이얼로그.

        결과 처리:
          - 사용자가 [시작하기] 누름                   → _welcome_seen=True 영구화
          - "다음부터 보지 않기" 체크 + 시작하기         → _welcome_seen=True 영구화
          - 창을 X 로 닫음 (dismiss)                  → 다음 실행에 다시 노출
        """
        from gui.dialogs import WelcomeDialog

        dlg = WelcomeDialog(self)
        result = dlg.exec()
        if result == WelcomeDialog.Accepted:
            settings = self.config_manager.get_gui_settings()
            settings["_welcome_seen"] = True
            self.config_manager.save_gui_settings(settings)

    def _check_for_updates(self, _checked: bool = False, *, silent: bool = False) -> None:
        """GitHub Releases 에서 최신 버전 확인.

        silent=True : 새 버전이 없을 때 토스트 안 띄움 (앱 시작 시 자동 체크).
        silent=False: 항상 결과 알림 (메뉴에서 사용자가 직접 누른 경우).

        ``_checked`` 위치 인자
        ----------------------
        qfluentwidgets NavigationPushButton 의 ``clicked = Signal(bool)`` 이
        emit 할 때 ``True`` 를 위치 인자로 전달합니다. 현재 PySide6 는 keyword-
        only slot 에 대해 잉여 positional 을 자동 drop 해 주지만, 이건 구현
        세부에 의존하는 동작이라 (Qt 6.x 마이너 버전이 바뀌면 깨질 수 있음)
        명시적으로 받아두는 게 안전합니다. 값 자체는 사용하지 않습니다.

        네트워크 요청은 별도 스레드에서 — UI 가 멈추지 않도록.
        """
        from core.services.updater import UpdateService

        logger.info("[update] _check_for_updates entry (silent=%s)", silent)

        # 1) 중복 실행 가드 — 사용자가 메뉴를 연타하거나 silent 체크가 이미
        #    돌고 있을 때 동일 worker 가 여러개 떠서 thread 정리가 꼬이는 것을
        #    막는다.
        existing = getattr(self, "_update_check_thread", None)
        if existing is not None and existing.isRunning():
            logger.info("[update] duplicate guard — existing check still running")
            if not silent:
                InfoBar.info(
                    title="이미 확인 중",
                    content="업데이트 확인이 진행 중입니다. 잠시만 기다려주세요.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=INFOBAR_DURATION_TRANSIENT_MS,
                )
            return

        # 2) 사용자 액션이면 즉시 시각 피드백.
        #    Sticky InfoBar — 결과 도착 시 _on_update_check_result 가 close() 함.
        #    또한 hard-timeout watchdog (아래) 이 만일에 worker 가 응답 안 줄 때
        #    강제로 close + 에러 InfoBar 를 띄움.
        #    isClosable=True — 사용자가 직접 X 눌러 dismiss 할 수 있게 (안전망).
        self._update_check_progress_bar = None
        if not silent:
            self._update_check_progress_bar = InfoBar.info(
                title="업데이트 확인 중",
                content="GitHub 에서 최신 버전을 조회하고 있어요...",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_STICKY,
                isClosable=True,
            )
            logger.info("[update] sticky progress InfoBar shown")

        worker = _UpdateCheckWorker(UpdateService())
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        # 결과 핸들러는 반드시 메인(GUI) 스레드에서 실행돼야 한다.
        # worker.finished 를 context 없는 lambda 에 연결하면 Qt 가 이를
        # DirectConnection 으로 처리해 슬롯이 'worker 스레드'에서 돌고, 거기서
        # InfoBar(위젯) 생성·QTimer 조작을 하면 UI 가 프리즈/크래시한다.
        # self(메인스레드 QObject)의 bound method 에 QueuedConnection 으로 연결해
        # 메인스레드 이벤트 루프에서 실행되도록 강제한다.
        self._pending_update_silent = silent
        worker.finished.connect(self._dispatch_update_check_result, Qt.QueuedConnection)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        # 사라진 thread 참조를 정리하는 콜백 — closeEvent 에서 cleanup 로직과 연계.
        thread.finished.connect(self._on_update_check_thread_finished)
        thread.start()
        logger.info("[update] worker thread started")
        # 참조 유지 (GC 방지)
        self._update_check_thread = thread
        self._update_check_worker = worker

        # 3) Hard-timeout watchdog — 어떤 이유로든 (urlopen 후크 누락, signal
        #    드롭, qfluentwidgets 버그 등) 결과가 안 돌아오면 UI 가 영원히 sticky
        #    InfoBar 와 함께 멈춤 상태로 보임. 이 timer 가 결정적으로 그것을 막음.
        #    결과 핸들러가 정상 실행되면 timer 는 stop() 으로 무력화됨.
        self._update_check_watchdog = QTimer(self)
        self._update_check_watchdog.setSingleShot(True)
        self._update_check_watchdog.timeout.connect(lambda: self._on_update_check_timeout(silent))
        self._update_check_watchdog.start(UPDATE_CHECK_HARD_TIMEOUT_MS)
        logger.info("[update] hard-timeout watchdog armed (%dms)", UPDATE_CHECK_HARD_TIMEOUT_MS)

    def _on_update_check_timeout(self, silent: bool) -> None:
        """Hard-timeout 발동 — worker 가 응답 없음. UI 를 항상 깨끗하게 복구."""
        from core.constants import INFOBAR_DURATION_WARNING_MS

        thread = getattr(self, "_update_check_thread", None)
        if thread is None or not thread.isRunning():
            # 결과가 timeout 직전에 도착했으면 아무것도 안 해도 됨.
            logger.info("[update] watchdog fired but thread already done — no-op")
            return
        logger.warning(
            "[update] HARD TIMEOUT — worker did not respond in %dms; forcing cleanup",
            self._update_check_watchdog.interval(),
        )
        # sticky InfoBar 강제 close.
        bar = getattr(self, "_update_check_progress_bar", None)
        if bar is not None:
            try:
                bar.close()
            except Exception:
                logger.exception("[update] failed to force-close sticky InfoBar")
            self._update_check_progress_bar = None
        # 스레드 정리는 closeEvent 의 graceful shutdown 에 위임 — 강제 terminate 는
        # 데이터 손상 위험. 대신 사용자 안내만.
        if not silent:
            InfoBar.warning(
                title="응답이 없어요",
                content=("업데이트 서버 응답이 늦어지고 있어요. 잠시 후 다시 시도해주세요."),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_WARNING_MS,
            )

    def _on_update_check_thread_finished(self) -> None:
        """Thread 정상 종료 시 우리 쪽 참조도 해제 — 그래야 다음 클릭이 동작."""
        self._update_check_thread = None
        self._update_check_worker = None

    def _dispatch_update_check_result(self, info) -> None:
        """worker.finished 를 '메인스레드'에서 받기 위한 bound-method 디스패처.

        worker.finished 를 context 없는 lambda 에 직접 연결하면 슬롯이 worker
        스레드에서 실행되어 InfoBar/QTimer 등 위젯 조작 시 프리즈/크래시한다.
        self 의 bound method 로 받으면 Qt 가 QueuedConnection 으로 메인스레드
        이벤트 루프에 디스패치한다. silent 플래그는 중복 가드 덕에 동시 실행이
        없으므로 인스턴스 속성으로 안전하게 전달한다.
        """
        silent = getattr(self, "_pending_update_silent", False)
        self._on_update_check_result(info, silent)

    def _on_update_check_result(self, info, silent: bool) -> None:
        """결과 InfoBar 분기 — outcome 별로 정확한 메시지.

        worker 가 끝나면서 self._update_check_worker._service.last_outcome 에
        결과 코드가 들어 있음 (이미 deleteLater 됐으면 attribute 가 사라져
        있을 수 있어 안전 fallback).
        """
        from core.services.updater import CheckOutcome, UpdateService

        logger.info(
            "[update] result handler entry: info=%s, silent=%s",
            "None" if info is None else f"v{info.version}",
            silent,
        )

        # Hard-timeout watchdog 무력화 — 정상 도착이니까 더 이상 강제 cleanup 불필요.
        watchdog = getattr(self, "_update_check_watchdog", None)
        if watchdog is not None:
            try:
                watchdog.stop()
                watchdog.deleteLater()
            except Exception:
                logger.exception("[update] watchdog disarm failed")
            self._update_check_watchdog = None

        # sticky "조회 중" InfoBar 가 떠 있으면 닫는다 — 결과 표시 직전에 정리해야
        # 사용자에게 끊김 없는 전환이 보임.
        progress_bar = getattr(self, "_update_check_progress_bar", None)
        if progress_bar is not None:
            try:
                progress_bar.close()
            except Exception:
                logger.exception("Failed to close update-checking InfoBar")
            self._update_check_progress_bar = None

        # last_outcome 추출 (worker 가 이미 GC 된 경우 LATEST 로 fallback).
        outcome = CheckOutcome.LATEST
        worker = getattr(self, "_update_check_worker", None)
        if worker is not None:
            service = getattr(worker, "_service", None)
            if service is not None:
                outcome = getattr(service, "last_outcome", CheckOutcome.LATEST)
        logger.info("[update] outcome=%s", outcome)

        if info is None:
            if silent:
                # silent 모드 (앱 시작 시 자동 체크) 에서 private 감지되면
                # 다음 부팅부터 자동 체크 비활성화 — 사용자 동작 없이 묵묵히.
                if outcome == CheckOutcome.PRIVATE_OR_MISSING:
                    settings = self.config_manager.get_gui_settings()
                    if settings.get("updates_check_on_startup", True):
                        settings["updates_check_on_startup"] = False
                        self.config_manager.save_gui_settings(settings)
                        logger.info(
                            "Auto-disabled startup update check after detecting "
                            "private/missing release endpoint."
                        )
                return
            if outcome == CheckOutcome.PRIVATE_OR_MISSING:
                # 명시적 [업데이트 확인] 클릭 — 사용자에게 명확한 다음 액션 제시.
                bar = InfoBar.warning(
                    title="저장소가 비공개입니다",
                    content=(
                        "자동 업데이트가 동작하지 않아요. "
                        "[정보 → 새 버전 받기] 로 GitHub Releases 페이지를 직접 열거나, "
                        "고급 설정에서 자동 체크를 꺼두실 수 있어요."
                    ),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=INFOBAR_DURATION_ATTENTION_MS,
                )
                # InfoBar action 버튼 추가 — qfluentwidgets InfoBar 는
                # addWidget 으로 임의 위젯을 받음.
                try:
                    from qfluentwidgets import PushButton as FluentButton

                    btn = FluentButton("Releases 페이지 열기")
                    btn.clicked.connect(self._open_releases_page)
                    bar.addWidget(btn)
                except Exception:
                    pass
            elif outcome == CheckOutcome.NETWORK_ERROR:
                InfoBar.warning(
                    title="네트워크 오류",
                    content="GitHub 에 연결하지 못했어요. 인터넷 연결을 확인해주세요.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=INFOBAR_DURATION_WARNING_MS,
                )
            elif outcome == CheckOutcome.PARSE_ERROR:
                InfoBar.warning(
                    title="응답 해석 실패",
                    content="GitHub 응답을 처리하지 못했어요. 잠시 후 다시 시도해주세요.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=INFOBAR_DURATION_WARNING_MS,
                )
            else:  # LATEST
                InfoBar.info(
                    title="최신 버전입니다",
                    content="현재 사용 중인 버전이 최신입니다.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=INFOBAR_DURATION_INFO_MS,
                )
            return

        from gui.dialogs import UpdateDialog

        UpdateDialog(info, UpdateService(), self).exec()

    # ──────────── 창 전체 파일 드래그 앤 드롭 ────────────
    def dragEnterEvent(self, event):
        """파일 URL 이 드래그되면 수락 표시."""
        md = event.mimeData()
        if md is not None and md.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        md = event.mimeData()
        if md is not None and md.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """떨궈진 파일 중 지원 형식(.html/.htm/.txt)만 홈 페이지에 추가."""
        md = event.mimeData()
        if md is None or not md.hasUrls():
            event.ignore()
            return
        supported = (".html", ".htm", ".txt")
        paths = []
        for url in md.urls():
            p = url.toLocalFile()
            if p and p.lower().endswith(supported):
                paths.append(p)
        if paths:
            self.home_page._on_files_dropped(paths)
            self._switch_to_page("home")
            event.acceptProposedAction()
        else:
            event.ignore()

    def closeEvent(self, event):
        """윈도우 닫기 이벤트.

        - 현재 페이지 leave 콜백 호출
        - 설정 영속화
        - 진행 중 워커가 있으면 사용자 확인 후 정리
        - AppState/cache 시그널 정리
        """
        if self._current_page is not None:
            try:
                self._current_page.on_page_leave()
            except Exception:
                logger.exception("on_page_leave 호출 실패")

        for page in self.pages.values():
            try:
                page.save_settings()
            except Exception:
                logger.exception("페이지 설정 저장 실패: %s", type(page).__name__)

        try:
            self.app_state.save()
        except Exception:
            logger.exception("AppState 영속화 실패")

        if self._worker is not None and self._worker.isRunning():
            reply = QMessageBox.question(
                self,
                "변환 중",
                "변환이 진행 중입니다. 정말 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

            self._worker.stop()
            if not self._worker.wait(self._SHUTDOWN_WORKER_TIMEOUT_MS):
                logger.warning(
                    "변환 워커가 %d ms 내에 종료되지 않아 강제 종료합니다.",
                    self._SHUTDOWN_WORKER_TIMEOUT_MS,
                )
                self._worker.terminate()
                self._worker.wait(THREAD_TERMINATE_GRACE_MS)

        self._cleanup_worker()

        # 업데이트 체크 thread 정리 — 진행 중일 수 있음 (urlopen 블로킹).
        # 정리 안 하면 Qt 가 "QThread destroyed while running" abort 를 띄움.
        update_thread = getattr(self, "_update_check_thread", None)
        if update_thread is not None and update_thread.isRunning():
            logger.info("Waiting for update check thread to finish...")
            update_thread.quit()
            # urlopen 의 timeout 은 4초 → 약간 더 줘서 5초 대기.
            if not update_thread.wait(UPDATE_THREAD_SHUTDOWN_TIMEOUT_MS):
                logger.warning("Update check thread did not finish in time; forcing terminate")
                update_thread.terminate()
                update_thread.wait(THREAD_TERMINATE_GRACE_MS)
        self._update_check_thread = None
        self._update_check_worker = None

        with contextlib.suppress(TypeError, RuntimeError):
            self.app_state.group_changed.disconnect(self._on_state_group_changed)

        event.accept()
