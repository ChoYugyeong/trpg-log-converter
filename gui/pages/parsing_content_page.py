"""
TRPG Log Converter Pro - 파싱 및 콘텐츠 통합 페이지
콘텐츠 필터, 장면 분할, 파싱 규칙을 하나의 탭으로 결합
"""

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit
from qfluentwidgets import InfoBar, InfoBarPosition, PrimaryPushButton
from qfluentwidgets import PushButton as FluentPushButton

from ..components import CollapsibleSection, ContentCard
from ..theme import Sizes, Spacing
from .base_page import BasePage

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 파싱 및 콘텐츠 통합 페이지
# ─────────────────────────────────────────────
class ParsingContentPage(BasePage):
    """파싱 및 콘텐츠 통합 페이지 - 콘텐츠 필터 / 장면 분할 / 파싱 규칙"""

    settings_changed = Signal()

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._setup_page()
        self.load_settings()

    # ──────────── UI 구성 ────────────
    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("파싱 및 콘텐츠", "콘텐츠 필터, 장면 분할, 파싱 규칙을 설정합니다")

        # ============================================================
        # 섹션 1: 콘텐츠 필터 (기본 펼침)
        # ============================================================
        self._section_content = CollapsibleSection("콘텐츠 필터", expanded=True)
        self._build_content_filter_section(self._section_content)
        self.content_layout.addWidget(self._section_content)

        # ============================================================
        # 섹션 2: 장면 분할 (접힘)
        # ============================================================
        self._section_scene = CollapsibleSection("장면 분할", expanded=False)
        self._build_scene_split_section(self._section_scene)
        self.content_layout.addWidget(self._section_scene)

        # ============================================================
        # 섹션 3: 파싱 규칙 (접힘)
        # ============================================================
        self._section_parsing = CollapsibleSection("파싱 규칙", expanded=False)
        self._build_parsing_rules_section(self._section_parsing)
        self.content_layout.addWidget(self._section_parsing)

        # 스트레치
        self.add_stretch()

    # ──────────── 섹션 1: 콘텐츠 필터 ────────────
    def _build_content_filter_section(self, section: CollapsibleSection):
        """콘텐츠 포함/제외 및 나레이션, 대화 병합, 이미지 설정"""

        # --- 포함 설정 카드 ---
        include_card = ContentCard("포함 설정")

        self.include_dice = include_card.add_checkbox(
            "주사위 굴림 결과 포함",
            "include_dice",
            checked=self.settings.get("include_dice", True),
            help_text="1d20 = 15 같은 주사위 결과를 변환에 포함합니다.",
        )
        self.include_effects = include_card.add_checkbox(
            "연출 효과 포함 (SE, BGM 등)",
            "include_effects",
            checked=self.settings.get("include_effects", True),
            help_text="[SE:효과음] [BGM:배경음악] 같은 연출 태그를 포함합니다.",
        )
        self.include_system = include_card.add_checkbox(
            "시스템 메시지 포함",
            "include_system",
            checked=self.settings.get("include_system", True),
            help_text="입장/퇴장, 알림 등 시스템 메시지를 포함합니다.",
        )
        self.include_ooc = include_card.add_checkbox(
            "OOC(Out of Character) 포함",
            "include_ooc",
            checked=self.settings.get("include_ooc", False),
            help_text="(( )) 또는 OOC: 로 시작하는 비RP 대화를 포함합니다.",
        )
        section.add_card(include_card)

        # --- 나레이션 설정 카드 ---
        narration_card = ContentCard("나레이션 설정", "나레이터로 인식할 사용자 설정")

        self.narrators_entry = narration_card.add_text_field(
            "나레이터 목록",
            "narrators",
            placeholder="GM, KP, DM, Keeper (쉼표로 구분)",
            default=self.settings.get("narrators", "GM, KP, DM, Keeper, 나레이터, 진행자"),
            help_text="쉼표로 구분. 이 이름들의 대사는 나레이션으로 처리됩니다.",
        )
        self.narration_prefix = narration_card.add_text_field(
            "나레이션 접두사",
            "narration_prefix",
            placeholder="＿",
            default=self.settings.get("narration_prefix", "＿"),
            help_text="나레이션 시작 부분에 붙는 기호입니다.",
        )
        self.narration_indent = narration_card.add_text_field(
            "나레이션 들여쓰기 (em)",
            "narration_indent",
            placeholder="1.5",
            default=self.settings.get("narration_indent", "1.5"),
            help_text="나레이션의 들여쓰기 정도(em 단위). 1.5~2.0 권장.",
        )
        section.add_card(narration_card)

        # --- 대화 병합 설정 카드 ---
        merge_card = ContentCard("대화 병합", "연속된 대사를 하나로 병합")

        self.merge_dialogue = merge_card.add_checkbox(
            "연속 대화 병합",
            "merge_dialogue",
            checked=self.settings.get("merge_dialogue", False),
            help_text="같은 캐릭터의 연속 대사를 하나로 합칩니다.",
        )
        self.merge_separator_combo = merge_card.add_dropdown(
            "병합 구분자",
            "merge_separator",
            options=["newline", "space", "dash"],
            default=self.settings.get("merge_separator", "newline"),
            help_text="병합된 대사들 사이에 들어갈 구분자입니다.",
        )
        self.merge_max = merge_card.add_text_field(
            "최대 병합 수",
            "merge_max",
            placeholder="5",
            default=self.settings.get("merge_max", "5"),
            help_text="한 번에 병합할 수 있는 최대 대사 수입니다.",
        )
        self.empty_dialogue = merge_card.add_text_field(
            "빈 대사 대체",
            "empty_dialogue",
            placeholder="……",
            default=self.settings.get("empty_dialogue", "……"),
            help_text="내용이 없는 대사를 대체할 텍스트입니다.",
        )
        section.add_card(merge_card)

        # --- 이미지 삽입 설정 카드 ---
        image_card = ContentCard("이미지 삽입", "로그에 포함된 이미지 처리 설정")

        self.images_enable = image_card.add_checkbox(
            "이미지 삽입 활성화",
            "images_enable",
            checked=self.settings.get("images_enable", True),
            help_text="로그에 포함된 이미지를 EPUB/DOCX에 삽입합니다.",
        )
        self.show_caption = image_card.add_checkbox(
            "캡션 표시",
            "show_caption",
            checked=self.settings.get("show_caption", True),
            help_text="이미지 아래에 캡션(설명)을 표시합니다.",
        )
        self.image_align = image_card.add_dropdown(
            "이미지 정렬",
            "image_align",
            options=["center", "left", "right"],
            default=self.settings.get("image_align", "center"),
            help_text="이미지의 가로 정렬 위치입니다.",
        )
        self.image_max_width = image_card.add_text_field(
            "최대 너비 (%)",
            "image_max_width",
            placeholder="100",
            default=self.settings.get("image_max_width", "100"),
            help_text="이미지의 최대 너비를 페이지 너비의 백분율로 지정합니다.",
        )
        section.add_card(image_card)

        # 체크박스 변경 시 자동 저장 연결
        for cb in [
            self.include_dice,
            self.include_effects,
            self.include_system,
            self.include_ooc,
            self.merge_dialogue,
            self.images_enable,
            self.show_caption,
        ]:
            cb.stateChanged.connect(self.save_settings)

    # ──────────── 섹션 2: 장면 분할 ────────────
    def _build_scene_split_section(self, section: CollapsibleSection):
        """챕터/장면 분할 관련 설정"""

        # --- 챕터 구분 카드 ---
        chapter_card = ContentCard("챕터 구분", "EPUB 챕터 분할 방식")

        self.split_mode_group = chapter_card.add_radio_group(
            [("장면 기반", "scene"), ("항목 수 기반", "count"), ("단일 챕터", "none")],
            "split_mode",
            default=self.settings.get("split_mode", "scene"),
        )
        # 분할 모드 변경 시 관련 필드 표시/숨김
        for btn in self.split_mode_group.buttons():
            btn.toggled.connect(self._on_split_mode_changed)

        self.scene_patterns = chapter_card.add_text_field(
            "장면 패턴",
            "scene_patterns",
            placeholder="■, 씬, Scene, 장면",
            default=self.settings.get("scene_patterns", "■, 씬, Scene, 장면, Act"),
            help_text="이 텍스트로 시작하는 메시지에서 새 챕터가 시작됩니다.",
        )
        self.min_scene_entries = chapter_card.add_text_field(
            "최소 장면 항목",
            "min_scene_entries",
            placeholder="10",
            default=self.settings.get("min_scene_entries", "10"),
            help_text="이보다 적은 항목의 장면은 이전 장면에 병합됩니다.",
        )
        self.entries_per_chapter = chapter_card.add_text_field(
            "챕터당 항목 수",
            "entries_per_chapter",
            placeholder="300",
            default=self.settings.get("entries_per_chapter", "300"),
            help_text="'항목 수 기반' 모드에서 사용. 이 수만큼 항목이 쌓이면 새 챕터.",
        )
        self.title_format = chapter_card.add_text_field(
            "챕터 제목 형식",
            "title_format",
            placeholder="장면 {n}",
            default=self.settings.get("title_format", "장면 {n}"),
            help_text="{n}은 장면 번호로 대체됩니다. 예: '제 {n} 장', 'Scene {n}'",
        )
        section.add_card(chapter_card)

        # 초기 분할 모드에 맞게 필드 표시/숨김
        self._on_split_mode_changed()

        # --- 장식 요소 카드 ---
        decoration_card = ContentCard("장식 요소")

        self.scene_marker = decoration_card.add_text_field(
            "장면 마커",
            "scene_marker",
            placeholder="■",
            default=self.settings.get("scene_marker", "■"),
            help_text="장면 제목 앞에 붙는 마커입니다.",
        )
        self.chapter_ornament = decoration_card.add_text_field(
            "챕터 장식",
            "chapter_ornament",
            placeholder="─────  ✦  ─────",
            default=self.settings.get("chapter_ornament", "─────  ✦  ─────"),
            help_text="챕터 시작 부분의 장식 문양입니다.",
        )
        self.scene_separator = decoration_card.add_text_field(
            "장면 구분선",
            "scene_separator",
            placeholder="＊　＊　＊",
            default=self.settings.get("scene_separator", "＊　＊　＊"),
            help_text="장면과 장면 사이의 구분선입니다.",
        )
        section.add_card(decoration_card)

    # ──────────── 섹션 3: 파싱 규칙 ────────────
    def _build_parsing_rules_section(self, section: CollapsibleSection):
        """플랫폼 템플릿, 이름/대사 구분, 나레이션 규칙, 주사위/시스템 패턴"""

        # --- 플랫폼 템플릿 카드 ---
        template_card = ContentCard(
            "빠른 시작", "플랫폼과 룰 시스템을 선택하면 파싱 규칙이 자동 설정됩니다"
        )

        template_layout = QHBoxLayout()
        template_layout.setSpacing(Spacing.SM)

        templates = [
            ("코코포리아", "cocofolia"),
            ("Roll20", "roll20"),
            ("카카오톡", "kakaotalk"),
            ("디스코드", "discord"),
            ("직접 설정", "custom"),
        ]
        for text, value in templates:
            btn = FluentPushButton(text)
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda checked, v=value: self._apply_template(v))
            template_layout.addWidget(btn)

        template_layout.addStretch()
        template_card.add_layout(template_layout)

        # 룰 시스템 선택 드롭다운
        self.rule_system = template_card.add_dropdown(
            "룰 시스템",
            "rule_system",
            options=[
                "자동 감지",
                "CoC 6e (크툴루의 부름 6판)",
                "CoC 7e (크툴루의 부름 7판)",
                "D&D 5e",
                "소드 월드 2.5",
                "인세인 (Insane)",
                "에모클로아 (Emoklore)",
                "시노비가미 (Shinobigami)",
                "더블크로스 (Double Cross)",
                "네크로니카 (Nechronica)",
                "기타 (범용 주사위)",
            ],
            default=self.settings.get("rule_system", "자동 감지"),
            help_text="룰 시스템에 따라 주사위 키워드와 결과 판정 방식이 달라집니다",
        )
        self.rule_system.currentTextChanged.connect(self._on_rule_system_changed)

        section.add_card(template_card)

        # --- 이름/대사 구분 규칙 카드 ---
        name_card = ContentCard(
            "이름·대사 구분", "캐릭터 이름과 대사를 어떻게 구분하는지 설정합니다"
        )

        self.separator_type = name_card.add_dropdown(
            "구분 방식",
            "separator_type",
            options=[
                "콜론 (:)",
                "탭 (Tab)",
                "대괄호 ([이름])",
                "꺾쇠 (<이름>)",
                "HTML 태그 자동",
                "직접 입력",
            ],
            default=self.settings.get("custom_separator_type", "콜론 (:)"),
            help_text="이름과 대사를 구분하는 방식을 선택합니다. '직접 입력'을 선택하면 커스텀 구분자를 지정할 수 있습니다.",
        )
        self.separator_type.currentTextChanged.connect(self._on_separator_type_changed)

        # 직접 입력 필드 (기본 숨김)
        from qfluentwidgets import LineEdit as FluentLineEdit

        self.custom_separator_input = FluentLineEdit()
        self.custom_separator_input.setPlaceholderText("구분자를 입력하세요 (예: ::, ->, |)")
        self.custom_separator_input.setMinimumHeight(Sizes.BUTTON_MD_H)
        self.custom_separator_input.setText(self.settings.get("custom_separator_text", ""))
        name_card.add_field(
            "커스텀 구분자",
            self.custom_separator_input,
            "custom_separator_text",
            help_text="이름과 대사 사이에 사용되는 구분 문자열을 입력하세요",
        )
        # 초기 표시 상태: '직접 입력'일 때만 행 전체를 표시 (행 단위 토글)
        self._set_field_row_visible(
            self.custom_separator_input,
            self.settings.get("custom_separator_type", "콜론 (:)") == "직접 입력",
        )
        self.name_position = name_card.add_dropdown(
            "이름 위치",
            "name_position",
            options=[
                "구분자 앞 (이름: 대사)",
                "구분자 안 ([이름] 대사)",
                "첫 번째 줄 (이름\\n대사)",
            ],
            default=self.settings.get("custom_name_position", "구분자 앞 (이름: 대사)"),
            help_text="이름이 대사 내에서 어디에 위치하는지 선택합니다",
        )
        self.name_max = name_card.add_text_field(
            "이름 최대 길이",
            "name_max",
            placeholder="50",
            default=self.settings.get("custom_name_max", "50"),
            help_text="이 길이를 초과하면 이름으로 인식하지 않습니다",
        )
        section.add_card(name_card)

        # --- 나레이션 인식 카드 ---
        narration_rule_card = ContentCard(
            "나레이션 규칙", "나레이션(지문)으로 인식할 조건을 설정합니다"
        )

        self.narration_users = narration_rule_card.add_text_field(
            "나레이터 이름",
            "narration_users",
            placeholder="GM, KP, DM, Keeper, 나레이터",
            default=self.settings.get("narrators", "GM, KP, DM, Keeper, 나레이터"),
            help_text="이 이름으로 발화하면 나레이션으로 처리합니다 (쉼표 구분)",
        )
        self.narration_no_name = narration_rule_card.add_checkbox(
            "이름 없는 텍스트는 나레이션으로 처리",
            "narration_no_name",
            checked=self.settings.get("narration_no_name", False),
            help_text="이름: 대사 형식이 아닌 줄을 나레이션으로 처리합니다",
        )
        section.add_card(narration_rule_card)

        # --- 주사위/시스템 메시지 카드 ---
        dice_card = ContentCard("주사위·시스템 메시지", "주사위 굴림이나 시스템 메시지 인식 규칙")

        self.dice_patterns_text = dice_card.add_text_field(
            "주사위 키워드",
            "dice_keywords",
            placeholder="CCB, 1D100, 1D20, roll, Rolling",
            default=self.settings.get("dice_keywords", "CCB, 1D100, 1D20, roll, Rolling"),
            help_text="이 키워드가 포함된 줄을 주사위 굴림으로 인식합니다",
        )
        self.system_prefix = dice_card.add_text_field(
            "시스템 접두사",
            "system_prefix",
            placeholder="System:, [시스템]",
            default=self.settings.get("system_prefix", "System:"),
            help_text="이 텍스트로 시작하는 줄을 시스템 메시지로 인식합니다",
        )
        section.add_card(dice_card)

        # --- 규칙 테스트 카드 ---
        test_card = ContentCard("규칙 테스트", "텍스트를 입력하여 파싱 결과를 미리 확인하세요")

        self.test_input = QPlainTextEdit()
        self.test_input.setPlaceholderText(
            "테스트할 로그 텍스트를 입력하세요...\n\n"
            "예시:\n"
            "홍길동: 안녕하세요\n"
            "GM: 모험이 시작됩니다\n"
            "■ 장면 1\n"
            "홍길동: CCB<=65 → 35 성공"
        )
        # 7줄짜리 안내(placeholder)가 들어가므로 높이를 넉넉히. 이전엔 max 150 이라
        # 고배율(125~150%) 화면에서 아래 두어 줄이 잘렸다.
        self.test_input.setMinimumHeight(190)
        self.test_input.setMaximumHeight(240)
        test_card.add_widget(self.test_input)

        test_btn = PrimaryPushButton("파싱 테스트")
        test_btn.setMinimumHeight(Sizes.BUTTON_MD_H)
        test_btn.clicked.connect(self._run_test)
        test_card.add_widget(test_btn)

        self.test_result = QPlainTextEdit()
        self.test_result.setObjectName("ParsingTestResult")
        self.test_result.setReadOnly(True)
        self.test_result.setMinimumHeight(160)
        self.test_result.setPlaceholderText("파싱 결과가 여기에 표시됩니다...")
        test_card.add_widget(self.test_result)
        section.add_card(test_card)

    # ──────────── 행 단위 표시/숨김 헬퍼 ────────────
    @staticmethod
    def _set_field_row_visible(widget, visible: bool):
        """필드가 속한 '행(라벨+위젯)' 컨테이너만 표시/숨김.

        widget.parent() 를 직접 숨기면 카드 전체(선택 라디오 포함)가 사라지는
        버그가 있었다. ContentCard 가 각 행을 별도 컨테이너로 감싸 widget 에
        부착해둔 _field_row 를 사용해 그 행만 안전하게 토글한다.
        """
        row = getattr(widget, "_field_row", None)
        (row if row is not None else widget).setVisible(visible)

    # ──────────── 분할 모드 변경 ────────────
    def _on_split_mode_changed(self, checked=True):
        """분할 모드 변경 시 관련 필드 표시/숨김"""
        checked_btn = self.split_mode_group.checkedButton()
        mode = checked_btn.property("value") if checked_btn else "scene"

        is_scene = mode == "scene"
        is_count = mode == "count"
        is_none = mode == "none"

        # 장면 기반 필드
        self._set_field_row_visible(self.scene_patterns, is_scene)
        self._set_field_row_visible(self.min_scene_entries, is_scene)

        # 항목 수 기반 필드
        self._set_field_row_visible(self.entries_per_chapter, is_count)

        # 제목 형식은 '단일 챕터' 외에는 표시
        self._set_field_row_visible(self.title_format, not is_none)

    # ──────────── 구분 방식 변경 ────────────
    def _on_separator_type_changed(self, text: str):
        """구분 방식 변경 시 직접 입력 필드 표시/숨김"""
        is_custom = text == "직접 입력"
        self._set_field_row_visible(self.custom_separator_input, is_custom)

    # ──────────── 룰 시스템 변경 ────────────
    def _on_rule_system_changed(self, rule_system: str):
        """룰 시스템 변경 시 주사위 키워드 자동 업데이트"""
        rule_dice_map = {
            "자동 감지": None,  # 변경하지 않음
            "CoC 6e (크툴루의 부름 6판)": "CCB, 1D100, 1D20, 2D6",
            "CoC 7e (크툴루의 부름 7판)": "CC, CCB, 1D100, 1D20, 2D6",
            "D&D 5e": "1d20, 1d4, 1d6, 1d8, 1d10, 1d12, roll, Rolling, attack, save",
            "소드 월드 2.5": "k, 2d6, gr, rating",
            "인세인 (Insane)": "2d6, FT, ET",
            "에모클로아 (Emoklore)": "2d6, ET",
            "시노비가미 (Shinobigami)": "2d6, ST, FumbleT, ET",
            "더블크로스 (Double Cross)": "DX, 4DX, 3DX, 2DX, 1d10",
            "네크로니카 (Nechronica)": "NC, 1d10",
            "기타 (범용 주사위)": "1d20, 1d100, 2d6, 1d6, roll",
        }
        keywords = rule_dice_map.get(rule_system)
        if keywords is not None:
            self.dice_patterns_text.setText(keywords)
            self.save_settings()
            InfoBar.info(
                title=f"룰 시스템: {rule_system}",
                content="주사위 키워드가 업데이트되었습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )

    # ──────────── 플랫폼 템플릿 적용 ────────────
    def _apply_template(self, platform: str):
        """플랫폼 템플릿 적용"""
        templates = {
            "cocofolia": {
                "separator_type": "HTML 태그 자동",
                "name_position": "구분자 앞 (이름: 대사)",
                "narration_users": "GM, KP, DM, Keeper",
                "dice_keywords": "CCB, 1D100, 1D20, 2D6",
                "system_prefix": "System:",
            },
            "roll20": {
                "separator_type": "HTML 태그 자동",
                "name_position": "구분자 앞 (이름: 대사)",
                "narration_users": "GM, DM, Narrator, Storyteller",
                "dice_keywords": "roll, Rolling, 1d20, 1d100, attack, save",
                "system_prefix": "System:",
            },
            "kakaotalk": {
                "separator_type": "대괄호 ([이름])",
                "name_position": "구분자 안 ([이름] 대사)",
                "narration_users": "GM, KP, 마스터, 진행자",
                "dice_keywords": "1D100, 1D20, 주사위",
                "system_prefix": "[시스템]",
            },
            "discord": {
                "separator_type": "콜론 (:)",
                "name_position": "구분자 앞 (이름: 대사)",
                "narration_users": "GM, DM, Bot, 봇",
                "dice_keywords": "!roll, /roll, 1d20",
                "system_prefix": "[Bot]",
            },
            "custom": {},
        }

        template = templates.get(platform, {})
        if not template:
            # 직접 설정 모드: 필드 초기화
            self.separator_type.setCurrentIndex(0)
            self.name_position.setCurrentIndex(0)
            self.narration_users.clear()
            self.dice_patterns_text.clear()
            self.system_prefix.clear()
            self.name_max.setText("50")
            self.save_settings()
            InfoBar.info(
                title="직접 설정 모드",
                content="필드가 초기화되었습니다. 아래에서 직접 설정해주세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return

        # 필드 값 적용
        if "separator_type" in template:
            idx = self.separator_type.findText(template["separator_type"])
            if idx >= 0:
                self.separator_type.setCurrentIndex(idx)
        if "name_position" in template:
            idx = self.name_position.findText(template["name_position"])
            if idx >= 0:
                self.name_position.setCurrentIndex(idx)
        if "narration_users" in template:
            self.narration_users.setText(template["narration_users"])
        if "dice_keywords" in template:
            self.dice_patterns_text.setText(template["dice_keywords"])
        if "system_prefix" in template:
            self.system_prefix.setText(template["system_prefix"])

        self.save_settings()

        InfoBar.success(
            title=f"{platform} 템플릿 적용",
            content="파싱 규칙이 업데이트되었습니다.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000,
        )

    # ──────────── 파싱 테스트 ────────────
    def _run_test(self):
        """파싱 테스트 실행"""
        text = self.test_input.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title="텍스트 없음",
                content="테스트할 텍스트를 입력해주세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return

        self.save_settings()

        results = []
        narrators = [n.strip() for n in self.narration_users.text().split(",") if n.strip()]
        scene_markers_list = [m.strip() for m in self.scene_patterns.text().split(",") if m.strip()]
        dice_keywords = [
            k.strip().upper() for k in self.dice_patterns_text.text().split(",") if k.strip()
        ]
        sys_prefix = self.system_prefix.text().strip()

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            entry_type = "dialogue"
            name = ""
            content = line

            # 장면 마커 체크
            is_scene = False
            for marker in scene_markers_list:
                if line.startswith(marker):
                    is_scene = True
                    break
            if is_scene:
                results.append(f"  [장면] {line}")
                continue

            # 시스템 메시지 체크
            if sys_prefix and line.lower().startswith(sys_prefix.lower()):
                content = line[len(sys_prefix) :].strip()
                results.append(f"  [시스템] {content}")
                continue

            # 이름:대사 분리
            if ":" in line:
                parts = line.split(":", 1)
                try:
                    name_max_len = int(self.name_max.text() or 50)
                except (ValueError, TypeError):
                    name_max_len = 50
                if len(parts[0].strip()) <= name_max_len:
                    name = parts[0].strip()
                    content = parts[1].strip()

            # 나레이터 체크
            if name and name in narrators:
                entry_type = "narration"

            # 주사위 체크 — 키워드 매칭 AND 결과 기호 (→ / = / >) 가 같이 있어야 dice.
            if any(kw in content.upper() for kw in dice_keywords) and (
                "→" in content or "=" in content or ">" in content
            ):
                entry_type = "dice"

            # 이름 없는 텍스트를 나레이션으로 처리
            if not name and self.narration_no_name.isChecked():
                entry_type = "narration"

            type_labels = {
                "dialogue": "대사",
                "narration": "나레이션",
                "dice": "주사위",
                "system": "시스템",
                "scene": "장면",
            }

            label = type_labels.get(entry_type, entry_type)
            if name:
                results.append(f"  [{label}] {name}: {content}")
            else:
                results.append(f"  [{label}] {content}")

        if results:
            self.test_result.setPlainText(
                f"=== 파싱 결과 ({len(results)}줄) ===\n" + "\n".join(results)
            )
        else:
            self.test_result.setPlainText("파싱 결과 없음")

    # ──────────── 설정 저장 ────────────
    def save_settings(self):
        """현재 UI 상태를 AppState에 저장."""
        state = self.app_state
        _s = state.set

        # 콘텐츠 필터
        _s("include_dice", self.include_dice.isChecked())
        _s("include_effects", self.include_effects.isChecked())
        _s("include_system", self.include_system.isChecked())
        _s("include_ooc", self.include_ooc.isChecked())

        # narrators: 문자열(STRING)로 저장
        _s("narrators", self.narrators_entry.text())
        _s("narration_prefix", self.narration_prefix.text())
        _s("narration_indent", self.narration_indent.text())

        _s("merge_dialogue", self.merge_dialogue.isChecked())
        _s("merge_separator", self.merge_separator_combo.currentText())
        _s("merge_max", self.merge_max.text())
        _s("empty_dialogue", self.empty_dialogue.text())

        _s("images_enable", self.images_enable.isChecked())
        _s("show_caption", self.show_caption.isChecked())
        _s("image_align", self.image_align.currentText())
        _s("image_max_width", self.image_max_width.text())

        # 장면 분할
        checked = self.split_mode_group.checkedButton()
        if checked:
            _s("split_mode", checked.property("value"))

        _s("scene_patterns", self.scene_patterns.text())
        _s("entries_per_chapter", self.entries_per_chapter.text())
        _s("min_scene_entries", self.min_scene_entries.text())
        _s("title_format", self.title_format.text())

        _s("scene_marker", self.scene_marker.text())
        _s("chapter_ornament", self.chapter_ornament.text())
        _s("scene_separator", self.scene_separator.text())

        # 파싱 규칙
        _s("custom_separator_type", self.separator_type.currentText())
        _s("custom_separator_text", self.custom_separator_input.text())
        _s("custom_name_position", self.name_position.currentText())
        _s("custom_name_max", self.name_max.text())
        _s("narration_no_name", self.narration_no_name.isChecked())
        _s("dice_keywords", self.dice_patterns_text.text())
        _s("system_prefix", self.system_prefix.text())
        _s("rule_system", self.rule_system.currentText())

        state.save()

    # ──────────── 설정 로드 ────────────
    def load_settings(self):
        """AppState에 저장된 설정을 UI에 반영"""
        _g = self.app_state.get

        # 콘텐츠 필터
        self.include_dice.setChecked(_g("include_dice", True))
        self.include_effects.setChecked(_g("include_effects", True))
        self.include_system.setChecked(_g("include_system", True))
        self.include_ooc.setChecked(_g("include_ooc", False))

        # narrators: 리스트인 경우 문자열로 변환
        narrators_val = _g("narrators", "GM, KP, DM, Keeper, 나레이터, 진행자")
        if isinstance(narrators_val, list):
            narrators_val = ", ".join(narrators_val)
        self.narrators_entry.setText(str(narrators_val))

        self.narration_prefix.setText(str(_g("narration_prefix", "＿")))
        self.narration_indent.setText(str(_g("narration_indent", "1.5")))

        self.merge_dialogue.setChecked(_g("merge_dialogue", False))
        self.safe_set_combo(self.merge_separator_combo, str(_g("merge_separator", "newline")))
        self.merge_max.setText(str(_g("merge_max", "5")))
        self.empty_dialogue.setText(str(_g("empty_dialogue", "……")))

        self.images_enable.setChecked(_g("images_enable", True))
        self.show_caption.setChecked(_g("show_caption", True))
        self.safe_set_combo(self.image_align, str(_g("image_align", "center")))
        self.image_max_width.setText(str(_g("image_max_width", "100")))

        # 장면 분할
        split_mode = _g("split_mode", "scene")
        for btn in self.split_mode_group.buttons():
            if btn.property("value") == split_mode:
                btn.setChecked(True)
                break

        scene_val = _g("scene_patterns", "■, 씬, Scene, 장면, Act")
        if isinstance(scene_val, list):
            scene_val = ", ".join(scene_val)
        self.scene_patterns.setText(str(scene_val))

        self.entries_per_chapter.setText(str(_g("entries_per_chapter", "300")))
        self.min_scene_entries.setText(str(_g("min_scene_entries", "10")))
        self.title_format.setText(str(_g("title_format", "장면 {n}")))

        self.scene_marker.setText(str(_g("scene_marker", "■")))
        self.chapter_ornament.setText(str(_g("chapter_ornament", "─────  ✦  ─────")))
        self.scene_separator.setText(str(_g("scene_separator", "＊　＊　＊")))

        # 필드 가시성 갱신
        self._on_split_mode_changed()

        # 파싱 규칙
        self.safe_set_combo(self.separator_type, str(_g("custom_separator_type", "콜론 (:)")))
        if hasattr(self, "custom_separator_input"):
            self.custom_separator_input.setText(str(_g("custom_separator_text", "")))
            self._on_separator_type_changed(str(_g("custom_separator_type", "콜론 (:)")))
        self.safe_set_combo(
            self.name_position, str(_g("custom_name_position", "구분자 앞 (이름: 대사)"))
        )
        self.name_max.setText(str(_g("custom_name_max", "50")))

        # 나레이션 규칙의 나레이터 이름 (narrators 키 공유)
        if hasattr(self, "narration_users"):
            narration_val = _g("narrators", "GM, KP, DM, Keeper, 나레이터")
            if isinstance(narration_val, list):
                narration_val = ", ".join(narration_val)
            self.narration_users.setText(str(narration_val))
        if hasattr(self, "narration_no_name"):
            self.narration_no_name.setChecked(_g("narration_no_name", False))
        if hasattr(self, "dice_patterns_text"):
            self.dice_patterns_text.setText(
                str(_g("dice_keywords", "CCB, 1D100, 1D20, roll, Rolling"))
            )
        if hasattr(self, "system_prefix"):
            self.system_prefix.setText(str(_g("system_prefix", "System:")))
        if hasattr(self, "rule_system"):
            self.safe_set_combo(self.rule_system, str(_g("rule_system", "자동 감지")))
