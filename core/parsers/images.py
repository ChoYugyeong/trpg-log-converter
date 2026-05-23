"""Image discovery & optimisation used during parsing/rendering.

``optimize_image`` is the heaviest function here because it depends on Pillow;
parsing fixtures may run without Pillow installed, in which case the function
returns the raw bytes untouched.
"""
from __future__ import annotations

import io
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def optimize_image(img_path: Path, config: Dict[str, Any]) -> Tuple[bytes, str, str]:
    """이미지를 최적화하여 ``(bytes, mime_type, filename)`` 반환.

    - ``images.max_resolution`` 이상이면 비율 유지 리사이즈
    - ``images.jpeg_quality`` 로 JPEG 품질 조절
    - ``images.convert_webp=True`` 면 WebP → JPEG 변환
    """
    images_config = config.get("images", {})
    max_res = images_config.get("max_resolution", 0)
    quality = images_config.get("jpeg_quality", 85)
    convert_webp = images_config.get("convert_webp", True)

    try:
        from PIL import Image
    except ImportError:
        logger.warning(
            "Pillow 가 설치되지 않아 이미지 최적화를 건너뜁니다. "
            "'pip install Pillow' 로 설치하세요."
        )
        with open(img_path, "rb") as f:
            data = f.read()
        mime, _ = mimetypes.guess_type(str(img_path))
        return data, mime or "image/jpeg", img_path.name

    img = Image.open(img_path)
    original_format = img.format or "PNG"
    filename = img_path.name

    is_webp = original_format.upper() == "WEBP" or str(img_path).lower().endswith(".webp")
    if is_webp and convert_webp:
        if img.mode in ("RGBA", "LA", "PA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        original_format = "JPEG"
        filename = img_path.stem + ".jpg"

    if max_res and max_res > 0:
        w, h = img.size
        longest = max(w, h)
        if longest > max_res:
            ratio = max_res / longest
            new_w, new_h = int(w * ratio), int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    save_format = original_format.upper()
    if save_format in ("JPEG", "JPG"):
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime_type = "image/jpeg"
        if not filename.lower().endswith((".jpg", ".jpeg")):
            filename = img_path.stem + ".jpg"
    elif save_format == "PNG":
        img.save(buf, format="PNG", optimize=True)
        mime_type = "image/png"
    else:
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime_type = "image/jpeg"
        filename = img_path.stem + ".jpg"

    return buf.getvalue(), mime_type, filename


def find_image_file(filename: str, config: Dict[str, Any]) -> Optional[Path]:
    images_dir = Path(config.get("paths", {}).get("images_dir", "./images"))
    if Path(filename).exists():
        return Path(filename)
    if images_dir.exists():
        img_path = images_dir / filename
        if img_path.exists():
            return img_path
    return None


def extract_image_markers(text: str, config: Dict[str, Any]) -> Tuple[Optional[str], str]:
    images_config = config.get("images", {})
    if not images_config.get("enable", True):
        return None, text
    markers = images_config.get("markers", [])
    for pattern in markers:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                remaining_text = re.sub(pattern, "", text, count=1).strip()
                return filename, remaining_text
        except re.error as e:
            logger.warning("이미지 마커 패턴 오류 '%s': %s", pattern, e)
    return None, text
