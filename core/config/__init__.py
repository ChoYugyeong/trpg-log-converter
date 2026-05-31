"""Single source of truth for engine config defaults & schema versioning."""

from core.config.defaults import (
    CONFIG_SCHEMA_VERSION,
    DEFAULT_ENGINE_CONFIG,
    default_engine_config,
)

__all__ = [
    "CONFIG_SCHEMA_VERSION",
    "DEFAULT_ENGINE_CONFIG",
    "default_engine_config",
]
