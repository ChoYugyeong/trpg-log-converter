"""Launch the app, bring it to front, screenshot just the app window.

Usage: python scripts/screenshot_app.py <output.png> [delay_seconds=4]

Strategy:
  1. Launch ``main.py`` as a subprocess.
  2. Poll for a window whose title contains "TRPG Log Converter".
  3. Force the window to the foreground (SetForegroundWindow + ShowWindow).
  4. Grab the window's screen rect via ``GetWindowRect`` and ``ImageGrab.grab(bbox=...)``.

Falls back to a full-desktop grab if Win32 helpers aren't available.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


def _find_window(title_substr: str):
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
    )

    matches: list[int] = []

    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if title_substr.lower() in buf.value.lower():
            matches.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(_enum), 0)
    return matches[0] if matches else None


def _bring_to_front(hwnd: int) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    # Some Windows builds refuse SetForegroundWindow without input focus.
    # Try ``BringWindowToTop`` as a fallback.
    user32.BringWindowToTop(hwnd)


def _window_rect(hwnd: int) -> tuple[int, int, int, int]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def _print_window(hwnd: int):
    """Capture an arbitrary HWND's contents via the Win32 PrintWindow API.

    Unlike ``ImageGrab``, this works even when the window is occluded by other
    apps — Windows asks the target window to render itself into a device
    context we own. Returns a PIL Image, or None on failure.
    """
    import ctypes
    from ctypes import wintypes

    from PIL import Image

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None

    hwnd_dc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    gdi32.SelectObject(mem_dc, bitmap)

    PW_RENDERFULLCONTENT = 0x00000002
    ok = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
    if not ok:
        # Some windows don't support full-content rendering; fall back to plain.
        user32.PrintWindow(hwnd, mem_dc, 0)

    # Copy DIB bits into a buffer and wrap in PIL.
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", wintypes.DWORD * 3),
        ]

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0  # BI_RGB

    buffer = (ctypes.c_ubyte * (width * height * 4))()
    gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), 0)

    image = Image.frombuffer(
        "RGBA", (width, height), bytes(buffer), "raw", "BGRA", 0, 1
    )

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)
    return image


def main(out_path: str, delay: float = 4.0) -> int:
    repo = Path(__file__).resolve().parent.parent
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(repo),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(delay)
        from PIL import ImageGrab

        hwnd = None
        deadline = time.time() + 8
        while time.time() < deadline:
            hwnd = _find_window("TRPG Log Converter")
            if hwnd:
                break
            time.sleep(0.3)

        if hwnd:
            _bring_to_front(hwnd)
            # Small pause so the window finishes rising before grab.
            time.sleep(0.6)
            bbox = _window_rect(hwnd)
            print(f"window hwnd={hwnd} bbox={bbox}")
            # PrintWindow captures even if occluded; ImageGrab does not.
            img = _print_window(hwnd)
            if img is None:
                img = ImageGrab.grab(bbox=bbox, all_screens=True)
        else:
            print("window not found — full desktop capture", file=sys.stderr)
            img = ImageGrab.grab(all_screens=False)

        img.save(out_path)
        print(f"saved: {out_path}  size={img.size}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: screenshot_app.py <out.png> [delay]")
        sys.exit(2)
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    sys.exit(main(sys.argv[1], delay))
