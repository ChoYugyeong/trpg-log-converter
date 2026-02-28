#!/usr/bin/env python3
"""
변환 엔진 테스트
"""

import pytest
import os
from pathlib import Path

from core.engine import (
    parse_log, filter_entries, merge_consecutive_dialogues,
    split_into_scenes, is_dice_roll, is_narration_user,
    smart_split_name_content, normalize_punctuation
)


class TestParsing:
    """파싱 테스트"""

    def test_smart_split_name_content_basic(self):
        """기본 이름:내용 분리"""
        name, content = smart_split_name_content("홍길동: 안녕하세요")
        assert name == "홍길동"
        assert content == "안녕하세요"

    def test_smart_split_name_content_with_space(self):
        """공백 있는 이름:내용 분리"""
        name, content = smart_split_name_content("홍길동 : 안녕하세요")
        assert name == "홍길동"
        assert content == "안녕하세요"

    def test_smart_split_name_content_no_colon(self):
        """콜론 없는 경우"""
        name, content = smart_split_name_content("안녕하세요")
        assert name is None
        assert content == "안녕하세요"

    def test_smart_split_name_content_time_format(self):
        """시간 형식 처리"""
        name, content = smart_split_name_content("10:30 회의 시작")
        # 시간 형식은 분리하지 않아야 함
        assert name is None or name != "10"

    def test_normalize_punctuation(self):
        """문장부호 정규화"""
        result = normalize_punctuation("잠시만...")
        assert result == "잠시만……"

        result = normalize_punctuation("정말....인가?")
        assert result == "정말……인가?"


class TestDiceRoll:
    """주사위 굴림 감지 테스트"""

    def test_cocofolia_style(self):
        """코코포리아 스타일"""
        assert is_dice_roll("CCB<=65 → 35 성공") is True
        assert is_dice_roll("1D100<=50 → 42 성공") is True

    def test_roll20_style(self):
        """Roll20 스타일"""
        assert is_dice_roll("/roll 2d6+3") is True
        assert is_dice_roll("Rolling 1d20") is True

    def test_attack_roll(self):
        """공격 굴림"""
        assert is_dice_roll("Attack: 1d20+5 vs AC 15") is True
        assert is_dice_roll("Damage: 2d6+3") is True

    def test_normal_text(self):
        """일반 텍스트"""
        assert is_dice_roll("안녕하세요") is False
        assert is_dice_roll("오늘 날씨가 좋네요") is False


class TestNarration:
    """나레이션 감지 테스트"""

    def test_gm_narration(self):
        """GM 나레이션"""
        config = {'narration': {'users': ['GM', 'KP', 'DM']}}
        assert is_narration_user("GM", config) is True
        assert is_narration_user("gm", config) is True
        assert is_narration_user("KP", config) is True

    def test_not_narration(self):
        """일반 사용자"""
        config = {'narration': {'users': ['GM', 'KP', 'DM']}}
        assert is_narration_user("홍길동", config) is False
        assert is_narration_user("Player1", config) is False


class TestFiltering:
    """필터링 테스트"""

    def test_filter_dice(self):
        """주사위 필터링"""
        entries = [
            {'type': 'dialogue', 'content': '안녕'},
            {'type': 'dice', 'content': '1d20=15'},
            {'type': 'dialogue', 'content': '반가워'},
        ]
        config = {'content': {'include_dice': False, 'include_system': True, 'include_effects': True}}
        result = filter_entries(entries, config)
        assert len(result) == 2
        assert all(e['type'] != 'dice' for e in result)

    def test_filter_system(self):
        """시스템 메시지 필터링"""
        entries = [
            {'type': 'dialogue', 'content': '안녕'},
            {'type': 'system', 'content': '세션 시작'},
            {'type': 'dialogue', 'content': '반가워'},
        ]
        config = {
            'content': {'include_dice': True, 'include_system': False, 'include_effects': True},
            'chapter': {'scene_patterns': []}
        }
        result = filter_entries(entries, config)
        assert len(result) == 2


