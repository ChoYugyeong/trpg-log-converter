"""
프리셋 서비스 테스트
"""

from pathlib import Path

import pytest

from core.services.presets import Preset, PresetService


class TestPresetService:
    """PresetService 테스트"""

    def test_builtin_presets_exist(self):
        """내장 프리셋이 존재하는지 확인"""
        service = PresetService()

        presets = service.list_presets()
        assert len(presets) > 0

        # 주요 프리셋 확인
        preset_names = [p.name for p in presets]
        assert "ccfolia_default" in preset_names
        assert "roll20_default" in preset_names

    def test_get_preset_returns_preset_object(self):
        """get_preset이 Preset 객체를 반환하는지 확인"""
        service = PresetService()

        preset = service.get_preset("ccfolia_default")
        assert isinstance(preset, Preset)
        assert preset.name == "ccfolia_default"
        assert preset.platform == "ccfolia"

    def test_get_preset_returns_none_for_unknown(self):
        """존재하지 않는 프리셋에 대해 None을 반환하는지 확인"""
        service = PresetService()

        result = service.get_preset("nonexistent_preset")
        assert result is None

    def test_get_preset_config_returns_dict(self):
        """get_preset_config가 설정 딕셔너리를 반환하는지 확인"""
        service = PresetService()

        config = service.get_preset_config("ccfolia_default")
        assert isinstance(config, dict)
        assert "log_source" in config

    def test_list_presets_filter_by_platform(self):
        """플랫폼으로 필터링이 작동하는지 확인"""
        service = PresetService()

        ccfolia_presets = service.list_presets(platform="ccfolia")
        roll20_presets = service.list_presets(platform="roll20")

        assert all(p.platform == "ccfolia" for p in ccfolia_presets)
        assert all(p.platform == "roll20" for p in roll20_presets)

    def test_get_platforms(self):
        """지원 플랫폼 목록을 올바르게 반환하는지 확인"""
        service = PresetService()

        platforms = service.get_platforms()
        assert "ccfolia" in platforms
        assert "roll20" in platforms

    def test_add_custom_preset(self):
        """사용자 정의 프리셋 추가가 작동하는지 확인"""
        service = PresetService()

        service.add_custom_preset(
            name="my_preset",
            config={"log_source": "custom"},
            display_name="내 프리셋",
            description="테스트 프리셋",
            platform="custom",
            tags=["test"]
        )

        preset = service.get_preset("my_preset")
        assert preset is not None
        assert preset.display_name == "내 프리셋"
        assert preset.config["log_source"] == "custom"

    def test_remove_custom_preset(self):
        """사용자 정의 프리셋 제거가 작동하는지 확인"""
        service = PresetService()

        service.add_custom_preset("temp_preset", {"test": True})
        assert service.get_preset("temp_preset") is not None

        result = service.remove_preset("temp_preset")
        assert result is True
        assert service.get_preset("temp_preset") is None

    def test_cannot_remove_builtin_preset(self):
        """내장 프리셋은 제거할 수 없는지 확인"""
        service = PresetService()

        result = service.remove_preset("ccfolia_default")
        assert result is False
        assert service.get_preset("ccfolia_default") is not None

    def test_apply_preset_merges_config(self):
        """apply_preset이 설정을 올바르게 병합하는지 확인"""
        service = PresetService()

        base_config = {
            "metadata": {"title": "테스트"},
            "log_source": "auto"
        }

        result = service.apply_preset(base_config, "ccfolia_default")

        # 기존 설정 유지
        assert result["metadata"]["title"] == "테스트"
        # 프리셋 설정 적용
        assert result["log_source"] == "ccfolia"

    def test_apply_preset_deep_merge(self):
        """중첩된 설정도 올바르게 병합되는지 확인"""
        service = PresetService()

        base_config = {
            "narration": {
                "users": ["GM"],
                "custom_field": "keep_this"
            }
        }

        result = service.apply_preset(base_config, "ccfolia_default")

        # 프리셋 값으로 덮어씀
        assert "KP" in result["narration"]["users"]
        # 기존 필드 유지
        assert result["narration"]["custom_field"] == "keep_this"

    def test_export_preset(self):
        """프리셋 내보내기가 작동하는지 확인"""
        service = PresetService()

        exported = service.export_preset("ccfolia_default")

        assert isinstance(exported, dict)
        assert "name" in exported
        assert "display_name" in exported
        assert "config" in exported
        assert "tags" in exported

    def test_import_preset(self):
        """프리셋 가져오기가 작동하는지 확인"""
        service = PresetService()

        preset_data = {
            "name": "imported_preset",
            "display_name": "가져온 프리셋",
            "description": "테스트용",
            "platform": "test",
            "config": {"test_key": "test_value"},
            "tags": ["imported"]
        }

        result = service.import_preset(preset_data)
        assert result is True

        preset = service.get_preset("imported_preset")
        assert preset is not None
        assert preset.config["test_key"] == "test_value"

    def test_import_preset_invalid_data(self):
        """잘못된 데이터로 가져오기 실패하는지 확인"""
        service = PresetService()

        result = service.import_preset({})  # name 없음
        assert result is False

    def test_preset_tags(self):
        """프리셋 태그가 올바르게 설정되는지 확인"""
        service = PresetService()

        preset = service.get_preset("ccfolia_default")
        assert "korean" in preset.tags
        assert "ccfolia" in preset.tags

    def test_custom_presets_in_constructor(self):
        """생성자에서 사용자 정의 프리셋을 전달할 수 있는지 확인"""
        custom = {
            "initial_preset": {"config_key": "value"}
        }

        service = PresetService(custom_presets=custom)

        preset = service.get_preset("initial_preset")
        assert preset is not None
