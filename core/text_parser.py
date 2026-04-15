#!/usr/bin/env python3
"""
텍스트 파일(.txt) 파서
다양한 형식의 TRPG 로그를 파싱
"""

import re
from pathlib import Path

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

    best = max(counts, key=counts.get)
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

        # 장면 마커 체크
        if is_scene_marker(line, scene_patterns):
            entries.append({
                'type': 'system',
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

    return entries


def parse_file(file_path, config):
    """파일 파싱 (HTML 또는 TXT)"""
    path = Path(file_path)

    # 여러 인코딩을 시도하여 파일 읽기 (한국어 파일은 EUC-KR/CP949일 수 있음)
    content = None
    for encoding in ('utf-8', 'utf-8-sig', 'euc-kr', 'cp949', 'latin-1'):
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        raise UnicodeDecodeError('utf-8', b'', 0, 1, f'지원되지 않는 인코딩: {path.name}')

    # HTML 파일 감지
    if path.suffix.lower() in ['.html', '.htm'] or '<html' in content.lower()[:1000]:
        from core.engine import parse_log
        return parse_log(content, config)

    # 텍스트 파일
    return parse_text_log(content, config)
