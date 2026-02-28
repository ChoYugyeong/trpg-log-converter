"""
TRPG Log Converter Pro - 커스텀 파싱 규칙 편집기
정규식을 몰라도 GUI에서 파싱 규칙을 정의할 수 있는 페이지
"""

import re
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPlainTextEdit, QFrame, QButtonGroup
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from qfluentwidgets import (
    BodyLabel, PushButton, PrimaryPushButton, LineEdit, ComboBox,
    RadioButton, InfoBar, InfoBarPosition, MessageBox, CheckBox
)

from .base_page import BasePage
from ..components import ContentCard

logger = logging.getLogger(__name__)


class ParsingRulePage(BasePage):
    """커스텀 파싱 규칙 편집기 - 정규식 없이 파싱 규칙 정의"""
    settings_changed = Signal()

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._rules = []
        self._setup_page()
        self.load_settings()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("파싱 규칙", "로그 형식에 맞는 파싱 규칙을 정의합니다")

        # === 플랫폼 템플릿 카드 ===
        template_card = ContentCard("빠른 시작", "자주 사용되는 플랫폼 템플릿을 선택하세요")

        template_layout = QHBoxLayout()
        template_layout.setSpacing(8)

        templates = [
            ("코코포리아", "cocofolia"),
            ("Roll20", "roll20"),
            ("카카오톡", "kakaotalk"),
            ("디스코드", "discord"),
            ("직접 설정", "custom"),
        ]
        for text, value in templates:
            btn = PushButton(text)
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda checked, v=value: self._apply_template(v))
            template_layout.addWidget(btn)

        template_layout.addStretch()
        template_card.add_layout(template_layout)
        self.content_layout.addWidget(template_card)

        # === 이름/대사 구분 규칙 카드 ===
        name_card = ContentCard("이름·대사 구분", "캐릭터 이름과 대사를 어떻게 구분하는지 설정합니다")

        # 구분자 방식
        self.separator_type = name_card.add_dropdown(
            "구분 방식", "separator_type",
            options=["콜론 (:)", "탭 (Tab)", "대괄호 ([이름])", "꺾쇠 (<이름>)", "HTML 태그 자동"],
            default="콜론 (:)",
            help_text="이름과 대사를 구분하는 방식을 선택합니다"
        )

        # 이름 위치
        self.name_position = name_card.add_dropdown(
            "이름 위치", "name_position",
            options=["구분자 앞 (이름: 대사)", "구분자 안 ([이름] 대사)", "첫 번째 줄 (이름\\n대사)"],
            default="구분자 앞 (이름: 대사)",
            help_text="이름이 대사 내에서 어디에 위치하는지 선택합니다"
        )

        # 이름 최대 길이
        self.name_max = name_card.add_text_field(
            "이름 최대 길이", "name_max",
            placeholder="50",
            default="50",
            help_text="이 길이를 초과하면 이름으로 인식하지 않습니다"
        )

        self.content_layout.addWidget(name_card)

        # === 나레이션 인식 카드 ===
        narration_card = ContentCard("나레이션 규칙", "나레이션(지문)으로 인식할 조건을 설정합니다")

        self.narration_users = narration_card.add_text_field(
            "나레이터 이름", "narration_users",
            placeholder="GM, KP, DM, Keeper, 나레이터",
            default=self.settings.get('narrators', 'GM, KP, DM, Keeper, 나레이터'),
            help_text="이 이름으로 발화하면 나레이션으로 처리합니다 (쉼표 구분)"
        )

        self.narration_no_name = narration_card.add_checkbox(
            "이름 없는 텍스트는 나레이션으로 처리",
            "narration_no_name",
            checked=self.settings.get('narration_no_name', False),
            help_text="이름: 대사 형식이 아닌 줄을 나레이션으로 처리합니다"
        )

        self.content_layout.addWidget(narration_card)

        # === 장면 구분 카드 ===
        scene_card = ContentCard("장면 구분", "장면(씬)을 구분하는 패턴을 설정합니다")

        self.scene_markers = scene_card.add_text_field(
            "장면 마커", "scene_markers",
            placeholder="■, ●, ▶, 씬, Scene, 장면",
            default=self.settings.get('scene_patterns', '■, 씬, Scene, 장면, Act'),
            help_text="이 텍스트로 시작하는 줄을 장면 구분으로 인식합니다 (쉼표 구분)"
        )

        self.scene_separator = scene_card.add_text_field(
            "구분선 패턴", "scene_separator",
            placeholder="---,  ===, ***",
            default=self.settings.get('scene_separator_pattern', '---'),
            help_text="이 패턴으로 된 줄을 장면 구분선으로 인식합니다"
        )

        self.content_layout.addWidget(scene_card)

        # === 주사위/시스템 메시지 카드 ===
        dice_card = ContentCard("주사위·시스템 메시지", "주사위 굴림이나 시스템 메시지 인식 규칙")

        self.dice_patterns_text = dice_card.add_text_field(
            "주사위 키워드", "dice_keywords",
            placeholder="CCB, 1D100, 1D20, roll, Rolling",
            default=self.settings.get('dice_keywords', 'CCB, 1D100, 1D20, roll, Rolling'),
            help_text="이 키워드가 포함된 줄을 주사위 굴림으로 인식합니다"
        )

        self.system_prefix = dice_card.add_text_field(
            "시스템 접두사", "system_prefix",
            placeholder="System:, [시스템]",
            default=self.settings.get('system_prefix', 'System:'),
            help_text="이 텍스트로 시작하는 줄을 시스템 메시지로 인식합니다"
        )

        self.content_layout.addWidget(dice_card)

        # === 미리보기/테스트 카드 ===
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
        self.test_input.setMinimumHeight(120)
        self.test_input.setMaximumHeight(150)
        test_card.add_widget(self.test_input)

        test_btn = PrimaryPushButton("파싱 테스트")
        test_btn.setMinimumHeight(38)
        test_btn.clicked.connect(self._run_test)
        test_card.add_widget(test_btn)

        # 결과 표시
        self.test_result = QPlainTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setMinimumHeight(120)
        self.test_result.setMaximumHeight(200)
        self.test_result.setPlaceholderText("파싱 결과가 여기에 표시됩니다...")
        self.test_result.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background: rgba(0, 0, 0, 0.03);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
            }
        """)
        test_card.add_widget(self.test_result)

        self.content_layout.addWidget(test_card)

        self.add_stretch()

    def _apply_template(self, platform: str):
        """플랫폼 템플릿 적용"""
        templates = {
            'cocofolia': {
                'separator_type': 'HTML 태그 자동',
                'name_position': '구분자 앞 (이름: 대사)',
                'narration_users': 'GM, KP, DM, Keeper',
                'scene_markers': '■, 씬, 장면',
                'dice_keywords': 'CCB, 1D100, 1D20, 2D6',
                'system_prefix': 'System:',
            },
            'roll20': {
                'separator_type': 'HTML 태그 자동',
                'name_position': '구분자 앞 (이름: 대사)',
                'narration_users': 'GM, DM, Narrator, Storyteller',
                'scene_markers': '■, Scene, Act, Session',
                'dice_keywords': 'roll, Rolling, 1d20, 1d100, attack, save',
                'system_prefix': 'System:',
            },
            'kakaotalk': {
                'separator_type': '대괄호 ([이름])',
                'name_position': '구분자 안 ([이름] 대사)',
                'narration_users': 'GM, KP, 마스터, 진행자',
                'scene_markers': '■, ●, ---',
                'dice_keywords': '1D100, 1D20, 주사위',
                'system_prefix': '[시스템]',
            },
            'discord': {
                'separator_type': '콜론 (:)',
                'name_position': '구분자 앞 (이름: 대사)',
                'narration_users': 'GM, DM, Bot, 봇',
                'scene_markers': '■, ==, ---',
                'dice_keywords': '!roll, /roll, 1d20',
                'system_prefix': '[Bot]',
            },
            'custom': {},
        }

        template = templates.get(platform, {})
        if not template:
            InfoBar.info(
                title='직접 설정 모드',
                content='아래 필드를 직접 수정해주세요.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        # 필드 값 적용
        if 'separator_type' in template:
            idx = self.separator_type.findText(template['separator_type'])
            if idx >= 0:
                self.separator_type.setCurrentIndex(idx)
        if 'name_position' in template:
            idx = self.name_position.findText(template['name_position'])
            if idx >= 0:
                self.name_position.setCurrentIndex(idx)
        if 'narration_users' in template:
            self.narration_users.setText(template['narration_users'])
        if 'scene_markers' in template:
            self.scene_markers.setText(template['scene_markers'])
        if 'dice_keywords' in template:
            self.dice_patterns_text.setText(template['dice_keywords'])
        if 'system_prefix' in template:
            self.system_prefix.setText(template['system_prefix'])

        self.save_settings()

        InfoBar.success(
            title=f'{platform} 템플릿 적용',
            content='파싱 규칙이 업데이트되었습니다.',
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _run_test(self):
        """파싱 테스트 실행"""
        text = self.test_input.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title='텍스트 없음',
                content='테스트할 텍스트를 입력해주세요.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        self.save_settings()

        results = []
        narrators = [n.strip() for n in self.narration_users.text().split(',') if n.strip()]
        scene_markers = [m.strip() for m in self.scene_markers.text().split(',') if m.strip()]
        dice_keywords = [k.strip().upper() for k in self.dice_patterns_text.text().split(',') if k.strip()]
        system_prefix = self.system_prefix.text().strip()

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            entry_type = 'dialogue'
            name = ''
            content = line

            # 장면 마커 체크
            is_scene = False
            for marker in scene_markers:
                if line.startswith(marker):
                    is_scene = True
                    break
            if is_scene:
                entry_type = 'scene'
                results.append(f"  [장면] {line}")
                continue

            # 시스템 메시지 체크
            if system_prefix and line.lower().startswith(system_prefix.lower()):
                entry_type = 'system'
                content = line[len(system_prefix):].strip()
                results.append(f"  [시스템] {content}")
                continue

            # 이름:대사 분리
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts[0].strip()) <= int(self.name_max.text() or 50):
                    name = parts[0].strip()
                    content = parts[1].strip()

            # 나레이터 체크
            if name and name in narrators:
                entry_type = 'narration'

            # 주사위 체크
            if any(kw in content.upper() for kw in dice_keywords):
                if '→' in content or '=' in content or '>' in content:
                    entry_type = 'dice'

            # 이름 없는 텍스트 → 나레이션
            if not name and self.narration_no_name.isChecked():
                entry_type = 'narration'

            type_labels = {
                'dialogue': '대사',
                'narration': '나레이션',
                'dice': '주사위',
                'system': '시스템',
                'scene': '장면',
            }

            label = type_labels.get(entry_type, entry_type)
            if name:
                results.append(f"  [{label}] {name}: {content}")
            else:
                results.append(f"  [{label}] {content}")

        if results:
            self.test_result.setPlainText(
                f"=== 파싱 결과 ({len(results)}줄) ===\n" + '\n'.join(results)
            )
        else:
            self.test_result.setPlainText("파싱 결과 없음")

    def save_settings(self):
        """설정 저장"""
        self.settings['custom_separator_type'] = self.separator_type.currentText()
        self.settings['custom_name_position'] = self.name_position.currentText()
        self.settings['custom_name_max'] = self.name_max.text()
        self.settings['narrators'] = self.narration_users.text()
        self.settings['narration_no_name'] = self.narration_no_name.isChecked()
        self.settings['scene_patterns'] = self.scene_markers.text()
        self.settings['scene_separator_pattern'] = self.scene_separator.text()
        self.settings['dice_keywords'] = self.dice_patterns_text.text()
        self.settings['system_prefix'] = self.system_prefix.text()
        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()
        if hasattr(self, 'separator_type'):
            self.separator_type.setCurrentText(self.settings.get('custom_separator_type', '콜론 (:)'))
        if hasattr(self, 'name_position'):
            self.name_position.setCurrentText(self.settings.get('custom_name_position', '구분자 앞 (이름: 대사)'))
        if hasattr(self, 'name_max'):
            self.name_max.setText(self.settings.get('custom_name_max', '50'))
        if hasattr(self, 'narration_users'):
            self.narration_users.setText(self.settings.get('narrators', 'GM, KP, DM, Keeper, 나레이터'))
        if hasattr(self, 'narration_no_name'):
            self.narration_no_name.setChecked(self.settings.get('narration_no_name', False))
        if hasattr(self, 'scene_markers'):
            self.scene_markers.setText(self.settings.get('scene_patterns', '■, 씬, Scene, 장면, Act'))
        if hasattr(self, 'scene_separator'):
            self.scene_separator.setText(self.settings.get('scene_separator_pattern', '---'))
        if hasattr(self, 'dice_patterns_text'):
            self.dice_patterns_text.setText(self.settings.get('dice_keywords', 'CCB, 1D100, 1D20, roll, Rolling'))
        if hasattr(self, 'system_prefix'):
            self.system_prefix.setText(self.settings.get('system_prefix', 'System:'))
