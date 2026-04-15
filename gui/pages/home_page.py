"""
TRPG Log Converter Pro - 홈 페이지
파일 선택, 기본 설정, 변환 옵션, 프리셋, 변환 실행을 하나의 페이지에 통합.
ConvertPage와 BasicPage(나레이터/언어)를 병합한 메인 워크플로우 페이지.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QFileDialog, QFrame, QButtonGroup
)
from PySide6.QtCore import Signal, Qt, QTimer
from pathlib import Path
import os
import logging

from qfluentwidgets import (
    BodyLabel, PushButton, PrimaryPushButton, LineEdit, ComboBox,
    RadioButton, ProgressBar, InfoBar, InfoBarPosition,
    FluentIcon as FIF,
)

from .base_page import BasePage
from ..components import ContentCard, CollapsibleSection, FileDropArea, HelpButton
from ..components.setting_cards import (
    HelpableLineEditCard, HelpableComboBoxCard, FluentSettingGroup,
)
from ..theme import LANGUAGE_MAP, LANGUAGE_REVERSE_MAP, DEFAULTS, Sizes, Spacing
from core.services import PresetService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _ensure_str(value, default=""):
    """리스트/기타 타입을 문자열로 안전하게 변환.
    narrators 등 내부적으로 문자열로 저장해야 하는 필드에 사용한다.
    """
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value) if value is not None else default


# ---------------------------------------------------------------------------
# HomePage
# ---------------------------------------------------------------------------

class HomePage(BasePage):
    """홈 페이지 - 파일 선택 · 기본 설정 · 변환 실행을 하나로 통합한 메인 워크플로우 페이지"""

    # --- 시그널 ---
    conversion_requested = Signal()       # 변환 시작 요청 (외부 컨트롤러에서 수신)
    conversion_started = Signal()         # 하위 호환: 변환 시작
    conversion_finished = Signal(bool, str)  # 변환 완료 (성공 여부, 메시지)
    files_updated = Signal(list)          # 파일 목록 변경
    entries_parsed = Signal(list)         # 엔트리 파싱 완료

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)

        self.files: list[str] = []
        self.preset_service = PresetService()
        self._parsed_entries: list = []

        # 미리보기 업데이트 디바운스 타이머 (대용량 파일 UI 블로킹 방지)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(500)
        self._preview_timer.timeout.connect(self._do_update_preview)
        self._pending_preview_files: list | None = None

        self._setup_page()

    # ==================================================================
    # UI 구성
    # ==================================================================

    def _setup_page(self):
        """페이지 전체 UI를 플랫(비-아코디언) 레이아웃으로 구성한다."""

        # ── 1. 헤더 ──
        self.add_header("로그 변환", "TRPG 채팅 로그를 EPUB/DOCX/PDF 형식으로 변환합니다")

        # ── 2. 파일 선택 카드 ──
        self._build_file_card()

        # ── 3. 최근 파일 카드 ──
        self._build_recent_card()

        # ── 4. 기본 설정 카드 (제목/저자/플랫폼/나레이터/언어) ──
        self._build_settings_card()

        # ── 5. 변환 옵션 카드 (모드/출력 형식) ──
        self._build_options_card()

        # ── 6. 프리셋 카드 ──
        self._build_preset_card()

        # ── 7. 변환 실행 카드 ──
        self._build_convert_card()

        self.add_stretch()
        self.load_settings()

    # ------------------------------------------------------------------
    # 2. 파일 선택 카드
    # ------------------------------------------------------------------

    def _build_file_card(self):
        """소스 파일 드래그 앤 드롭 + 파일 목록 + 관리 버튼"""
        file_card = ContentCard("파일 선택", "변환할 로그 파일을 추가하세요")

        # 드래그 앤 드롭 영역
        self.drop_area = FileDropArea()
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        file_card.add_widget(self.drop_area)

        file_card.add_spacing(8)

        # 파일 목록 (드래그로 순서 변경 가능)
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(80)
        self.file_list.setMaximumHeight(200)
        self.file_list.setDragDropMode(QListWidget.InternalMove)
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        file_card.add_widget(self.file_list)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(Spacing.SM)

        add_btn = PushButton("파일 추가")
        add_btn.setMinimumHeight(Sizes.BUTTON_SM_H)
        add_btn.clicked.connect(self._add_files)
        btn_row.addWidget(add_btn)

        folder_btn = PushButton("폴더 추가")
        folder_btn.setMinimumHeight(Sizes.BUTTON_SM_H)
        folder_btn.clicked.connect(self._add_folder)
        btn_row.addWidget(folder_btn)

        btn_row.addStretch()

        remove_btn = PushButton("선택 제거")
        remove_btn.setMinimumHeight(Sizes.BUTTON_SM_H)
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(remove_btn)

        clear_btn = PushButton("전체 삭제")
        clear_btn.setMinimumHeight(Sizes.BUTTON_SM_H)
        clear_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(clear_btn)

        file_card.add_layout(btn_row)
        self.content_layout.addWidget(file_card)

        # 로그 추출 가이드 (접힌 상태)
        self._build_log_guide()

    # ------------------------------------------------------------------
    # 2-1. 로그 추출 가이드
    # ------------------------------------------------------------------

    def _build_log_guide(self):
        """플랫폼별 로그 추출 방법 안내"""
        guide_section = CollapsibleSection("로그 추출 방법 안내", expanded=False)

        # Roll20 가이드
        roll20_card = ContentCard(
            "Roll20 채팅 로그 추출",
            help_text="Roll20에서 채팅 로그를 HTML 파일로 다운로드하는 방법입니다."
        )
        roll20_guide = BodyLabel(
            "1. Roll20 캠페인에 접속합니다\n"
            "2. 우측 상단 톱니바퀴 > 'Chat Archive' (채팅 아카이브) 클릭\n"
            "3. 날짜 범위를 선택하고 'View Monthly Chat Archive' 클릭\n"
            "4. 브라우저에 채팅 로그가 표시되면\n"
            "   Ctrl+S (또는 Cmd+S)로 '웹 페이지, HTML만' 저장\n"
            "5. 저장된 .html 파일을 여기에 드래그하세요\n"
            "\n"
            "* GM/DM만 Chat Archive에 접근할 수 있습니다\n"
            "* Pro 구독 시 API 스크립트로 더 상세한 로그 추출 가능\n"
            "* Chat Archive가 없는 경우: 게임 화면에서\n"
            "  채팅 창 우클릭 > '전체 선택' > 메모장에 붙여넣기 후\n"
            "  .txt 파일로 저장하여 사용할 수 있습니다"
        )
        roll20_guide.setWordWrap(True)
        roll20_guide.setObjectName("GuideLabel")
        roll20_card.add_widget(roll20_guide)
        guide_section.add_card(roll20_card)

        # 코코포리아 가이드
        coco_card = ContentCard(
            "코코포리아 (Cocofolia) 로그 추출",
            help_text="코코포리아에서 채팅 로그를 다운로드하는 방법입니다."
        )
        coco_guide = BodyLabel(
            "1. 코코포리아 세션 종료 후 '로그' 탭 클릭\n"
            "2. '로그 다운로드' 또는 '로그 저장' 버튼 클릭\n"
            "3. HTML 형식으로 저장됩니다\n"
            "4. 저장된 .html 파일을 여기에 드래그하세요\n"
            "\n"
            "* 채널별로 로그가 분리되어 저장됩니다\n"
            "* [메인] 채널 로그를 사용하는 것을 권장합니다\n"
            "* 잡담 채널 등은 '고급 설정 > 제외할 채널'에서 필터링 가능"
        )
        coco_guide.setWordWrap(True)
        coco_guide.setObjectName("GuideLabel")
        coco_card.add_widget(coco_guide)
        guide_section.add_card(coco_card)

        # TXT 형식 가이드
        txt_card = ContentCard(
            "텍스트(.txt) 파일 형식",
            help_text="직접 정리한 텍스트 로그도 변환할 수 있습니다."
        )
        txt_guide = BodyLabel(
            "지원되는 텍스트 형식:\n"
            "  이름 : 대사       (콜론 형식 - 코코포리아 스타일)\n"
            "  [이름] 대사       (대괄호 형식)\n"
            "  (이름) 대사       (소괄호 형식)\n"
            "  이름\\t대사        (탭 구분 형식)\n"
            "\n"
            "* UTF-8 인코딩으로 저장해주세요\n"
            "* 파일 확장자: .txt, .log, .html 지원"
        )
        txt_guide.setWordWrap(True)
        txt_guide.setObjectName("GuideLabel")
        txt_card.add_widget(txt_guide)
        guide_section.add_card(txt_card)

        self.content_layout.addWidget(guide_section)

    # ------------------------------------------------------------------
    # 3. 최근 파일 카드
    # ------------------------------------------------------------------

    def _build_recent_card(self):
        """최근에 작업한 파일 목록 + 추가/지우기 버튼"""
        recent_card = ContentCard("최근 파일", "최근에 작업한 파일을 빠르게 열기")

        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(60)
        self.recent_list.setMaximumHeight(120)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_file_clicked)
        self.recent_list.setSelectionMode(QListWidget.ExtendedSelection)
        recent_card.add_widget(self.recent_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(Spacing.SM)

        load_btn = PushButton("선택 항목 추가")
        load_btn.clicked.connect(self._add_selected_recent)
        btn_row.addWidget(load_btn)

        clear_btn = PushButton("목록 지우기")
        clear_btn.clicked.connect(self._clear_recent_files)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        recent_card.add_layout(btn_row)

        self.content_layout.addWidget(recent_card)

    # ------------------------------------------------------------------
    # 4. 기본 설정 카드 (ConvertPage + BasicPage 병합)
    # ------------------------------------------------------------------

    def _build_settings_card(self):
        """제목 · 저자 · 플랫폼 · 나레이터 · 언어 · 출력 폴더를 FluentSettingGroup으로 배치"""
        group = FluentSettingGroup("기본 설정", self.scroll_widget)

        # 제목
        self.title_card = HelpableLineEditCard(
            FIF.EDIT, "제목", "변환될 문서의 제목",
            placeholder="TRPG 리플레이",
            help_text="EPUB/DOCX 파일에 표시될 제목",
        )
        group.addSettingCard(self.title_card)

        # 저자
        self.author_card = HelpableLineEditCard(
            FIF.PEOPLE, "저자", "문서 저자",
            placeholder="GM",
            help_text="메타데이터에 기록될 저자명",
        )
        group.addSettingCard(self.author_card)

        # 플랫폼
        self.platform_card = HelpableComboBoxCard(
            FIF.GLOBE, "플랫폼", "로그 출처 플랫폼",
            options=["cocofolia", "roll20", "auto"],
            default="cocofolia",
            help_text="로그 출처 플랫폼 (auto는 자동 감지)",
        )
        group.addSettingCard(self.platform_card)

        # 나레이터 이름 (BasicPage에서 흡수)
        self.narrators_card = HelpableLineEditCard(
            FIF.CHAT, "나레이터", "나레이션 처리할 이름 목록 (쉼표 구분)",
            placeholder=DEFAULTS["narrators"],
            default=_ensure_str(
                self.settings.get("narrators"), DEFAULTS["narrators"]
            ),
            help_text="이 이름들의 대사는 나레이션으로 처리됩니다. 쉼표로 구분 (예: GM, KP, DM)",
        )
        group.addSettingCard(self.narrators_card)

        # 언어 (BasicPage에서 흡수) - 표시명으로 보여주고 코드로 저장
        lang_code = self.settings.get("language", DEFAULTS["language"])
        lang_display = LANGUAGE_REVERSE_MAP.get(
            lang_code, list(LANGUAGE_MAP.keys())[0]
        )
        self.language_card = HelpableComboBoxCard(
            FIF.LANGUAGE, "언어", "문서 언어 설정",
            options=list(LANGUAGE_MAP.keys()),
            default=lang_display,
            help_text="EPUB 메타데이터에 기록되는 문서 언어입니다.",
        )
        group.addSettingCard(self.language_card)

        # 출력 폴더 — HelpableLineEditCard는 찾아보기 버튼을 지원하지 않으므로
        # ContentCard로 별도 구성하여 group 아래에 배치
        output_card = ContentCard("출력 폴더", "변환된 파일이 저장될 폴더")

        self.output_entry = LineEdit()
        self.output_entry.setText("./export")
        self.output_entry.setMinimumHeight(Sizes.BUTTON_MD_H)

        browse_btn = PushButton("찾아보기")
        browse_btn.clicked.connect(self._browse_output)
        browse_btn.setFixedWidth(100)
        browse_btn.setMinimumHeight(Sizes.BUTTON_MD_H)

        output_widget = QWidget()
        output_layout = QHBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(Spacing.SM)
        output_layout.addWidget(self.output_entry)
        output_layout.addWidget(browse_btn)

        output_card.add_widget(output_widget)

        self.content_layout.addWidget(group)
        self.content_layout.addWidget(output_card)

    # ------------------------------------------------------------------
    # 5. 변환 옵션 카드
    # ------------------------------------------------------------------

    def _build_options_card(self):
        """변환 모드(단일/병합/일괄) + 출력 형식(EPUB/DOCX/PDF) 선택"""
        options_card = ContentCard("변환 옵션", "변환 모드 및 출력 형식 선택")

        # ── 변환 모드 ──
        mode_header = QHBoxLayout()
        mode_header.setSpacing(6)
        mode_label = BodyLabel("변환 모드")
        mode_header.addWidget(mode_label)
        mode_help = HelpButton(
            "단일: 파일 1개 변환\n병합: 여러 파일을 1개로 합쳐 변환\n일괄: 여러 파일을 각각 따로 변환"
        )
        mode_header.addWidget(mode_help)
        mode_header.addStretch()
        options_card.add_layout(mode_header)

        self.mode_group = QButtonGroup(self)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(Spacing.LG)

        modes = [
            ("단일 파일", "single", "파일 1개를 변환합니다"),
            ("병합", "merge", "여러 파일을 하나로 합쳐서 변환합니다"),
            ("일괄 변환", "batch", "여러 파일을 각각 따로 변환합니다"),
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

        # ── 출력 형식 ──
        fmt_header = QHBoxLayout()
        fmt_header.setSpacing(6)
        fmt_label = BodyLabel("출력 형식")
        fmt_header.addWidget(fmt_label)
        fmt_help = HelpButton(
            "EPUB: 전자책 뷰어용\nDOCX: Word 문서 (인쇄/편집용)\nPDF: 고정 레이아웃 출력"
        )
        fmt_header.addWidget(fmt_help)
        fmt_header.addStretch()
        options_card.add_layout(fmt_header)

        self.format_group = QButtonGroup(self)
        fmt_layout = QHBoxLayout()
        fmt_layout.setSpacing(Spacing.LG)

        formats = [
            ("EPUB + DOCX", "both"),
            ("EPUB만", "epub"),
            ("DOCX만", "docx"),
            ("모두 (PDF 포함)", "all"),
        ]
        for text, value in formats:
            radio = RadioButton(text)
            radio.setProperty("value", value)
            if value == "both":
                radio.setChecked(True)
            self.format_group.addButton(radio)
            fmt_layout.addWidget(radio)

        fmt_layout.addStretch()
        options_card.add_layout(fmt_layout)

        self.content_layout.addWidget(options_card)

    # ------------------------------------------------------------------
    # 6. 프리셋 카드
    # ------------------------------------------------------------------

    def _build_preset_card(self):
        """저장된 스타일 프리셋을 빠르게 적용"""
        preset_card = ContentCard("프리셋", "저장된 설정 프리셋을 빠르게 적용")

        presets = self.preset_service.list_presets()
        preset_items: list[tuple[str, str | None]] = [("없음 (기본 설정)", None)]
        preset_items.extend([(p.name, p.name) for p in presets])

        self.preset_combo = ComboBox()
        for text, value in preset_items:
            self.preset_combo.addItem(text, value)
        self.preset_combo.setMinimumHeight(Sizes.BUTTON_MD_H)

        # 가장 긴 프리셋 이름에 맞춰 너비 설정
        if preset_items:
            fm = self.preset_combo.fontMetrics()
            max_w = max(fm.horizontalAdvance(t) for t, _ in preset_items)
            self.preset_combo.setMinimumWidth(max(200, max_w + 80))

        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_card.add_field(
            "프리셋 선택", self.preset_combo,
            help_text="저장된 스타일 프리셋 적용"
        )

        # 프리셋 설명 라벨 (선택 시 표시)
        self.preset_desc = BodyLabel("")
        self.preset_desc.setObjectName("PresetDescription")
        self.preset_desc.setWordWrap(True)
        self.preset_desc.setVisible(False)
        preset_card.add_widget(self.preset_desc)

        self.content_layout.addWidget(preset_card)

    # ------------------------------------------------------------------
    # 7. 변환 실행 카드
    # ------------------------------------------------------------------

    def _build_convert_card(self):
        """파일 상태 표시 · 진행률 바 · 변환 시작 버튼"""
        convert_card = ContentCard("변환 실행")

        # 파일 상태 표시
        self.file_count_label = BodyLabel("파일을 선택해주세요")
        self.file_count_label.setObjectName("FileCountLabel")
        convert_card.add_widget(self.file_count_label)

        self.file_size_label = BodyLabel("")
        self.file_size_label.setObjectName("FileSizeLabel")
        convert_card.add_widget(self.file_size_label)

        convert_card.add_spacing(8)

        # 진행 상태 프레임 (변환 중에만 표시)
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("ProgressFrame")
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(16, 12, 16, 12)
        progress_layout.setSpacing(Spacing.SM)

        self.progress_label = BodyLabel("변환 준비 중...")
        self.progress_label.setObjectName("ProgressLabel")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimumHeight(6)
        self.progress_bar.setMaximumHeight(6)
        progress_layout.addWidget(self.progress_bar)

        convert_card.add_widget(self.progress_frame)

        convert_card.add_spacing(12)

        # 변환 시작 버튼
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.convert_btn = PrimaryPushButton("변환 시작")
        self.convert_btn.setObjectName("ConvertStartButton")
        self.convert_btn.setCursor(Qt.PointingHandCursor)
        self.convert_btn.clicked.connect(self._start_conversion)
        btn_layout.addWidget(self.convert_btn)

        convert_card.add_layout(btn_layout)
        self.content_layout.addWidget(convert_card)

    # ==================================================================
    # 파일 관리
    # ==================================================================

    def _on_files_dropped(self, files: list):
        """드래그 앤 드롭 또는 대화상자로 파일이 추가되었을 때"""
        added = False
        large_files: list[str] = []

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
                title="대용량 파일 경고",
                content=(
                    f'10MB 이상 파일이 포함되어 있습니다: {", ".join(large_files)}. '
                    "변환에 시간이 걸릴 수 있습니다."
                ),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
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
            "지원 형식 (*.html *.htm *.txt);;HTML (*.html *.htm);;텍스트 (*.txt);;모든 파일 (*.*)",
        )
        if files:
            self._on_files_dropped(files)

    def _add_folder(self):
        """폴더 내 지원 파일 일괄 추가"""
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            found: list[str] = []
            for ext in ["*.html", "*.htm", "*.txt"]:
                found.extend(str(p) for p in Path(folder).glob(ext))
            if found:
                self._on_files_dropped(sorted(found))
            else:
                InfoBar.warning(
                    title="알림",
                    content="폴더에 지원되는 파일이 없습니다.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000,
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
        if hasattr(self, "document_preview"):
            self.document_preview.clear_preview()

    def _set_file_count_state(self, state: str):
        """파일 카운트 라벨의 QSS 동적 프로퍼티를 전환한다.

        Why: setStyleSheet로 인라인 색상을 박으면 다크 모드와 테마 변경에
             대응할 수 없으므로 QSS 속성 셀렉터로 분기한다.
        """
        label = self.file_count_label
        label.setProperty("state", state)
        label.style().unpolish(label)
        label.style().polish(label)

    def _update_file_count(self):
        """파일 개수·크기 라벨 갱신"""
        count = len(self.files)
        if count == 0:
            self.file_count_label.setText("파일을 선택해주세요")
            self._set_file_count_state("empty")
            self.file_size_label.setText("")
        else:
            self.file_count_label.setText(f"파일 {count}개 준비됨")
            self._set_file_count_state("ready")
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

    # ==================================================================
    # 최근 파일
    # ==================================================================

    def load_recent_files(self, recent_files: list):
        """최근 파일 목록 로드 (외부에서 호출)"""
        if not hasattr(self, "recent_list"):
            return
        self.recent_list.clear()
        for file_path in recent_files:
            if os.path.exists(file_path):
                item = QListWidgetItem(f"  {Path(file_path).name}")
                item.setData(Qt.UserRole, file_path)
                item.setToolTip(file_path)
                self.recent_list.addItem(item)

    def _on_recent_file_clicked(self, item: QListWidgetItem):
        """최근 파일 더블클릭 시 소스 목록에 추가"""
        file_path = item.data(Qt.UserRole)
        if file_path and os.path.exists(file_path):
            self._on_files_dropped([file_path])

    def _add_selected_recent(self):
        """선택된 최근 파일을 소스 목록에 추가"""
        selected = self.recent_list.selectedItems()
        if not selected:
            InfoBar.warning(
                title="알림",
                content="추가할 파일을 선택해주세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return

        files = [
            item.data(Qt.UserRole)
            for item in selected
            if item.data(Qt.UserRole) and os.path.exists(item.data(Qt.UserRole))
        ]
        if files:
            self._on_files_dropped(files)

    def _clear_recent_files(self):
        """최근 파일 목록 지우기"""
        parent = self.window()
        if hasattr(parent, "recent_files_manager"):
            parent.recent_files_manager.clear()
        self.recent_list.clear()
        InfoBar.info(
            title="완료",
            content="최근 파일 목록이 지워졌습니다.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000,
        )

    # ==================================================================
    # 출력 폴더
    # ==================================================================

    def _browse_output(self):
        """출력 폴더 선택 대화상자"""
        folder = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if folder:
            self.output_entry.setText(folder)

    # ==================================================================
    # 프리셋
    # ==================================================================

    def _on_preset_changed(self, index: int):
        """프리셋 드롭다운 변경 시 설명 표시 및 플랫폼 자동 설정"""
        preset_name = self.preset_combo.currentData()
        if preset_name:
            preset = self.preset_service.get_preset(preset_name)
            if preset:
                self.preset_desc.setText(preset.description)
                self.preset_desc.setVisible(True)

                # 프리셋에 지정된 플랫폼 자동 적용
                platform_map = {
                    "ccfolia": "cocofolia",
                    "roll20": "roll20",
                    "discord": "auto",
                    "text": "auto",
                }
                platform = platform_map.get(preset.platform, "auto")
                idx = self.platform_card.combo_box.findText(platform)
                if idx >= 0:
                    self.platform_card.combo_box.setCurrentIndex(idx)
        else:
            self.preset_desc.setVisible(False)

    # ==================================================================
    # 미리보기 연동
    # ==================================================================

    def _update_document_preview(self, files: list | None = None):
        """문서 미리보기 업데이트 (디바운스 적용)"""
        if files is None:
            files = self.files
        if not files or not hasattr(self, "document_preview"):
            return
        self._pending_preview_files = files
        self._preview_timer.start()

    def _do_update_preview(self):
        """실제 미리보기 업데이트 (타이머 콜백)"""
        files = self._pending_preview_files
        if not files:
            return

        try:
            file_path = files[0]
            if not os.path.isfile(file_path):
                logger.warning("미리보기 대상 파일 없음: %s", file_path)
                return
            platform = self.platform_card.get_value()
            from core.text_parser import parse_file

            log_source = platform if platform != "ccfolia" else "cocofolia"
            narrators_raw = _ensure_str(
                self.settings.get("narrators", DEFAULTS["narrators"])
            )
            narrator_list = [n.strip() for n in narrators_raw.split(",") if n.strip()]

            config = {
                "log_source": log_source,
                "narration": {"users": narrator_list},
            }

            entries = parse_file(file_path, config)
            self._parsed_entries = entries
            self.entries_parsed.emit(entries)

            preview_settings = {
                "font_family": self.settings.get("font_family", "Noto Serif KR"),
                "font_size": self.settings.get("font_size", 11),
                "line_height": self.settings.get("line_height", 1.8),
                "dialogue_color": self.settings.get("dialogue_color", "#333333"),
                "narration_color": self.settings.get("narration_color", "#555555"),
                "scene_marker": self.settings.get("scene_marker", "■"),
                "narration_prefix": self.settings.get("narration_prefix", "＿"),
                "narrators": _ensure_str(
                    self.settings.get("narrators", DEFAULTS["narrators"])
                ),
            }
            self.document_preview.update_preview(
                entries=entries, settings=preview_settings
            )
        except Exception as e:
            logger.warning("미리보기 업데이트 오류: %s", e, exc_info=True)

    def _show_preview(self):
        """미리보기 패널 표시 및 업데이트"""
        parent = self.window()
        if hasattr(parent, "_preview_visible") and not parent._preview_visible:
            parent.toggle_preview()
        if self.files:
            self._update_document_preview(self.files)
        if hasattr(parent, "document_preview"):
            parent.document_preview.setFocus()

    # ==================================================================
    # 변환 실행
    # ==================================================================

    def _start_conversion(self):
        """변환 시작 - 파일 유효성 확인 후 시그널 발행"""
        files = self.get_files()
        if not files:
            InfoBar.warning(
                title="파일 없음",
                content="변환할 파일을 추가해주세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
            return

        self.save_settings()
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("준비 중...")
        self.convert_btn.setEnabled(False)

        # 메인 윈도우(또는 외부 컨트롤러)에서 실제 변환을 처리한다
        self.conversion_requested.emit()
        self.conversion_started.emit()

    def update_progress(self, value: int, message: str = ""):
        """진행 상태 업데이트 (외부에서 호출)"""
        self.progress_bar.setValue(value)
        if message:
            self.progress_label.setText(message)

    def conversion_complete(self, success: bool, message: str):
        """변환 완료 처리 (외부에서 호출)"""
        self.progress_frame.setVisible(False)
        self.convert_btn.setEnabled(True)

        if success:
            InfoBar.success(
                title="변환 완료",
                content=message,
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )
        else:
            InfoBar.error(
                title="변환 실패",
                content=message,
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

        self.conversion_finished.emit(success, message)

    # ==================================================================
    # 공개 접근자 (getter)
    # ==================================================================

    def get_files(self) -> list:
        """파일 목록 반환 (QListWidget 드래그 재정렬 순서 반영)"""
        files: list[str] = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            path = item.data(Qt.UserRole)
            if path:
                files.append(path)
        return files

    def get_title(self) -> str:
        """제목 반환"""
        if hasattr(self, "title_card"):
            return self.title_card.get_value() or "TRPG 리플레이"
        return "TRPG 리플레이"

    def get_author(self) -> str:
        """저자 반환"""
        if hasattr(self, "author_card"):
            return self.author_card.get_value() or "GM"
        return "GM"

    def get_convert_mode(self) -> str:
        """변환 모드 반환 (single / merge / batch)"""
        checked = self.mode_group.checkedButton()
        return checked.property("value") if checked else "single"

    def get_output_format(self) -> str:
        """출력 형식 반환 (both / epub / docx / all)"""
        checked = self.format_group.checkedButton()
        return checked.property("value") if checked else "both"

    def get_preset_name(self) -> str:
        """선택된 프리셋 이름 반환"""
        return self.preset_combo.currentData() or ""

    def get_preset_config(self):
        """선택된 프리셋 설정 반환 (없으면 None)"""
        preset_name = self.get_preset_name()
        if preset_name:
            return self.preset_service.get_preset_config(preset_name)
        return None

    # ==================================================================
    # 설정 저장 / 로드
    # ==================================================================

    def save_settings(self):
        """현재 UI 상태를 AppState에 저장.

        narrators는 반드시 문자열로 저장한다 (build_engine_config에서 .split(',') 사용).
        """
        state = self.app_state
        state.set("title", self.title_card.get_value())
        state.set("author", self.author_card.get_value())
        state.set("platform", self.platform_card.get_value())
        state.set("output_dir", self.output_entry.text())
        state.set("narrators", _ensure_str(self.narrators_card.get_value().strip()))
        state.set(
            "language",
            LANGUAGE_MAP.get(self.language_card.get_value(), DEFAULTS["language"]),
        )

        mode = self.mode_group.checkedButton()
        if mode:
            state.set("convert_mode", mode.property("value"))

        fmt = self.format_group.checkedButton()
        if fmt:
            state.set("output_format", fmt.property("value"))

        state.save()

    def load_settings(self):
        """AppState에 저장된 설정을 UI에 반영"""
        state = self.app_state
        self.title_card.set_value(str(state.get("title", "")))
        self.author_card.set_value(str(state.get("author", "")))
        self.platform_card.set_value(str(state.get("platform", "cocofolia")))
        self.output_entry.setText(str(state.get("output_dir", "./export")))
        self.narrators_card.set_value(
            _ensure_str(state.get("narrators"), DEFAULTS["narrators"])
        )

        lang_code = state.get("language", DEFAULTS["language"])
        self.language_card.set_value(
            LANGUAGE_REVERSE_MAP.get(lang_code, list(LANGUAGE_MAP.keys())[0])
        )

        saved_mode = state.get("convert_mode", "single")
        for btn in self.mode_group.buttons():
            if btn.property("value") == saved_mode:
                btn.setChecked(True)
                break

        saved_format = state.get("output_format", "both")
        for btn in self.format_group.buttons():
            if btn.property("value") == saved_format:
                btn.setChecked(True)
                break

    # ==================================================================
    # 페이지 라이프사이클
    # ==================================================================

    def on_page_enter(self):
        """페이지 진입 시 호출 - 다른 페이지에서 변경된 output_dir 동기화"""
        if hasattr(self, "output_entry"):
            current = self.config_manager.get_gui_settings().get(
                "output_dir", "./export"
            )
            if self.output_entry.text() != current:
                self.output_entry.setText(current)

    def _on_secondary_action(self, action: str):
        """보조 액션 처리 (하위 호환)"""
        if action == "preview":
            self._show_preview()
        elif action == "settings":
            parent = self.window()
            if hasattr(parent, "_switch_to_page"):
                parent._switch_to_page("basic")
