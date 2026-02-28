"""
GUI 테스트 - pytest-qt 기반
ConvertPage, MainWindow, ConversionWorker 검증
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.config_manager import ConfigManager


@pytest.fixture
def config_manager_for_gui(tmp_path):
    """GUI 테스트용 ConfigManager"""
    (tmp_path / 'data').mkdir(exist_ok=True)
    return ConfigManager(tmp_path)


@pytest.fixture
def sample_log_file(tmp_path):
    """샘플 로그 파일 생성"""
    log_file = tmp_path / "test_log.html"
    log_file.write_text(
        '<html><body>'
        '<p><span class="firing_name_홍길동 firing_firing">: 안녕하세요</span></p>'
        '<p><span class="firing_name_GM firing_firing">: 모험 시작</span></p>'
        '</body></html>',
        encoding='utf-8'
    )
    return str(log_file)


class TestConvertPage:
    """ConvertPage 테스트"""

    def test_initial_state(self, qtbot, config_manager_for_gui):
        """초기 상태 검증"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        assert page.files == []
        assert page.file_list.count() == 0
        assert page.progress_frame.isVisible() is False
        assert page.convert_btn.isEnabled()

    def test_add_files(self, qtbot, config_manager_for_gui, sample_log_file):
        """파일 추가 검증"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page._on_files_dropped([sample_log_file])

        assert len(page.files) == 1
        assert page.file_list.count() == 1
        assert sample_log_file in page.files

    def test_add_duplicate_file(self, qtbot, config_manager_for_gui, sample_log_file):
        """중복 파일 추가 시 무시"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page._on_files_dropped([sample_log_file])
        page._on_files_dropped([sample_log_file])

        assert len(page.files) == 1

    def test_clear_files(self, qtbot, config_manager_for_gui, sample_log_file):
        """파일 전체 삭제"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page._on_files_dropped([sample_log_file])
        page._clear_files()

        assert page.files == []
        assert page.file_list.count() == 0

    def test_remove_selected(self, qtbot, config_manager_for_gui, sample_log_file):
        """선택 파일 제거"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page._on_files_dropped([sample_log_file])
        page.file_list.setCurrentRow(0)
        page._remove_selected()

        assert page.files == []
        assert page.file_list.count() == 0

    def test_progress_update(self, qtbot, config_manager_for_gui):
        """진행률 업데이트 검증"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page.progress_frame.setVisible(True)
        page.update_progress(50, "변환 중...")

        assert page.progress_bar.value() == 50
        assert page.progress_label.text() == "변환 중..."

    def test_conversion_complete_success(self, qtbot, config_manager_for_gui):
        """변환 완료 (성공)"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page.progress_frame.setVisible(True)
        page.convert_btn.setEnabled(False)

        page.conversion_complete(True, "변환 완료!")

        assert page.progress_frame.isVisible() is False
        assert page.convert_btn.isEnabled()

    def test_conversion_complete_failure(self, qtbot, config_manager_for_gui):
        """변환 완료 (실패)"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page.progress_frame.setVisible(True)
        page.convert_btn.setEnabled(False)

        page.conversion_complete(False, "오류 발생")

        assert page.progress_frame.isVisible() is False
        assert page.convert_btn.isEnabled()

    def test_get_title_default(self, qtbot, config_manager_for_gui):
        """제목 기본값"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page.title_entry.setText("")
        assert page.get_title() == "TRPG 리플레이"

    def test_get_title_custom(self, qtbot, config_manager_for_gui):
        """커스텀 제목"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        page.title_entry.setText("테스트 제목")
        assert page.get_title() == "테스트 제목"

    def test_get_convert_mode(self, qtbot, config_manager_for_gui):
        """변환 모드 기본값"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        assert page.get_convert_mode() == "single"

    def test_get_output_format(self, qtbot, config_manager_for_gui):
        """출력 형식 기본값"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        assert page.get_output_format() == "both"

    def test_files_updated_signal(self, qtbot, config_manager_for_gui, sample_log_file):
        """files_updated 시그널 발생 확인"""
        from gui.pages.convert_page import ConvertPage
        page = ConvertPage(config_manager_for_gui)
        qtbot.addWidget(page)

        with qtbot.waitSignal(page.files_updated, timeout=1000):
            page._on_files_dropped([sample_log_file])


class TestConversionWorker:
    """ConversionWorker 테스트"""

    def test_worker_creation(self, config_manager_for_gui):
        """워커 인스턴스 생성"""
        from gui.main_window import ConversionWorker
        worker = ConversionWorker(
            config_manager=config_manager_for_gui,
            files=["/test/file.html"],
            title="테스트",
            mode="single",
            output_format="epub",
        )

        assert worker.files == ["/test/file.html"]
        assert worker.title == "테스트"
        assert worker.mode == "single"
        assert worker.output_format == "epub"
        assert worker.character_colors == {}

    def test_worker_with_options(self, config_manager_for_gui):
        """워커 옵션 전달"""
        from gui.main_window import ConversionWorker
        colors = {"홍길동": "#ff0000"}
        worker = ConversionWorker(
            config_manager=config_manager_for_gui,
            files=["/a.html", "/b.html"],
            title="병합",
            mode="merge",
            output_format="both",
            character_colors=colors,
        )

        assert worker.mode == "merge"
        assert worker.character_colors == colors
        assert len(worker.files) == 2
