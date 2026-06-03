"""Tests for the GUI settings schema migration framework."""

from __future__ import annotations

import pytest

from core.config.defaults import CONFIG_SCHEMA_VERSION
from core.config.migrations import _REGISTRY, migrate_gui_settings, migration
from core.exceptions import SchemaMigrationError


class TestMigrateExistingChain:
    def test_unversioned_file_is_treated_as_v1(self):
        settings = {"margins": "1.0in"}
        result = migrate_gui_settings(settings)
        assert result["_schema_version"] == CONFIG_SCHEMA_VERSION
        assert isinstance(result["margins"], dict)
        assert set(result["margins"].keys()) == {"top", "bottom", "left", "right"}

    def test_v1_string_margins_become_dict(self):
        settings = {"_schema_version": 1, "margins": "1.0in"}
        result = migrate_gui_settings(settings)
        assert result["margins"] == {
            "top": "1.0",
            "bottom": "1.0",
            "left": "1.0",
            "right": "1.0",
        }

    def test_already_current_version_is_no_op(self):
        settings = {"_schema_version": CONFIG_SCHEMA_VERSION, "margins": {"top": "0.5"}}
        result = migrate_gui_settings(dict(settings))
        assert result == settings

    def test_future_version_is_preserved_with_warning(self, caplog):
        settings = {"_schema_version": CONFIG_SCHEMA_VERSION + 5, "extra": "future"}
        result = migrate_gui_settings(dict(settings))
        assert result == settings

    def test_v2_to_v3_resets_stale_dice_icon(self):
        """v2 -> v3: 죽은 설정이던 dice_icon=True 는 False 로 리셋된다."""
        settings = {"_schema_version": 2, "dice_icon": True}
        result = migrate_gui_settings(settings)
        assert result["dice_icon"] is False
        assert result["_schema_version"] == CONFIG_SCHEMA_VERSION

    def test_v2_to_v3_keeps_explicit_false(self):
        settings = {"_schema_version": 2, "dice_icon": False}
        result = migrate_gui_settings(settings)
        assert result["dice_icon"] is False

    def test_v2_to_v3_strips_main_from_skip_channels(self):
        settings = {"_schema_version": 2, "skip_channels": "[main], [잡담], [ooc]"}
        result = migrate_gui_settings(settings)
        assert "[main]" not in result["skip_channels"]
        assert "[잡담]" in result["skip_channels"]
        assert "[ooc]" in result["skip_channels"]

    def test_v2_to_v3_resets_stale_separator(self):
        settings = {"_schema_version": 2, "style_separator": "「 」 (꺾쇠)"}
        result = migrate_gui_settings(settings)
        assert result["style_separator"] == "없음"

    def test_v2_to_v3_keeps_explicit_separator(self):
        settings = {"_schema_version": 2, "style_separator": '" " (따옴표)'}
        result = migrate_gui_settings(settings)
        assert result["style_separator"] == '" " (따옴표)'


class TestRegistryGuards:
    def test_duplicate_registration_raises(self):
        # ``from_version=1`` is already registered by core.config.migrations.
        with pytest.raises(RuntimeError, match="Duplicate migration"):

            @migration(from_version=1)
            def _dup(settings: dict) -> dict:
                return settings

    def test_missing_step_raises_structured_error(self, monkeypatch):
        """If we move two versions forward but only register one step, fail loudly."""
        from core.config import migrations

        # Pretend the app is now at v99; registered steps stop at v3 -> v4 (absent).
        monkeypatch.setattr(migrations, "CONFIG_SCHEMA_VERSION", 99)
        with pytest.raises(SchemaMigrationError) as excinfo:
            migrate_gui_settings({"_schema_version": 3})

        ctx = excinfo.value.context
        assert ctx["from"] == 3
        assert ctx["to"] == 4

    def test_step_failure_wraps_cause(self, monkeypatch):
        from core.config import migrations

        def boom(_settings: dict) -> dict:
            raise ValueError("boom")

        monkeypatch.setitem(_REGISTRY, 50, boom)
        monkeypatch.setattr(migrations, "CONFIG_SCHEMA_VERSION", 51)

        with pytest.raises(SchemaMigrationError) as excinfo:
            migrate_gui_settings({"_schema_version": 50})

        assert "boom" in excinfo.value.context["cause"]
        assert excinfo.value.context["from"] == 50
