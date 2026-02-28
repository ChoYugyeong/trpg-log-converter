#!/usr/bin/env python3
"""
변환 이력 관리
최근 변환 기록 저장 및 조회
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ConversionRecord:
    """변환 기록 데이터"""
    id: str
    timestamp: str
    input_file: str
    input_filename: str
    output_files: List[str]
    output_format: str
    title: str
    author: str
    entry_count: int
    scene_count: int
    success: bool
    error_message: Optional[str] = None
    duration_ms: int = 0
    profile_used: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversionRecord':
        return cls(**data)


class HistoryManager:
    """변환 이력 관리자"""

    def __init__(self, app_dir: Path, max_records: int = 100):
        self._app_dir = app_dir
        self._history_file = app_dir / 'data' / 'conversion_history.json'
        self._max_records = max_records
        self._records: List[ConversionRecord] = []
        self._load()

    def _load(self):
        """이력 파일 로드"""
        try:
            if self._history_file.exists():
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._records = [ConversionRecord.from_dict(r) for r in data.get('records', [])]
                logger.debug(f"변환 이력 로드: {len(self._records)}개")
        except Exception as e:
            logger.warning(f"변환 이력 로드 실패: {e}")
            self._records = []

    def _save(self):
        """이력 파일 저장"""
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'version': 1,
                    'updated': datetime.now().isoformat(),
                    'records': [r.to_dict() for r in self._records]
                }, f, ensure_ascii=False, indent=2)
            logger.debug(f"변환 이력 저장: {len(self._records)}개")
        except Exception as e:
            logger.error(f"변환 이력 저장 실패: {e}")

    def add_record(self, input_file: str, output_files: List[str],
                   output_format: str, title: str, author: str,
                   entry_count: int, scene_count: int,
                   success: bool, error_message: str = None,
                   duration_ms: int = 0, profile_used: str = None) -> ConversionRecord:
        """새 변환 기록 추가"""
        record = ConversionRecord(
            id=datetime.now().strftime('%Y%m%d_%H%M%S_%f'),
            timestamp=datetime.now().isoformat(),
            input_file=str(input_file),
            input_filename=Path(input_file).name,
            output_files=[str(f) for f in output_files],
            output_format=output_format,
            title=title,
            author=author,
            entry_count=entry_count,
            scene_count=scene_count,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            profile_used=profile_used,
        )

        self._records.insert(0, record)

        # 최대 개수 초과시 오래된 기록 삭제
        if len(self._records) > self._max_records:
            self._records = self._records[:self._max_records]

        self._save()
        logger.info(f"변환 기록 추가: {record.input_filename} -> {output_format}")
        return record

    def get_records(self, limit: int = None) -> List[ConversionRecord]:
        """이력 목록 가져오기"""
        if limit:
            return self._records[:limit]
        return self._records.copy()

    def get_record_by_id(self, record_id: str) -> Optional[ConversionRecord]:
        """ID로 기록 조회"""
        for record in self._records:
            if record.id == record_id:
                return record
        return None

    def get_recent_files(self, limit: int = 10) -> List[str]:
        """최근 변환 파일 목록"""
        files = []
        seen = set()
        for record in self._records:
            if record.input_file not in seen:
                files.append(record.input_file)
                seen.add(record.input_file)
            if len(files) >= limit:
                break
        return files

    def get_stats(self) -> Dict:
        """변환 통계"""
        if not self._records:
            return {
                'total_conversions': 0,
                'success_count': 0,
                'failure_count': 0,
                'total_entries': 0,
                'avg_entries': 0,
                'formats_used': {},
            }

        success_count = sum(1 for r in self._records if r.success)
        total_entries = sum(r.entry_count for r in self._records)

        formats = {}
        for r in self._records:
            formats[r.output_format] = formats.get(r.output_format, 0) + 1

        return {
            'total_conversions': len(self._records),
            'success_count': success_count,
            'failure_count': len(self._records) - success_count,
            'total_entries': total_entries,
            'avg_entries': total_entries // len(self._records) if self._records else 0,
            'formats_used': formats,
        }

    def clear(self):
        """모든 이력 삭제"""
        self._records.clear()
        self._save()
        logger.info("변환 이력 초기화됨")

    def delete_record(self, record_id: str) -> bool:
        """특정 기록 삭제"""
        for i, record in enumerate(self._records):
            if record.id == record_id:
                del self._records[i]
                self._save()
                return True
        return False

    def search(self, query: str) -> List[ConversionRecord]:
        """이력 검색"""
        query_lower = query.lower()
        results = []
        for record in self._records:
            if (query_lower in record.input_filename.lower() or
                query_lower in record.title.lower() or
                query_lower in record.author.lower()):
                results.append(record)
        return results
