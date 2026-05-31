"""Shared type aliases used across parsers and renderers.

Defines the structural shape of parsed log entries so that callers (and mypy)
don't have to thread ``Dict[str, Any]`` through every function. Entries are
plain dicts at runtime — ``TypedDict`` exists purely for documentation /
type-checking and adds no runtime overhead.

Usage:

    from core.types import Entry, Scene

    def filter(entries: list[Entry]) -> list[Entry]: ...
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypedDict

# Discrete entry types the parsers emit. Keep this in sync with the engine's
# rendering switch in ``core.renderers.epub.entries_to_html`` and the DOCX/PDF
# renderers.
EntryType = Literal[
    "dialogue",
    "narration",
    "dice",
    "system",
    "effect",
    "image",
    "scene",
    "scene_end",
    "whisper",
    "highlight",
]


class Entry(TypedDict, total=False):
    """A single parsed log line.

    ``total=False`` because legacy code may omit ``channel`` / ``raw`` for
    entries built outside the main pipeline (e.g. text parser fallback).
    """

    type: EntryType
    name: str
    content: str
    raw: str
    image: str | None
    channel: str | None


class Scene(TypedDict):
    """A grouped collection of entries forming one chapter / scene."""

    title: str | None
    entries: list[Entry]


# Progress callbacks consistently use ``(current, total, message)``.
ProgressCallback = Callable[[int, int, str], None]


__all__ = [
    "Entry",
    "EntryType",
    "ProgressCallback",
    "Scene",
]
