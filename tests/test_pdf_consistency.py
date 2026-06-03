#!/usr/bin/env python3
"""
PDF 렌더러 일관성 테스트.

EPUB 에서 동작하던 사용자 스타일 설정(style/header)이 PDF 에서도
반영되는지 확인한다. reportlab 이 없으면 전체를 skip 한다.
"""

import pytest

from core.pdf_generator import PDF_AVAILABLE

pytestmark = pytest.mark.skipif(
    not PDF_AVAILABLE, reason="reportlab (PDF) 미설치 환경 - PDF 테스트 skip"
)


def _custom_config():
    return {
        "style": {
            "name_color": "#112233",
            "body_text": "#0a0b0c",
            "system_color": "#445566",
            "effect_bg": "#fafbfc",
            "effect_border": "#abcdef",
            "dialogue_line_height": "2.0",  # 문자열로 들어와도 안전 변환
            "narration_line_height": 2.0,
            "narration_indent": 2.0,
            "dice_color": "#778899",
        },
        "header": {
            "size": 20,
            "color": "#a1b2c3",
            "box": True,
            "box_color": "#eeddcc",
        },
    }


def test_create_styles_reflects_config():
    """create_styles 가 config["style"]/header 값을 그대로 반영하는지 검증."""
    from reportlab.lib.colors import HexColor

    from core.pdf_generator import create_styles

    config = _custom_config()
    styles = create_styles("Helvetica", "Helvetica-Bold", config)

    # 색상 와이어링
    assert styles["DialogueName"].textColor == HexColor("#112233")
    assert styles["Dialogue"].textColor == HexColor("#0a0b0c")
    assert styles["Narration"].textColor == HexColor("#0a0b0c")
    assert styles["System"].textColor == HexColor("#445566")
    assert styles["Effect"].backColor == HexColor("#fafbfc")

    # line-height / indent 계산 (문자열 강제 변환 포함)
    assert styles["Dialogue"].leading == pytest.approx(10.5 * 2.0)
    assert styles["Narration"].leading == pytest.approx(10.0 * 2.0)
    from reportlab.lib.units import mm

    assert styles["Narration"].leftIndent == pytest.approx(2.0 * 8 * mm)

    # header.box 가 켜지면 SceneTitle 에 박스(backColor) 적용
    assert styles["SceneTitle"].backColor == HexColor("#eeddcc")
    assert styles["SceneTitle"].textColor == HexColor("#a1b2c3")


def test_create_styles_defaults_preserve_current_output():
    """설정이 없을 때 기존 출력값(기본값)을 유지하는지 검증."""
    from reportlab.lib.colors import HexColor

    from core.pdf_generator import create_styles

    styles = create_styles("Helvetica", "Helvetica-Bold", {})

    assert styles["DialogueName"].textColor == HexColor("#2d2d2d")
    assert styles["System"].textColor == HexColor("#666666")
    assert styles["Effect"].backColor == HexColor("#f5f5f5")
    # 기본 line-height: 16.x ≈ 기존 하드코딩 16
    assert styles["Dialogue"].leading == pytest.approx(10.5 * 1.5)
    assert styles["Narration"].leading == pytest.approx(10.0 * 1.7)
    # header.box 기본 off → 박스 backColor 미적용
    assert getattr(styles["SceneTitle"], "backColor", None) is None


def test_create_styles_handles_bad_values():
    """잘못된 타입/형식의 설정값도 default 로 안전 처리되는지."""
    from reportlab.lib.colors import HexColor

    from core.pdf_generator import create_styles

    config = {
        "style": {
            "name_color": "not-a-hex",
            "dialogue_line_height": "abc",
            "narration_indent": None,
        },
        "header": {"box": True, "box_color": 12345},
    }
    styles = create_styles("Helvetica", "Helvetica-Bold", config)

    assert styles["DialogueName"].textColor == HexColor("#2d2d2d")
    assert styles["Dialogue"].leading == pytest.approx(10.5 * 1.5)
    # 잘못된 box_color 는 기본값으로
    assert styles["SceneTitle"].backColor == HexColor("#f5f5f5")


def test_full_render_creates_nonempty_pdf(tmp_path):
    """커스텀 색상으로 실제 PDF 를 생성해 파일이 만들어지고 비어있지 않은지."""
    from core.pdf_generator import create_pdf

    config = _custom_config()
    config["paths"] = {"fonts_dir": "./fonts"}

    entries = [
        {"type": "dialogue", "name": "홍길동", "content": "안녕하세요."},
        {"type": "narration", "content": "바람이 분다."},
        {"type": "system", "content": "시스템 메시지"},
        {"type": "dice", "content": "1d100 = 42"},
        {"type": "effect", "content": "효과음"},
    ]

    out_path = tmp_path / "out.pdf"
    result = create_pdf(
        entries=entries,
        output_path=str(out_path),
        config=config,
        title="테스트",
        author="작가",
    )

    assert result is not None
    assert out_path.exists()
    assert out_path.stat().st_size > 0
