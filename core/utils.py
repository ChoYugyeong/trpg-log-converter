"""
TRPG Log Converter Pro - 공용 유틸리티
"""

import copy
import unicodedata


def split_first_grapheme(text: str) -> tuple[str, str]:
    """첫 '글자(grapheme cluster)'와 나머지로 분리한다.

    드롭캡처럼 첫 글자만 떼어낼 때 ``text[0]`` / ``text[1:]`` 로 자르면
    결합 문자(combining mark), 변형 선택자(variation selector), ZWJ 이모지
    (예: 가족 이모지)가 코드포인트 경계에서 쪼개져 글자가 깨진다.
    이 함수는 그런 부속 코드포인트를 첫 글자에 붙여 안전하게 분리한다.
    (astral 문자(😀 등)는 Python str 이 코드포인트 단위라 애초에 안 쪼개진다.)
    """
    if not text:
        return "", ""
    i = 1
    n = len(text)
    while i < n:
        ch = text[i]
        cp = ord(ch)
        # 결합 문자 / 변형 선택자(U+FE00–U+FE0F) → 앞 글자에 붙는다
        if unicodedata.combining(ch) or 0xFE00 <= cp <= 0xFE0F:
            i += 1
            continue
        # ZWJ(U+200D) → 뒤따르는 글자까지 한 묶음(이모지 시퀀스)
        if cp == 0x200D:
            i += 1
            if i < n:
                i += 1
            continue
        break
    return text[:i], text[i:]


def deep_merge(base: dict, override: dict) -> dict:
    """딕셔너리 깊은 병합 (완전히 독립된 새 딕셔너리 반환, override 우선).

    이전 구현은 ``base.copy()`` (얕은 복사)라 override 가 덮어쓰지 않은 중첩
    dict/list 가 base 와 같은 객체로 공유됐다. 그래서 병합 결과를 수정하면
    원본 base(보통 기본 설정/프리셋)까지 함께 바뀌는 잠재적 버그가 있었다.
    값을 deepcopy 해 호출 측이 결과를 자유롭게 변형해도 입력이 오염되지 않게 한다.
    """
    result = {key: copy.deepcopy(value) for key, value in base.items()}
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def safe_int(value, default: int = 0) -> int:
    """안전한 int 변환. '85 (권장)' 같은 문자열에서도 숫자 추출."""
    if isinstance(value, int):
        return value
    try:
        return int(str(value).split()[0])
    except (ValueError, TypeError, IndexError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """안전한 float 변환."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).split()[0])
    except (ValueError, TypeError, IndexError):
        return default
