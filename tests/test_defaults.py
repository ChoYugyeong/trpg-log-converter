"""Tests for the single-source default engine config."""
from __future__ import annotations

from core.config.defaults import (
    CONFIG_SCHEMA_VERSION,
    DEFAULT_ENGINE_CONFIG,
    default_engine_config,
)


def test_default_returns_deep_copy():
    """Callers must not be able to corrupt the module-level default."""
    a = default_engine_config()
    a["paths"]["output_dir"] = "/tmp/mutated"
    b = default_engine_config()
    assert b["paths"]["output_dir"] != "/tmp/mutated"


def test_schema_version_is_positive():
    assert CONFIG_SCHEMA_VERSION >= 1


def test_required_sections_present():
    cfg = default_engine_config()
    for section in (
        "paths",
        "cover",
        "toc",
        "fonts",
        "style",
        "narration",
        "content",
        "dialogue",
        "images",
        "chapter",
        "parsing",
        "performance",
    ):
        assert section in cfg, f"{section} missing from defaults"


def test_performance_defaults_sane():
    perf = DEFAULT_ENGINE_CONFIG["performance"]
    assert perf["parse_max_workers"] >= 1
    assert perf["max_html_bytes"] >= 1 * 1024 * 1024


def test_config_manager_alias_matches():
    """Legacy callers using ConfigManager.DEFAULT_CONFIG must see the same dict."""
    from core.config_manager import ConfigManager
    assert ConfigManager.DEFAULT_CONFIG is DEFAULT_ENGINE_CONFIG
