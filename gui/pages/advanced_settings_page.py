"""
TRPG Log Converter Pro - 고급 설정 통합 페이지
출력 설정, 고급 옵션, 설정 관리를 하나의 탭으로 결합
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QWidget
from qfluentwidgets import BodyLabel, InfoBar, InfoBarPosition, LineEdit, MessageBox
from qfluentwidgets import PushButton as FluentPushButton

from ..components import CollapsibleSection, ContentCard
from ..theme import DEFAULTS, Sizes, Spacing
from .base_page import BasePage

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 고급 설정 통합 페이지
# ─────────────────────────────────────────────
class AdvancedSettingsPage(BasePage):
    """고급 설정 통합 페이지 - 출력 설정 / 고급 옵션 / 설정 관리"""

    settings_changed = Signal()

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._setup_page()
        self.load_settings()

    # ──────────── UI 구성 ────────────
    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("고급 설정", "출력 형식, 고급 옵션, 설정 관리를 설정합니다")

        # ============================================================
        # 섹션 1: 출력 설정 (기본 펼침)
        # ============================================================
        self._section_output = CollapsibleSection("출력 설정", expanded=True)
        self._build_output_section(self._section_output)
        self.content_layout.addWidget(self._section_output)

        # ============================================================
        # 섹션 2: 고급 옵션 (접힘)
        # ============================================================
        self._section_advanced = CollapsibleSection("고급 옵션", expanded=False)
        self._build_advanced_section(self._section_advanced)
        self.content_layout.addWidget(self._section_advanced)

        # ============================================================
        # 섹션 3: 설정 관리 (접힘)
        # ============================================================
        self._section_manage = CollapsibleSection("설정 관리", expanded=False)
        self._build_settings_manage_section(self._section_manage)
        self.content_layout.addWidget(self._section_manage)

        # 스트레치
        self.add_stretch()

    # ──────────── 섹션 1: 출력 설정 ────────────
    def _build_output_section(self, section: CollapsibleSection):
        """EPUB/DOCX 판형, 출력 폴더, DOCX 여백"""

        # --- EPUB 설정 카드 ---
        epub_card = ContentCard(
            "EPUB 설정",
            "전자책 뷰어용 EPUB 출력 설정",
            help_text="EPUB 파일의 페이지 크기와 비율을 설정합니다.",
        )

        self.epub_page_size = epub_card.add_dropdown(
            "판형",
            "epub_page_format",
            options=[
                "EPUB (6x9)",
                "EPUB (5x8)",
                "A5 (148x210mm)",
                "신국판 (152x225mm)",
                "문고판 (105x148mm)",
            ],
            default=self.settings.get("epub_page_format", "EPUB (6x9)"),
            help_text="EPUB 뷰어에서 표시되는 기본 페이지 비율입니다.",
        )
        section.add_card(epub_card)

        # --- DOCX 설정 카드 ---
        docx_card = ContentCard(
            "DOCX 설정",
            "Word 문서 페이지 크기 설정 (인쇄/편집용)",
            help_text="DOCX 출력의 페이지 크기를 설정합니다.",
        )

        self.page_format = docx_card.add_dropdown(
            "판형",
            "page_format",
            options=[
                "A4 (210x297mm)",
                "A5 (148x210mm)",
                "B5 (182x257mm)",
                "신국판 (152x225mm)",
                "국판 (148x210mm)",
                "46배판 (128x188mm)",
                "문고판 (105x148mm)",
                "Letter (8.5x11in)",
                "사용자 정의",
            ],
            default=self.settings.get("page_format", "A5 (148x210mm)"),
            help_text="출판용 DOCX의 페이지 크기. 신국판/문고판은 한국 출판 표준입니다.",
        )
        self.page_format.currentTextChanged.connect(self._on_page_format_changed)

        # 사용자 정의 크기 입력
        custom_size_row = QHBoxLayout()
        custom_size_row.setSpacing(Spacing.SM)

        self.custom_width = LineEdit()
        self.custom_width.setPlaceholderText("너비 (mm)")
        self.custom_width.setText(self.settings.get("custom_page_width", "148"))
        self.custom_width.setMaximumWidth(80)
        custom_size_row.addWidget(BodyLabel("너비"))
        custom_size_row.addWidget(self.custom_width)

        custom_size_row.addWidget(BodyLabel("x"))

        self.custom_height = LineEdit()
        self.custom_height.setPlaceholderText("높이 (mm)")
        self.custom_height.setText(self.settings.get("custom_page_height", "210"))
        self.custom_height.setMaximumWidth(80)
        custom_size_row.addWidget(BodyLabel("높이"))
        custom_size_row.addWidget(self.custom_height)

        custom_size_row.addWidget(BodyLabel("mm"))
        custom_size_row.addStretch()
        docx_card.add_layout(custom_size_row)

        # 초기 사용자 정의 크기 표시/숨김
        self._update_custom_size_visibility()
        section.add_card(docx_card)

        # --- 출력 폴더 카드 ---
        folder_card = ContentCard("출력 폴더", "변환된 파일이 저장되는 폴더를 지정합니다")

        folder_row = QHBoxLayout()
        folder_row.setSpacing(Spacing.SM)

        self.output_dir = LineEdit()
        self.output_dir.setPlaceholderText("출력 폴더 경로")
        self.output_dir.setText(self.settings.get("output_dir", str(Path.cwd() / "export")))
        folder_row.addWidget(self.output_dir, 1)

        browse_btn = FluentPushButton("찾기")
        browse_btn.clicked.connect(self._browse_output)
        folder_row.addWidget(browse_btn)

        open_btn = FluentPushButton("열기")
        open_btn.clicked.connect(self._open_output)
        folder_row.addWidget(open_btn)

        folder_card.add_layout(folder_row)
        section.add_card(folder_card)

        # --- DOCX 여백 카드 ---
        margin_card = ContentCard(
            "DOCX 여백",
            "페이지 여백 설정 (인치 단위, 1인치=25.4mm)",
            help_text="DOCX 문서의 상하좌우 여백을 인치 단위로 설정합니다.",
        )

        margins = self.settings.get("margins", {})

        margin_row = QHBoxLayout()
        margin_row.setSpacing(Spacing.XL)

        for key, label in [("top", "상"), ("bottom", "하"), ("left", "좌"), ("right", "우")]:
            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(Spacing.SM)

            lbl = BodyLabel(label)
            lbl.setFixedWidth(Sizes.MARGIN_LABEL_W)
            item_layout.addWidget(lbl)

            entry = LineEdit()
            entry.setPlaceholderText(DEFAULTS["margin"])
            entry.setText(margins.get(key, DEFAULTS["margin"]))
            entry.setFixedWidth(Sizes.MARGIN_INPUT_W)
            entry.setMinimumHeight(Sizes.INPUT_MIN_HEIGHT + 2)
            setattr(self, f"margin_{key}", entry)
            item_layout.addWidget(entry)

            margin_row.addWidget(item)

        margin_row.addStretch()
        margin_card.add_layout(margin_row)
        section.add_card(margin_card)

    # ──────────── 섹션 2: 고급 옵션 ────────────
    def _build_advanced_section(self, section: CollapsibleSection):
        """파싱, Roll20, 이미지 최적화, 캠페인 모드"""

        # --- 파싱 설정 카드 ---
        parsing_card = ContentCard("파싱 설정")

        self.name_max_length = parsing_card.add_text_field(
            "이름 최대 길이",
            "name_max_length",
            placeholder="50",
            default=self.settings.get("name_max_length", "50"),
            help_text="캐릭터 이름의 최대 문자 수입니다. 이보다 긴 이름은 잘립니다.",
        )
        self.skip_channels = parsing_card.add_text_field(
            "제외할 채널",
            "skip_channels",
            placeholder="[main], [잡담], [ooc]",
            default=self.settings.get("skip_channels", "[main], [잡담], [ooc]"),
            help_text="변환에서 제외할 채널 이름을 쉼표로 구분하여 입력합니다.",
        )
        self.normalize_punct = parsing_card.add_checkbox(
            "구두점 정규화",
            "normalize_punct",
            checked=self.settings.get("normalize_punct", True),
            help_text="전각/반각 구두점을 일관되게 변환합니다.",
        )
        section.add_card(parsing_card)

        # --- Roll20 특화 설정 카드 ---
        roll20_card = ContentCard("Roll20 설정", "Roll20 로그 전용 옵션")

        self.session_gap = roll20_card.add_text_field(
            "세션 간격 (분)",
            "session_gap",
            placeholder="60",
            default=self.settings.get("session_gap", "60"),
            help_text="메시지 간격이 이 시간을 초과하면 새 세션으로 구분합니다.",
        )
        self.emote_style = roll20_card.add_dropdown(
            "이모트 스타일",
            "emote_style",
            options=["italic", "normal", "bold"],
            default=self.settings.get("emote_style", "italic"),
            help_text="이모트(/em, /me) 텍스트의 스타일을 지정합니다.",
        )
        self.include_whisper = roll20_card.add_checkbox(
            "귓속말 포함",
            "include_whisper",
            checked=self.settings.get("include_whisper", False),
            help_text="Roll20 귓속말(whisper) 메시지를 변환에 포함합니다.",
        )
        section.add_card(roll20_card)

        # --- 이미지 최적화 카드 ---
        image_opt_card = ContentCard("이미지 최적화", "이미지 리사이즈 및 압축 설정")

        self.image_max_resolution = image_opt_card.add_text_field(
            "최대 해상도 (px)",
            "image_max_resolution",
            placeholder="1600",
            default=self.settings.get("image_max_resolution", "1600"),
            help_text="이미지의 긴 변이 이 값을 초과하면 자동으로 축소합니다. 0이면 리사이즈하지 않습니다.",
        )
        self.image_jpeg_quality = image_opt_card.add_dropdown(
            "JPEG 품질",
            "image_jpeg_quality",
            options=["95 (최고)", "85 (권장)", "75 (보통)", "60 (낮음)"],
            default=self.settings.get("image_jpeg_quality", "85 (권장)"),
            help_text="JPEG/WEBP 이미지의 압축 품질입니다. 낮을수록 파일이 작아집니다.",
        )
        self.image_convert_webp = image_opt_card.add_checkbox(
            "WebP → JPEG 변환",
            "image_convert_webp",
            checked=self.settings.get("image_convert_webp", True),
            help_text="WebP 이미지를 JPEG로 변환합니다. EPUB 리더 호환성이 향상됩니다.",
        )
        section.add_card(image_opt_card)

        # --- 캠페인 모드 카드 ---
        campaign_card = ContentCard("캠페인 모드", "여러 세션을 하나의 EPUB으로 병합")

        self.campaign_enable = campaign_card.add_checkbox(
            "캠페인 모드 활성화",
            "campaign_enable",
            checked=self.settings.get("campaign_enable", False),
            help_text="여러 로그 파일을 하나의 EPUB으로 병합합니다.",
        )
        self.campaign_title = campaign_card.add_text_field(
            "캠페인 제목",
            "campaign_title",
            placeholder="캠페인 리플레이",
            default=self.settings.get("campaign_title", "캠페인 리플레이"),
            help_text="병합된 EPUB의 전체 제목입니다.",
        )
        self.session_title_format = campaign_card.add_text_field(
            "세션 제목 형식",
            "session_title_format",
            placeholder="Session {n}: {filename}",
            default=self.settings.get("session_title_format", "Session {n}: {filename}"),
            help_text="{n}은 세션 번호, {filename}은 파일명으로 대체됩니다.",
        )
        section.add_card(campaign_card)

    # ──────────── 섹션 3: 설정 관리 ────────────
    def _build_settings_manage_section(self, section: CollapsibleSection):
        """설정 저장/내보내기/가져오기/초기화"""

        manage_card = ContentCard(
            "설정 관리", "모든 페이지의 설정을 저장하거나 JSON 파일로 관리합니다"
        )

        btn_row = QHBoxLayout()
        btn_row.setSpacing(Spacing.MD)

        save_btn = FluentPushButton("설정 저장")
        save_btn.clicked.connect(self._save_all_settings)
        btn_row.addWidget(save_btn)

        export_btn = FluentPushButton("설정 내보내기")
        export_btn.clicked.connect(self._export_settings)
        btn_row.addWidget(export_btn)

        import_btn = FluentPushButton("설정 가져오기")
        import_btn.clicked.connect(self._import_settings)
        btn_row.addWidget(import_btn)

        reset_btn = FluentPushButton("기본값 복원")
        reset_btn.clicked.connect(self._reset_settings)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()
        manage_card.add_layout(btn_row)

        # 단축키 안내
        mod = "\u2318" if sys.platform == "darwin" else "Ctrl+"
        shortcut_label = BodyLabel(
            f"단축키: {mod}O 파일열기, {mod}R 변환시작, {mod}P 미리보기, "
            f"{mod}E 설정내보내기, {mod}I 설정가져오기, {mod}L 로그보기, {mod}1~9 페이지전환"
        )
        shortcut_label.setObjectName("ShortcutHintLabel")
        shortcut_label.setWordWrap(True)
        manage_card.add_widget(shortcut_label)

        section.add_card(manage_card)

    # ──────────── 판형 변경 ────────────
    def _on_page_format_changed(self, format_name: str):
        """DOCX 판형 변경 시"""
        self._update_custom_size_visibility()
        self.save_settings()

    def _update_custom_size_visibility(self):
        """사용자 정의 크기 입력 필드 활성화/비활성화"""
        is_custom = "사용자 정의" in self.page_format.currentText()
        self.custom_width.setEnabled(is_custom)
        self.custom_height.setEnabled(is_custom)

    # ──────────── 출력 폴더 ────────────
    def _browse_output(self):
        """출력 폴더 선택 다이얼로그"""
        path = QFileDialog.getExistingDirectory(
            self, "출력 폴더 선택", self.output_dir.text() or str(Path.cwd())
        )
        if path:
            self.output_dir.setText(path)
            self.save_settings()

    def _open_output(self):
        """출력 폴더를 파일 탐색기에서 열기"""
        path = self.output_dir.text()
        if path and Path(path).exists():
            if sys.platform == "darwin":
                subprocess.run(["open", path])
            elif sys.platform == "win32":
                subprocess.run(["explorer", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            InfoBar.warning(
                title="경고",
                content="폴더가 존재하지 않습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )

    # ──────────── 설정 관리 액션 ────────────
    def _save_all_settings(self):
        """모든 설정 저장"""
        self.save_settings()
        InfoBar.success(
            title="저장 완료",
            content="설정이 저장되었습니다.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    def _export_settings(self):
        """설정 JSON 파일로 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "설정 파일 내보내기", "trpg_converter_settings.json", "JSON 파일 (*.json)"
        )
        if not file_path:
            return

        settings = self.config_manager.get_gui_settings()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        InfoBar.success(
            title="내보내기 완료",
            content=f"설정이 저장되었습니다: {file_path}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    def _import_settings(self):
        """설정 JSON 파일에서 가져오기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "설정 파일 가져오기", "", "JSON 파일 (*.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                imported = json.load(f)
            imported.pop("_meta", None)  # 프리셋 메타는 앱 설정이 아님

            # 1) 현재 설정과 병합 후 저장
            current = self.config_manager.get_gui_settings()
            current.update(imported)
            self.config_manager.save_gui_settings(current)

            main_window = self.window()
            # 2) AppState 를 import 된 값으로 리로드
            if hasattr(main_window, "app_state"):
                main_window.app_state.load()

            # 3) 페이지 리로드 중에는 save / set 을 모두 무효화한다.
            # load_settings 가 UI 위젯을 순차 세팅하면서 textChanged 등 시그널이
            # 발화해 save_settings() 가 호출되면, 아직 세팅되지 않은 다른 위젯의
            # 기본값이 state.set() / save_gui_settings() 로 AppState · 디스크에
            # 유입되어 import 값이 부분 롤백된다. 두 경로 모두 차단.
            original_save = self.config_manager.save_gui_settings
            self.config_manager.save_gui_settings = lambda _s: None
            if hasattr(main_window, "app_state"):
                main_window.app_state._suspend_set = True
            try:
                if hasattr(main_window, "pages"):
                    for page in main_window.pages.values():
                        if hasattr(page, "load_settings"):
                            try:
                                page.load_settings()
                            except Exception as page_err:
                                logger.warning("페이지 설정 로드 중 오류(계속 진행): %s", page_err)
                else:
                    self.load_settings()
            finally:
                if hasattr(main_window, "app_state"):
                    main_window.app_state._suspend_set = False
                self.config_manager.save_gui_settings = original_save

            # 4) 페이지 리로드가 끝났으니 import 값을 최종 확정 저장하고
            #    AppState 도 다시 동기화한다.
            self.config_manager.save_gui_settings(current)
            if hasattr(main_window, "app_state"):
                main_window.app_state.load()

            InfoBar.success(
                title="가져오기 완료",
                content="설정이 적용되었습니다. 일부 UI 요소는 앱 재시작 후 완전히 반영됩니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )
        except Exception as e:
            InfoBar.error(
                title="오류",
                content=f"설정 파일을 읽을 수 없습니다: {e}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

    def _reset_settings(self):
        """기본값으로 복원"""
        w = MessageBox("설정 초기화", "모든 설정을 기본값으로 초기화하시겠습니까?", self.window())

        if not w.exec():
            return

        default_settings = self.config_manager.get_default_gui_settings()
        self.config_manager.save_gui_settings(default_settings)

        main_window = self.window()
        # AppState 도 기본값으로 동기화 (이 페이지만이 아니라 전체가 대상)
        if hasattr(main_window, "app_state"):
            main_window.app_state.load()

        # 모든 페이지의 UI 를 다시 로드한다. 한 페이지만 load_settings 하면
        # 다른 페이지(예: 파싱 및 콘텐츠)의 숨김/표시 상태가 갱신되지 않아
        # 초기화해도 화면이 복구되지 않는 문제가 있었다.
        # 리로드 중 위젯 시그널이 save_settings 를 거쳐 기본값으로 디스크를
        # 오염시키지 않도록 set/save 를 잠근다(_import_settings 와 동일 패턴).
        original_save = self.config_manager.save_gui_settings
        self.config_manager.save_gui_settings = lambda _s: None
        if hasattr(main_window, "app_state"):
            main_window.app_state._suspend_set = True
        try:
            if hasattr(main_window, "pages"):
                for page in main_window.pages.values():
                    if hasattr(page, "load_settings"):
                        try:
                            page.load_settings()
                        except Exception as page_err:
                            logger.warning("페이지 설정 로드 중 오류(계속 진행): %s", page_err)
            else:
                self.load_settings()
        finally:
            if hasattr(main_window, "app_state"):
                main_window.app_state._suspend_set = False
            self.config_manager.save_gui_settings = original_save

        # 리로드 후 기본값을 최종 확정 저장하고 AppState 재동기화
        self.config_manager.save_gui_settings(default_settings)
        if hasattr(main_window, "app_state"):
            main_window.app_state.load()

        InfoBar.success(
            title="초기화 완료",
            content="모든 설정이 기본값으로 초기화되었습니다.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    # ──────────── 페이지 진입 ────────────
    def on_page_enter(self):
        """페이지 진입 시 호출 - 출력 폴더 동기화"""
        current_output_dir = self.config_manager.get_gui_settings().get(
            "output_dir", str(Path.cwd() / "export")
        )
        if self.output_dir.text() != current_output_dir:
            self.output_dir.setText(current_output_dir)

    # ──────────── 설정 저장 ────────────
    def save_settings(self):
        """현재 UI 상태를 AppState에 저장."""
        state = self.app_state
        _s = state.set

        # 출력 설정
        _s("epub_page_format", self.epub_page_size.currentText())
        _s("page_format", self.page_format.currentText())
        _s("custom_page_width", self.custom_width.text())
        _s("custom_page_height", self.custom_height.text())
        _s("output_dir", self.output_dir.text())
        _s(
            "margins",
            {
                "top": self.margin_top.text(),
                "bottom": self.margin_bottom.text(),
                "left": self.margin_left.text(),
                "right": self.margin_right.text(),
            },
        )

        # 고급 옵션: 파싱
        _s("name_max_length", self.name_max_length.text())
        _s("skip_channels", self.skip_channels.text())
        _s("normalize_punct", self.normalize_punct.isChecked())

        # 고급 옵션: Roll20
        _s("session_gap", self.session_gap.text())
        _s("emote_style", self.emote_style.currentText())
        _s("include_whisper", self.include_whisper.isChecked())

        # 고급 옵션: 이미지 최적화
        _s("image_max_resolution", self.image_max_resolution.text())
        _s("image_jpeg_quality", self.image_jpeg_quality.currentText())
        _s("image_convert_webp", self.image_convert_webp.isChecked())

        # 고급 옵션: 캠페인 모드
        _s("campaign_enable", self.campaign_enable.isChecked())
        _s("campaign_title", self.campaign_title.text())
        _s("session_title_format", self.session_title_format.text())

        state.save()

    # ──────────── 설정 로드 ────────────
    def load_settings(self):
        """AppState에 저장된 설정을 UI에 반영"""
        _g = self.app_state.get

        # 출력 설정
        self.safe_set_combo(self.epub_page_size, str(_g("epub_page_format", "EPUB (6x9)")))
        self.safe_set_combo(self.page_format, str(_g("page_format", "A5 (148x210mm)")))
        self.custom_width.setText(str(_g("custom_page_width", "148")))
        self.custom_height.setText(str(_g("custom_page_height", "210")))
        self._update_custom_size_visibility()

        self.output_dir.setText(str(_g("output_dir", str(Path.cwd() / "export"))))

        margins = _g("margins", {})
        if isinstance(margins, dict):
            self.margin_top.setText(margins.get("top", DEFAULTS["margin"]))
            self.margin_bottom.setText(margins.get("bottom", DEFAULTS["margin"]))
            self.margin_left.setText(margins.get("left", DEFAULTS["margin"]))
            self.margin_right.setText(margins.get("right", DEFAULTS["margin"]))
        else:
            for key in ("top", "bottom", "left", "right"):
                getattr(self, f"margin_{key}").setText(DEFAULTS["margin"])

        # 고급 옵션: 파싱
        self.name_max_length.setText(str(_g("name_max_length", "50")))
        self.skip_channels.setText(str(_g("skip_channels", "[main], [잡담], [ooc]")))
        self.normalize_punct.setChecked(_g("normalize_punct", True))

        # 고급 옵션: Roll20
        self.session_gap.setText(str(_g("session_gap", "60")))
        self.safe_set_combo(self.emote_style, str(_g("emote_style", "italic")))
        self.include_whisper.setChecked(_g("include_whisper", False))

        # 고급 옵션: 이미지 최적화
        self.image_max_resolution.setText(str(_g("image_max_resolution", "1600")))
        self.safe_set_combo(self.image_jpeg_quality, str(_g("image_jpeg_quality", "85 (권장)")))
        self.image_convert_webp.setChecked(_g("image_convert_webp", True))

        # 고급 옵션: 캠페인 모드
        self.campaign_enable.setChecked(_g("campaign_enable", False))
        self.campaign_title.setText(str(_g("campaign_title", "캠페인 리플레이")))
        self.session_title_format.setText(
            str(_g("session_title_format", "Session {n}: {filename}"))
        )
