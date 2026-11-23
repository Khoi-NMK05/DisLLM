"""
In-app Update Dialog for DisLLM.
Displays GitHub release notes, downloads and verifies the update package,
and safely hands off installation without touching user data in %APPDATA%\\DisLLM.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from bot.updater import (
    ReleaseInfo,
    UpdateError,
    detect_install_mode,
    download_file,
    fetch_expected_checksum,
    get_update_staging_dir,
    launch_installer_update,
    launch_portable_zip_update,
    verify_sha256,
)
from bot.version import APP_NAME, APP_VERSION

if TYPE_CHECKING:
    from gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class UpdateDialog(QDialog):
    """Modal dialog presenting an available DisLLM update and handling download/install."""

    def __init__(self, release: ReleaseInfo, main_window: MainWindow, parent=None) -> None:
        super().__init__(parent or main_window)
        self.release = release
        self.main_window = main_window
        self.install_mode = detect_install_mode()
        self._busy = False

        self.setWindowTitle(f"Update Available — {APP_NAME} v{release.version}")
        self.setMinimumSize(520, 400)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"A new version of {APP_NAME} is available!")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        version_lbl = QLabel(f"Installed: <b>v{APP_VERSION}</b>  →  Latest: <b>v{self.release.version}</b>")
        layout.addWidget(version_lbl)

        safe_note = QLabel(
            "Your saved AI personas, conversation memory, tokens, custom commands, "
            "and plugins are stored separately and will not be wiped."
        )
        safe_note.setWordWrap(True)
        safe_note.setProperty("class", "muted")
        layout.addWidget(safe_note)

        notes_label = QLabel("Release Notes:")
        layout.addWidget(notes_label)

        self.notes_box = QTextEdit()
        self.notes_box.setReadOnly(True)
        self.notes_box.setPlainText(self.release.body or "No release notes provided.")
        layout.addWidget(self.notes_box, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setProperty("class", "muted")
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.btn_github = QPushButton("View on GitHub")
        self.btn_github.clicked.connect(self._open_release_page)
        btn_row.addWidget(self.btn_github)

        btn_row.addStretch()

        self.btn_later = QPushButton("Later")
        self.btn_later.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_later)

        self.btn_install = QPushButton(self._primary_button_label())
        self.btn_install.setProperty("class", "primary")
        self.btn_install.clicked.connect(self._on_install_clicked)
        btn_row.addWidget(self.btn_install)

        layout.addLayout(btn_row)

    def _primary_button_label(self) -> str:
        if self.install_mode == "source":
            return "Open Release Page"
        if not self.release.installer_url and not self.release.portable_zip_url:
            return "Open Release Page"
        return "Download && Install Update"

    def _open_release_page(self) -> None:
        if self.release.html_url:
            QDesktopServices.openUrl(QUrl(self.release.html_url))

    def _on_install_clicked(self) -> None:
        if self._busy:
            return

        if self.install_mode == "source" or (
            not self.release.installer_url and not self.release.portable_zip_url
        ):
            self._open_release_page()
            self.accept()
            return

        asyncio.create_task(self._download_and_apply())

    def _pick_download_target(self) -> tuple[str, str, str]:
        """Returns (kind, url, filename) where kind is 'installer' or 'portable'."""
        if self.install_mode == "installer" and self.release.installer_url and self.release.installer_name:
            return "installer", self.release.installer_url, self.release.installer_name
        if self.install_mode == "portable" and self.release.portable_zip_url and self.release.portable_zip_name:
            return "portable", self.release.portable_zip_url, self.release.portable_zip_name
        if self.release.installer_url and self.release.installer_name:
            return "installer", self.release.installer_url, self.release.installer_name
        assert self.release.portable_zip_url and self.release.portable_zip_name
        return "portable", self.release.portable_zip_url, self.release.portable_zip_name

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.btn_install.setEnabled(not busy)
        self.btn_later.setEnabled(not busy)
        self.progress_bar.setVisible(busy)

    async def _download_and_apply(self) -> None:
        self._set_busy(True)
        try:
            kind, url, filename = self._pick_download_target()
            dest = get_update_staging_dir() / filename
            self.status_label.setText(f"Downloading {filename}...")

            def on_progress(downloaded: int, total: int) -> None:
                if total > 0:
                    pct = min(100, int((downloaded / total) * 100))
                    self.progress_bar.setRange(0, 100)
                    self.progress_bar.setValue(pct)
                    mb_done = downloaded / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    self.status_label.setText(f"Downloading {filename}... {mb_done:.1f} / {mb_total:.1f} MB ({pct}%)")
                else:
                    self.progress_bar.setRange(0, 0)
                    mb_done = downloaded / (1024 * 1024)
                    self.status_label.setText(f"Downloading {filename}... {mb_done:.1f} MB")

            await download_file(url, dest, progress_callback=on_progress)

            if self.release.checksums_url:
                self.status_label.setText("Verifying SHA-256 checksum...")
                expected = await fetch_expected_checksum(self.release.checksums_url, filename)
                if expected and not verify_sha256(dest, expected):
                    raise UpdateError(
                        f"Checksum mismatch for {filename}. Download may be corrupted; update aborted."
                    )

            self.status_label.setText("Stopping Discord bot and launching updater...")
            await self.main_window.prepare_for_update_exit()

            if kind == "installer":
                launch_installer_update(dest)
            else:
                launch_portable_zip_update(dest)

            self.accept()
            self.main_window.quit_for_update()
        except Exception as err:
            logger.error("Update failed: %s", err)
            self._set_busy(False)
            self.status_label.setText(f"Update failed: {err}")
            self.status_label.setStyleSheet("color: #f23f43;")
            QMessageBox.warning(
                self,
                "Update Failed",
                f"Could not complete the update:\n\n{err}\n\nYou can also download it manually from GitHub.",
            )
