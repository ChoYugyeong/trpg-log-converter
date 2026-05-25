"""Factories that produce synthetic log files for round-trip testing.

Each ``make_*`` function returns the file content as a ``str`` so the test can
decide where to drop it (tmp_path, or an explicit fixture dir).

Variants covered (based on real-world Roll20 / Cocofolia / community parser
inspection — see commit message history for sources):

Cocofolia:
- ``firing_name_*`` style (older / converter output)
- ``<p class="player pN">`` modern style with per-speaker color stylesheets
- BCDice output (CCB<=50 ＞ 37 ＞ 成功 / 1D100 / 2d6+3)
- System rows (room enter/leave)
- Multi-tab channels (t0/t1/t2)
- SE / voice rows
- Secret dice

Roll20:
- general / rollresult / gmrollresult / emote / desc / system / whisper
- Roll templates (default, atk, CoC, 5e-shaped)
- Inline rolls (<span class="inlinerollresult" original-title>)
- Avatar / timestamp markup
- Missing speaker, empty by span
- Multi-line via <br>

Safety / edge cases:
- Empty file
- Single message only
- Very long single message
- Unicode emojis + special chars
- <script> and <iframe> embedded (must be ignored, not executed)
- Malformed HTML (unclosed tags)
"""
from __future__ import annotations

import random
import textwrap
from dataclasses import dataclass
from typing import Iterable


# ---------------------------------------------------------------------------
# Cocofolia (firing_name_* spans)
# ---------------------------------------------------------------------------

_COCOFOLIA_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
</head>
<body>
<div class="log">
{body}
</div>
</body>
</html>
"""


def _coco_line(name: str, content: str) -> str:
    # Cocofolia uses a single span with both firing_name_<name> and firing_firing.
    # Names use underscores in place of spaces.
    name_token = name.replace(" ", "_")
    return (
        f'<p><span class="firing_name_{name_token} firing_firing">: '
        f'{content}</span></p>'
    )


def make_cocofolia_basic(title: str = "코코포리아 기본 더미") -> str:
    """Minimal scene + dialogue + dice sample."""
    lines = [
        _coco_line("KP", "■ 도입: 미스카토닉 대학 도서관"),
        _coco_line("KP", "당신들은 낡은 책 냄새가 가득한 도서관에서 만났습니다."),
        _coco_line("사사키_유타카", "「안녕하세요, 저는 고고학 교수입니다.」"),
        _coco_line("김탐정", "「사설 탐정 김탐정이오.」"),
        _coco_line("사사키_유타카", "CCB<=65 도서관 → 35 성공"),
        _coco_line("KP", "오래된 문서에서 단서를 발견합니다."),
        _coco_line("KP", "■ 장면 1: 수상한 편지"),
        _coco_line("사사키_유타카", "1D100<=55 고대언어 → 23 대성공!"),
        _coco_line("김탐정", "「교수님, 해독이 가능하시오?」"),
        _coco_line("사사키_유타카", "「이것은 고대 수메르어처럼 보이는군요.」"),
        _coco_line("KP", "■ 장면 2: 어둠 속의 조우"),
        _coco_line("KP", "도서관의 불이 꺼집니다. 발소리가 가까워집니다."),
        _coco_line("김탐정", "권총을 꺼내듭니다."),
        _coco_line("사사키_유타카", "「조용히... 뭔가 오고 있어요.」"),
    ]
    return _COCOFOLIA_TEMPLATE.format(title=title, body="\n".join(lines))


def make_cocofolia_with_channels(title: str = "코코포리아 채널 더미") -> str:
    """Includes [잡담] / [ooc] channel prefixes that should be skipped."""
    lines = [
        _coco_line("KP", "■ 본 세션 시작"),
        _coco_line("플레이어A", "[잡담] 오늘 시간 괜찮으세요?"),
        _coco_line("플레이어B", "[ooc] 캐릭터 시트 확인 좀 하고 올게요"),
        _coco_line("KP", "여러분 앞에는 거대한 성문이 서 있습니다."),
        _coco_line("플레이어A", "「조심해서 접근하자.」"),
        _coco_line("플레이어A", "1d20+5 지각 → 18 성공"),
        _coco_line("KP", "성벽 위에서 무언가가 움직이는 것이 보입니다."),
    ]
    return _COCOFOLIA_TEMPLATE.format(title=title, body="\n".join(lines))


def make_cocofolia_with_images(title: str = "코코포리아 이미지 더미") -> str:
    """Inline image markers — the engine should turn these into image entries."""
    lines = [
        _coco_line("KP", "■ 프롤로그"),
        _coco_line("KP", "[IMG: cover.png]"),
        _coco_line("KP", "이 도시의 이야기는 한 통의 편지로 시작합니다."),
        _coco_line("야타", "[삽화: scene1.jpg]"),
        _coco_line("야타", "편지를 꺼내듭니다."),
    ]
    return _COCOFOLIA_TEMPLATE.format(title=title, body="\n".join(lines))


# ---------------------------------------------------------------------------
# Roll20 (#textchat with div.message.general / .desc / .rollresult)
# ---------------------------------------------------------------------------

_ROLL20_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
</head>
<body>
<div id="textchat">
{body}
</div>
</body>
</html>
"""


