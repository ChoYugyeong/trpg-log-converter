"""
TRPG Log Converter Pro - 공용 유틸리티
"""

import copy


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
