"""
TRPG Log Converter Pro - 프리셋 편집 페이지
프리셋 목록 관리 및 편집
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QFrame, QPlainTextEdit, QDialog, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import json

from qfluentwidgets import (
    BodyLabel, PushButton, LineEdit, ComboBox, TextEdit,
    InfoBar, InfoBarPosition, MessageBox
)

from .base_page import BasePage
from ..components import ContentCard
from core.services import PresetService


class PresetEditDialog(QDialog):
    """프리셋 편집 대화상자"""

    def __init__(self, preset_data: dict = None, parent=None):
        super().__init__(parent)
        self.preset_data = preset_data or {}
        self.setWindowTitle("프리셋 편집" if preset_data else "새 프리셋")
        self.setMinimumSize(500, 600)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 기본 정보
        info_card = ContentCard("기본 정보")

        self.name_entry = info_card.add_text_field(
            "이름 (ID)", "name",
            placeholder="my_preset",
            help_text="영문, 숫자, 언더스코어만 사용"
        )

        self.display_name_entry = info_card.add_text_field(
            "표시 이름", "display_name",
            placeholder="내 프리셋",
            help_text="목록에 표시될 이름"
        )

        self.description_entry = info_card.add_text_field(
            "설명", "description",
            placeholder="프리셋에 대한 설명",
            help_text="프리셋의 용도 설명"
        )

        self.platform_combo = info_card.add_dropdown(
            "플랫폼", "platform",
            options=["ccfolia", "roll20", "discord", "text", "custom"],
            default="custom",
            help_text="이 프리셋이 적용되는 플랫폼"
        )

        self.tags_entry = info_card.add_text_field(
            "태그", "tags",
            placeholder="korean, trpg, custom",
            help_text="쉼표로 구분"
        )

        layout.addWidget(info_card)

        # 설정 JSON
        config_card = ContentCard("설정 (JSON)", "프리셋 설정값을 JSON 형식으로 입력")

        self.config_editor = QPlainTextEdit()
        self.config_editor.setPlaceholderText('{\n  "style": {\n    "scene_marker": "★"\n  }\n}')
        self.config_editor.setMinimumHeight(200)
        import sys as _sys
        self.config_editor.setFont(QFont("Consolas" if _sys.platform == "win32" else "Monaco", 12))
        self.config_editor.setStyleSheet("""
            QPlainTextEdit {
                background: palette(base);
                color: palette(text);
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 8px;
                padding: 12px;
            }
        """)

        config_card.add_widget(self.config_editor)
        layout.addWidget(config_card)

        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = PushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = PushButton("저장")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _load_data(self):
        """기존 데이터 로드"""
        if self.preset_data:
            self.name_entry.setText(self.preset_data.get("name", ""))
            self.display_name_entry.setText(self.preset_data.get("display_name", ""))
            self.description_entry.setText(self.preset_data.get("description", ""))
            self.platform_combo.setCurrentText(self.preset_data.get("platform", "custom"))

            tags = self.preset_data.get("tags", [])
            self.tags_entry.setText(", ".join(tags))

            config = self.preset_data.get("config", {})
            self.config_editor.setPlainText(json.dumps(config, indent=2, ensure_ascii=False))

    def _save(self):
        """저장"""
        name = self.name_entry.text().strip()
        if not name:
            InfoBar.warning(
                title="입력 오류",
                content="이름을 입력하세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        # JSON 파싱 검증
        try:
            config_text = self.config_editor.toPlainText().strip()
            config = json.loads(config_text) if config_text else {}
        except json.JSONDecodeError as e:
            InfoBar.error(
                title="JSON 오류",
                content=f"설정 JSON 형식이 올바르지 않습니다: {e}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )
            return

        # 태그 파싱
        tags_text = self.tags_entry.text().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []

        self.result_data = {
            "name": name,
            "display_name": self.display_name_entry.text().strip() or name,
            "description": self.description_entry.text().strip(),
            "platform": self.platform_combo.currentText(),
            "config": config,
            "tags": tags,
        }

        self.accept()

    def get_result(self) -> dict:
        """결과 데이터 반환"""
        return getattr(self, 'result_data', {})


class PresetPage(BasePage):
    """프리셋 관리 페이지"""
    preset_changed = Signal()

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self.preset_service = PresetService()
        self._custom_presets = self._load_custom_presets()
        self._setup_page()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("프리셋 관리", "변환 설정 프리셋을 관리합니다")

        # 프리셋 목록 카드
        list_card = ContentCard("프리셋 목록")

        # 목록
        self.preset_list = QListWidget()
        self.preset_list.setMinimumHeight(250)
        self.preset_list.itemClicked.connect(self._on_preset_selected)
        self.preset_list.itemDoubleClicked.connect(self._edit_preset)
        list_card.add_widget(self.preset_list)

        # 버튼
        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        save_current_btn = PushButton("현재 설정 저장")
        save_current_btn.setObjectName("primary")
        save_current_btn.clicked.connect(self._save_current_settings)
        buttons.addWidget(save_current_btn)

        add_btn = PushButton("새 프리셋")
        add_btn.clicked.connect(self._add_preset)
        buttons.addWidget(add_btn)

        edit_btn = PushButton("편집")
        edit_btn.clicked.connect(self._edit_preset)
        buttons.addWidget(edit_btn)

        duplicate_btn = PushButton("복제")
        duplicate_btn.clicked.connect(self._duplicate_preset)
        buttons.addWidget(duplicate_btn)

        delete_btn = PushButton("삭제")
        delete_btn.setObjectName("danger")
        delete_btn.clicked.connect(self._delete_preset)
        buttons.addWidget(delete_btn)

        buttons.addSpacing(16)

        apply_btn = PushButton("적용")
        apply_btn.clicked.connect(self._apply_preset)
        buttons.addWidget(apply_btn)

        buttons.addStretch()

        import_btn = PushButton("가져오기")
        import_btn.clicked.connect(self._import_preset)
        buttons.addWidget(import_btn)

        export_btn = PushButton("내보내기")
        export_btn.clicked.connect(self._export_preset)
        buttons.addWidget(export_btn)

        list_card.add_layout(buttons)
        self.content_layout.addWidget(list_card)

        # 프리셋 상세 정보 카드
        detail_card = ContentCard("프리셋 상세")

        self.detail_name = BodyLabel("선택된 프리셋 없음")
        self.detail_name.setStyleSheet("font-size: 16px; font-weight: 600;")
        detail_card.add_widget(self.detail_name)

        self.detail_desc = BodyLabel("")
        self.detail_desc.setWordWrap(True)
        self.detail_desc.setStyleSheet("color: palette(mid);")
        detail_card.add_widget(self.detail_desc)

        self.detail_platform = BodyLabel("")
        detail_card.add_widget(self.detail_platform)

        self.detail_tags = BodyLabel("")
        self.detail_tags.setStyleSheet("color: palette(link);")
        detail_card.add_widget(self.detail_tags)

        # 설정 미리보기
        self.config_preview = QPlainTextEdit()
        self.config_preview.setReadOnly(True)
        self.config_preview.setMaximumHeight(150)
        import sys as _sys
        self.config_preview.setFont(QFont("Consolas" if _sys.platform == "win32" else "Monaco", 11))
        self.config_preview.setStyleSheet("""
            QPlainTextEdit {
                background: rgba(128, 128, 128, 0.05);
                border: 1px solid rgba(128, 128, 128, 0.1);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        detail_card.add_widget(self.config_preview)

        self.content_layout.addWidget(detail_card)

        self.add_stretch()

        # 목록 로드
        self._refresh_list()

    def _load_custom_presets(self) -> dict:
        """저장된 커스텀 프리셋 로드"""
        return self.settings.get('custom_presets', {})

    def _save_custom_presets(self):
        """커스텀 프리셋 저장"""
        self.settings['custom_presets'] = self._custom_presets
        self.config_manager.save_gui_settings(self.settings)

    def _refresh_list(self):
        """프리셋 목록 새로고침"""
        self.preset_list.clear()

        # 내장 프리셋
        for preset in self.preset_service.list_presets():
            item = QListWidgetItem(f"[Built-in] {preset.display_name}")
            item.setData(Qt.UserRole, {"name": preset.name, "builtin": True})
            self.preset_list.addItem(item)

        # 커스텀 프리셋
        for name, data in self._custom_presets.items():
            display_name = data.get("display_name", name)
            item = QListWidgetItem(f"[Custom] {display_name}")
            item.setData(Qt.UserRole, {"name": name, "builtin": False})
            self.preset_list.addItem(item)

    def _on_preset_selected(self, item: QListWidgetItem):
        """프리셋 선택 시"""
        data = item.data(Qt.UserRole)
        name = data["name"]
        builtin = data["builtin"]

        if builtin:
            preset = self.preset_service.get_preset(name)
            if preset:
                self.detail_name.setText(f"[Built-in] {preset.display_name}")
                self.detail_desc.setText(preset.description)
                self.detail_platform.setText(f"플랫폼: {preset.platform}")
                self.detail_tags.setText(f"태그: {', '.join(preset.tags)}")
                self.config_preview.setPlainText(
                    json.dumps(preset.config, indent=2, ensure_ascii=False)
                )
        else:
            preset_data = self._custom_presets.get(name, {})
            self.detail_name.setText(f"[Custom] {preset_data.get('display_name', name)}")
            self.detail_desc.setText(preset_data.get("description", ""))
            self.detail_platform.setText(f"플랫폼: {preset_data.get('platform', 'custom')}")
            self.detail_tags.setText(f"태그: {', '.join(preset_data.get('tags', []))}")
            self.config_preview.setPlainText(
                json.dumps(preset_data.get("config", {}), indent=2, ensure_ascii=False)
            )

    def _save_current_settings(self):
        """현재 설정을 프리셋으로 저장"""
        # 현재 모든 GUI 설정 가져오기
        current_settings = self.config_manager.get_gui_settings()

        # 불필요한 키 제외 (최근 파일 등)
        exclude_keys = ['recent_files', 'custom_presets', 'window_geometry']
        config = {k: v for k, v in current_settings.items() if k not in exclude_keys}

        # 대화상자에 현재 설정 포함
        preset_data = {
            "name": "",
            "display_name": "내 스타일",
            "description": "현재 설정에서 저장됨",
            "platform": "custom",
            "tags": ["custom", "saved"],
            "config": config
        }

        dialog = PresetEditDialog(preset_data, parent=self)
        dialog.setWindowTitle("현재 설정을 프리셋으로 저장")

        if dialog.exec():
            data = dialog.get_result()
            name = data["name"]

            if name in self._custom_presets or name in PresetService.BUILTIN_PRESETS:
                InfoBar.warning(
                    title="중복",
                    content="이미 존재하는 프리셋 이름입니다.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return

            self._custom_presets[name] = data
            self._save_custom_presets()
            self._refresh_list()
            self.preset_changed.emit()

            InfoBar.success(
                title="저장됨",
                content=f"현재 설정이 '{data['display_name']}' 프리셋으로 저장되었습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _add_preset(self):
        """새 프리셋 추가"""
        dialog = PresetEditDialog(parent=self)
        if dialog.exec():
            data = dialog.get_result()
            name = data["name"]

            if name in self._custom_presets or name in PresetService.BUILTIN_PRESETS:
                InfoBar.warning(
                    title="중복",
                    content="이미 존재하는 프리셋 이름입니다.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return

            self._custom_presets[name] = data
            self._save_custom_presets()
            self._refresh_list()
            self.preset_changed.emit()

            InfoBar.success(
                title="추가됨",
                content=f"프리셋 '{data['display_name']}'이(가) 추가되었습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _edit_preset(self):
        """프리셋 편집"""
        item = self.preset_list.currentItem()
        if not item:
            return

        data = item.data(Qt.UserRole)
        if data["builtin"]:
            InfoBar.warning(
                title="편집 불가",
                content="내장 프리셋은 편집할 수 없습니다. 복제 후 편집하세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        name = data["name"]
        preset_data = self._custom_presets.get(name)
        if not preset_data:
            return

        dialog = PresetEditDialog(preset_data, parent=self)
        if dialog.exec():
            new_data = dialog.get_result()
            new_name = new_data["name"]

            # 이름이 변경된 경우
            if new_name != name:
                del self._custom_presets[name]

            self._custom_presets[new_name] = new_data
            self._save_custom_presets()
            self._refresh_list()
            self.preset_changed.emit()

            InfoBar.success(
                title="저장됨",
                content="프리셋이 저장되었습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _duplicate_preset(self):
        """프리셋 복제"""
        item = self.preset_list.currentItem()
        if not item:
            return

        data = item.data(Qt.UserRole)
        name = data["name"]

        # 원본 데이터 가져오기
        if data["builtin"]:
            preset = self.preset_service.get_preset(name)
            if preset:
                original = self.preset_service.export_preset(name)
        else:
            original = self._custom_presets.get(name, {}).copy()

        if not original:
            return

        # 새 이름 생성
        new_name = f"{name}_copy"
        counter = 1
        while new_name in self._custom_presets or new_name in PresetService.BUILTIN_PRESETS:
            new_name = f"{name}_copy_{counter}"
            counter += 1

        original["name"] = new_name
        original["display_name"] = f"{original.get('display_name', name)} (복제)"

        dialog = PresetEditDialog(original, parent=self)
        if dialog.exec():
            result = dialog.get_result()
            self._custom_presets[result["name"]] = result
            self._save_custom_presets()
            self._refresh_list()
            self.preset_changed.emit()

    def _apply_preset(self):
        """프리셋 적용"""
        item = self.preset_list.currentItem()
        if not item:
            InfoBar.warning(
                title="선택 필요",
                content="적용할 프리셋을 선택하세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        data = item.data(Qt.UserRole)
        name = data["name"]

        # 프리셋 설정 가져오기
        if data["builtin"]:
            preset = self.preset_service.get_preset(name)
            if preset:
                config = preset.config
                display_name = preset.display_name
            else:
                return
        else:
            preset_data = self._custom_presets.get(name, {})
            config = preset_data.get("config", {})
            display_name = preset_data.get("display_name", name)

        if not config:
            InfoBar.warning(
                title="설정 없음",
                content="이 프리셋에는 적용할 설정이 없습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        # 현재 설정에 프리셋 설정 병합
        current_settings = self.config_manager.get_gui_settings()
        current_settings.update(config)
        self.config_manager.save_gui_settings(current_settings)

        self.preset_changed.emit()

        InfoBar.success(
            title="적용 완료",
            content=f"'{display_name}' 프리셋이 적용되었습니다.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )

    def _delete_preset(self):
        """프리셋 삭제"""
        item = self.preset_list.currentItem()
        if not item:
            return

        data = item.data(Qt.UserRole)
        if data["builtin"]:
            InfoBar.warning(
                title="삭제 불가",
                content="내장 프리셋은 삭제할 수 없습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        name = data["name"]
        preset_data = self._custom_presets.get(name, {})
        display_name = preset_data.get("display_name", name)

        w = MessageBox(
            "프리셋 삭제",
            f"'{display_name}' 프리셋을 삭제하시겠습니까?",
            self
        )
        w.yesButton.setText("삭제")
        w.cancelButton.setText("취소")

        if w.exec():
            del self._custom_presets[name]
            self._save_custom_presets()
            self._refresh_list()
            self.preset_changed.emit()

            InfoBar.success(
                title="삭제됨",
                content="프리셋이 삭제되었습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _import_preset(self):
        """프리셋 가져오기"""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "프리셋 파일 가져오기",
            "",
            "JSON 파일 (*.json);;모든 파일 (*.*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            name = data.get("name")
            if not name:
                raise ValueError("프리셋 이름이 없습니다.")

            if name in self._custom_presets:
                w = MessageBox(
                    "중복 프리셋",
                    f"'{name}' 프리셋이 이미 존재합니다. 덮어쓰시겠습니까?",
                    self
                )
                if not w.exec():
                    return

            self._custom_presets[name] = data
            self._save_custom_presets()
            self._refresh_list()
            self.preset_changed.emit()

            InfoBar.success(
                title="가져오기 완료",
                content=f"프리셋 '{data.get('display_name', name)}'을(를) 가져왔습니다.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

        except Exception as e:
            InfoBar.error(
                title="가져오기 실패",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )

    def _export_preset(self):
        """프리셋 내보내기"""
        from PySide6.QtWidgets import QFileDialog

        item = self.preset_list.currentItem()
        if not item:
            InfoBar.warning(
                title="선택 필요",
                content="내보낼 프리셋을 선택하세요.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        data = item.data(Qt.UserRole)
        name = data["name"]

        if data["builtin"]:
            export_data = self.preset_service.export_preset(name)
        else:
            export_data = self._custom_presets.get(name, {})

        if not export_data:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "프리셋 파일 내보내기",
            f"{name}.json",
            "JSON 파일 (*.json)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            InfoBar.success(
                title="내보내기 완료",
                content=f"프리셋이 저장되었습니다: {file_path}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

        except Exception as e:
            InfoBar.error(
                title="내보내기 실패",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )

    def save_settings(self):
        """설정 저장"""
        self._save_custom_presets()

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()
        self._custom_presets = self._load_custom_presets()
        self._refresh_list()