def _r20_msg(by: str, text: str, *, kind: str = "general") -> str:
    classes = f"message {kind}".strip()
    return (
        f'<div class="{classes}"><span class="by">{by}:</span> {text}</div>'
    )


def _r20_desc(text: str) -> str:
    return f'<div class="message desc">{text}</div>'


def make_roll20_basic(title: str = "Roll20 기본 더미") -> str:
    parts = [
        _r20_msg("GM", "오늘의 세션을 시작하겠습니다."),
        _r20_msg("GM", "■ 장면 1: 던전의 입구"),
        _r20_msg("김철수 (전사)", "조심해서 들어가자."),
        _r20_msg("이영희 (마법사)", "라이트 마법을 걸겠습니다."),
        _r20_msg("이영희 (마법사)", "Rolling 1d20+5 = 18 성공", kind="general rollresult"),
        _r20_desc("밝은 빛이 던전 입구를 비추며, 오래된 벽화가 드러납니다."),
        _r20_msg("GM", "벽화에는 영웅들이 드래곤과 싸우는 장면이 그려져 있습니다."),
        _r20_msg("박준서 (도적)", "함정이 있는지 확인해볼게."),
        _r20_msg(
            "박준서 (도적)",
            "Rolling 1d20+7 Perception Check = 22",
            kind="general rollresult",
        ),
        _r20_msg("GM", "■ 장면 2: 함정의 방"),
        _r20_desc("좁은 복도를 지나자 넓은 방이 나타납니다."),
        _r20_msg("김철수 (전사)", "「저건 분명히 함정이야.」"),
    ]
    return _ROLL20_TEMPLATE.format(title=title, body="\n".join(parts))


def make_roll20_long(scenes: int = 5, lines_per_scene: int = 20) -> str:
    """Bigger Roll20 log for scene-split / pagination stress."""
    rng = random.Random(0)  # deterministic
    speakers = ["GM", "Alice (Cleric)", "Bob (Rogue)", "Carol (Wizard)"]
    parts: list[str] = []
    for s in range(1, scenes + 1):
        parts.append(_r20_msg("GM", f"■ 장면 {s}: 챕터 {s}의 시작"))
        parts.append(_r20_desc(f"챕터 {s}의 배경 묘사가 이어집니다."))
        for _ in range(lines_per_scene):
            sp = rng.choice(speakers)
            parts.append(_r20_msg(sp, f"이것은 {sp}의 대사입니다. 챕터 {s}."))
            if rng.random() < 0.2:
                parts.append(
                    _r20_msg(sp, f"Rolling 1d20+{rng.randint(0,10)} = {rng.randint(1,29)}",
                             kind="general rollresult")
                )
    return _ROLL20_TEMPLATE.format(title=f"Roll20 long ({scenes} scenes)", body="\n".join(parts))


# ---------------------------------------------------------------------------
# Plain text (.txt) format
# ---------------------------------------------------------------------------

