"""Factories that produce synthetic log files for round-trip testing.

Each ``make_*`` function returns the file content as a ``str`` so the test can
decide where to drop it (tmp_path, or an explicit fixture dir).
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
# Catalog
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DummyLog:
    name: str
    suffix: str
    content: str


def all_dummy_logs() -> Iterable[DummyLog]:
    yield DummyLog("cocofolia_basic", ".html", make_cocofolia_basic())
    yield DummyLog("cocofolia_channels", ".html", make_cocofolia_with_channels())
    yield DummyLog("cocofolia_images", ".html", make_cocofolia_with_images())
    yield DummyLog("roll20_basic", ".html", make_roll20_basic())
    yield DummyLog("roll20_long", ".html", make_roll20_long())
    yield DummyLog("plain_text", ".txt", make_text_log())
