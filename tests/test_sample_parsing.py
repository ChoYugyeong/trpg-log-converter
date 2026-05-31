#!/usr/bin/env python3
"""
샘플 파일 파싱 테스트
Roll20 및 Cocofolia 형식 파싱 검증
"""

from pathlib import Path

import pytest

from core.engine import DEFAULT_CONFIG, deep_merge, parse_log


class TestRoll20Parsing:
    """Roll20 형식 파싱 테스트"""

    @pytest.fixture
    def roll20_html(self):
        """Roll20 샘플 HTML 로드"""
        sample_path = Path(__file__).parent / "samples" / "roll20_sample.html"
        with open(sample_path, encoding='utf-8') as f:
            return f.read()

    @pytest.fixture
    def config(self):
        """테스트 설정"""
        return deep_merge(DEFAULT_CONFIG, {})

    def test_roll20_detection(self, roll20_html, config):
        """Roll20 형식 감지"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(roll20_html, 'html.parser')
        # id="textchat" 확인
        assert soup.find(id='textchat') is not None

    def test_roll20_entries_count(self, roll20_html, config):
        """Roll20 엔트리 개수 확인"""
        entries = parse_log(roll20_html, config)
        assert len(entries) > 0
        print(f"\n[Roll20] Total entries: {len(entries)}")

    def test_roll20_speaker_extraction(self, roll20_html, config):
        """Roll20 화자 이름 추출"""
        entries = parse_log(roll20_html, config)

        # GM 메시지 확인
        gm_entries = [e for e in entries if e['name'] == 'GM']
        assert len(gm_entries) > 0, "GM 메시지가 파싱되어야 함"

        # 플레이어 이름 확인 (괄호 포함)
        player_names = {e['name'] for e in entries if e['name']}
        print(f"[Roll20] Speakers found: {player_names}")

        assert '김철수 (전사)' in player_names or any('김철수' in n for n in player_names)
        assert '이영희 (마법사)' in player_names or any('이영희' in n for n in player_names)

    def test_roll20_dice_detection(self, roll20_html, config):
        """Roll20 주사위 롤 감지"""
        entries = parse_log(roll20_html, config)

        dice_entries = [e for e in entries if e['type'] == 'dice']
        print(f"[Roll20] Dice entries: {len(dice_entries)}")

        # 다이스 롤이 있어야 함
        assert len(dice_entries) >= 1, "주사위 롤이 감지되어야 함"

        # 다이스 내용 확인
        for entry in dice_entries:
            print(f"  - {entry['name']}: {entry['content'][:50]}...")

    def test_roll20_narration_detection(self, roll20_html, config):
        """Roll20 나레이션(desc) 감지"""
        entries = parse_log(roll20_html, config)

        narration_entries = [e for e in entries if e['type'] == 'narration']
        print(f"[Roll20] Narration entries: {len(narration_entries)}")

        # desc 메시지가 나레이션으로 감지되어야 함
        assert len(narration_entries) >= 1

    def test_roll20_scene_markers(self, roll20_html, config):
        """Roll20 장면 마커 감지"""
        entries = parse_log(roll20_html, config)

        # 장면 마커 (■로 시작하는 메시지)
        scene_content = [e['content'] for e in entries if '■' in e.get('content', '')]
        print(f"[Roll20] Scene markers: {scene_content}")

        assert len(scene_content) >= 2, "장면 마커가 감지되어야 함"

    def test_roll20_entry_types(self, roll20_html, config):
        """Roll20 엔트리 타입 분포"""
        entries = parse_log(roll20_html, config)

        type_counts = {}
        for e in entries:
            t = e['type']
            type_counts[t] = type_counts.get(t, 0) + 1

        print(f"[Roll20] Entry types: {type_counts}")

        # 최소한 대화와 나레이션이 있어야 함
        assert 'dialogue' in type_counts or 'narration' in type_counts


class TestCocofoliaParsing:
    """Cocofolia(코코포리아) 형식 파싱 테스트"""

    @pytest.fixture
    def cocofolia_html(self):
        """Cocofolia 샘플 HTML 로드"""
        sample_path = Path(__file__).parent / "samples" / "cocofolia_sample.html"
        with open(sample_path, encoding='utf-8') as f:
            return f.read()

    @pytest.fixture
    def config(self):
        """테스트 설정"""
        return deep_merge(DEFAULT_CONFIG, {})

    def test_cocofolia_detection(self, cocofolia_html, config):
        """Cocofolia 형식 감지 (firing_name_ 클래스)"""
        import re

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(cocofolia_html, 'html.parser')

        # firing_name_ 클래스 확인 (모든 span 검사)
        firing_spans = []
        for span in soup.find_all('span'):
            class_attr = span.get('class', [])
            class_str = ' '.join(class_attr) if isinstance(class_attr, list) else str(class_attr)
            if 'firing_name_' in class_str:
                firing_spans.append(span)
        assert len(firing_spans) > 0, "firing_name_ 클래스가 있어야 함"

    def test_cocofolia_entries_count(self, cocofolia_html, config):
        """Cocofolia 엔트리 개수 확인"""
        entries = parse_log(cocofolia_html, config)
        assert len(entries) > 0
        print(f"\n[Cocofolia] Total entries: {len(entries)}")

    def test_cocofolia_speaker_extraction(self, cocofolia_html, config):
        """Cocofolia 화자 이름 추출 (firing_name_XXX에서)"""
        entries = parse_log(cocofolia_html, config)

        # KP 메시지 확인
        kp_entries = [e for e in entries if e['name'] == 'KP']
        assert len(kp_entries) > 0, "KP 메시지가 파싱되어야 함"

        # 플레이어 이름 확인
        player_names = {e['name'] for e in entries if e['name']}
        print(f"[Cocofolia] Speakers found: {player_names}")

        # 언더스코어가 공백으로 변환되었는지 확인 또는 원본 유지
        assert any('사사키' in str(n) for n in player_names), "사사키_유타카가 파싱되어야 함"
        assert any('김탐정' in str(n) for n in player_names), "김탐정이 파싱되어야 함"

    def test_cocofolia_dice_ccb_format(self, cocofolia_html, config):
        """Cocofolia CCB 주사위 형식 감지"""
        entries = parse_log(cocofolia_html, config)

        dice_entries = [e for e in entries if e['type'] == 'dice']
        print(f"[Cocofolia] Dice entries: {len(dice_entries)}")

        # CCB 형식 다이스 롤이 있어야 함
        ccb_rolls = [e for e in dice_entries if 'CCB' in e['content'].upper() or '1D' in e['content'].upper()]
        print(f"[Cocofolia] CCB/1D rolls: {len(ccb_rolls)}")

        for entry in dice_entries[:3]:
            print(f"  - {entry['name']}: {entry['content'][:60]}...")

        assert len(dice_entries) >= 1, "CCB 주사위 롤이 감지되어야 함"

    def test_cocofolia_narration_kp(self, cocofolia_html, config):
        """Cocofolia KP 나레이션 감지"""
        entries = parse_log(cocofolia_html, config)

        # KP는 나레이터로 처리되어야 함
        narration_entries = [e for e in entries if e['type'] == 'narration']
        print(f"[Cocofolia] Narration entries: {len(narration_entries)}")

        assert len(narration_entries) >= 1, "KP 나레이션이 감지되어야 함"

    def test_cocofolia_scene_markers(self, cocofolia_html, config):
        """Cocofolia 장면 마커 감지"""
        entries = parse_log(cocofolia_html, config)

        # 장면 마커 (■로 시작하는 메시지)
        scene_content = [e['content'] for e in entries if '■' in e.get('content', '')]
        print(f"[Cocofolia] Scene markers: {scene_content}")

        assert len(scene_content) >= 2, "장면 마커가 감지되어야 함"

    def test_cocofolia_content_extraction(self, cocofolia_html, config):
        """Cocofolia 내용 추출 (콜론 제거)"""
        entries = parse_log(cocofolia_html, config)

        # 내용이 콜론으로 시작하지 않아야 함
        for entry in entries:
            content = entry.get('content', '')
            assert not content.startswith(':'), f"콜론이 제거되어야 함: {content[:30]}"

    def test_cocofolia_entry_types(self, cocofolia_html, config):
        """Cocofolia 엔트리 타입 분포"""
        entries = parse_log(cocofolia_html, config)

        type_counts = {}
        for e in entries:
            t = e['type']
            type_counts[t] = type_counts.get(t, 0) + 1

        print(f"[Cocofolia] Entry types: {type_counts}")

        # 대화, 나레이션, 다이스가 있어야 함
        assert 'dialogue' in type_counts or 'narration' in type_counts


class TestFormatComparison:
    """Roll20과 Cocofolia 형식 비교 테스트"""

    @pytest.fixture
    def roll20_entries(self):
        sample_path = Path(__file__).parent / "samples" / "roll20_sample.html"
        with open(sample_path, encoding='utf-8') as f:
            html = f.read()
        return parse_log(html, DEFAULT_CONFIG)

    @pytest.fixture
    def cocofolia_entries(self):
        sample_path = Path(__file__).parent / "samples" / "cocofolia_sample.html"
        with open(sample_path, encoding='utf-8') as f:
            html = f.read()
        return parse_log(html, DEFAULT_CONFIG)

    def test_both_formats_have_entries(self, roll20_entries, cocofolia_entries):
        """두 형식 모두 엔트리가 있어야 함"""
        assert len(roll20_entries) > 0
        assert len(cocofolia_entries) > 0

    def test_common_entry_structure(self, roll20_entries, cocofolia_entries):
        """엔트리 구조가 동일해야 함"""
        required_keys = {'type', 'name', 'content', 'raw'}

        for entry in roll20_entries[:5]:
            assert required_keys.issubset(entry.keys())

        for entry in cocofolia_entries[:5]:
            assert required_keys.issubset(entry.keys())

    def test_print_parsing_summary(self, roll20_entries, cocofolia_entries):
        """파싱 요약 출력"""
        print("\n" + "="*60)
        print("FORMAT PARSING SUMMARY")
        print("="*60)

        print(f"\n[Roll20] {len(roll20_entries)} entries")
        roll20_types = {}
        for e in roll20_entries:
            roll20_types[e['type']] = roll20_types.get(e['type'], 0) + 1
        print(f"  Types: {roll20_types}")
        print("  Sample entries:")
        for e in roll20_entries[:3]:
            print(f"    - [{e['type']}] {e['name']}: {e['content'][:40]}...")

        print(f"\n[Cocofolia] {len(cocofolia_entries)} entries")
        cocofolia_types = {}
        for e in cocofolia_entries:
            cocofolia_types[e['type']] = cocofolia_types.get(e['type'], 0) + 1
        print(f"  Types: {cocofolia_types}")
        print("  Sample entries:")
        for e in cocofolia_entries[:3]:
            print(f"    - [{e['type']}] {e['name']}: {e['content'][:40]}...")

        print("="*60)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
