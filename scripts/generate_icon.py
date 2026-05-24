"""Generate app icon (.ico + .icns + .png) from a procedural design.

Why procedural: no designer available, but we still need something better than
the default Python rocket. The output should:
  - Be readable at 16x16 (taskbar) and 256x256 (alt-tab) — strong silhouette.
  - Use the app brand color (#0A84FF accent) on a neutral surface.
  - Carry a clear identity: monogram "TR" inside a stylized book/log icon.

Outputs:
  resources/icon.png       (1024x1024 source)
  resources/icon.ico       (Windows multi-resolution)
  resources/icon.icns      (macOS, generated via iconutil if available)

Run once and commit the outputs; the build script just references the files.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "resources"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SIZE = 1024
BG = (255, 255, 255, 0)             # transparent
SURFACE = (245, 247, 250, 255)       # cool neutral
ACCENT = (10, 132, 255, 255)         # iOS / Material primary
INK = (26, 26, 26, 255)              # near-black text
SOFT_INK = (44, 56, 72, 255)         # for monogram


def _load_font(size_px: int) -> ImageFont.FreeTypeFont:
    """Pick the first usable bold sans font on the build machine."""
    candidates = [
        # Project-bundled
        ROOT / "resources" / "fonts" / "Pretendard-Bold.ttf",
        ROOT / "resources" / "fonts" / "Pretendard-SemiBold.ttf",
        # Windows
        Path(r"C:\Windows\Fonts\malgunbd.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        # macOS
        Path("/System/Library/Fonts/Supplemental/Helvetica Bold.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
        # Linux
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for f in candidates:
        if f.exists():
            try:
                return ImageFont.truetype(str(f), size_px)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_book_silhouette(draw: ImageDraw.ImageDraw) -> None:
    """Rounded square card with accent spine — a stylized "book"."""
    pad = int(SIZE * 0.08)
    radius = int(SIZE * 0.22)

    # Outer card (light surface)
    draw.rounded_rectangle(
        [(pad, pad), (SIZE - pad, SIZE - pad)],
        radius=radius,
        fill=SURFACE,
        outline=None,
    )

    # Spine: tall accent rectangle on the left
    spine_w = int(SIZE * 0.16)
    spine_x = pad
    spine_y = pad + int(SIZE * 0.04)
    spine_h = SIZE - pad - spine_y - int(SIZE * 0.04)
    draw.rounded_rectangle(
        [(spine_x, spine_y), (spine_x + spine_w, spine_y + spine_h)],
        radius=int(SIZE * 0.06),
        fill=ACCENT,
    )

    # Horizontal "text lines" hint on the right side
    line_x_start = spine_x + spine_w + int(SIZE * 0.08)
    line_x_end = SIZE - pad - int(SIZE * 0.12)
    line_thickness = int(SIZE * 0.018)
    line_gap = int(SIZE * 0.06)
    y = int(SIZE * 0.32)
    for i in range(5):
        alpha = 60 + i * 18
        color = (44, 56, 72, alpha)
        draw.rounded_rectangle(
            [(line_x_start, y), (line_x_end - i * int(SIZE * 0.02), y + line_thickness)],
            radius=line_thickness // 2,
            fill=color,
        )
        y += line_gap


def _draw_monogram(img: Image.Image) -> None:
    """Place "TR" monogram centered on the upper portion."""
    draw = ImageDraw.Draw(img)
    font = _load_font(int(SIZE * 0.24))
    text = "TR"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (SIZE - tw) // 2 - bbox[0]
    y = int(SIZE * 0.18) - bbox[1]
    # Soft drop shadow
    shadow = (0, 0, 0, 36)
    draw.text((x + 3, y + 4), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=SOFT_INK)


def build_png() -> Path:
    """Build the master 1024×1024 PNG."""
    img = Image.new("RGBA", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    _draw_book_silhouette(draw)
    _draw_monogram(img)

    png_path = OUT_DIR / "icon.png"
    img.save(png_path, "PNG", optimize=True)
    print(f"wrote {png_path} ({img.size})")
    return png_path


def build_ico(png_path: Path) -> Path:
    """Build multi-resolution .ico — required sizes for Windows shell."""
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
             (128, 128), (256, 256)]
    ico_path = OUT_DIR / "icon.ico"
    # Pillow .ico save supports multi-size via sizes= argument.
    Image.open(png_path).save(ico_path, format="ICO", sizes=sizes)
    print(f"wrote {ico_path} ({len(sizes)} sizes)")
    return ico_path


def build_icns(png_path: Path) -> Path | None:
    """Build .icns on macOS using iconutil; on Win/Linux skip gracefully."""
    if sys.platform != "darwin":
        print(f"skip .icns (need macOS + iconutil); {png_path.name} remains the master")
        return None

    iconset = OUT_DIR / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()

    # Apple iconset naming: icon_<size>x<size>[@2x].png
    pairs = [
        (16, "16x16"),
        (32, "16x16@2x"),
        (32, "32x32"),
        (64, "32x32@2x"),
        (128, "128x128"),
        (256, "128x128@2x"),
        (256, "256x256"),
        (512, "256x256@2x"),
        (512, "512x512"),
        (1024, "512x512@2x"),
    ]
    src = Image.open(png_path)
    for px, suffix in pairs:
        out = iconset / f"icon_{suffix}.png"
        src.resize((px, px), Image.LANCZOS).save(out, "PNG")

    icns_path = OUT_DIR / "icon.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
        check=True,
    )
    shutil.rmtree(iconset)
    print(f"wrote {icns_path}")
    return icns_path


def main() -> int:
    png = build_png()
    build_ico(png)
    build_icns(png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
