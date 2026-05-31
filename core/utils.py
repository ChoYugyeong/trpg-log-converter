"""
TRPG Log Converter Pro - 공용 유틸리티
"""


def deep_merge(base: dict, override: dict) -> dict:
    """딕셔너리 깊은 병합 (새 딕셔너리 반환, override 우선)"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
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
