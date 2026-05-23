"""Merge a JSON preset into the built app's gui_settings.json.

Usage:
    python scripts/apply_preset.py [PRESET_JSON] [TARGET_JSON]

Defaults:
    PRESET_JSON = <project>/presets/default.json
    TARGET_JSON = <project>/dist/TRPG_Converter_Pro/gui_settings.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRESET = ROOT / "presets" / "default.json"
DEFAULT_TARGET = ROOT / "dist" / "TRPG_Converter_Pro" / "gui_settings.json"


def apply_preset(preset_path: Path, target_path: Path) -> None:
    if not preset_path.exists():
        raise FileNotFoundError(f"Preset not found: {preset_path}")

    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    preset.pop("_meta", None)

    current = {}
    if target_path.exists():
        current = json.loads(target_path.read_text(encoding="utf-8"))

    current.update(preset)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"applied -> {target_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preset", nargs="?", type=Path, default=DEFAULT_PRESET)
    parser.add_argument("target", nargs="?", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)
    try:
        apply_preset(args.preset, args.target)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
