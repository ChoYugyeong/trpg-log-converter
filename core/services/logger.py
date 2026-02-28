#!/usr/bin/env python3
"""
로깅 시스템
애플리케이션 전체 로깅 관리
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import os


class AppLogger:
    """애플리케이션 로거 관리"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if AppLogger._initialized:
            return
        AppLogger._initialized = True

        self._log_dir = None
        self._file_handler = None
        self._console_handler = None
        self._log_level = logging.INFO

    def setup(self, app_dir: Path, log_level: int = logging.INFO,
              console_output: bool = True, file_output: bool = True):
        """로깅 시스템 초기화"""
        self._log_level = log_level
        self._log_dir = app_dir / 'logs'

        # 로그 디렉토리 생성
        if file_output:
            self._log_dir.mkdir(parents=True, exist_ok=True)

        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 콘솔 핸들러
        if console_output:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(log_level)
            self._console_handler.setFormatter(formatter)
            root_logger.addHandler(self._console_handler)

        # 파일 핸들러
        if file_output:
            log_file = self._log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
            self._file_handler = logging.FileHandler(log_file, encoding='utf-8')
            self._file_handler.setLevel(log_level)
            self._file_handler.setFormatter(formatter)
            root_logger.addHandler(self._file_handler)

        # 오래된 로그 파일 정리
        self._cleanup_old_logs(max_days=30)

        logging.info("로깅 시스템 초기화 완료")

    def _cleanup_old_logs(self, max_days: int = 30):
        """오래된 로그 파일 정리"""
        if not self._log_dir or not self._log_dir.exists():
            return

        cutoff = datetime.now().timestamp() - (max_days * 24 * 60 * 60)

        for log_file in self._log_dir.glob('*.log'):
            try:
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    logging.debug(f"오래된 로그 삭제: {log_file.name}")
            except Exception as e:
                logging.warning(f"로그 파일 삭제 실패: {log_file} - {e}")

    def get_logger(self, name: str) -> logging.Logger:
        """이름으로 로거 가져오기"""
        return logging.getLogger(name)

    def set_level(self, level: int):
        """로그 레벨 변경"""
        self._log_level = level
        logging.getLogger().setLevel(level)
        if self._console_handler:
            self._console_handler.setLevel(level)
        if self._file_handler:
            self._file_handler.setLevel(level)

    def get_log_dir(self) -> Optional[Path]:
        """로그 디렉토리 경로"""
        return self._log_dir

    def get_recent_logs(self, lines: int = 100) -> list:
        """최근 로그 내용 가져오기"""
        if not self._log_dir:
            return []

        log_files = sorted(self._log_dir.glob('*.log'), reverse=True)
        if not log_files:
            return []

        try:
            with open(log_files[0], 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        except Exception:
            return []


# 전역 로거 인스턴스
app_logger = AppLogger()


def setup_logging(app_dir: Path, debug: bool = False):
    """간편 로깅 설정 함수"""
    level = logging.DEBUG if debug else logging.INFO
    app_logger.setup(app_dir, log_level=level)


def get_logger(name: str) -> logging.Logger:
    """로거 가져오기 헬퍼"""
    return logging.getLogger(name)
