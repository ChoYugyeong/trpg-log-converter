"""First-run welcome dialog — 3-step onboarding for new users.

Triggered only when ``gui_settings['_welcome_seen']`` is missing. After the
user clicks "시작하기" the flag is set permanently.

UI/UX Pro Max:
- §5 visual-hierarchy : header (앱 이름) → 부제 → 3-step cards → CTA
- §8 progressive-disclosure : 한 화면에 3단계만, 부가 정보는 다이얼로그 밖
- §1 escape-routes      : "X" 닫기 + "다시 보지 않기" 체크박스
- §2 touch-target-size  : CTA 36px 높이, 체크박스도 클릭 영역 충분

Implementation note (재작성 사유):
이전 버전은 QLabel + HTML <table> 로 step 카드를 그렸는데, Qt 의 rich-text
엔진은 ``border-radius`` 를 지원하지 않아 동그란 배지가 세로 직사각형으로
렌더링되는 버그가 있었음. 또 헤딩에 "1." 숫자 prefix 가 들어가 배지의 숫자
와 중복되어 시각 노이즈. 이번엔 paintEvent 로 직접 원을 그리는 ``_StepBadge``
+ 실제 ``QLabel`` 두 개로 정렬을 픽셀 단위로 통제.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.version import __app_name__, __version__

# ---------------------------------------------------------------------------
# Step rendering
# ---------------------------------------------------------------------------

class _StepBadge(QWidget):
    """Circular numeric badge — 32×32 painted via QPainter for true round shape.

    Qt's rich-text engine ignores ``border-radius`` inside QLabel HTML, so we
    can't rely on inline CSS. Painting directly guarantees a circle on any
    Qt version / DPI.
    """

    _SIZE = 32
    _BG = QColor("#0A84FF")
    _FG = QColor("#FFFFFF")

    def __init__(self, number: int, parent=None) -> None:
        super().__init__(parent)
        self._number = number
        self.setFixedSize(self._SIZE, self._SIZE)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(self._SIZE, self._SIZE)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Filled circle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._BG))
        painter.drawEllipse(0, 0, self._SIZE, self._SIZE)

        # Centered number
        painter.setPen(QPen(self._FG))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, str(self._number))


class _StepCard(QFrame):
    """One onboarding row — circular badge on the left, heading + body on the right.

    Width: full parent. Inner left badge column is fixed 48px (badge 32 + 16
    gap), text column expands. Vertical alignment: badge top-aligned with the
    heading baseline visually (achieved by matching badge height to heading
    line-height).
    """

    def __init__(self, number: int, heading: str, body: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("WelcomeStepCard")
        self.setFrameShape(QFrame.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # Badge column — narrow fixed width so all 3 cards align consistently.
        badge_col = QVBoxLayout()
        badge_col.setContentsMargins(0, 0, 0, 0)
        badge_col.setSpacing(0)
        badge_col.addWidget(_StepBadge(number))
        badge_col.addStretch()
        layout.addLayout(badge_col)

        # Text column — heading + body stacked.
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)

        heading_label = QLabel(heading)
        heading_label.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: palette(text); "
            "margin: 0; padding: 0;"
        )
        # Match line-height to badge top so they baseline up.
        heading_label.setMinimumHeight(_StepBadge._SIZE)
        heading_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        text_col.addWidget(heading_label)

        body_label = QLabel(body)
        body_label.setWordWrap(True)
        body_label.setStyleSheet(
            "font-size: 12px; color: palette(mid); line-height: 1.6; "
            "margin: 0; padding: 0;"
        )
        body_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        body_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        text_col.addWidget(body_label)

        text_col.addStretch()
        layout.addLayout(text_col, 1)


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

_STEPS = [
    (
        "로그 파일 추가",
        "코코포리아·Roll20에서 받은 HTML 파일을 드래그하거나 [파일 추가] "
        "버튼으로 선택하세요. 여러 파일을 한 번에 병합할 수도 있습니다.",
    ),
    (
        "작품 정보 입력",
        "제목과 GM 이름을 입력하면 표지·메타데이터에 자동 반영됩니다. "
        "출력 형식(EPUB·DOCX·PDF)도 함께 선택하세요.",
    ),
    (
        "변환 시작",
        "[변환 시작] 버튼을 누르면 자동으로 장면 분할·정리 후 전자책 파일을 "
        "만듭니다. 결과는 좌측 미리보기에서 실시간 확인 가능합니다.",
    ),
]


class WelcomeDialog(QDialog):
    """Modal shown on first launch."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} 시작하기")
        self.setMinimumSize(580, 540)
        self.setModal(True)
        self.setStyleSheet(self._stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        title = QLabel(f"환영합니다 — {__app_name__}")
        title.setObjectName("WelcomeTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        subtitle = QLabel(
            f"버전 {__version__} · 코코포리아 / Roll20 채팅 로그를 "
            f"EPUB · DOCX · PDF 전자책으로 변환합니다."
        )
        subtitle.setObjectName("WelcomeSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # ── Separator ───────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("WelcomeSeparator")
        layout.addWidget(sep)

        # ── 3-step guide ────────────────────────────────────
        for n, (heading, body) in enumerate(_STEPS, start=1):
            layout.addWidget(_StepCard(n, heading, body))

        layout.addStretch()

        # ── Bottom row : checkbox + CTA on the same baseline ─
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(12)

        self._dont_show = QCheckBox("다음부터 이 창을 보지 않기")
        self._dont_show.setObjectName("WelcomeCheckbox")
        # Remove default focus rectangle that visually noises the text.
        self._dont_show.setFocusPolicy(Qt.NoFocus)
        bottom.addWidget(self._dont_show)

        bottom.addStretch()

        start_btn = QPushButton("시작하기")
        start_btn.setObjectName("WelcomePrimary")
        start_btn.setDefault(True)
        start_btn.setMinimumSize(130, 38)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.clicked.connect(self.accept)
        bottom.addWidget(start_btn)

        layout.addLayout(bottom)

    def was_dismissed_forever(self) -> bool:
        return self._dont_show.isChecked()

    # ── Local stylesheet ────────────────────────────────────
    @staticmethod
    def _stylesheet() -> str:
        return """
        QDialog { background: palette(window); }

        #WelcomeTitle {
            font-size: 22px;
            font-weight: 700;
            color: palette(text);
            letter-spacing: -0.5px;
            margin: 0;
            padding: 0;
        }
        #WelcomeSubtitle {
            font-size: 12px;
            color: palette(mid);
            margin: 0;
            padding: 0;
        }
        #WelcomeSeparator {
            background: rgba(128, 128, 128, 0.18);
            max-height: 1px;
            border: none;
        }

        #WelcomeStepCard {
            background: rgba(10, 132, 255, 0.04);
            border: 1px solid rgba(10, 132, 255, 0.10);
            border-radius: 10px;
        }
        #WelcomeStepCard:hover {
            background: rgba(10, 132, 255, 0.06);
        }

        #WelcomeCheckbox {
            font-size: 12px;
            color: palette(text);
            spacing: 8px;
        }
        #WelcomeCheckbox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid rgba(128, 128, 128, 0.4);
            border-radius: 3px;
            background: palette(base);
        }
        #WelcomeCheckbox::indicator:checked {
            background: #0A84FF;
            border-color: #0A84FF;
            image: none;
        }

        #WelcomePrimary {
            background: #0A84FF;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            padding: 0 18px;
        }
        #WelcomePrimary:hover { background: #0070D8; }
        #WelcomePrimary:pressed { background: #0058B0; }
        """
