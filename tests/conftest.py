#!/usr/bin/env python3
"""
Pytest 설정 및 공통 fixture
"""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root():
    """프로젝트 루트 경로"""
    return PROJECT_ROOT


@pytest.fixture
def temp_dir():
    """임시 디렉토리 (테스트 후 자동 정리)"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_config():
    """샘플 설정"""
    return {
        "paths": {
            "input_dir": "./input",
            "output_dir": "./export",
            "fonts_dir": "./fonts",
            "images_dir": "./images",
        },
        "output_format": "both",
        "log_source": "auto",
        "cover": {
            "include": True,
            "title_on_cover": True,
            "author_on_cover": True,
        },
        "toc": {"include": True, "title": "목차"},
        "style": {
            "narration_prefix": "＿",
            "scene_marker": "■",
        },
        "narration": {"users": ["GM", "KP", "DM"]},
        "content": {"include_dice": True, "include_system": True, "include_effects": True},
        "dialogue": {"merge_consecutive": False, "merge_separator": "\n", "merge_max": 5},
        "chapter": {
            "split_mode": "scene",
            "scene_patterns": ["^■", "^씬\\s*\\d+"],
            "entries_per_chapter": 300,
            "min_scene_entries": 10,
            "title_format": "장면 {n}",
            "extract_scene_title": True,
        },
        "parsing": {"name_max_length": 50, "skip_channels": [], "normalize_punctuation": True},
    }


@pytest.fixture
def sample_entries():
    """샘플 엔트리"""
    return [
        {
            "type": "system",
            "name": "",
            "content": "■ 장면 1: 시작",
            "raw": "■ 장면 1: 시작",
            "image": None,
        },
        {
            "type": "dialogue",
            "name": "홍길동",
            "content": "안녕하세요",
            "raw": "홍길동: 안녕하세요",
            "image": None,
        },
        {
            "type": "narration",
            "name": "GM",
            "content": "모험이 시작됩니다",
            "raw": "GM: 모험이 시작됩니다",
            "image": None,
        },
        {
            "type": "dice",
            "name": "홍길동",
            "content": "1D20 → 15 성공",
            "raw": "홍길동: 1D20 → 15 성공",
            "image": None,
        },
        {
            "type": "dialogue",
            "name": "김철수",
            "content": "반가워요",
            "raw": "김철수: 반가워요",
            "image": None,
        },
    ]


@pytest.fixture
def sample_html_cocofolia():
    """코코포리아 스타일 샘플 HTML"""
    return """
<!DOCTYPE html>
<html>
<head><title>코코포리아 로그</title></head>
<body>
<div class="log">
    <p><span class="firing_name_홍길동 firing_firing">: 안녕하세요</span></p>
    <p><span class="firing_name_GM firing_firing">: 모험이 시작됩니다</span></p>
    <p><span class="firing_name_홍길동 firing_firing">: CCB<=65 → 35 성공</span></p>
    <p><span class="firing_name_김철수 firing_firing">: 반가워요</span></p>
</div>
</body>
</html>
"""


@pytest.fixture
def sample_html_roll20():
    """Roll20 스타일 샘플 HTML"""
    return """
<!DOCTYPE html>
<html>
<head><title>Roll20 Chat Log</title></head>
<body>
<div id="textchat">
    <div class="message general">
        <span class="by">Player1:</span> 안녕하세요
    </div>
    <div class="message general">
        <span class="by">GM:</span> 모험이 시작됩니다
    </div>
    <div class="message general rollresult">
        <span class="by">Player1:</span> Rolling 1d20 = 15
    </div>
    <div class="message desc">
        갑자기 어둠이 밀려온다
    </div>
</div>
</body>
</html>
"""


@pytest.fixture
def config_manager(temp_dir, sample_config):
    """ConfigManager 인스턴스"""
    from core.config_manager import ConfigManager

    # 필요한 디렉토리 생성
    (temp_dir / "data").mkdir(exist_ok=True)

    manager = ConfigManager(temp_dir)
    return manager
