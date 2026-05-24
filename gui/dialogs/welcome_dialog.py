"""First-run welcome dialog — 3-step onboarding for new users.

Triggered only when ``gui_settings['_welcome_seen']`` is missing. After the
user clicks "시작하기" or "다시 보지 않기", the flag is set permanently.

UI/UX Pro Max §8 progressive-disclosure:
- Concise 3-step illustration (drag file → set GM → convert)
- Single primary action, no menu noise
- Escape route: "Skip" / "다시 보지 않기" instantly closes
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.version import __app_name__, __version__


class WelcomeDialog(QDialog):
    """Modal shown on first launch. Returns True if user wants to keep seeing it.

    Use ``WelcomeDialog.was_dismissed_forever()`` after exec() to know whether
    to persist the "don't show again" flag.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} 시작하기")
        self.setMinimumSize(560, 460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        title = QLabel(f"환영합니다 — {__app_name__}")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: palette(text); "
            "letter-spacing: -0.5px; margin: 0; padding: 0;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            f"버전 {__version__} · 코코포리아/Roll20 채팅 로그를 "
            f"EPUB · DOCX · PDF 전자책으로 변환합니다."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 12px; color: palette(mid);")
        layout.addWidget(subtitle)

        # ── 3-step guide ────────────────────────────────────
        for n, (head, body) in enumerate(_STEPS, start=1):
            layout.addWidget(_StepCard(n, head, body))

        # ── Spacer ──────────────────────────────────────────
        layout.addStretch()

        # ── Don't show again + Start button ─────────────────
        self._dont_show = QCheckBox("다음부터 이 창을 보지 않기")
        self._dont_show.setStyleSheet("font-size: 12px; color: palette(text);")
        layout.addWidget(self._dont_show)

        actions = QHBoxLayout()
        actions.addStretch()
        start_btn = QPushButton("시작하기")
        start_btn.setDefault(True)
        start_btn.setMinimumWidth(120)
        start_btn.setMinimumHeight(36)
        start_btn.clicked.connect(self.accept)
        actions.addWidget(start_btn)
        layout.addLayout(actions)

    def was_dismissed_forever(self) -> bool:
        return self._dont_show.isChecked()


_STEPS = [
    (
        "1. 로그 파일 추가",
        "코코포리아·Roll20에서 받은 HTML 파일을 드래그하거나, "
        "[파일 추가] 버튼으로 선택하세요. 여러 파일을 한 번에 병합할 수도 있습니다.",
    ),
    (
        "2. 작품 정보 입력",
        "제목과 GM 이름을 입력하면 표지·메타데이터에 자동 반영됩니다. "
        "출력 형식(EPUB·DOCX·PDF)도 함께 선택하세요.",
    ),
    (
        "3. 변환 시작",
        "[변환 시작] 버튼을 누르면 자동으로 장면 분할·정리 후 전자책 파일을 만듭니다. "
        "결과는 좌측 미리보기에서 실시간 확인 가능합니다.",
    ),
]


class _StepCard(QLabel):
    """Single onboarding row — number badge + heading + body."""

    def __init__(self, number: int, heading: str, body: str, parent=None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setTextFormat(Qt.RichText)
        self.setText(
            f"""
            <table cellspacing='0' cellpadding='0' style='margin:0;padding:0;'>
              <tr>
                <td valign='top' style='padding-right: 14px;'>
                  <div style='
                    background: #0A84FF; color: white;
                    width: 28px; height: 28px;
                    border-radius: 14px;
                    text-align: center;
                    font-weight: 700;
                    font-size: 14px;
                    line-height: 28px;'>{number}</div>
                </td>
                <td>
                  <div style='font-size:14px; font-weight:600; color:#1a1a1a;'>{heading}</div>
                  <div style='font-size:12px; color:#4a4a4a; line-height:1.6; margin-top:4px;'>{body}</div>
                </td>
              </tr>
            </table>
            """
        )
        self.setStyleSheet(
            "QLabel { padding: 12px 14px; background: rgba(128,128,128,0.04); "
            "border-radius: 8px; }"
        )
