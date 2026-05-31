"""Schema migration framework for GUI settings (gui_settings.json).

Inspired by Alembic / Django migrations: each version-bump is a small named
function registered with ``@migration(from_version=N)``. ``migrate_gui_settings``
walks the chain from the file's recorded version up to the current one.

Adding a new migration:

    @migration(from_version=2)
    def _v2_to_v3(settings: dict) -> dict:
        # Move flat ``foo_bar`` into ``foo: {bar: ...}``.
        if "foo_bar" in settings:
            settings.setdefault("foo", {})["bar"] = settings.pop("foo_bar")
        return settings

The framework guarantees:

* Migrations run in version order, exactly once per upgrade.
* If a migration raises, ``SchemaMigrationError`` propagates with structured
  context (``from``, ``to``, root cause).
* ``_schema_version`` is stamped at the end of each step so partial upgrades
  are recoverable.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from core.config.defaults import CONFIG_SCHEMA_VERSION
from core.exceptions import SchemaMigrationError

logger = logging.getLogger(__name__)

MigrationFn = Callable[[dict], dict]

_REGISTRY: dict[int, MigrationFn] = {}


def migration(*, from_version: int) -> Callable[[MigrationFn], MigrationFn]:
    """Decorator: register a function that upgrades schema ``from_version`` to ``from_version + 1``."""

    def decorate(fn: MigrationFn) -> MigrationFn:
        if from_version in _REGISTRY:
            raise RuntimeError(
                f"Duplicate migration registered for v{from_version} -> v{from_version + 1}"
            )
        _REGISTRY[from_version] = fn
        return fn

    return decorate


def migrate_gui_settings(settings: dict) -> dict:
    """Walk the migration chain from the file's version up to ``CONFIG_SCHEMA_VERSION``.

    Mutates and returns ``settings``. Raises ``SchemaMigrationError`` if any step fails.
    """
    current = int(settings.get("_schema_version", 1))
    if current > CONFIG_SCHEMA_VERSION:
        logger.warning(
            "설정 파일이 더 높은 스키마 버전입니다 (file=%d, app=%d). 그대로 사용합니다.",
            current,
            CONFIG_SCHEMA_VERSION,
        )
        return settings

    while current < CONFIG_SCHEMA_VERSION:
        fn = _REGISTRY.get(current)
        if fn is None:
            raise SchemaMigrationError(
                f"No migration registered for v{current} -> v{current + 1}",
                context={"from": current, "to": current + 1},
            )
        try:
            settings = fn(settings)
        except SchemaMigrationError:
            raise
        except Exception as exc:
            raise SchemaMigrationError(
                f"Migration v{current} -> v{current + 1} failed: {exc}",
                context={"from": current, "to": current + 1, "cause": repr(exc)},
            ) from exc
        current += 1
        settings["_schema_version"] = current
        logger.info("설정 스키마 v%d → v%d 마이그레이션 완료", current - 1, current)

    return settings


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------


@migration(from_version=1)
def _v1_to_v2(settings: dict) -> dict:
    """v1 -> v2: ``margins`` was a free-form string, now a per-edge dict."""
    margins = settings.get("margins")
    if isinstance(margins, str):
        settings["margins"] = {
            "top": "1.0",
            "bottom": "1.0",
            "left": "1.0",
            "right": "1.0",
        }
    return settings


__all__ = [
    "MigrationFn",
    "migrate_gui_settings",
    "migration",
]
