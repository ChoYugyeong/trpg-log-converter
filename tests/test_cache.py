"""
캐시 서비스 테스트
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from core.services.cache import CacheService


@pytest.fixture
def temp_cache_dir():
    """임시 캐시 디렉토리 생성"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_file():
    """테스트용 샘플 파일 생성. Windows CI 의 cp1252 default 가 한글을 못
    인코딩해 UnicodeEncodeError 가 떴던 회귀 — encoding="utf-8" 명시."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write("테스트 파일 내용\n캐릭터A: 안녕하세요\n캐릭터B: 반갑습니다")
        return f.name


@pytest.fixture(autouse=True)
def cleanup_sample_file(sample_file):
    """샘플 파일 정리"""
    yield
    if os.path.exists(sample_file):
        os.unlink(sample_file)


class TestCacheService:
    """CacheService 테스트"""

    def test_cache_disabled(self):
        """캐시 비활성화 상태에서 작동 확인"""
        service = CacheService(enabled=False)

        assert service.enabled is False
        assert service.get("/some/file", {}) is None

    def test_set_and_get_cache(self, temp_cache_dir, sample_file):
        """캐시 저장 및 조회"""
        service = CacheService(cache_dir=temp_cache_dir)

        entries = [{"type": "dialogue", "name": "테스트", "content": "내용"}]
        characters = ["테스트"]
        config = {"parsing": {"name_max_length": 50}}

        # 캐시 저장
        result = service.set(sample_file, config, entries, characters)
        assert result is True

        # 캐시 조회
        cached = service.get(sample_file, config)
        assert cached is not None
        assert cached[0] == entries
        assert cached[1] == characters

    def test_cache_miss_on_modified_file(self, temp_cache_dir, sample_file):
        """파일 수정 시 캐시 미스"""
        service = CacheService(cache_dir=temp_cache_dir)

        entries = [{"type": "dialogue", "name": "테스트", "content": "내용"}]
        config = {}

        # 캐시 저장
        service.set(sample_file, config, entries, [])

        # 파일 수정
        time.sleep(0.1)  # 수정 시간 차이를 위해
        with open(sample_file, "a", encoding="utf-8") as f:
            f.write("\n추가 내용")

        # 캐시 미스
        cached = service.get(sample_file, config)
        assert cached is None

    def test_cache_miss_on_different_config(self, temp_cache_dir, sample_file):
        """설정 변경 시 캐시 미스"""
        service = CacheService(cache_dir=temp_cache_dir)

        entries = [{"type": "dialogue", "name": "테스트", "content": "내용"}]
        config1 = {"parsing": {"name_max_length": 50}}
        config2 = {"parsing": {"name_max_length": 100}}

        # config1으로 캐시 저장
        service.set(sample_file, config1, entries, [])

        # config2로 조회 시 미스
        cached = service.get(sample_file, config2)
        assert cached is None

        # config1으로 조회 시 히트
        cached = service.get(sample_file, config1)
        assert cached is not None

    def test_memory_cache(self, temp_cache_dir, sample_file):
        """메모리 캐시 작동 확인"""
        service = CacheService(cache_dir=temp_cache_dir)

        entries = [{"type": "dialogue", "name": "테스트", "content": "내용"}]
        config = {}

        service.set(sample_file, config, entries, [])

        # 디스크 캐시 삭제
        for f in Path(temp_cache_dir).glob("*.json"):
            f.unlink()

        # 메모리 캐시에서 조회
        cached = service.get(sample_file, config)
        assert cached is not None

    def test_invalidate_cache(self, temp_cache_dir, sample_file):
        """특정 파일 캐시 무효화"""
        service = CacheService(cache_dir=temp_cache_dir)

        entries = [{"type": "dialogue", "name": "테스트", "content": "내용"}]
        config = {}

        service.set(sample_file, config, entries, [])
        assert service.get(sample_file, config) is not None

        service.invalidate(sample_file)
        assert service.get(sample_file, config) is None

    def test_clear_cache(self, temp_cache_dir, sample_file):
        """전체 캐시 삭제"""
        service = CacheService(cache_dir=temp_cache_dir)

        entries = []
        config = {}

        service.set(sample_file, config, entries, [])
        service.clear()

        assert service.get(sample_file, config) is None
        assert len(list(Path(temp_cache_dir).glob("*.json"))) == 0

    def test_cleanup_old_cache(self, temp_cache_dir):
        """오래된 캐시 정리"""
        import os

        service = CacheService(
            cache_dir=temp_cache_dir,
            max_age_days=0,  # 즉시 만료
        )

        # 수동으로 오래된 캐시 파일 생성
        old_cache = Path(temp_cache_dir) / "old_cache.json"
        with open(old_cache, "w", encoding="utf-8") as f:
            json.dump({"cached_at": 0}, f)

        # 파일 수정 시간을 과거로 설정 (1일 전)
        old_time = time.time() - (2 * 24 * 60 * 60)  # 2일 전
        os.utime(old_cache, (old_time, old_time))

        # 정리 실행
        deleted = service.cleanup()
        assert deleted >= 1
        assert not old_cache.exists()

    def test_get_stats(self, temp_cache_dir, sample_file):
        """캐시 통계 조회"""
        service = CacheService(cache_dir=temp_cache_dir)

        service.set(sample_file, {}, [], [])

        stats = service.get_stats()

        assert stats["enabled"] is True
        assert stats["file_count"] >= 1
        assert stats["memory_count"] >= 1
        assert "total_size_mb" in stats

    def test_cache_nonexistent_file(self, temp_cache_dir):
        """존재하지 않는 파일에 대한 캐시 조회"""
        service = CacheService(cache_dir=temp_cache_dir)

        result = service.get("/nonexistent/file.txt", {})
        assert result is None

    def test_enabled_property(self, temp_cache_dir):
        """enabled 속성 getter/setter"""
        service = CacheService(cache_dir=temp_cache_dir, enabled=False)

        assert service.enabled is False

        service.enabled = True
        assert service.enabled is True


class TestCacheServiceIntegration:
    """CacheService 통합 테스트"""

    def test_multiple_files_caching(self, temp_cache_dir):
        """여러 파일 캐싱"""
        service = CacheService(cache_dir=temp_cache_dir)

        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
                encoding="utf-8",
            ) as f:
                f.write(f"파일 {i} 내용")
                files.append(f.name)

        try:
            config = {}
            for i, file_path in enumerate(files):
                entries = [{"id": i}]
                service.set(file_path, config, entries, [])

            for i, file_path in enumerate(files):
                cached = service.get(file_path, config)
                assert cached is not None
                assert cached[0][0]["id"] == i

        finally:
            for f in files:
                if os.path.exists(f):
                    os.unlink(f)

    def test_concurrent_access(self, temp_cache_dir, sample_file):
        """동시 접근 테스트 (스레드 안전성)"""
        import threading

        service = CacheService(cache_dir=temp_cache_dir)
        config = {}
        results = []

        def set_cache():
            entries = [{"thread": threading.current_thread().name}]
            service.set(sample_file, config, entries, [])
            results.append("set")

        def get_cache():
            service.get(sample_file, config)
            results.append("get")

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=set_cache))
            threads.append(threading.Thread(target=get_cache))

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 예외 없이 완료되어야 함
        assert len(results) == 10
