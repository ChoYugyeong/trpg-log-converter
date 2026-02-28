#!/usr/bin/env python3
"""
설정 프로필 관리
여러 설정을 프로필로 저장/불러오기
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
import copy

logger = logging.getLogger(__name__)


@dataclass
class Profile:
    """설정 프로필"""
    id: str
    name: str
    description: str
    created: str
    modified: str
    settings: Dict
    is_default: bool = False
    is_builtin: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Profile':
        return cls(**data)


# 기본 제공 프로필들
BUILTIN_PROFILES = [
    {
        'id': 'default',
        'name': '기본',
        'description': '기본 설정',
        'settings': {},
        'is_default': True,
        'is_builtin': True,
    },
    {
        'id': 'novel_style',
        'name': '소설 스타일',
        'description': '소설처럼 읽히는 스타일 (나레이션 강조)',
        'settings': {
            'style': {
                'narration_prefix': '　',
                'scene_marker': '◆',
            },
            'dialogue': {
                'merge_consecutive': True,
                'merge_separator': '\n',
            },
            'content': {
                'include_dice': False,
                'include_system': False,
            },
        },
        'is_builtin': True,
    },
    {
        'id': 'replay_style',
        'name': '리플레이 스타일',
        'description': 'TRPG 리플레이 형식 (주사위 포함)',
        'settings': {
            'style': {
                'narration_prefix': '＿',
                'scene_marker': '■',
            },
            'content': {
                'include_dice': True,
                'include_system': True,
                'include_effects': True,
            },
        },
        'is_builtin': True,
    },
    {
        'id': 'minimal',
        'name': '미니멀',
        'description': '대사만 포함 (시스템 메시지 제외)',
        'settings': {
            'content': {
                'include_dice': False,
                'include_system': False,
                'include_effects': False,
            },
            'cover': {
                'include': False,
            },
            'toc': {
                'include': False,
            },
        },
        'is_builtin': True,
    },
    {
        'id': 'print_ready',
        'name': '인쇄용',
        'description': '인쇄에 최적화된 설정 (A5, 넓은 여백)',
        'settings': {
            'page': {
                'format': 'A5',
                'margins': {
                    'left': 20,
                    'right': 15,
                    'top': 25,
                    'bottom': 25,
                },
            },
            'style': {
                'body_font_size': 11,
                'visual_line_height': 1.8,
            },
        },
        'is_builtin': True,
    },
]


class ProfileManager:
    """설정 프로필 관리자"""

    def __init__(self, app_dir: Path):
        self._app_dir = app_dir
        self._profiles_file = app_dir / 'data' / 'profiles.json'
        self._profiles: Dict[str, Profile] = {}
        self._active_profile_id: str = 'default'
        self._load()

    def _load(self):
        """프로필 파일 로드"""
        # 기본 프로필 로드
        for builtin in BUILTIN_PROFILES:
            profile = Profile(
                id=builtin['id'],
                name=builtin['name'],
                description=builtin['description'],
                created=datetime.now().isoformat(),
                modified=datetime.now().isoformat(),
                settings=builtin['settings'],
                is_default=builtin.get('is_default', False),
                is_builtin=builtin.get('is_builtin', False),
            )
            self._profiles[profile.id] = profile

        # 사용자 프로필 로드
        try:
            if self._profiles_file.exists():
                with open(self._profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._active_profile_id = data.get('active_profile', 'default')

                    for profile_data in data.get('profiles', []):
                        if not profile_data.get('is_builtin', False):
                            profile = Profile.from_dict(profile_data)
                            self._profiles[profile.id] = profile

                logger.debug(f"프로필 로드: {len(self._profiles)}개")
        except Exception as e:
            logger.warning(f"프로필 로드 실패: {e}")

    def _save(self):
        """프로필 파일 저장"""
        try:
            self._profiles_file.parent.mkdir(parents=True, exist_ok=True)

            # 사용자 프로필만 저장 (내장 프로필은 저장하지 않음)
            user_profiles = [p.to_dict() for p in self._profiles.values() if not p.is_builtin]

            with open(self._profiles_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'version': 1,
                    'active_profile': self._active_profile_id,
                    'profiles': user_profiles,
                }, f, ensure_ascii=False, indent=2)

            logger.debug(f"프로필 저장: {len(user_profiles)}개 사용자 프로필")
        except Exception as e:
            logger.error(f"프로필 저장 실패: {e}")

    def get_profiles(self) -> List[Profile]:
        """모든 프로필 목록"""
        return list(self._profiles.values())

    def get_profile(self, profile_id: str) -> Optional[Profile]:
        """ID로 프로필 조회"""
        return self._profiles.get(profile_id)

    def get_active_profile(self) -> Profile:
        """현재 활성 프로필"""
        return self._profiles.get(self._active_profile_id, self._profiles['default'])

    def set_active_profile(self, profile_id: str) -> bool:
        """활성 프로필 변경"""
        if profile_id in self._profiles:
            self._active_profile_id = profile_id
            self._save()
            logger.info(f"활성 프로필 변경: {profile_id}")
            return True
        return False

    def create_profile(self, name: str, description: str = '',
                       settings: Dict = None, base_profile_id: str = None) -> Profile:
        """새 프로필 생성"""
        profile_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 기반 프로필 설정 복사
        if base_profile_id and base_profile_id in self._profiles:
            base_settings = copy.deepcopy(self._profiles[base_profile_id].settings)
            if settings:
                base_settings = self._deep_merge(base_settings, settings)
            settings = base_settings
        elif settings is None:
            settings = {}

        profile = Profile(
            id=profile_id,
            name=name,
            description=description,
            created=datetime.now().isoformat(),
            modified=datetime.now().isoformat(),
            settings=settings,
            is_default=False,
            is_builtin=False,
        )

        self._profiles[profile_id] = profile
        self._save()
        logger.info(f"프로필 생성: {name} ({profile_id})")
        return profile

    def update_profile(self, profile_id: str, name: str = None,
                       description: str = None, settings: Dict = None) -> Optional[Profile]:
        """프로필 업데이트"""
        profile = self._profiles.get(profile_id)
        if not profile or profile.is_builtin:
            logger.warning(f"프로필 수정 불가: {profile_id}")
            return None

        if name is not None:
            profile.name = name
        if description is not None:
            profile.description = description
        if settings is not None:
            profile.settings = settings
        profile.modified = datetime.now().isoformat()

        self._save()
        logger.info(f"프로필 업데이트: {profile.name}")
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """프로필 삭제"""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False

        if profile.is_builtin:
            logger.warning(f"내장 프로필은 삭제할 수 없음: {profile_id}")
            return False

        del self._profiles[profile_id]

        # 활성 프로필이 삭제되면 기본으로 변경
        if self._active_profile_id == profile_id:
            self._active_profile_id = 'default'

        self._save()
        logger.info(f"프로필 삭제: {profile.name}")
        return True

    def duplicate_profile(self, profile_id: str, new_name: str) -> Optional[Profile]:
        """프로필 복제"""
        original = self._profiles.get(profile_id)
        if not original:
            return None

        return self.create_profile(
            name=new_name,
            description=f"{original.description} (복제)",
            settings=copy.deepcopy(original.settings),
        )

    def apply_profile_to_config(self, config: Dict, profile_id: str = None) -> Dict:
        """프로필 설정을 config에 적용"""
        profile = self._profiles.get(profile_id or self._active_profile_id)
        if not profile:
            return config

        return self._deep_merge(config, profile.settings)

    def extract_profile_settings(self, config: Dict, name: str,
                                 description: str = '') -> Profile:
        """현재 config에서 프로필 생성"""
        # 중요 설정만 추출
        settings = {}
        important_keys = ['style', 'content', 'cover', 'toc', 'page', 'dialogue', 'fonts']

        for key in important_keys:
            if key in config:
                settings[key] = copy.deepcopy(config[key])

        return self.create_profile(name, description, settings)

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """딕셔너리 깊은 병합"""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def export_profile(self, profile_id: str, output_path: Path) -> bool:
        """프로필을 파일로 내보내기"""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"프로필 내보내기: {output_path}")
            return True
        except Exception as e:
            logger.error(f"프로필 내보내기 실패: {e}")
            return False

    def import_profile(self, input_path: Path) -> Optional[Profile]:
        """파일에서 프로필 가져오기"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 새 ID 생성
            data['id'] = f"imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            data['is_builtin'] = False
            data['is_default'] = False
            data['modified'] = datetime.now().isoformat()

            profile = Profile.from_dict(data)
            self._profiles[profile.id] = profile
            self._save()

            logger.info(f"프로필 가져오기: {profile.name}")
            return profile
        except Exception as e:
            logger.error(f"프로필 가져오기 실패: {e}")
            return None
