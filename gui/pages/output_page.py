"""
TRPG Log Converter Pro - 출력 페이지
출력 형식, 폴더, 설정 관리
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
)
from PySide6.QtCore import Qt
from pathlib import Path

from qfluentwidgets import (
    BodyLabel, LineEdit, PushButton, InfoBar, InfoBarPosition, MessageBox
)

from .base_page import BasePage
from ..components import ContentCard


class OutputPage(BasePage):
    """출력 페이지 - 출력 형식, 폴더, 설정 관리"""

    def __init__(self, config_manager, inspector=None, parent=None):
        super().__init__(config_manager, inspector, parent)
        self._setup_page()
        self.load_settings()

    def _setup_page(self):
        """페이지 UI 구성"""
        self.add_header("출력 설정", "출력 형식과 저장 위치를 설정합니다")

        # 출력 형식 카드
        format_card = ContentCard("출력 형식", "생성할 파일 유형 선택")

        self.output_format = format_card.add_radio_group(
            [
                ("EPUB + DOCX", "both"),
                ("EPUB만", "epub"),
                ("DOCX만", "docx"),
            ],
            "output_format",
            default=self.settings.get('output_format', 'both')
        )

        self.content_layout.addWidget(format_card)

        # 출판 판형 카드
        page_format_card = ContentCard("출판 판형", "DOCX 페이지 크기 설정 (인쇄용)")

        self.page_format = page_format_card.add_dropdown(
            "판형", "page_format",
            options=[
                "A4 (210×297mm)",
                "A5 (148×210mm)",
                "B5 (182×257mm)",
                "신국판 (152×225mm)",
                "국판 (148×210mm)",
                "46배판 (128×188mm)",
                "문고판 (105×148mm)",
                "Letter (8.5×11in)",
                "사용자 정의"
            ],
            default=self.settings.get('page_format', 'A5 (148×210mm)'),
            help_text="출판용 DOCX의 페이지 크기. 신국판/문고판은 한국 출판 표준입니다."
        )
        self.page_format.currentTextChanged.connect(self._on_page_format_changed)

        # 사용자 정의 크기
        custom_size_row = QHBoxLayout()
        custom_size_row.setSpacing(8)

        self.custom_width = LineEdit()
        self.custom_width.setPlaceholderText("너비 (mm)")
        self.custom_width.setText(self.settings.get('custom_page_width', '148'))
        self.custom_width.setMaximumWidth(80)
        custom_size_row.addWidget(BodyLabel("너비"))
        custom_size_row.addWidget(self.custom_width)

        custom_size_row.addWidget(BodyLabel("×"))

        self.custom_height = LineEdit()
        self.custom_height.setPlaceholderText("높이 (mm)")
        self.custom_height.setText(self.settings.get('custom_page_height', '210'))
        self.custom_height.setMaximumWidth(80)
        custom_size_row.addWidget(BodyLabel("높이"))
        custom_size_row.addWidget(self.custom_height)

        custom_size_row.addWidget(BodyLabel("mm"))
        custom_size_row.addStretch()

        page_format_card.add_layout(custom_size_row)

        # 초기 상태 설정
        self._update_custom_size_visibility()

        self.content_layout.addWidget(page_format_card)

        # 출력 폴더 카드
        folder_card = ContentCard("출력 폴더", "변환된 파일이 저장될 위치")

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        self.output_dir = LineEdit()
        self.output_dir.setPlaceholderText("출력 폴더 경로")
        self.output_dir.setText(self.settings.get('output_dir', str(Path.cwd() / 'export')))
        folder_row.addWidget(self.output_dir, 1)

        browse_btn = PushButton("찾기")
        browse_btn.clicked.connect(self._browse_output)
        folder_row.addWidget(browse_btn)

        open_btn = PushButton("열기")
        open_btn.clicked.connect(self._open_output)
        folder_row.addWidget(open_btn)

        folder_card.add_layout(folder_row)

        self.content_layout.addWidget(folder_card)

        # DOCX 여백 카드
        margin_card = ContentCard("DOCX 여백", "페이지 여백 설정 (인치 단위, 1인치=25.4mm)")

        margins = self.settings.get('margins', {})

        margin_row = QHBoxLayout()
        margin_row.setSpacing(16)

        for key, label in [('top', '상'), ('bottom', '하'), ('left', '좌'), ('right', '우')]:
            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)

            lbl = BodyLabel(label)
            item_layout.addWidget(lbl)

            entry = LineEdit()
            entry.setPlaceholderText("1.0")
            entry.setText(margins.get(key, '1.0'))
            entry.setMaximumWidth(60)
            setattr(self, f"margin_{key}", entry)
            item_layout.addWidget(entry)

            margin_row.addWidget(item)

        margin_row.addStretch()
        margin_card.add_layout(margin_row)

        self.content_layout.addWidget(margin_card)

        # 설정 관리 카드
        settings_card = ContentCard("설정 관리")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        save_btn = PushButton("설정 저장")
        save_btn.clicked.connect(self._save_all_settings)
        btn_row.addWidget(save_btn)

        export_btn = PushButton("설정 내보내기")
        export_btn.clicked.connect(self._export_settings)
        btn_row.addWidget(export_btn)

        import_btn = PushButton("설정 가져오기")
        import_btn.clicked.connect(self._import_settings)
        btn_row.addWidget(import_btn)

        reset_btn = PushButton("기본값 복원")
        reset_btn.clicked.connect(self._reset_settings)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()
        settings_card.add_layout(btn_row)

        self.content_layout.addWidget(settings_card)

        self.add_stretch()

    def _on_page_format_changed(self, format_name: str):
        """판형 변경 시"""
        self._update_custom_size_visibility()
        self.save_settings()

    def _update_custom_size_visibility(self):
        """사용자 정의 크기 입력 필드 표시/숨김"""
        is_custom = "사용자 정의" in self.page_format.currentText()
        self.custom_width.setEnabled(is_custom)
        self.custom_height.setEnabled(is_custom)

    def _browse_output(self):
        """출력 폴더 선택"""
        path = QFileDialog.getExistingDirectory(
            self,
            "출력 폴더 선택",
            self.output_dir.text() or str(Path.cwd())
        )
        if path:
            self.output_dir.setText(path)
            self.save_settings()

    def _open_output(self):
        """출력 폴더 열기"""
        import subprocess
        import sys

        path = self.output_dir.text()
        if path and Path(path).exists():
            if sys.platform == 'darwin':
                subprocess.run(['open', path])
            elif sys.platform == 'win32':
                subprocess.run(['explorer', path])
            else:
                subprocess.run(['xdg-open', path])
        else:
            InfoBar.warning(
                title='경고',
                content='폴더가 존재하지 않습니다.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _save_all_settings(self):
        """모든 설정 저장"""
        self.save_settings()
        InfoBar.success(
            title='저장 완료',
            content='설정이 저장되었습니다.',
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )

    def _export_settings(self):
        """설정 내보내기"""
        import json

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "설정 파일 내보내기",
            "trpg_converter_settings.json",
            "JSON 파일 (*.json)"
        )
        if not file_path:
            return

        settings = self.config_manager.get_gui_settings()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        InfoBar.success(
            title='내보내기 완료',
            content=f'설정이 저장되었습니다: {file_path}',
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )

    def _import_settings(self):
        """설정 가져오기"""
        import json

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "설정 파일 가져오기",
            "",
            "JSON 파일 (*.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            self.config_manager.save_gui_settings(settings)
            self.load_settings()

            InfoBar.success(
                title='가져오기 완료',
                content='설정을 불러왔습니다. 다른 페이지의 설정도 업데이트하려면 앱을 재시작하세요.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )
        except Exception as e:
            InfoBar.error(
                title='오류',
                content=f'설정 파일을 읽을 수 없습니다: {e}',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )

    def _reset_settings(self):
        """기본값으로 복원"""
        w = MessageBox(
            "설정 초기화",
            "모든 설정을 기본값으로 초기화하시겠습니까?",
            self.window()
        )

        if w.exec():
            default_settings = self.config_manager.get_default_gui_settings()
            self.config_manager.save_gui_settings(default_settings)
            self.load_settings()
            InfoBar.success(
                title='초기화 완료',
                content='모든 설정이 기본값으로 초기화되었습니다.',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def save_settings(self):
        """설정 저장"""
        # 출력 형식
        checked = self.output_format.checkedButton()
        if checked:
            self.settings['output_format'] = checked.property("value")

        # 판형
        self.settings['page_format'] = self.page_format.currentText()
        self.settings['custom_page_width'] = self.custom_width.text()
        self.settings['custom_page_height'] = self.custom_height.text()

        # output_dir: 위젯에 값이 있으면 저장 (사용자가 이 페이지에서 변경했을 수 있음)
        self.settings['output_dir'] = self.output_dir.text()

        self.settings['margins'] = {
            'top': self.margin_top.text(),
            'bottom': self.margin_bottom.text(),
            'left': self.margin_left.text(),
            'right': self.margin_right.text(),
        }

        self.config_manager.save_gui_settings(self.settings)

    def load_settings(self):
        """설정 로드"""
        self.settings = self.config_manager.get_gui_settings()

        # 출력 형식
        output_format = self.settings.get('output_format', 'both')
        for button in self.output_format.buttons():
            if button.property("value") == output_format:
                button.setChecked(True)
                break

        # 판형
        self.page_format.setCurrentText(self.settings.get('page_format', 'A5 (148×210mm)'))
        self.custom_width.setText(self.settings.get('custom_page_width', '148'))
        self.custom_height.setText(self.settings.get('custom_page_height', '210'))
        self._update_custom_size_visibility()

        self.output_dir.setText(self.settings.get('output_dir', str(Path.cwd() / 'export')))

        margins = self.settings.get('margins', {})
        self.margin_top.setText(margins.get('top', '1.0'))
        self.margin_bottom.setText(margins.get('bottom', '1.0'))
        self.margin_left.setText(margins.get('left', '1.0'))
        self.margin_right.setText(margins.get('right', '1.0'))

    def on_page_enter(self):
        """페이지 진입 시 호출 - 출력 폴더 동기화"""
        # 다른 페이지에서 변경된 output_dir을 동기화
        current_output_dir = self.config_manager.get_gui_settings().get('output_dir', str(Path.cwd() / 'export'))
        if self.output_dir.text() != current_output_dir:
            self.output_dir.setText(current_output_dir)
