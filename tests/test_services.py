#!/usr/bin/env python3
"""
서비스 모듈 테스트
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from core.services.errors import (
    ConversionError,
    ErrorHandler,
    ErrorSeverity,
    ExportError,
    FileError,
    ParseError,
    safe_operation,
    validate_config,
    validate_file_path,
)
from core.services.history import ConversionRecord, HistoryManager
from core.services.profiles import Profile, ProfileManager


class TestHistoryManager:
    """변환 이력 관리자 테스트"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 생성"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def history_manager(self, temp_dir):
        """HistoryManager 인스턴스"""
        return HistoryManager(temp_dir)

    def test_add_record(self, history_manager):
        """기록 추가"""
        record = history_manager.add_record(
            input_file="/path/to/input.html",
            output_files=["/path/to/output.epub"],
            output_format="epub",
            title="테스트 리플레이",
            author="GM",
            entry_count=100,
            scene_count=5,
            success=True,
        )
        assert record is not None
        assert record.title == "테스트 리플레이"
        assert record.entry_count == 100

    def test_get_records(self, history_manager):
        """기록 조회"""
        history_manager.add_record(
            input_file="/path/to/input.html",
            output_files=["/path/to/output.epub"],
            output_format="epub",
            title="테스트 1",
            author="GM",
            entry_count=50,
            scene_count=3,
            success=True,
        )
        history_manager.add_record(
            input_file="/path/to/input2.html",
            output_files=["/path/to/output2.epub"],
            output_format="epub",
            title="테스트 2",
            author="GM",
            entry_count=80,
            scene_count=4,
            success=True,
        )
        records = history_manager.get_records()
        assert len(records) == 2

    def test_get_stats(self, history_manager):
        """통계 조회"""
        history_manager.add_record(
            input_file="/path/to/input.html",
            output_files=["/path/to/output.epub"],
            output_format="epub",
            title="테스트",
            author="GM",
            entry_count=100,
            scene_count=5,
            success=True,
        )
        stats = history_manager.get_stats()
        assert stats["total_conversions"] == 1
        assert stats["success_count"] == 1

    def test_search(self, history_manager):
        """검색"""
        history_manager.add_record(
            input_file="/path/to/fantasy_game.html",
            output_files=["/path/to/output.epub"],
            output_format="epub",
            title="판타지 모험",
            author="GM",
            entry_count=100,
            scene_count=5,
            success=True,
        )
        results = history_manager.search("판타지")
        assert len(results) == 1
        assert results[0].title == "판타지 모험"


class TestProfileManager:
    """프로필 관리자 테스트"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 생성"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def profile_manager(self, temp_dir):
        """ProfileManager 인스턴스"""
        return ProfileManager(temp_dir)

    def test_builtin_profiles(self, profile_manager):
        """내장 프로필 확인"""
        profiles = profile_manager.get_profiles()
        assert len(profiles) >= 5  # 기본, 소설, 리플레이, 미니멀, 인쇄용

        # 기본 프로필 확인
        default = profile_manager.get_profile("default")
        assert default is not None
        assert default.is_builtin is True

    def test_create_profile(self, profile_manager):
        """프로필 생성"""
        profile = profile_manager.create_profile(
            name="내 프로필",
            description="테스트용 프로필",
            settings={"style": {"narration_prefix": "→"}},
        )
        assert profile is not None
        assert profile.name == "내 프로필"
        assert profile.settings["style"]["narration_prefix"] == "→"

    def test_update_profile(self, profile_manager):
        """프로필 수정"""
        profile = profile_manager.create_profile(
            name="수정 테스트",
            description="수정 전",
        )
        profile_manager.update_profile(profile.id, name="수정됨", description="수정 후")
        updated = profile_manager.get_profile(profile.id)
        assert updated.name == "수정됨"
        assert updated.description == "수정 후"

    def test_delete_profile(self, profile_manager):
        """프로필 삭제"""
        profile = profile_manager.create_profile(name="삭제 테스트")
        result = profile_manager.delete_profile(profile.id)
        assert result is True
        assert profile_manager.get_profile(profile.id) is None

    def test_cannot_delete_builtin(self, profile_manager):
        """내장 프로필 삭제 불가"""
        result = profile_manager.delete_profile("default")
        assert result is False

    def test_apply_profile(self, profile_manager):
        """프로필 적용"""
        config = {"style": {"narration_prefix": "＿", "scene_marker": "■"}}
        result = profile_manager.apply_profile_to_config(config, "novel_style")
        assert result["style"]["narration_prefix"] == "　"
        assert result["style"]["scene_marker"] == "◆"


class TestErrorHandler:
    """에러 핸들러 테스트"""

    @pytest.fixture
    def error_handler(self):
        return ErrorHandler()

    def test_handle_error(self, error_handler):
        """에러 처리"""
        try:
            raise ValueError("테스트 에러")
        except Exception as e:
            message = error_handler.handle(e, context="테스트")
            assert "테스트 에러" in message

    def test_get_recent_errors(self, error_handler):
        """최근 에러 조회"""
        error_handler.handle(ValueError("에러 1"), context="test")
        error_handler.handle(ValueError("에러 2"), context="test")
        errors = error_handler.get_recent_errors(10)
        assert len(errors) == 2

    def test_error_summary(self, error_handler):
        """에러 요약"""
        error_handler.handle(ValueError("에러"), severity=ErrorSeverity.ERROR)
        error_handler.handle(RuntimeError("에러"), severity=ErrorSeverity.WARNING)
        summary = error_handler.get_error_summary()
        assert summary["total"] == 2


class TestValidation:
    """유효성 검사 테스트"""

    def test_validate_file_path_empty(self):
        """빈 경로"""
        with pytest.raises(FileError):
            validate_file_path("")

    def test_validate_file_path_not_exist(self):
        """존재하지 않는 파일"""
        with pytest.raises(FileError):
            validate_file_path("/nonexistent/file.txt")

    def test_validate_config_missing_keys(self):
        """필수 키 누락"""
        with pytest.raises(ConversionError):
            validate_config({"a": 1}, required_keys=["a", "b", "c"])

    def test_validate_config_success(self):
        """유효한 설정"""
        result = validate_config({"a": 1, "b": 2}, required_keys=["a", "b"])
        assert result is True


class TestCustomErrors:
    """커스텀 에러 테스트"""

    def test_conversion_error(self):
        """ConversionError"""
        error = ConversionError("테스트", stage="parsing", recoverable=True)
        assert error.stage == "parsing"
        assert error.recoverable is True

    def test_file_error(self):
        """FileError"""
        error = FileError("파일 오류", file_path="/test/file.txt")
        assert error.file_path == "/test/file.txt"
        assert error.stage == "file_io"

    def test_parse_error(self):
        """ParseError"""
        error = ParseError("파싱 오류", line_number=42)
        assert error.line_number == 42
        assert error.stage == "parsing"

    def test_export_error(self):
        """ExportError"""
        error = ExportError("내보내기 오류", format="epub")
        assert error.format == "epub"
        assert error.stage == "export"


class TestSafeOperation:
    """안전 실행 데코레이터 테스트"""

    def test_safe_operation_success(self):
        """성공 케이스"""

        @safe_operation(default_return=-1)
        def good_func():
            return 42

        result = good_func()
        assert result == 42

    def test_safe_operation_failure(self):
        """실패 케이스"""

        @safe_operation(default_return=-1, suppress_errors=True)
        def bad_func():
            raise ValueError("에러")

        result = bad_func()
        assert result == -1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
