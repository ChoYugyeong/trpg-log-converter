"""Log parsing package.

Public API:
    parse_log              — entry point, auto-detects format
    parse_roll20           — Roll20 chat archive specifically
    parse_cocofolia        — Cocofolia HTML specifically
    filter_entries         — drop entries by content type
    merge_consecutive_dialogues
    split_into_scenes      — chapter-split for output

Lower-level helpers live in:
    parsers.helpers   — pure text utilities (dice/scene detection, etc.)
    parsers.images    — image marker extraction & optimisation
    parsers.fonts     — font-file discovery
"""
from core.parsers.helpers import (  # noqa: F401
    escape_html,
    extract_scene_title,
    hex_to_rgb,
    is_dice_roll,
    is_narration_user,
    is_scene_end,
    is_scene_marker,
    match_custom_style,
    normalize_punctuation,
    smart_split_name_content,
    strip_channel_prefix,
    validate_regex,
)
from core.parsers.images import (  # noqa: F401
    extract_image_markers,
    find_image_file,
    optimize_image,
)
from core.parsers.fonts import (  # noqa: F401
    get_font_family_name,
    get_font_files,
)
from core.parsers.cocofolia import parse_cocofolia  # noqa: F401
from core.parsers.roll20 import parse_roll20  # noqa: F401
from core.parsers.pipeline import (  # noqa: F401
    filter_entries,
    merge_consecutive_dialogues,
    parse_log,
    split_by_count,
    split_by_scene,
    split_into_scenes,
)
