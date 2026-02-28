"""
플랫폼별 프리셋 서비스
코코포리아, Roll20 등 플랫폼별 최적화 설정
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class Preset:
    """프리셋 데이터 클래스"""
    name: str
    display_name: str
    description: str
    platform: str
    config: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


class PresetService:
    """플랫폼별 프리셋 관리 서비스"""

    # 내장 프리셋 정의
    BUILTIN_PRESETS: Dict[str, Preset] = {
        # ============ 코코포리아 (Cocofolia) 프리셋 ============
        "ccfolia_default": Preset(
            name="ccfolia_default",
            display_name="코코포리아 기본",
            description="코코포리아 HTML 로그 기본 변환 (CoC/Insane 등)",
            platform="ccfolia",
            config={
                "log_source": "ccfolia",
                "parsing": {
                    "name_max_length": 30,
                    # 코코포리아 HTML 구조: .tab 내 .player / .player b (이름)
                    "html_selectors": {
                        "entry": ".tab",
                        "player": ".player",
                        "name": ".player b",
                        "dice": ".diceroll",
                        "tabs": ["メイン", "main", "情報", "info", "雑談", "other", "메인", "정보", "잡담"]
                    },
                    "skip_channels": ["雑談", "other", "잡담"],  # OOC 채널 제외
                    "normalize_punctuation": True,
                },
                "narration": {
                    "users": ["GM", "KP", "Keeper", "시스템", "ナレーター", "진행자"],
                    "style": "indent",
                },
                "style": {
                    "narration_prefix": "＿",
                    "scene_marker": "■",
                    "dialogue_margin": 0.12,
                    "narration_margin": 0.8,
                    "dialogue_bracket": "「」",  # 일본식 꺾쇠
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [r"^■", r"^씬\s*\d+", r"^장면\s*\d+", r"^シーン\s*\d+"],
                    "extract_scene_title": True,
                },
                "content": {
                    "include_dice": True,
                    "include_system": True,
                    "include_effects": True,  # SE, BGM 태그 포함
                },
            },
            tags=["korean", "japanese", "trpg", "ccfolia", "coc"],
        ),

        "ccfolia_coc": Preset(
            name="ccfolia_coc",
            display_name="코코포리아 CoC",
            description="크툴루의 부름 (CoC) 세션용 최적화",
            platform="ccfolia",
            config={
                "log_source": "ccfolia",
                "parsing": {
                    "name_max_length": 30,
                    "skip_channels": ["雑談", "other", "잡담", "ooc"],
                    "normalize_punctuation": True,
                },
                "narration": {
                    "users": ["KP", "Keeper", "キーパー", "GM", "시스템"],
                    "style": "indent",
                },
                "style": {
                    "narration_prefix": "＿",
                    "scene_marker": "■",
                    "dice_color": "#4A7C59",  # 산악색 (CoC 테마)
                    "dialogue_bracket": "「」",
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [r"^■", r"^導入", r"^본편", r"^엔딩", r"^ED", r"^OP"],
                    "title_format": "장면 {n}",
                },
                "content": {
                    "include_dice": True,  # CCB, 1D100 등 결과
                    "include_system": True,
                    "include_effects": True,
                },
            },
            tags=["korean", "japanese", "coc", "ccfolia", "horror"],
        ),

        "ccfolia_novel": Preset(
            name="ccfolia_novel",
            display_name="코코포리아 소설풍",
            description="대사를 소설 형식으로 변환 (이름: 대사 → 이름이 말했다)",
            platform="ccfolia",
            config={
                "log_source": "ccfolia",
                "style": {
                    "narration_prefix": "",
                    "scene_marker": "◆",
                    "dialogue_margin": 0.0,
                    "narration_margin": 0.5,
                    "narration_indent": 2.0,
                    "dialogue_format": "novel",  # 소설체
                    "dialogue_bracket": '""',  # 서양식 따옴표
                },
                "narration": {
                    "users": ["GM", "KP", "Keeper", "키퍼"],
                    "style": "paragraph",
                },
                "dialogue": {
                    "merge_consecutive": True,
                    "merge_separator": "\n",
                    "merge_max": 3,
                },
                "chapter": {
                    "split_mode": "scene",
                    "title_format": "제 {n} 장",
                },
            },
            tags=["korean", "trpg", "novel", "ccfolia"],
        ),

        "ccfolia_minimal": Preset(
            name="ccfolia_minimal",
            display_name="코코포리아 미니멀",
            description="다이스/시스템 메시지 제외, 순수 대사만",
            platform="ccfolia",
            config={
                "log_source": "ccfolia",
                "parsing": {
                    "skip_channels": ["雑談", "other", "잡담", "情報", "info", "정보"],
                },
                "content": {
                    "include_dice": False,
                    "include_system": False,
                    "include_effects": False,
                },
                "chapter": {
                    "split_mode": "count",
                    "entries_per_chapter": 200,
                },
            },
            tags=["korean", "minimal", "ccfolia"],
        ),

        "ccfolia_insane": Preset(
            name="ccfolia_insane",
            display_name="코코포리아 인세인",
            description="인세인 (Insane) 세션용 - 2D6 판정, 공포 판정, 광기 카드",
            platform="ccfolia",
            config={
                "log_source": "ccfolia",
                "parsing": {
                    "name_max_length": 30,
                    "skip_channels": ["雑談", "other", "잡담", "ooc"],
                    "normalize_punctuation": True,
                    "dice_patterns": [
                        r"2D6",           # 기본 판정
                        r"\d+D6",         # 변형 판정
                        r"ST判定",        # 공포 판정 (일본어)
                        r"공포\s*판정",   # 공포 판정 (한국어)
                    ],
                },
                "narration": {
                    "users": ["GM", "KP", "キーパー", "Keeper", "시스템", "진행자", "ナレーター"],
                    "style": "indent",
                },
                "style": {
                    "narration_prefix": "＿",
                    "scene_marker": "■",
                    "dice_color": "#8B0000",  # 다크레드 (호러 테마)
                    "dialogue_bracket": "「」",
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [
                        r"^■", r"^씬\s*\d+", r"^シーン\s*\d+",
                        r"^장면\s*\d+", r"^사이클\s*\d+", r"^サイクル\s*\d+",
                        r"^클라이맥스", r"^クライマックス",
                        r"^도입", r"^導入", r"^엔딩", r"^エンディング",
                    ],
                    "extract_scene_title": True,
                    "title_format": "씬 {n}",
                },
                "content": {
                    "include_dice": True,
                    "include_system": True,
                    "include_effects": True,
                },
            },
            tags=["korean", "japanese", "insane", "ccfolia", "horror", "2d6"],
        ),

        "ccfolia_dx3": Preset(
            name="ccfolia_dx3",
            display_name="코코포리아 더블크로스",
            description="더블크로스 The 3rd Edition - xDX 다이스풀, 이펙트, 침식률",
            platform="ccfolia",
            config={
                "log_source": "ccfolia",
                "parsing": {
                    "name_max_length": 30,
                    "skip_channels": ["雑談", "other", "잡담", "ooc"],
                    "normalize_punctuation": True,
                    "dice_patterns": [
                        r"\d+DX",          # DX 다이스풀 (10면체)
                        r"\d+D10",         # 10면체 판정
                        r"C\(\d+\)",       # 크리티컬 값
                        r"侵蝕率",         # 침식률 (일본어)
                        r"침식률",         # 침식률 (한국어)
                    ],
                },
                "narration": {
                    "users": ["GM", "マスター", "Master", "시스템", "진행자"],
                    "style": "indent",
                },
                "style": {
                    "narration_prefix": "＿",
                    "scene_marker": "■",
                    "dice_color": "#FF4500",  # 오렌지레드 (DX 테마)
                    "dialogue_bracket": "「」",
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [
                        r"^■", r"^씬\s*\d+", r"^シーン\s*\d+",
                        r"^오프닝", r"^オープニング", r"^OP",
                        r"^미들", r"^ミドル", r"^MD",
                        r"^클라이맥스", r"^クライマックス", r"^CL",
                        r"^엔딩", r"^エンディング", r"^ED",
                    ],
                    "extract_scene_title": True,
                    "title_format": "씬 {n}",
                },
                "content": {
                    "include_dice": True,
                    "include_system": True,
                    "include_effects": True,  # 이펙트/콤보 표시
                },
            },
            tags=["korean", "japanese", "doublecross", "dx3", "ccfolia", "superhero"],
        ),

        # ============ Roll20 프리셋 ============
        "roll20_default": Preset(
            name="roll20_default",
            display_name="Roll20 기본",
            description="Roll20 Chat Archive HTML 기본 변환",
            platform="roll20",
            config={
                "log_source": "roll20",
                "parsing": {
                    "name_max_length": 40,
                    # Roll20 HTML 구조: div 기반, CSS 스타일 포함
                    "html_selectors": {
                        "entry": "div.message",
                        "avatar": "div.avatar",
                        "content": "div.content",
                        "timestamp": "span.tstamp"
                    },
                    "skip_channels": [],
                    "include_whisper": False,  # 귓속말 기본 제외
                    "normalize_punctuation": True,
                    "session_gap_minutes": 60,  # 60분 이상 간격 = 새 세션
                },
                "narration": {
                    "users": ["GM", "DM", "Dungeon Master", "Game Master", "Narrator"],
                    "style": "indent",
                },
                "style": {
                    "narration_prefix": "",
                    "scene_marker": "---",
                    "dice_color": "#5865F2",  # Roll20 블루
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [r"^---", r"^###", r"^Scene\s*\d+", r"^\*\*\*"],
                },
                "content": {
                    "include_dice": True,
                    "include_system": True,
                    "include_effects": True,
                    "include_roll_templates": True,  # Roll20 롤 템플릿
                },
            },
            tags=["english", "trpg", "roll20"],
        ),

        "roll20_dnd5e": Preset(
            name="roll20_dnd5e",
            display_name="Roll20 D&D 5e",
            description="D&D 5판 세션용 Roll20 설정",
            platform="roll20",
            config={
                "log_source": "roll20",
                "narration": {
                    "users": ["DM", "Dungeon Master"],
                    "style": "block",
                },
                "style": {
                    "dice_color": "#CC0000",  # D&D 레드
                    "scene_marker": "⚔️",
                    "dialogue_bracket": '""',
                },
                "chapter": {
                    "title_format": "Chapter {n}",
                    "scene_patterns": [r"^Chapter", r"^Session\s*\d+", r"^Long Rest", r"^Short Rest"],
                },
            },
            tags=["english", "dnd", "5e", "roll20"],
        ),

        "roll20_coc": Preset(
            name="roll20_coc",
            display_name="Roll20 크툴루의 부름",
            description="Call of Cthulhu (CoC) 세션용 - d100 판정, 정신력(SAN), 기능 굴림",
            platform="roll20",
            config={
                "log_source": "roll20",
                "parsing": {
                    "name_max_length": 40,
                    "include_whisper": False,
                    "normalize_punctuation": True,
                    "dice_patterns": [
                        r"1[dD]100",        # 퍼센타일 판정
                        r"[dD]100",         # 축약형
                        r"CCB",             # CoC 판정 매크로
                        r"1[dD]20",         # 행운/POW 대항
                        r"SAN\s*체크",      # SAN 체크 (한국어)
                        r"SAN\s*Check",     # SAN Check (영어)
                        r"Sanity",          # Sanity roll
                    ],
                },
                "narration": {
                    "users": ["GM", "Keeper", "KP", "Game Master"],
                    "style": "indent",
                },
                "style": {
                    "narration_prefix": "",
                    "scene_marker": "---",
                    "dice_color": "#2E7D32",  # 다크 그린 (CoC 테마)
                    "dialogue_bracket": '""',
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [
                        r"^---", r"^###",
                        r"^Scene\s*\d+", r"^장면\s*\d+",
                        r"^Introduction", r"^도입",
                        r"^Climax", r"^클라이맥스",
                        r"^Ending", r"^엔딩",
                    ],
                    "title_format": "Scene {n}",
                },
                "content": {
                    "include_dice": True,
                    "include_system": True,
                    "include_effects": True,
                    "include_roll_templates": True,
                },
            },
            tags=["english", "korean", "coc", "roll20", "horror", "d100"],
        ),

        "roll20_insane": Preset(
            name="roll20_insane",
            display_name="Roll20 인세인",
            description="인세인 (Insane) 세션용 Roll20 설정 - 2D6 판정, 공포 판정",
            platform="roll20",
            config={
                "log_source": "roll20",
                "parsing": {
                    "name_max_length": 40,
                    "include_whisper": False,
                    "normalize_punctuation": True,
                    "dice_patterns": [
                        r"2[dD]6",          # 기본 판정
                        r"\d+[dD]6",        # 변형 판정
                        r"ST判定",          # 공포 판정 (일본어)
                        r"공포\s*판정",     # 공포 판정 (한국어)
                        r"Fear\s*Check",    # Fear Check (영어)
                    ],
                },
                "narration": {
                    "users": ["GM", "KP", "Keeper", "Game Master"],
                    "style": "indent",
                },
                "style": {
                    "narration_prefix": "",
                    "scene_marker": "---",
                    "dice_color": "#8B0000",  # 다크레드 (호러 테마)
                    "dialogue_bracket": '""',
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [
                        r"^---", r"^###",
                        r"^Scene\s*\d+", r"^씬\s*\d+", r"^シーン\s*\d+",
                        r"^Cycle\s*\d+", r"^사이클\s*\d+", r"^サイクル\s*\d+",
                        r"^Climax", r"^클라이맥스", r"^クライマックス",
                        r"^Introduction", r"^도입", r"^導入",
                        r"^Ending", r"^엔딩", r"^エンディング",
                    ],
                    "extract_scene_title": True,
                    "title_format": "Scene {n}",
                },
                "content": {
                    "include_dice": True,
                    "include_system": True,
                    "include_effects": True,
                    "include_roll_templates": True,
                },
            },
            tags=["english", "korean", "japanese", "insane", "roll20", "horror", "2d6"],
        ),

        "roll20_pf2e": Preset(
            name="roll20_pf2e",
            display_name="Roll20 Pathfinder 2e",
            description="패스파인더 2판 세션용 설정",
            platform="roll20",
            config={
                "log_source": "roll20",
                "narration": {
                    "users": ["GM", "Game Master"],
                    "style": "indent",
                },
                "style": {
                    "dice_color": "#5D0000",  # PF2e 딥 레드
                    "scene_marker": "◆",
                },
                "chapter": {
                    "title_format": "Encounter {n}",
                    "scene_patterns": [r"^Encounter", r"^Combat", r"^Exploration"],
                },
            },
            tags=["english", "pathfinder", "pf2e", "roll20"],
        ),

        # ============ Discord 프리셋 ============
        "discord_default": Preset(
            name="discord_default",
            display_name="Discord 기본",
            description="Discord 채팅 로그 변환 (Avrae/Tupperbox 지원)",
            platform="discord",
            config={
                "log_source": "discord",
                "parsing": {
                    "name_max_length": 32,  # Discord 닉네임 제한
                    "skip_channels": [],
                    # 봇 메시지 처리
                    "bot_handlers": {
                        "avrae": True,   # Avrae 다이스 봇
                        "tupperbox": True,  # Tupperbox 캐릭터 봇
                    },
                },
                "style": {
                    "dice_color": "#5865F2",  # Discord 블루프플
                },
                "content": {
                    "include_dice": True,
                    "include_system": False,
                    "include_effects": False,
                },
            },
            tags=["discord", "chat", "avrae"],
        ),

        "discord_pbp": Preset(
            name="discord_pbp",
            display_name="Discord PBP (Play-by-Post)",
            description="디스코드 포럼/스레드 기반 PBP 세션용",
            platform="discord",
            config={
                "log_source": "discord",
                "parsing": {
                    "name_max_length": 32,
                },
                "narration": {
                    "users": ["GM", "DM", "Narrator"],
                    "style": "paragraph",
                },
                "style": {
                    "dialogue_bracket": '""',
                    "narration_indent": 1.5,
                },
                "dialogue": {
                    "merge_consecutive": True,
                    "merge_max": 5,
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [r"^---", r"^Scene:", r"^\*\*Scene"],
                },
            },
            tags=["discord", "pbp", "play-by-post"],
        ),

        # ============ 일반 텍스트 프리셋 ============
        "text_simple": Preset(
            name="text_simple",
            display_name="텍스트 기본",
            description="일반 텍스트 파일 변환 (이름: 대사 형식)",
            platform="text",
            config={
                "log_source": "text",
                "parsing": {
                    "name_max_length": 50,
                    "normalize_punctuation": True,
                    # 자동 형식 감지: colon, bracket, paren, tab
                    "auto_detect_format": True,
                },
                "chapter": {
                    "split_mode": "count",
                    "entries_per_chapter": 300,
                },
            },
            tags=["text", "simple"],
        ),

        "text_screenplay": Preset(
            name="text_screenplay",
            display_name="시나리오/대본",
            description="시나리오/대본 형식 텍스트 변환",
            platform="text",
            config={
                "log_source": "text",
                "parsing": {
                    "name_max_length": 30,
                },
                "style": {
                    "dialogue_bracket": "",
                    "dialogue_margin": 1.5,
                    "name_style": "bold_center",  # 이름 중앙정렬 굵게
                },
                "chapter": {
                    "split_mode": "scene",
                    "scene_patterns": [r"^INT\.", r"^EXT\.", r"^S#\d+", r"^장면\s*\d+"],
                },
            },
            tags=["text", "screenplay", "script"],
        ),

        # ============ 출판용 프리셋 ============
        "publish_ebook": Preset(
            name="publish_ebook",
            display_name="전자책 출판용",
            description="전자책(EPUB) 출판용 최적화 설정",
            platform="all",
            config={
                "style": {
                    "dialogue_bracket": '""',
                    "narration_indent": 2.0,
                    "base_font_size": 1.0,
                },
                "chapter": {
                    "split_mode": "scene",
                    "title_format": "제 {n} 장",
                },
                "cover": {
                    "include": True,
                    "title_on_cover": True,
                    "author_on_cover": True,
                },
                "content": {
                    "include_dice": False,
                    "include_system": False,
                    "include_effects": False,
                },
            },
            tags=["publish", "ebook", "epub"],
        ),

        "publish_print": Preset(
            name="publish_print",
            display_name="종이책 출판용",
            description="POD(Print on Demand) 출판용 DOCX 설정",
            platform="all",
            config={
                "page_format": "신국판 (152×225mm)",
                "margins": {
                    "top": "0.8",
                    "bottom": "0.8",
                    "left": "0.7",
                    "right": "0.6",
                },
                "style": {
                    "dialogue_bracket": '""',
                    "base_font_size": 1.0,
                    "body_line_height": "1.8",
                },
                "chapter": {
                    "split_mode": "scene",
                },
                "content": {
                    "include_dice": False,
                    "include_system": False,
                    "include_effects": False,
                },
            },
            tags=["publish", "print", "pod", "docx"],
        ),
    }

    def __init__(self, custom_presets: Optional[Dict[str, Dict]] = None):
        """
        Args:
            custom_presets: 사용자 정의 프리셋 딕셔너리
        """
        self._presets: Dict[str, Preset] = deepcopy(self.BUILTIN_PRESETS)

        if custom_presets:
            for name, config in custom_presets.items():
                self.add_custom_preset(name, config)

    def get_preset(self, name: str) -> Optional[Preset]:
        """프리셋 조회"""
        return self._presets.get(name)

    def get_preset_config(self, name: str) -> Optional[Dict[str, Any]]:
        """프리셋 설정값만 반환"""
        preset = self.get_preset(name)
        return deepcopy(preset.config) if preset else None

    def list_presets(self, platform: Optional[str] = None) -> List[Preset]:
        """
        프리셋 목록 반환

        Args:
            platform: 필터링할 플랫폼 (None이면 전체)
        """
        presets = list(self._presets.values())

        if platform:
            presets = [p for p in presets if p.platform == platform]

        return presets

    def get_platforms(self) -> List[str]:
        """지원 플랫폼 목록"""
        platforms = set(p.platform for p in self._presets.values())
        return sorted(platforms)

    def add_custom_preset(
        self,
        name: str,
        config: Dict[str, Any],
        display_name: Optional[str] = None,
        description: str = "",
        platform: str = "custom",
        tags: Optional[List[str]] = None,
    ) -> None:
        """사용자 정의 프리셋 추가"""
        self._presets[name] = Preset(
            name=name,
            display_name=display_name or name,
            description=description,
            platform=platform,
            config=config,
            tags=tags or ["custom"],
        )

    def remove_preset(self, name: str) -> bool:
        """프리셋 제거 (내장 프리셋은 제거 불가)"""
        if name in self.BUILTIN_PRESETS:
            return False
        if name in self._presets:
            del self._presets[name]
            return True
        return False

    def apply_preset(self, base_config: Dict[str, Any], preset_name: str) -> Dict[str, Any]:
        """
        기본 설정에 프리셋 적용

        Args:
            base_config: 기본 설정 딕셔너리
            preset_name: 적용할 프리셋 이름

        Returns:
            프리셋이 적용된 설정 딕셔너리
        """
        preset = self.get_preset(preset_name)
        if not preset:
            return base_config

        result = deepcopy(base_config)
        self._deep_merge(result, preset.config)
        return result

    def _deep_merge(self, base: dict, override: dict) -> None:
        """딕셔너리 깊은 병합 (in-place)"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = deepcopy(value)

    def export_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """프리셋을 직렬화 가능한 딕셔너리로 내보내기"""
        preset = self.get_preset(name)
        if not preset:
            return None

        return {
            "name": preset.name,
            "display_name": preset.display_name,
            "description": preset.description,
            "platform": preset.platform,
            "config": deepcopy(preset.config),
            "tags": list(preset.tags),
        }

    def import_preset(self, data: Dict[str, Any]) -> bool:
        """직렬화된 프리셋 가져오기"""
        try:
            name = data["name"]
            self.add_custom_preset(
                name=name,
                config=data.get("config", {}),
                display_name=data.get("display_name"),
                description=data.get("description", ""),
                platform=data.get("platform", "custom"),
                tags=data.get("tags"),
            )
            return True
        except (KeyError, TypeError):
            return False
