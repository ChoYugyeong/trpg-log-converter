"""Tests for parser variants and safety against real-world HTML quirks.

Covers (based on Roll20 wiki + Cocofolia docs + community parser inspection):

* Modern Cocofolia ``<p class="player pN">`` format
* Multi-tab Cocofolia exports
* Roll20 roll templates (default / 5e / CoC)
* Roll20 emote / desc / whisper / system message types
* Avatar + timestamp + data-* attributes that real exports embed
* Missing speaker (empty ``<span class="by"></span>``)
* Edge cases: empty file, single message, very long message, unicode emoji
* Security: ``<script>`` / ``<iframe>`` / event handlers must NOT execute, and
  their content must NOT leak into entry text.

These specifically prevent regressions where a future parser change might
silently break a real-world format.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config_manager import ConfigManager
from core.engine import ConversionEngine
from tests.fixtures.dummy_logs import (
    make_cocofolia_modern,
    make_cocofolia_multitab,
    make_empty_html,
    make_html_with_script_injection,
    make_malformed_html,
    make_roll20_emote_and_desc,
    make_roll20_with_avatar_timestamp,
    make_roll20_with_missing_speaker,
    make_roll20_with_roll_template,
    make_roll20_with_whisper,
    make_single_message_html,
    make_unicode_emoji_html,
    make_very_long_message_html,
)


@pytest.fixture
def engine(tmp_path: Path) -> ConversionEngine:
    cm = ConfigManager(app_dir=tmp_path)
    return ConversionEngine(cm.build_engine_config())


# ---------------------------------------------------------------------------
# Cocofolia variants
# ---------------------------------------------------------------------------


class TestCocofoliaModern:
    """Modern ccfolia.com export uses ``<p class="player pN">``."""

    def test_modern_format_parses(self, engine: ConversionEngine):
        entries = engine.parse_html(make_cocofolia_modern())
        assert len(entries) >= 5

        names = {e.get("name") for e in entries if e.get("name")}
        assert any("사사키" in n for n in names)
        assert any("KP" in n for n in names)

    def test_modern_scenes_detected(self, engine: ConversionEngine):
        entries = engine.parse_html(make_cocofolia_modern())
        scene_count = sum(1 for e in entries if e.get("type") == "scene")
        assert scene_count >= 2, "expected at least 2 ■-marked scenes"

    def test_modern_dice_detected(self, engine: ConversionEngine):
        entries = engine.parse_html(make_cocofolia_modern())
        dice = [e for e in entries if e.get("type") == "dice"]
        assert dice, "BCDice-style rolls must be classified as dice"

    def test_multitab_parses(self, engine: ConversionEngine):
        """Both ``<div class="tab t0">`` and ``t1`` content should appear."""
        entries = engine.parse_html(make_cocofolia_multitab())
        joined = "\n".join(e.get("content", "") for e in entries)
        # Content from both tabs
        assert "■ 시작" in joined or "갑니다" in joined
        # ``addAddedfile`` 식 잡담도 들어옴 (필터 안 걸렸을 때)
        assert len(entries) >= 2


# ---------------------------------------------------------------------------
# Roll20 variants
# ---------------------------------------------------------------------------


class TestRoll20Variants:
    def test_emote_is_recognised(self, engine: ConversionEngine):
        entries = engine.parse_html(make_roll20_emote_and_desc())
        # Even though /me has no <span class="by">, the parser should not crash
        # and should produce SOME entry for the emote text.
        joined = "\n".join(e.get("content", "") for e in entries)
        assert "draws his sword" in joined or "sword" in joined.lower()

    def test_desc_is_recognised(self, engine: ConversionEngine):
        entries = engine.parse_html(make_roll20_emote_and_desc())
        # `desc` text should appear in the output
        joined = "\n".join(e.get("content", "") for e in entries)
        assert "cave is dark" in joined

    def test_whisper_does_not_crash(self, engine: ConversionEngine):
        entries = engine.parse_html(make_roll20_with_whisper())
        assert len(entries) >= 2
        # Whisper appears in output (parser keeps it; filtering is user's choice)
        joined = "\n".join(e.get("content", "") for e in entries)
        assert "너만 알 수 있는" in joined

    def test_roll_template_parses(self, engine: ConversionEngine):
        """sheet-rolltemplate-* wrapper must not break parsing of surrounding messages."""
        entries = engine.parse_html(make_roll20_with_roll_template())
        # At minimum the surrounding dialogue + scene must be extracted.
        names = {e.get("name") for e in entries if e.get("name")}
        assert "Aragorn" in names or any("Aragorn" in n for n in names)
        scene_count = sum(1 for e in entries if e.get("type") == "scene")
        assert scene_count >= 1

    def test_avatar_timestamp_ignored(self, engine: ConversionEngine):
        """Avatar img / tstamp span must not pollute the content text."""
        entries = engine.parse_html(make_roll20_with_avatar_timestamp())
        contents = [e.get("content", "") for e in entries]
        joined = "\n".join(contents)
        assert "avatar.png" not in joined  # URL must not leak
        # The actual speech is preserved
        assert "시작합시다" in joined

    def test_missing_speaker_does_not_crash(self, engine: ConversionEngine):
        entries = engine.parse_html(make_roll20_with_missing_speaker())
        assert isinstance(entries, list)
        # Even with an empty <span class="by"></span> the GM message should be picked up.
        joined = "\n".join(e.get("content", "") for e in entries)
        assert "본격적으로 시작" in joined


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_html_returns_empty_list(self, engine: ConversionEngine):
        entries = engine.parse_html(make_empty_html())
        assert entries == []

    def test_single_message_works(self, engine: ConversionEngine):
        entries = engine.parse_html(make_single_message_html())
        assert len(entries) == 1
        assert "단 한 줄" in entries[0]["content"]

    def test_very_long_message_does_not_crash(self, engine: ConversionEngine):
        """~30KB single message — must parse in reasonable time without OOM."""
        import time

        start = time.monotonic()
        entries = engine.parse_html(make_very_long_message_html())
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"parsing took {elapsed:.2f}s (too slow)"
        assert len(entries) == 1
        # Content truncation isn't expected; verify length carried through.
        assert len(entries[0]["content"]) > 10_000

    def test_unicode_emoji_preserved(self, engine: ConversionEngine):
        entries = engine.parse_html(make_unicode_emoji_html())
        joined = "\n".join(e.get("content", "") for e in entries)
        assert "🎲" in joined
        assert "✨" in joined
        assert "★彡" in joined

    def test_malformed_html_recovers(self, engine: ConversionEngine):
        """BeautifulSoup is lenient — we should get at least one entry, not crash."""
        entries = engine.parse_html(make_malformed_html())
        assert isinstance(entries, list)
        assert len(entries) >= 1


# ---------------------------------------------------------------------------
# Security — these are the highest-priority assertions
# ---------------------------------------------------------------------------


class TestSecurity:
    """A converted EPUB/DOCX must NEVER carry executable web content. Even if a
    log author intentionally embedded ``<script>`` or event handlers in chat,
    the parser must strip them silently.
    """

    def test_script_tags_do_not_leak(self, engine: ConversionEngine):
        entries = engine.parse_html(make_html_with_script_injection())
        joined = "\n".join(e.get("content", "") for e in entries)
        assert "alert(" not in joined
        assert "<script" not in joined.lower()
        # The safe sibling messages still come through.
        assert "안전한 메시지 1" in joined
        assert "안전한 메시지 2" in joined

    def test_iframe_does_not_leak(self, engine: ConversionEngine):
        entries = engine.parse_html(make_html_with_script_injection())
        joined = "\n".join(e.get("content", "") for e in entries)
        assert "<iframe" not in joined.lower()
        assert "javascript:" not in joined.lower()

    def test_event_handlers_stripped(self, engine: ConversionEngine):
        """onload / onerror attributes inside content must not survive into entries.

        The parser uses ``get_text()`` which discards attributes anyway, but the
        regression test pins this guarantee.
        """
        entries = engine.parse_html(make_html_with_script_injection())
        joined = "\n".join(e.get("content", "") for e in entries)
        assert "onload" not in joined.lower()
        assert "onerror" not in joined.lower()
