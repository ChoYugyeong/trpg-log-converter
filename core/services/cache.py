"""
파싱 결과 캐싱 서비스
파일 해시 기반 캐싱으로 중복 파싱 방지
"""

import hashlib
import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    """캐시 엔트리"""

    file_hash: str
    file_path: str
    file_size: int
    file_mtime: float
    entries: list[dict]
    characters: list[str]
    entry_count: int
    cached_at: float
    config_hash: str


class CacheService:
    """파싱 결과 캐시 서비스"""

    DEFAULT_CACHE_DIR = ".trpg_cache"
    MAX_CACHE_SIZE_MB = 100
    MAX_CACHE_AGE_DAYS = 7

    def __init__(
        self,
        cache_dir: str | None = None,
        max_size_mb: int = MAX_CACHE_SIZE_MB,
        max_age_days: int = MAX_CACHE_AGE_DAYS,
        enabled: bool = True,
    ):
        """
        Args:
            cache_dir: 캐시 디렉토리 경로
            max_size_mb: 최대 캐시 크기 (MB)
            max_age_days: 캐시 유효 기간 (일)
            enabled: 캐시 활성화 여부
        """
        self._cache_dir = Path(cache_dir) if cache_dir else Path.home() / self.DEFAULT_CACHE_DIR
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._max_age_seconds = max_age_days * 24 * 60 * 60
        self._enabled = enabled
        self._memory_cache: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

        if self._enabled:
            self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """캐시 디렉토리 생성"""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, file_path: str) -> str:
        """파일 해시 계산 (SHA-256, 첫 1MB만)"""
        hasher = hashlib.sha256()

        with open(file_path, "rb") as f:
            # 큰 파일은 첫 1MB만 해시
            chunk = f.read(1024 * 1024)
            hasher.update(chunk)

        # 파일 크기도 해시에 포함
        file_size = os.path.getsize(file_path)
        hasher.update(str(file_size).encode())

        return hasher.hexdigest()[:16]

    def _get_config_hash(self, config: dict[str, Any]) -> str:
        """설정 해시 계산"""
        # 캐시에 영향을 주는 설정만 추출. parse_file 가 파싱 후 filter/merge/대사
        # 구분자/빈 대사/🎲 등 후처리를 적용하므로 dialogue/style/images 도 키에
        # 포함해야 설정 변경 시 stale 결과가 반환되지 않는다.
        relevant_keys = [
            "parsing",
            "narration",
            "chapter",
            "content",
            "dialogue",
            "style",
            "images",
        ]
        relevant_config = {k: config.get(k, {}) for k in relevant_keys}

        config_str = json.dumps(relevant_config, sort_keys=True)
        # MD5 는 캐시 key 생성용 — security 가 아니라 빠른 fingerprint 가 목적.
        # usedforsecurity=False 로 명시해 bandit B324 false positive 차단.
        return hashlib.md5(config_str.encode(), usedforsecurity=False).hexdigest()[:8]

    def _get_cache_key(self, file_path: str, config: dict[str, Any]) -> str:
        """캐시 키 생성"""
        file_hash = self._get_file_hash(file_path)
        config_hash = self._get_config_hash(config)
        return f"{file_hash}_{config_hash}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """캐시 파일 경로"""
        return self._cache_dir / f"{cache_key}.json"

    def get(
        self,
        file_path: str,
        config: dict[str, Any],
    ) -> tuple[list[dict], list[str]] | None:
        """
        캐시된 파싱 결과 조회

        Args:
            file_path: 원본 파일 경로
            config: 파싱 설정

        Returns:
            (엔트리 리스트, 캐릭터 리스트) 또는 None
        """
        if not self._enabled:
            return None

        try:
            cache_key = self._get_cache_key(file_path, config)

            # 메모리 캐시 확인
            with self._lock:
                if cache_key in self._memory_cache:
                    entry = self._memory_cache[cache_key]
                    if self._is_valid(entry, file_path):
                        return (entry.entries, entry.characters)
                    else:
                        del self._memory_cache[cache_key]

            # 디스크 캐시 확인
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                with open(cache_path, encoding="utf-8") as f:
                    data = json.load(f)

                entry = CacheEntry(**data)

                if self._is_valid(entry, file_path):
                    # 메모리 캐시에 추가
                    with self._lock:
                        self._memory_cache[cache_key] = entry
                    return (entry.entries, entry.characters)
                else:
                    # 유효하지 않은 캐시 삭제
                    cache_path.unlink()

        except (OSError, json.JSONDecodeError, TypeError, KeyError):
            pass

        return None

    def set(
        self,
        file_path: str,
        config: dict[str, Any],
        entries: list[dict],
        characters: list[str],
    ) -> bool:
        """
        파싱 결과 캐싱

        Args:
            file_path: 원본 파일 경로
            config: 파싱 설정
            entries: 파싱된 엔트리 리스트
            characters: 추출된 캐릭터 리스트

        Returns:
            저장 성공 여부
        """
        if not self._enabled:
            return False

        try:
            file_stat = os.stat(file_path)
            cache_key = self._get_cache_key(file_path, config)

            entry = CacheEntry(
                file_hash=self._get_file_hash(file_path),
                file_path=str(Path(file_path).absolute()),
                file_size=file_stat.st_size,
                file_mtime=file_stat.st_mtime,
                entries=entries,
                characters=characters,
                entry_count=len(entries),
                cached_at=time.time(),
                config_hash=self._get_config_hash(config),
            )

            # 메모리 캐시 저장
            with self._lock:
                self._memory_cache[cache_key] = entry

            # 디스크 캐시 저장
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(asdict(entry), f, ensure_ascii=False)

            return True

        except (OSError, TypeError):
            return False

    def _is_valid(self, entry: CacheEntry, file_path: str) -> bool:
        """캐시 유효성 검사"""
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                return False

            file_stat = os.stat(file_path)

            # 파일 크기 변경 확인
            if file_stat.st_size != entry.file_size:
                return False

            # 파일 수정 시간 확인
            if file_stat.st_mtime != entry.file_mtime:
                return False

            # 캐시 만료 확인
            return not time.time() - entry.cached_at > self._max_age_seconds

        except OSError:
            return False

    def invalidate(self, file_path: str) -> None:
        """특정 파일의 캐시 무효화"""
        try:
            file_hash = self._get_file_hash(file_path)

            # 메모리 캐시에서 제거
            with self._lock:
                keys_to_remove = [k for k in self._memory_cache if k.startswith(file_hash)]
                for key in keys_to_remove:
                    del self._memory_cache[key]

            # 디스크 캐시에서 제거
            for cache_file in self._cache_dir.glob(f"{file_hash}_*.json"):
                cache_file.unlink()

        except OSError:
            pass

    def clear(self) -> None:
        """전체 캐시 삭제"""
        with self._lock:
            self._memory_cache.clear()

        try:
            for cache_file in self._cache_dir.glob("*.json"):
                cache_file.unlink()
        except OSError:
            pass

    def cleanup(self) -> int:
        """
        오래된/크기 초과 캐시 정리

        Returns:
            삭제된 캐시 파일 수
        """
        if not self._enabled:
            return 0

        deleted = 0
        current_time = time.time()
        cache_files: list[tuple[Path, float, int]] = []

        try:
            # 캐시 파일 목록 수집
            for cache_file in self._cache_dir.glob("*.json"):
                stat = cache_file.stat()
                cache_files.append((cache_file, stat.st_mtime, stat.st_size))

            # 오래된 캐시 삭제
            for path, mtime, _ in cache_files:
                if current_time - mtime > self._max_age_seconds:
                    path.unlink()
                    deleted += 1

            # 크기 초과 시 오래된 것부터 삭제
            cache_files = [(p, m, s) for p, m, s in cache_files if p.exists()]
            cache_files.sort(key=lambda x: x[1])  # 수정 시간순 정렬

            total_size = sum(s for _, _, s in cache_files)

            while total_size > self._max_size_bytes and cache_files:
                path, _, size = cache_files.pop(0)
                if path.exists():
                    path.unlink()
                    total_size -= size
                    deleted += 1

        except OSError:
            pass

        return deleted

    def get_stats(self) -> dict[str, Any]:
        """캐시 통계"""
        try:
            cache_files = list(self._cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "enabled": self._enabled,
                "cache_dir": str(self._cache_dir),
                "file_count": len(cache_files),
                "memory_count": len(self._memory_cache),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "max_size_mb": self._max_size_bytes / (1024 * 1024),
                "max_age_days": self._max_age_seconds / (24 * 60 * 60),
            }
        except OSError:
            return {
                "enabled": self._enabled,
                "error": "Unable to access cache directory",
            }

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if value:
            self._ensure_cache_dir()
