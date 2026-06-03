"""Focused tests for the three wired Roll20 config features.

Covers:
  * include_whisper — ``hidden-message`` rows skipped by default, surfaced as
    type "whisper" when the setting is on.
  * emote_style — ``emote`` rows map to "whisper" (italic) or "narration".
  * session_gap_minutes — a long timestamp gap inserts a synthetic scene.

Tests build soup directly (mirroring tests/test_parser_variants.py's reliance on
BeautifulSoup) and call ``parse_roll20`` so we exercise the parser in isolation.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from core.parsers.roll20 import parse_roll20


def _soup(body: str) -> BeautifulSoup:
    html = (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'></head>"
        f"<body><div id='textchat'>{body}</div></body></html>"
    )
    return BeautifulSoup(html, "html.parser")


def _config(**roll20) -> dict:
    base = {
        "session_gap_minutes": 60,
        "emote_style": "italic",
        "include_whisper": False,
    }
    base.update(roll20)
    return {
        "parsing": {"normalize_punctuation": True},
        "chapter": {"scene_patterns": [r"^■"]},
        "roll20": base,
    }


# ---------------------------------------------------------------------------
# include_whisper
# ---------------------------------------------------------------------------


WHISPER_BODY = """
<div class="message general" data-messageid="-N1">
  <span class="by">GM:</span> 세션을 시작합니다.
</div>
<div class="message general hidden-message" data-messageid="-N2">
  <span class="by">GM:</span> 너만 알 수 있는 비밀 정보야.
</div>
<div class="message general" data-messageid="-N3">
  <span class="by">Aragorn:</span> 「알겠습니다.」
</div>
"""


def test_whisper_skipped_when_disabled():
    entries = parse_roll20(_soup(WHISPER_BODY), _config(include_whisper=False))
    joined = "\n".join(e["content"] for e in entries)
    assert "비밀 정보" not in joined
    assert not any(e["type"] == "whisper" for e in entries)
    # The two visible messages still parse.
    assert len(entries) == 2


def test_whisper_included_as_whisper_when_enabled():
    entries = parse_roll20(_soup(WHISPER_BODY), _config(include_whisper=True))
    joined = "\n".join(e["content"] for e in entries)
    assert "비밀 정보" in joined
    whispers = [e for e in entries if e["type"] == "whisper"]
    assert len(whispers) == 1
    assert "비밀 정보" in whispers[0]["content"]
    assert len(entries) == 3


def test_whisper_scene_marker_still_scene():
    body = """
    <div class="message general hidden-message">
      <span class="by">GM:</span> ■ 비밀 장면
    </div>
    """
    entries = parse_roll20(_soup(body), _config(include_whisper=True))
    assert len(entries) == 1
    assert entries[0]["type"] == "scene"


# ---------------------------------------------------------------------------
# emote_style
# ---------------------------------------------------------------------------


EMOTE_BODY = """
<div class="message emote" data-messageid="-N1">
  <div class="spacer"></div>Aragorn draws his sword silently.
</div>
"""


def test_emote_italic_maps_to_whisper():
    entries = parse_roll20(_soup(EMOTE_BODY), _config(emote_style="italic"))
    assert len(entries) == 1
    assert entries[0]["type"] == "whisper"
    assert "draws his sword" in entries[0]["content"]


def test_emote_non_italic_maps_to_narration():
    entries = parse_roll20(_soup(EMOTE_BODY), _config(emote_style="normal"))
    assert len(entries) == 1
    assert entries[0]["type"] == "narration"
    assert "draws his sword" in entries[0]["content"]


def test_normal_message_not_misclassified_as_emote():
    body = '<div class="message general"><span class="by">Aragorn:</span> 평범한 대사.</div>'
    entries = parse_roll20(_soup(body), _config(emote_style="italic"))
    assert len(entries) == 1
    assert entries[0]["type"] == "dialogue"


# ---------------------------------------------------------------------------
# session_gap_minutes
# ---------------------------------------------------------------------------


def _gap_body(t1: str, t2: str) -> str:
    return f"""
    <div class="message general">
      <span class="tstamp" aria-label="{t1}">{t1}</span>
      <span class="by">Aragorn:</span> 첫 메시지.
    </div>
    <div class="message general">
      <span class="tstamp" aria-label="{t2}">{t2}</span>
      <span class="by">Aragorn:</span> 둘째 메시지.
    </div>
    """


def test_session_gap_inserts_scene_when_exceeded():
    body = _gap_body("January 1, 2024 3:00PM", "January 1, 2024 5:30PM")
    entries = parse_roll20(_soup(body), _config(session_gap_minutes=60))
    scenes = [e for e in entries if e["type"] == "scene"]
    assert len(scenes) == 1
    assert "세션" in scenes[0]["content"]
    # Scene is inserted BEFORE the second message.
    types = [e["type"] for e in entries]
    assert types == ["dialogue", "scene", "dialogue"]


def test_session_gap_no_scene_when_within():
    body = _gap_body("January 1, 2024 3:00PM", "January 1, 2024 3:30PM")
    entries = parse_roll20(_soup(body), _config(session_gap_minutes=60))
    assert not any(e["type"] == "scene" for e in entries)
    assert len(entries) == 2


def test_session_gap_disabled_when_zero():
    body = _gap_body("January 1, 2024 3:00PM", "January 1, 2024 9:00PM")
    entries = parse_roll20(_soup(body), _config(session_gap_minutes=0))
    assert not any(e["type"] == "scene" for e in entries)


def test_session_gap_skips_unparsable_timestamps():
    body = _gap_body("not a date", "also bad")
    entries = parse_roll20(_soup(body), _config(session_gap_minutes=60))
    assert not any(e["type"] == "scene" for e in entries)
    assert len(entries) == 2


def test_session_gap_string_config_coerced():
    body = _gap_body("January 1, 2024 3:00PM", "January 1, 2024 5:30PM")
    entries = parse_roll20(_soup(body), _config(session_gap_minutes="60"))
    assert any(e["type"] == "scene" for e in entries)