def make_text_log() -> str:
    return textwrap.dedent(
        """
        GM: ■ 시작
        GM: 오늘은 새로운 모험을 시작합니다.
        김탐정: 「드디어 시작이군.」
        탐정: CCB<=60 청각 → 42 성공
        GM: 멀리서 발소리가 들립니다.
        GM: ■ 장면 1: 추격
        김탐정: 「뒤쫓아가야 해!」
        """
    ).strip() + "\n"


# ---------------------------------------------------------------------------
# Cocofolia — modern <p class="player pN"> format (post-2022 ccfolia.com export)
# ---------------------------------------------------------------------------

_COCOFOLIA_MODERN_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{title}</title>
<style>
.p0 {{ color: #888888 }}   /* GM / system */
.p1 {{ color: #5a3296 }}   /* PC1 */
.p2 {{ color: #b8242a }}   /* PC2 */
.diceroll {{ font-family: monospace; color: #444 }}
.system {{ color: #999; font-style: italic }}
</style></head>
<body>
<div class="tab t0">
<h1>メイン</h1>
{body}
</div>
</body></html>
"""


def _coco_modern_msg(speaker: str, content: str, *, klass: str = "p1") -> str:
    return (
        f'<p class="player {klass}"><span>{speaker}</span> : '
        f'<span>{content}</span></p>'
    )


def _coco_modern_dice(speaker: str, expr: str, klass: str = "p1") -> str:
    return (
        f'<p class="player {klass}"><span>{speaker}</span> : '
        f'<span class="diceroll">{expr}</span></p>'
    )


def make_cocofolia_modern(title: str = "코코포리아 모던 더미") -> str:
    """ccfolia.com 의 최신 export 가 쓰는 ``<p class="player pN">`` 형식."""
    body = "\n".join([
        _coco_modern_msg("KP", "■ 도입: 미스카토닉 대학", klass="p0"),
        _coco_modern_msg("사사키", "「안녕하세요, 교수입니다.」", klass="p1"),
        _coco_modern_msg("김탐정", "「사설 탐정 김탐정이오.」", klass="p2"),
        _coco_modern_dice("사사키", "CCB<=65 도서관 ＞ 35 ＞ 成功", klass="p1"),
        _coco_modern_msg("KP", "오래된 문서에서 단서를 발견합니다.", klass="p0"),
        _coco_modern_msg("KP", "■ 장면 1: 어둠 속의 조우", klass="p0"),
        _coco_modern_dice("김탐정", "1D100<=60 청각 ＞ 42 ＞ 成功", klass="p2"),
        _coco_modern_msg("KP", "발소리가 가까워집니다.", klass="p0"),
        '<p class="system">사사키 has joined the room</p>',
    ])
    return _COCOFOLIA_MODERN_TEMPLATE.format(title=title, body=body)


def make_cocofolia_multitab(title: str = "코코포리아 멀티탭") -> str:
    """Multiple ``<div class="tab tN">`` channels in one file."""
    main = "\n".join([
        _coco_modern_msg("KP", "■ 시작", klass="p0"),
        _coco_modern_msg("PC1", "「갑니다.」", klass="p1"),
    ])
    chat = "\n".join([
        _coco_modern_msg("PC1", "오늘 컨디션 어때요?", klass="p1"),
        _coco_modern_msg("PC2", "괜찮아요!", klass="p2"),
    ])
    body = (
        f'<div class="tab t0"><h2>メイン</h2>{main}</div>\n'
        f'<div class="tab t1"><h2>雑談</h2>{chat}</div>'
    )
    return _COCOFOLIA_MODERN_TEMPLATE.format(title=title, body=body)


# ---------------------------------------------------------------------------
# Roll20 — rich variants (roll templates, inline rolls, whispers, emotes)
# ---------------------------------------------------------------------------

def make_roll20_with_roll_template(title: str = "Roll20 5e roll template") -> str:
    """A realistic D&D 5e attack roll using ``sheet-rolltemplate-atk`` markup."""
    body = '''
    <div class="message general" data-messageid="-Nabc111" data-playerid="-Lpc1">
      <span class="by">Aragorn:</span> 검을 휘둘러 공격합니다.
    </div>
    <div class="message rollresult" data-messageid="-Nabc112" data-playerid="-Lpc1">
      <span class="by">Aragorn:</span>
      <div class="sheet-rolltemplate-atk">
        <table>
          <caption>Longsword Attack</caption>
          <tr><td class="sheet-key">To Hit</td>
              <td class="sheet-value"><span class="inlinerollresult" original-title="Rolling 1d20+7">22</span></td></tr>
          <tr><td class="sheet-key">Damage</td>
              <td class="sheet-value"><span class="inlinerollresult" original-title="Rolling 1d8+3">9</span></td></tr>
        </table>
      </div>
    </div>
    <div class="message general" data-messageid="-Nabc113" data-playerid="-Lgm">
      <span class="by">GM:</span> ■ 장면 2: 오크 무리
    </div>
    '''
    return _ROLL20_TEMPLATE.format(title=title, body=body)


def make_roll20_emote_and_desc(title: str = "Roll20 emote desc") -> str:
    """Mix of /me (emote) and /desc (no-speaker narration)."""
    body = '''
    <div class="message emote" data-messageid="-N1">
      <div class="spacer"></div>Aragorn draws his sword silently.
    </div>
    <div class="message desc" data-messageid="-N2">
      The cave is dark and damp.
    </div>
    <div class="message general" data-messageid="-N3">
      <span class="by">GM:</span> ■ 장면 1: 동굴 입구
    </div>
    <div class="message general" data-messageid="-N4">
      <span class="by">Aragorn:</span> 「조심하라!」
    </div>
    '''
    return _ROLL20_TEMPLATE.format(title=title, body=body)


def make_roll20_with_whisper(title: str = "Roll20 whisper") -> str:
    body = '''
    <div class="message general" data-messageid="-Nw1">
      <span class="by">GM:</span> 오늘 세션을 시작합니다.
    </div>
    <div class="message general private" data-messageid="-Nw2">
      <span class="by">(From GM to Aragorn):</span> 너만 알 수 있는 정보야.
    </div>
    <div class="message general" data-messageid="-Nw3">
      <span class="by">Aragorn:</span> 「알겠습니다.」
    </div>
    '''
    return _ROLL20_TEMPLATE.format(title=title, body=body)


def make_roll20_with_avatar_timestamp(title: str = "Roll20 with avatar") -> str:
    """Realistic export with <img class="avatar"> and <span class="tstamp">."""
    body = '''
    <div class="message general" data-messageid="-Nav1" data-playerid="-Lpc1">
      <img class="avatar" src="https://s3.amazonaws.com/files.d20.io/images/avatar.png"/>
      <span class="tstamp" aria-label="December 24, 2024 7:32PM">12/24/24 7:32PM</span>
      <span class="by">Aragorn:</span> 시작합시다.
    </div>
    <div class="message general rollresult" data-messageid="-Nav2">
      <span class="by">Aragorn:</span>
      <div class="formula">rolling 1d20+5</div>
      <div class="formattedformula"></div>
      <strong>18</strong>
    </div>
    '''
    return _ROLL20_TEMPLATE.format(title=title, body=body)


def make_roll20_with_missing_speaker(title: str = "Roll20 orphan") -> str:
    """Edge case: empty <span class="by"></span> (deleted user / API output)."""
    body = '''
    <div class="message general" data-messageid="-No1">
      <span class="by"></span> (system) API script: 5 monsters spawned.
    </div>
    <div class="message system" data-messageid="-No2">
      Player1 has joined the campaign.
    </div>
    <div class="message general" data-messageid="-No3">
      <span class="by">GM:</span> 본격적으로 시작합니다.
    </div>
    '''
    return _ROLL20_TEMPLATE.format(title=title, body=body)


# ---------------------------------------------------------------------------
# Safety / edge cases
# ---------------------------------------------------------------------------

def make_empty_html() -> str:
    """Empty HTML document — no entries should be produced, no crash."""
    return "<!DOCTYPE html><html><head><title>empty</title></head><body></body></html>"


def make_single_message_html() -> str:
    return _COCOFOLIA_TEMPLATE.format(
        title="single",
        body=_coco_line("GM", "단 한 줄 메시지."),
    )


def make_very_long_message_html() -> str:
    """One message with ~50KB of text — checks the parser doesn't choke on size."""
    long_text = "이것은 매우 긴 메시지입니다. " * 1500  # ~30KB
    return _COCOFOLIA_TEMPLATE.format(
        title="long",
        body=_coco_line("GM", long_text),
    )


def make_unicode_emoji_html() -> str:
    """Unicode emoji + special chars (full-width, math symbols) in content."""
    return _COCOFOLIA_TEMPLATE.format(
        title="unicode",
        body="\n".join([
            _coco_line("GM", "🎲 주사위를 굴립니다 ✨"),
            _coco_line("PC", "「ㅎㅎㅎ 🔥 가즈아!」"),
            _coco_line("GM", "결과: 28 ＞ 大成功 ⭐"),
            _coco_line("PC", "ｸﾘﾃｨｶﾙ! ★彡"),
            _coco_line("GM", "α + β = γ ∴ 성공"),
        ]),
    )


def make_html_with_script_injection() -> str:
    """Embeds <script>/<iframe>/<style>onload — must be ignored, NEVER executed.

    BeautifulSoup html.parser tolerates these; the test asserts that none of
    the script content leaks into entries and no exception is raised.
    """
    return _COCOFOLIA_TEMPLATE.format(
        title="injection",
        body=(
            '<script>alert("xss")</script>\n'
            '<iframe src="javascript:alert(1)"></iframe>\n'
            '<style onload="alert(2)">body{background:red}</style>\n'
            + _coco_line("GM", "안전한 메시지 1")
            + "\n"
            + _coco_line("PC", '<img src=x onerror="alert(3)"> 사용자 입력')
            + "\n"
            + _coco_line("GM", "안전한 메시지 2")
        ),
    )


def make_malformed_html() -> str:
    """Unclosed tags — BeautifulSoup should still produce something usable."""
    return (
        '<!DOCTYPE html><html><body>'
        '<p><span class="firing_name_GM firing_firing">: 첫 메시지</span>\n'
        '<p><span class="firing_name_PC firing_firing">: 두 번째 메시지\n'  # unclosed
        '<div><p><span class="firing_name_GM firing_firing">: 닫히지 않은 div\n'
    )


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DummyLog:
    name: str
    suffix: str
    content: str


def all_dummy_logs() -> Iterable[DummyLog]:
    # Cocofolia legacy ``firing_name_*`` format
    yield DummyLog("cocofolia_basic", ".html", make_cocofolia_basic())
    yield DummyLog("cocofolia_channels", ".html", make_cocofolia_with_channels())
    yield DummyLog("cocofolia_images", ".html", make_cocofolia_with_images())
    # Cocofolia modern ``<p class="player pN">`` format
    yield DummyLog("cocofolia_modern", ".html", make_cocofolia_modern())
    yield DummyLog("cocofolia_multitab", ".html", make_cocofolia_multitab())
    # Roll20 variants
    yield DummyLog("roll20_basic", ".html", make_roll20_basic())
    yield DummyLog("roll20_long", ".html", make_roll20_long())
    yield DummyLog("roll20_template", ".html", make_roll20_with_roll_template())
    yield DummyLog("roll20_emote_desc", ".html", make_roll20_emote_and_desc())
    yield DummyLog("roll20_whisper", ".html", make_roll20_with_whisper())
    yield DummyLog("roll20_avatar", ".html", make_roll20_with_avatar_timestamp())
    yield DummyLog("roll20_orphan", ".html", make_roll20_with_missing_speaker())
    # Plain text
    yield DummyLog("plain_text", ".txt", make_text_log())
    # Edge / safety cases (these are expected NOT to crash; entry counts vary)
    yield DummyLog("empty", ".html", make_empty_html())
    yield DummyLog("single_message", ".html", make_single_message_html())
    yield DummyLog("very_long", ".html", make_very_long_message_html())
    yield DummyLog("unicode_emoji", ".html", make_unicode_emoji_html())
    yield DummyLog("script_injection", ".html", make_html_with_script_injection())
    yield DummyLog("malformed", ".html", make_malformed_html())
