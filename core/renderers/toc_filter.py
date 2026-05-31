"""TOC (Table of Contents) scene filtering.

Why a separate module
---------------------
User feedback: TOC 가 진짜 씬 제목 외에 ``Main Process`` 같은 시스템 노이즈도
포함해서, 사용자가 책을 펴서 목차를 보면 어수선해 보임.

``split_by_scene`` 은 모든 매치를 다 scene 으로 만드는데, 그 중 일부는
- 사용자가 명시적으로 쓴 제목 (예: ``Scene 1 — 숲의 입구``)
- 자동 생성된 제목 (예: ``장면 5`` — 매칭은 됐지만 본문에 제목 없음)
- 시스템/외부 도구 노이즈 (예: ``Main Process Started``)

이 함수는 config 옵션에 따라 TOC 후보를 걸러낸다. 실제 챕터 분할은 건드리지
않음 — 본문 구조는 그대로 두고, 목차에서만 숨김.

Config keys (``config["toc"]`` 아래)
-------------------------------------
* ``scene_only`` (bool, default False)
    True 면 ``auto_title=True`` 인 scene 은 TOC 에서 제외. 즉 자동 생성된
    ``장면 N`` 류와 split_mode='count' / 'none' 산출물이 안 보임.
* ``exclude_patterns`` (list[str], default [])
    각 패턴은 ``re.IGNORECASE`` 로 scene 의 ``title`` 에 ``re.search`` 됨.
    하나라도 매칭되면 그 scene 은 TOC 에서 제외.
* ``min_entries`` (int, default 0)
    이 미만 entries 를 가진 scene 은 TOC 에서 제외 — 단발성 마커가 잡혀
    실제 콘텐츠는 거의 없는 경우 정리용.

기본값 (모두 OFF) 으로 두면 기존 동작 100% 보존.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def filter_toc_scenes(
    scenes: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Tuple[int, Dict[str, Any]]]:
    """Return ``(original_index, scene)`` pairs eligible for the TOC.

    원본 ``scenes`` 의 인덱스를 유지해서 ``chapter_{idx+1}.xhtml`` / PDF
    bookmark 등 챕터 식별자가 깨지지 않도록 함. 호출자는 보통:

        for original_idx, scene in filter_toc_scenes(scenes, config):
            href = f"chapter_{original_idx + 1}.xhtml"
            ...

    형태로 사용.
    """
    toc_cfg = config.get("toc", {}) or {}
    scene_only: bool = bool(toc_cfg.get("scene_only", False))
    raw_patterns = toc_cfg.get("exclude_patterns", []) or []
    min_entries: int = int(toc_cfg.get("min_entries", 0) or 0)

    # 패턴 컴파일 — 잘못된 정규식은 경고만 찍고 skip (사용자 설정이라 강제 실패는 가혹).
    compiled = []
    for raw in raw_patterns:
        if not raw:
            continue
        try:
            compiled.append(re.compile(raw, re.IGNORECASE))
        except re.error as exc:
            logger.warning("TOC exclude_patterns 정규식 오류 '%s': %s", raw, exc)

    result: List[Tuple[int, Dict[str, Any]]] = []
    for idx, scene in enumerate(scenes):
        title = scene.get("title") or ""
        entries = scene.get("entries") or []
        auto = bool(scene.get("auto_title", False))

        if scene_only and auto:
            logger.debug("TOC skip (auto_title): %s", title)
            continue
        if min_entries and len(entries) < min_entries:
            logger.debug("TOC skip (entries<%d): %s", min_entries, title)
            continue
        if compiled and any(p.search(title) for p in compiled):
            logger.debug("TOC skip (exclude_patterns matched): %s", title)
            continue
        result.append((idx, scene))

    return result


__all__ = ["filter_toc_scenes"]
