#!/usr/bin/env python3
"""
텍스트 파일(.txt) 파서
다양한 형식의 TRPG 로그를 파싱
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# 모듈 레벨에서 정규식 미리 컴파일 (성능 최적화)
_RE_COLON = re.compile(r'^.{1,30}\s*:\s*.+')
_RE_BRACKET = re.compile(r'^\[(.+?)\]\s*(.+)$')
_RE_PAREN = re.compile(r'^\((.+?)\)\s*(.+)$')
_RE_DICE = re.compile(r'(CCB|1D100|2D6|\d+D\d+)', re.IGNORECASE)


def detect_format(content):
    """텍스트 형식 자동 감지"""
    lines = content.strip().split('\n')[:50]

    # 코코포리아 스타일: "이름 : 대사"
    colon_count = sum(1 for line in lines if _RE_COLON.match(line))

    # 대괄호 스타일: "[이름] 대사"
    bracket_count = sum(1 for line in lines if _RE_BRACKET.match(line))

    # 괄호 스타일: "(이름) 대사"
    paren_count = sum(1 for line in lines if _RE_PAREN.match(line))

    # 탭 구분: "이름\t대사"
    tab_count = sum(1 for line in lines if '\t' in line and line.count('\t') == 1)

    counts = {
        'colon': colon_count,
        'bracket': bracket_count,
        'paren': paren_count,
        'tab': tab_count
    }

    best = max(counts, key=lambda k: counts[k])
    if counts[best] < len(lines) * 0.3:
        return 'plain'
    return best


def parse_colon_format(line, config):
    """콜론 형식 파싱: "이름 : 대사" """
    if ':' not in line:
        return None

    colon_pos = line.find(':')
    name_max = config.get('parsing', {}).get('name_max_length', 50)

    if colon_pos > name_max or colon_pos < 1:
        return None

    name = line[:colon_pos].strip()
    content = line[colon_pos + 1:].strip()

    if not name or not content:
        return None

    return {'name': name, 'content': content}


def parse_bracket_format(line):
    """대괄호 형식 파싱: "[이름] 대사" """
    match = _RE_BRACKET.match(line)
    if match:
        return {'name': match.group(1).strip(), 'content': match.group(2).strip()}
    return None


def parse_paren_format(line):
    """괄호 형식 파싱: "(이름) 대사" """
    match = _RE_PAREN.match(line)
    if match:
        return {'name': match.group(1).strip(), 'content': match.group(2).strip()}
    return None


def parse_tab_format(line):
    """탭 형식 파싱: "이름\t대사" """
    if '\t' not in line:
        return None
    parts = line.split('\t', 1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return {'name': parts[0].strip(), 'content': parts[1].strip()}
    return None


def is_narration_user(name, config):
    """나레이션 사용자인지 확인"""
    narration_users = config.get('narration', {}).get('users', ['GM', 'KP', 'DM'])
    return name.lower().strip() in [u.lower() for u in narration_users]


def is_dice_roll(text):
    """다이스 롤인지 확인"""
    if _RE_DICE.search(text) and ('→' in text or '=' in text or '>' in text):
        return True
    return False


def is_scene_marker(text, patterns):
    """장면 마커인지 확인"""
    for pattern in patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            # 잘못된 정규식은 리터럴 매칭으로 폴백
            if pattern in text:
                return True
    return False


def parse_text_log(content, config):
    """텍스트 로그 파싱"""
    entries = []
    format_type = detect_format(content)

    scene_patterns = config.get('chapter', {}).get('scene_patterns', ['^■'])

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue

        # 장면 마커 체크 (전체 라인이 ^■ 등으로 시작하는 경우)
        if is_scene_marker(line, scene_patterns):
            entries.append({
                'type': 'scene',
                'name': '',
                'content': line,
                'raw': line,
                'image': None
            })
            continue

        # 형식에 따른 파싱
        parsed = None
        if format_type == 'colon':
            parsed = parse_colon_format(line, config)
        elif format_type == 'bracket':
            parsed = parse_bracket_format(line)
        elif format_type == 'paren':
            parsed = parse_paren_format(line)
        elif format_type == 'tab':
            parsed = parse_tab_format(line)

        if parsed:
            name = parsed['name']
            content_text = parsed['content']

            # 시스템 메시지
            if name.lower() == 'system':
                entries.append({
                    'type': 'system',
                    'name': '',
                    'content': content_text,
                    'raw': line,
                    'image': None
                })
            # 나레이션
            elif is_narration_user(name, config):
                entries.append({
                    'type': 'narration',
                    'name': name,
                    'content': content_text,
                    'raw': line,
                    'image': None
                })
            # 다이스 롤
            elif is_dice_roll(content_text):
                entries.append({
                    'type': 'dice',
                    'name': name,
                    'content': content_text,
                    'raw': line,
                    'image': None
                })
            # 일반 대사
            else:
                entries.append({
                    'type': 'dialogue',
                    'name': name,
                    'content': content_text,
                    'raw': line,
                    'image': None
                })
        else:
            # 파싱 실패 시 일반 텍스트로 처리
            if line:
                entries.append({
                    'type': 'dialogue',
                    'name': '',
                    'content': line,
                    'raw': line,
                    'image': None
                })

    # ``GM: ■ 시작`` 처럼 화자 뒤에 마커가 붙은 라인은 위 ``parse_*_format`` 분기에서
    # dialogue/narration 으로 들어가므로, content 기준으로 한 번 더 scene 분류한다.
    # (HTML 파서도 동일한 post-pass 를 수행한다.)
    for entry in entries:
        if entry.get('type') == 'scene':
            continue
        content_text = entry.get('content') or ''
        if content_text and is_scene_marker(content_text, scene_patterns):
            entry['type'] = 'scene'

    return entries


def _detect_and_read(path: Path) -> tuple[str, str]:
    """Decode ``path`` using the best available encoding.

    Strategy (in order):
      1. Try a short whitelist of likely encodings (UTF-8 family, Korean CJK).
         These succeed only on actually-clean files — no garbage-decoding.
      2. Fall back to ``charset-normalizer`` if available — statistical
         detection over a sample. Catches obscure encodings.
      3. As a last resort try ``cp949``/``latin-1`` decode with replacement so
         the user gets *something* rather than a hard failure, but log a warning
         so the issue is visible.

    Returns ``(text, encoding_label)``.
    Raises :class:`core.exceptions.EncodingError` only if every strategy fails.
    """
    from core.exceptions import EncodingError

    raw = path.read_bytes()

    # 1. Strict whitelist — these are the encodings we expect from Ccfolia /
    #    Roll20 exports and Korean text editors. ``strict`` means a single bad
    #    byte rejects the encoding, so we never silently mojibake.
    whitelist = ('utf-8-sig', 'utf-8', 'euc-kr', 'cp949')
    for enc in whitelist:
        try:
            text = raw.decode(enc)
            return text, enc
        except UnicodeDecodeError:
            continue

    # 2. charset-normalizer — best-effort statistical detection. Lazy import so
    #    that the rest of the package keeps working if the dep is missing.
    try:
        from charset_normalizer import from_bytes
    except ImportError:
        from_bytes = None  # type: ignore[assignment]

    if from_bytes is not None:
        try:
            best = from_bytes(raw).best()
            if best is not None and best.encoding:
                logger.info(
                    "charset-normalizer chose %s (chaos=%.2f, coherence=%.2f) for %s",
                    best.encoding, best.chaos, best.coherence, path.name,
                )
                return str(best), best.encoding
        except Exception:  # noqa: BLE001 — detector is best-effort
            logger.warning("charset-normalizer 감지 실패: %s", path.name, exc_info=True)

    # 3. Last-resort decode with replacement so the user isn't blocked entirely.
    #    Loud warning makes it obvious that text is degraded.
    for enc in ('cp949', 'latin-1'):
        try:
            text = raw.decode(enc, errors='replace')
            logger.warning(
                "인코딩 감지 실패, %s + replace 로 복호화: %s "
                "(일부 글자가 깨질 수 있습니다)",
                enc, path.name,
            )
            return text, f"{enc}+replace"
        except UnicodeDecodeError:
            continue

    raise EncodingError(
        f"지원되지 않는 인코딩: {path.name}",
        context={
            "path": str(path),
            "tried": list(whitelist) + ["charset-normalizer", "cp949+replace", "latin-1+replace"],
        },
    )


def parse_file(file_path, config):
    """파일 파싱 (HTML 또는 TXT).

    Input safety:
      - ``performance.max_html_bytes`` 보다 큰 파일은 ``ParseError`` 로 차단해
        OOM 을 막는다 (기본 50 MiB).
      - 인코딩 감지는 strict whitelist → charset-normalizer →
        replacement-fallback 순서로 시도한다. 어느 단계에서도 성공하지 못하면
        ``EncodingError`` 를 던지며 시도 목록을 context 에 담는다.
    """
    from core.exceptions import ParseError

    path = Path(file_path)

    max_bytes = int(
        (config or {}).get('performance', {}).get('max_html_bytes', 50 * 1024 * 1024)
    )
    try:
        file_size = path.stat().st_size
    except OSError as exc:
        raise ParseError(
            f"파일에 접근할 수 없습니다: {path}",
            context={"path": str(path), "cause": repr(exc)},
        ) from exc
    if file_size > max_bytes:
        raise ParseError(
            f"파일이 너무 큽니다: {file_size:,} bytes (한계 {max_bytes:,} bytes)",
            user_message=(
                f"파일이 너무 큽니다 ({file_size // (1024*1024)} MiB). "
                f"설정의 max_html_bytes 보다 작은 파일만 처리합니다."
            ),
            context={"path": str(path), "file_size": file_size, "limit": max_bytes},
        )

    content, used_encoding = _detect_and_read(path)
    logger.debug("Decoded %s as %s (%d chars)", path.name, used_encoding, len(content))

    # HTML 파일 감지
    if path.suffix.lower() in ['.html', '.htm'] or '<html' in content.lower()[:1000]:
        from core.parsers import parse_log
        return parse_log(content, config)

    # 텍스트 파일
    return parse_text_log(content, config)
