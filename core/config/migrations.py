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


@migration(from_version=2)
def _v2_to_v3(settings: dict) -> dict:
    """v2 -> v3: 과거 기본값이 잘못 저장돼 출력을 망치는 두 키를 정리한다.

    1) ``dice_icon``: 이전까지 어디서도 소비되지 않던 죽은 설정이라 과거 위젯
       기본값(True)이 무의미하게 저장돼 있을 수 있다. 이제 실제로 🎲 를 그리므로
       사용자가 의도한 적 없는 True 를 기본(False)로 리셋한다.
    2) ``skip_channels``: 과거 기본값에 ``[main]`` 이 들어 있어, 메인 채널을 쓰는
       로그의 본문이 통째로 제외되는 위험이 있었다. ``[main]``/``[메인]`` 토큰만
       제거한다(사용자가 추가한 다른 채널은 보존).
    """
    if settings.get("dice_icon") is True:
        settings["dice_icon"] = False

    skip = settings.get("skip_channels")
    if isinstance(skip, str) and skip.strip():
        kept = [
            tok.strip()
            for tok in skip.split(",")
            if tok.strip() and tok.strip().lower() not in ("[main]", "[메인]", "main", "메인")
        ]
        settings["skip_channels"] = ", ".join(kept)

    # 3) ``style_separator``(대사 구분자)도 직전까지 소비되지 않던 죽은 설정이라
    #    과거 위젯 기본값 '「 」 (꺾쇠)' 이 무의미하게 저장돼 있을 수 있다. 이제
    #    실제로 대사를 「」 로 감싸므로, 의도한 적 없는 옛 기본값을 '없음'(원문 유지)
    #    으로 리셋한다. (원하면 서식 탭에서 다시 선택.)
    if settings.get("style_separator") == "「 」 (꺾쇠)":
        settings["style_separator"] = "없음"

    return settings


__all__ = [
    "MigrationFn",
    "migrate_gui_settings",
    "migration",
]
