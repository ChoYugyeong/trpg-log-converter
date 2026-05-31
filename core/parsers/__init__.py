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

from core.parsers.cocofolia import parse_cocofolia
from core.parsers.fonts import (
    get_font_family_name,
    get_font_files,
)
from core.parsers.helpers import (
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
from core.parsers.images import (
    extract_image_markers,
    find_image_file,
    optimize_image,
)
from core.parsers.pipeline import (
    filter_entries,
    merge_consecutive_dialogues,
    parse_log,
    split_by_count,
    split_by_scene,
    split_into_scenes,
)
from core.parsers.roll20 import parse_roll20