class TestMerge:
    """대사 병합 테스트"""

    def test_merge_consecutive(self):
        """연속 대사 병합"""
        entries = [
            {'type': 'dialogue', 'name': '홍길동', 'content': '안녕'},
            {'type': 'dialogue', 'name': '홍길동', 'content': '반가워'},
            {'type': 'dialogue', 'name': '김철수', 'content': '나도 반가워'},
        ]
        config = {
            'dialogue': {
                'merge_consecutive': True,
                'merge_separator': '\n',
                'merge_max': 5
            }
        }
        result = merge_consecutive_dialogues(entries, config)
        assert len(result) == 2
        assert '안녕\n반가워' in result[0]['content']

    def test_no_merge(self):
        """병합 비활성화"""
        entries = [
            {'type': 'dialogue', 'name': '홍길동', 'content': '안녕'},
            {'type': 'dialogue', 'name': '홍길동', 'content': '반가워'},
        ]
        config = {'dialogue': {'merge_consecutive': False}}
        result = merge_consecutive_dialogues(entries, config)
        assert len(result) == 2


class TestSceneSplit:
    """장면 분할 테스트"""

    def test_split_by_marker(self):
        """마커로 장면 분할"""
        entries = [
            {'type': 'system', 'content': '■ 장면 1'},
            {'type': 'dialogue', 'name': '홍길동', 'content': '안녕'},
            {'type': 'system', 'content': '■ 장면 2'},
            {'type': 'dialogue', 'name': '김철수', 'content': '반가워'},
        ]
        config = {
            'chapter': {
                'split_mode': 'scene',
                'scene_patterns': ['^■'],
                'min_scene_entries': 1,
                'title_format': '장면 {n}',
                'extract_scene_title': True
            }
        }
        scenes = split_into_scenes(entries, config)
        assert len(scenes) >= 2

    def test_split_by_count(self):
        """개수로 장면 분할"""
        entries = [{'type': 'dialogue', 'content': f'대사 {i}'} for i in range(10)]
        config = {
            'chapter': {
                'split_mode': 'count',
                'entries_per_chapter': 3,
                'title_format': '장면 {n}'
            }
        }
        scenes = split_into_scenes(entries, config)
        assert len(scenes) == 4  # 10 / 3 = 3.33 -> 4 장면

    def test_no_split(self):
        """분할 없음"""
        entries = [{'type': 'dialogue', 'content': '안녕'}]
        config = {'chapter': {'split_mode': 'none'}}
        scenes = split_into_scenes(entries, config)
        assert len(scenes) == 1


class TestHTMLParsing:
    """HTML 파싱 테스트"""

    def test_parse_cocofolia_html(self):
        """코코포리아 HTML 파싱"""
        html = '''
        <html><body>
        <p><span class="firing_name_홍길동 firing_firing">: 안녕하세요</span></p>
        <p><span class="firing_name_GM firing_firing">: 장면 시작입니다</span></p>
        </body></html>
        '''
        config = {
            'parsing': {'name_max_length': 50, 'skip_channels': [], 'normalize_punctuation': True},
            'scene_detection': {'patterns': []},
            'chapter': {'scene_patterns': ['^■']},
            'narration': {'users': ['GM']}
        }
        entries = parse_log(html, config)
        assert len(entries) >= 2

    def test_parse_roll20_html(self):
        """Roll20 HTML 파싱"""
        html = '''
        <html><body>
        <div id="textchat">
            <div class="message general">
                <span class="by">Player1:</span> 안녕하세요
            </div>
            <div class="message general">
                <span class="by">GM:</span> 장면 시작입니다
            </div>
        </div>
        </body></html>
        '''
        config = {
            'parsing': {'name_max_length': 50, 'skip_channels': [], 'normalize_punctuation': True},
            'chapter': {'scene_patterns': ['^■']},
            'narration': {'users': ['GM']}
        }
        entries = parse_log(html, config)
        assert len(entries) >= 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
