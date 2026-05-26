"""About dialog — shows version, license, open-source credits, system info.

UI/UX Pro Max §5 visual-hierarchy: app name + version 헤더, 그 아래
설명, 크레딧, 시스템 정보 순서로 정보 위계 명확히.
"""
from __future__ import annotations

import platform
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from core.version import (
    __app_name__,
    __author__,
    __copyright__,
    __homepage__,
    __license__,
    __version__,
)


_CREDITS = """\
오픈소스 라이브러리

  • PySide6 / Qt for Python — Qt Company (LGPL)
  • PySide6-Fluent-Widgets — zhiyiYo (GPLv3 / Commercial)
  • ebooklib — Aleksandar Erkalović (AGPL)
  • python-docx — python-openxml (MIT)
  • beautifulsoup4 — Leonard Richardson (MIT)
  • lxml — lxml team (BSD)
  • Pillow — Jeffrey Clark, contributors (HPND)
  • reportlab — ReportLab (BSD)
  • pydantic — Samuel Colvin (MIT)
  • charset-normalizer — TAHRI Ahmed (MIT)
  • PyYAML — Kirill Simonov (MIT)

폰트
  • Pretendard — Kil Hyung-jin (OFL 1.1)

각 라이브러리의 라이선스 전문은 dist/_internal/ 하위의 *-dist-info/
디렉터리 또는 위 깃 저장소에서 확인할 수 있습니다.
"""


class AboutDialog(QDialog):
    """앱 정보 다이얼로그.

    크기 480×520, 모달. 헤더 / 본문 / 크레딧 탭 / 닫기 버튼 구조.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} 정보")
        self.setMinimumSize(520, 560)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # ── 헤더: 앱 이름 + 버전 ─────────────────────────────────
        name = QLabel(__app_name__)
        name.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: palette(text); "
            "letter-spacing: -0.5px; margin: 0; padding: 0;"
        )
        layout.addWidget(name)

        version = QLabel(f"버전 {__version__}")
        version.setStyleSheet(
            "font-size: 13px; font-weight: 500; color: palette(highlight); "
            "margin: 0; padding: 0;"
        )
        layout.addWidget(version)

        # ── 본문: 설명 ─────────────────────────────────────────
        desc = QLabel(
            "코코포리아 / Roll20 채팅 로그를 EPUB · DOCX · PDF 전자책으로\n"
            "변환하는 TRPG 리플레이 전용 출판 도구입니다."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: palette(text); margin-top: 8px;")
        layout.addWidget(desc)

        # ── 시스템 정보 ────────────────────────────────────────
        sysinfo = QLabel(
            f"OS · {platform.system()} {platform.release()}\n"
            f"Python · {sys.version.split()[0]}\n"
            f"라이선스 · {__license__}\n"
            f"{__copyright__}"
        )
        sysinfo.setStyleSheet(
            "font-size: 11px; color: palette(mid); line-height: 1.6; "
            "padding: 10px 12px; background: rgba(128,128,128,0.06); "
            "border-radius: 6px; margin-top: 6px;"
        )
        layout.addWidget(sysinfo)

        # ── 크레딧 (스크롤 가능) ──────────────────────────────
        credits = QTextBrowser()
        credits.setPlainText(_CREDITS)
        credits.setStyleSheet(
            "QTextBrowser { background: palette(base); "
            "border: 1px solid rgba(128,128,128,0.18); border-radius: 6px; "
            "padding: 10px; font-size: 12px; line-height: 1.7; }"
        )
        layout.addWidget(credits, 1)

        # ── 액션 : 새 버전 받기 + 저장소 + 닫기 ─────────────────
        # private 저장소 운영 시 자동 업데이트가 동작 안 함 → 수동 다운로드
        # 경로를 항상 제공. 사용자가 브라우저에서 GitHub 로그인 되어 있으면
        # private 저장소도 접근 가능.
        actions = QHBoxLayout()
        actions.setSpacing(8)

        releases_btn = QPushButton("새 버전 받기 (Releases)")
        releases_btn.clicked.connect(self._open_releases)
        releases_btn.setToolTip(
            "GitHub Releases 페이지를 브라우저로 엽니다.\n"
            "private 저장소도 GitHub 로그인 후 접근 가능."
        )
        actions.addWidget(releases_btn)

        diag_btn = QPushButton("진단 정보 내보내기")
        diag_btn.clicked.connect(self._export_diagnostics)
        diag_btn.setToolTip(
            "로그·시스템 정보·설정을 ZIP 한 개로 묶어 바탕화면에 저장합니다.\n"
            "버그 신고 시 첨부해 주세요. (이미지 등 큰 데이터는 자동 마스킹)"
        )
        actions.addWidget(diag_btn)

        homepage_btn = QPushButton("저장소")
        homepage_btn.clicked.connect(self._open_homepage)
        actions.addWidget(homepage_btn)

        actions.addStretch()

        close_btn = QPushButton("닫기")
        close_btn.setDefault(True)
        close_btn.setMinimumWidth(80)
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)

        layout.addLayout(actions)

    def _open_homepage(self) -> None:
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(__homepage__))

    def _open_releases(self) -> None:
        """Releases 페이지를 시스템 기본 브라우저로. private 저장소도 OK."""
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(f"{__homepage__}/releases/latest"))

    def _export_diagnostics(self) -> None:
        """버그 신고용 진단 ZIP 을 생성하고 결과를 메시지로 보고."""
        from PySide6.QtWidgets import QMessageBox

        try:
            from core.services.diagnostics import build_diagnostic_zip
            path = build_diagnostic_zip()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self, "진단 정보 내보내기 실패",
                f"진단 ZIP 을 만들지 못했어요:\n{exc}",
            )
            return

        size_kb = path.stat().st_size / 1024
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("진단 정보 저장 완료")
        msg.setText(
            f"진단 ZIP 이 만들어졌어요 ({size_kb:.0f} KB).\n\n{path}"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
        # 파일 위치를 시스템 파일 탐색기에서 열어주면 사용자가 바로 찾을 수 있음.
        try:
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
        except Exception:  # noqa: BLE001
            pass
