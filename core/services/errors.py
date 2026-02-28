#!/usr/bin/env python3
"""
에러 처리 유틸리티
애플리케이션 전반의 예외 처리 및 복구 기능
"""

import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Any, Dict
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """에러 심각도"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ConversionError(Exception):
    """변환 관련 에러"""
    def __init__(self, message: str, stage: str = None,
                 recoverable: bool = True, details: Dict = None):
        super().__init__(message)
        self.stage = stage
        self.recoverable = recoverable
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class FileError(ConversionError):
    """파일 관련 에러"""
    def __init__(self, message: str, file_path: str = None, **kwargs):
        super().__init__(message, stage="file_io", **kwargs)
        self.file_path = file_path


class ParseError(ConversionError):
    """파싱 관련 에러"""
    def __init__(self, message: str, line_number: int = None, **kwargs):
        super().__init__(message, stage="parsing", **kwargs)
        self.line_number = line_number


class ExportError(ConversionError):
    """내보내기 관련 에러"""
    def __init__(self, message: str, format: str = None, **kwargs):
        super().__init__(message, stage="export", **kwargs)
        self.format = format


class ErrorHandler:
    """에러 핸들러"""

    def __init__(self, app_dir: Path = None):
        self._app_dir = app_dir
        self._error_log = []
        self._max_log_size = 100
        self._callbacks = {
            ErrorSeverity.INFO: [],
            ErrorSeverity.WARNING: [],
            ErrorSeverity.ERROR: [],
            ErrorSeverity.CRITICAL: [],
        }

    def handle(self, error: Exception, severity: ErrorSeverity = ErrorSeverity.ERROR,
               context: str = None, suppress: bool = False) -> Optional[str]:
        """에러 처리"""
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity.value,
            'type': type(error).__name__,
            'message': str(error),
            'context': context,
            'traceback': traceback.format_exc() if not suppress else None,
        }

        # 에러 로그 추가
        self._error_log.append(error_info)
        if len(self._error_log) > self._max_log_size:
            self._error_log = self._error_log[-self._max_log_size:]

        # 로깅
        log_message = f"[{context or 'Unknown'}] {error}"
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=not suppress)
        elif severity == ErrorSeverity.ERROR:
            logger.error(log_message, exc_info=not suppress)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 콜백 실행
        for callback in self._callbacks.get(severity, []):
            try:
                callback(error_info)
            except Exception as e:
                logger.warning(f"에러 콜백 실행 실패: {e}")

        return error_info.get('message')

    def register_callback(self, severity: ErrorSeverity, callback: Callable):
        """에러 콜백 등록"""
        if severity in self._callbacks:
            self._callbacks[severity].append(callback)

    def get_recent_errors(self, count: int = 10) -> list:
        """최근 에러 목록"""
        return self._error_log[-count:]

    def clear_errors(self):
        """에러 로그 초기화"""
        self._error_log.clear()

    def get_error_summary(self) -> Dict:
        """에러 요약"""
        summary = {
            'total': len(self._error_log),
            'by_severity': {},
            'by_type': {},
        }
        for error in self._error_log:
            sev = error.get('severity', 'unknown')
            typ = error.get('type', 'unknown')
            summary['by_severity'][sev] = summary['by_severity'].get(sev, 0) + 1
            summary['by_type'][typ] = summary['by_type'].get(typ, 0) + 1
        return summary


# 전역 에러 핸들러
_error_handler = None


def get_error_handler(app_dir: Path = None) -> ErrorHandler:
    """전역 에러 핸들러 가져오기"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(app_dir)
    return _error_handler


def safe_operation(default_return=None, suppress_errors: bool = False,
                   context: str = None, severity: ErrorSeverity = ErrorSeverity.ERROR):
    """안전한 작업 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                handler.handle(e, severity=severity,
                               context=context or func.__name__,
                               suppress=suppress_errors)
                return default_return
        return wrapper
    return decorator


def try_operation(operation: Callable, default=None, context: str = None) -> Any:
    """단일 작업 안전 실행"""
    try:
        return operation()
    except Exception as e:
        handler = get_error_handler()
        handler.handle(e, context=context)
        return default


def validate_file_path(path: str, must_exist: bool = True,
                       allowed_extensions: list = None) -> Path:
    """파일 경로 유효성 검사"""
    if not path:
        raise FileError("파일 경로가 비어있습니다")

    file_path = Path(path)

    if must_exist and not file_path.exists():
        raise FileError(f"파일이 존재하지 않습니다: {path}", file_path=str(path))

    if allowed_extensions:
        if file_path.suffix.lower() not in [e.lower() for e in allowed_extensions]:
            raise FileError(
                f"지원하지 않는 파일 형식입니다: {file_path.suffix}",
                file_path=str(path),
                details={'allowed': allowed_extensions}
            )

    return file_path


def validate_config(config: Dict, required_keys: list = None) -> bool:
    """설정 유효성 검사"""
    if not config:
        raise ConversionError("설정이 비어있습니다", stage="config")

    if required_keys:
        missing = [k for k in required_keys if k not in config]
        if missing:
            raise ConversionError(
                f"필수 설정이 누락되었습니다: {', '.join(missing)}",
                stage="config",
                details={'missing_keys': missing}
            )

    return True


class RetryHandler:
    """재시도 핸들러"""

    def __init__(self, max_retries: int = 3, delay_seconds: float = 1.0,
                 exponential_backoff: bool = True):
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self.exponential_backoff = exponential_backoff

    def execute(self, operation: Callable, context: str = None) -> Any:
        """작업 재시도 실행"""
        import time

        last_error = None
        for attempt in range(self.max_retries):
            try:
                return operation()
            except Exception as e:
                last_error = e
                logger.warning(f"[{context}] 시도 {attempt + 1}/{self.max_retries} 실패: {e}")

                if attempt < self.max_retries - 1:
                    delay = self.delay_seconds
                    if self.exponential_backoff:
                        delay *= (2 ** attempt)
                    time.sleep(delay)

        raise last_error


def with_retry(max_retries: int = 3, delay: float = 1.0):
    """재시도 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = RetryHandler(max_retries=max_retries, delay_seconds=delay)
            return handler.execute(lambda: func(*args, **kwargs), context=func.__name__)
        return wrapper
    return decorator
