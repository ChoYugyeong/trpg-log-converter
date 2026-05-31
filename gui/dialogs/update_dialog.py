"""Update notification dialog — shows release notes + download + apply flow.

Three states (UI/UX Pro Max §8 multi-step-progress):
1. NOTIFY  - user sees "v2.3.0 available" + release notes + [Update / Later]
2. DOWNLOADING - progress bar + cancel
3. READY   - "Restart now to apply" + [Restart / Later]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from core.services.updater import UpdateInfo, UpdateService

logger = logging.getLogger(__name__)


class _DownloadWorker(QObject):
    progress = Signal(int, int)  # downloaded, total
    finished = Signal(object)  # Path on success
    failed = Signal(str)

    def __init__(self, service: UpdateService, info: UpdateInfo) -> None:
        super().__init__()
        self._service = service
        self._info = info

    def run(self) -> None:
        try:
            path = self._service.download(
                self._info,
                on_progress=lambda d, t: self.progress.emit(d, t),
            )
            self.finished.emit(path)
        except Exception as exc:
            logger.exception("Update download failed")
            self.failed.emit(str(exc))


class UpdateDialog(QDialog):
    """Single dialog that walks NOTIFY → DOWNLOADING → READY states."""

    STATE_NOTIFY = "notify"
    STATE_DOWNLOADING = "downloading"
    STATE_READY = "ready"
    STATE_FAILED = "failed"

    def __init__(self, info: UpdateInfo, service: UpdateService, parent=None) -> None:
        super().__init__(parent)
        self._info = info
        self._service = service
        self._archive_path: Path | None = None
        self._thread: QThread | None = None
        self._worker: _DownloadWorker | None = None

        self.setWindowTitle("업데이트 알림")
        self.setMinimumSize(520, 480)
        self.setModal(True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 20, 24, 20)
        self._layout.setSpacing(12)

        self._build_header()
        self._build_body()
        self._build_actions()
        self._set_state(self.STATE_NOTIFY)

    # ── Layout ──────────────────────────────────────────────────

    def _build_header(self) -> None:
        title = QLabel(f"새 버전이 있어요 — {self._info.tag}")
        title.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: palette(text); letter-spacing: -0.4px;"
        )
        self._layout.addWidget(title)

        subtitle = QLabel(self._info.title or "새 버전이 출시되었습니다.")
        subtitle.setStyleSheet("font-size: 12px; color: palette(mid); margin-top: -4px;")
        self._layout.addWidget(subtitle)

    def _build_body(self) -> None:
        # Release notes (always shown)
        self._notes = QTextBrowser()
        self._notes.setMarkdown(self._info.body or "_릴리스 노트가 없습니다._")
        self._notes.setOpenExternalLinks(True)
        self._notes.setStyleSheet(
            "QTextBrowser { background: palette(base); "
            "border: 1px solid rgba(128,128,128,0.18); border-radius: 6px; "
            "padding: 10px; font-size: 12px; line-height: 1.6; }"
        )
        self._layout.addWidget(self._notes, 1)

        # Progress bar (shown only during download)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setVisible(False)
        self._progress.setTextVisible(True)
        self._layout.addWidget(self._progress)

        # Status line (changes per state)
        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 12px; color: palette(mid);")
        self._status.setVisible(False)
        self._layout.addWidget(self._status)

    def _build_actions(self) -> None:
        self._actions = QHBoxLayout()
        self._actions.setSpacing(8)

        self._later_btn = QPushButton("나중에")
        self._later_btn.clicked.connect(self.reject)

        self._primary_btn = QPushButton("지금 업데이트")
        self._primary_btn.setDefault(True)
        self._primary_btn.setMinimumWidth(120)
        self._primary_btn.clicked.connect(self._on_primary)

        self._actions.addStretch()
        self._actions.addWidget(self._later_btn)
        self._actions.addWidget(self._primary_btn)
        self._layout.addLayout(self._actions)

    # ── State machine ──────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        self._state = state
        size_mb = self._info.asset_size / (1024 * 1024) if self._info.asset_size else 0

        if state == self.STATE_NOTIFY:
            self._progress.setVisible(False)
            self._status.setVisible(True)
            self._status.setText(
                f"다운로드 크기: {size_mb:.1f} MiB · 적용은 앱 재시작과 함께 자동 진행됩니다."
            )
            self._primary_btn.setText("지금 업데이트")
            self._primary_btn.setEnabled(True)
            self._later_btn.setEnabled(True)

        elif state == self.STATE_DOWNLOADING:
            self._progress.setVisible(True)
            self._progress.setValue(0)
            self._status.setVisible(True)
            self._status.setText("다운로드 중...")
            self._primary_btn.setEnabled(False)
            self._primary_btn.setText("다운로드 중...")
            self._later_btn.setEnabled(True)
            self._later_btn.setText("취소")

        elif state == self.STATE_READY:
            self._progress.setVisible(False)
            self._status.setVisible(True)
            self._status.setText("다운로드 완료. [지금 재시작] 을 누르면 새 버전이 적용됩니다.")
            self._primary_btn.setEnabled(True)
            self._primary_btn.setText("지금 재시작")
            self._later_btn.setEnabled(True)
            self._later_btn.setText("나중에")

        elif state == self.STATE_FAILED:
            self._progress.setVisible(False)
            self._status.setVisible(True)
            self._primary_btn.setEnabled(True)
            self._primary_btn.setText("다시 시도")
            self._later_btn.setEnabled(True)
            self._later_btn.setText("닫기")

    # ── Actions ────────────────────────────────────────────────

    def _on_primary(self) -> None:
        if self._state == self.STATE_NOTIFY or self._state == self.STATE_FAILED:
            self._start_download()
        elif self._state == self.STATE_READY:
            self._launch_apply()

    def _start_download(self) -> None:
        self._set_state(self.STATE_DOWNLOADING)
        self._thread = QThread(self)
        self._worker = _DownloadWorker(self._service, self._info)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_downloaded)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()

    def _on_progress(self, downloaded: int, total: int) -> None:
        pct = int(downloaded * 100 / total) if total > 0 else 0
        self._progress.setValue(pct)
        mb = downloaded / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        self._status.setText(f"다운로드 중... {mb:.1f} / {tot_mb:.1f} MiB ({pct}%)")

    def _on_downloaded(self, path) -> None:
        self._archive_path = path
        self._cleanup_thread()
        self._set_state(self.STATE_READY)

    def _on_failed(self, err: str) -> None:
        self._cleanup_thread()
        self._status.setStyleSheet("font-size: 12px; color: rgb(200,30,30);")
        self._status.setText(f"다운로드 실패: {err}")
        self._set_state(self.STATE_FAILED)

    def _cleanup_thread(self) -> None:
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
            self._worker = None

    def _launch_apply(self) -> None:
        if self._archive_path is None:
            return
        try:
            self._service.apply(self._info, self._archive_path)
        except Exception as exc:
            self._status.setStyleSheet("font-size: 12px; color: rgb(200,30,30);")
            self._status.setText(f"적용 실패: {exc}")
            return
        # Apply script is now running in the background — exit ourselves so it
        # can replace the install dir.
        self.accept()
        # The parent main window's closeEvent should also fire, but ensure exit
        # in case the dialog was launched outside the normal lifecycle.
        from PySide6.QtCore import QTimer

        QTimer.singleShot(100, lambda: sys.exit(0))

    def closeEvent(self, event) -> None:
        self._cleanup_thread()
        super().closeEvent(event)
