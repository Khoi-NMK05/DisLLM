"""
Main application window for the Discord AI Companion Desktop app.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bot.config import BotConfig
from bot.runner import BotRunner, BotState
from gui.log_handler import QtLogHandler
from gui.tabs import (
    AIModelsTab,
    BotControlTab,
    CommandsTab,
    DashboardTab,
    SettingsTab,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary window housing the tabs, status bar, and bot orchestration."""

    def __init__(self, config: BotConfig, runner: BotRunner | None = None) -> None:
        super().__init__()
        self.config = config
        self.runner = runner or BotRunner(
            config=self.config,
            on_state_change=self._on_bot_state_changed,
        )

        self._init_ui()
        self._setup_logging_bridge()
        self._force_quit = False
        self._setup_system_tray()

    def _setup_system_tray(self) -> None:
        """Sets up the Windows system tray icon and background menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        # Generate a neat programmatic Discord Blurple icon
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#5865f2"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 8, 8)
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(16)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "B")
        painter.end()

        self.tray_icon = QSystemTrayIcon(QIcon(pix), self)
        self.tray_icon.setToolTip("Discord AI Companion")

        tray_menu = QMenu()
        act_show = QAction("Show Window", self)
        act_show.triggered.connect(self._restore_from_tray)

        act_dashboard = QAction("Dashboard", self)
        act_dashboard.triggered.connect(lambda: (self.tabs.setCurrentIndex(0), self._restore_from_tray()))

        act_exit = QAction("Exit & Disconnect", self)
        act_exit.triggered.connect(self._force_exit)

        tray_menu.addAction(act_show)
        tray_menu.addAction(act_dashboard)
        tray_menu.addSeparator()
        tray_menu.addAction(act_exit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()

    def _force_exit(self) -> None:
        self._force_quit = True
        self.close()

    def _init_ui(self) -> None:
        self.setWindowTitle("Discord AI Companion — Desktop Control Center")
        self.resize(1000, 720)
        self.setMinimumSize(850, 580)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Tab navigation container
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.dashboard_tab = DashboardTab(main_window=self)
        self.bot_control_tab = BotControlTab(main_window=self)
        self.ai_models_tab = AIModelsTab(main_window=self)
        self.commands_tab = CommandsTab(main_window=self)
        self.settings_tab = SettingsTab(main_window=self)

        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.bot_control_tab, "🎭 Bot & Multi-Server")
        self.tabs.addTab(self.ai_models_tab, "🧠 AI Engine & Models")
        self.tabs.addTab(self.commands_tab, "⚡ Commands & Personas")
        self.tabs.addTab(self.settings_tab, "🛡️ Moderation & Settings")

        main_layout.addWidget(self.tabs)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Application Ready. Configure your Discord Bot Token to begin.")

    def _setup_logging_bridge(self) -> None:
        """Hooks QtLogHandler into root logger to forward logs to the GUI."""
        self.qt_log_handler = QtLogHandler(self)
        self.qt_log_handler.emitter.log_record_received.connect(
            self.dashboard_tab.append_log_record
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(self.qt_log_handler)
        root_logger.setLevel(logging.INFO)

    def _on_bot_state_changed(self, state: BotState, detail: str) -> None:
        """Thread/async callback passed to BotRunner."""
        self.dashboard_tab.on_bot_state_changed(state, detail)
        self.bot_control_tab.on_bot_state_changed(state, detail)
        self.commands_tab._refresh_plugins_table()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimizes to tray if configured, or prompts cleanly before stopping the bot."""
        should_tray = (
            not self._force_quit
            and hasattr(self, "settings_tab")
            and hasattr(self.settings_tab, "mod_manager")
            and self.settings_tab.mod_manager.settings.minimize_to_tray_on_close
            and hasattr(self, "tray_icon")
            and self.tray_icon.isVisible()
        )

        if should_tray:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Discord AI Companion",
                "App minimized to Windows system tray. Double-click tray icon to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
            return

        root_logger = logging.getLogger()
        if hasattr(self, "qt_log_handler"):
            root_logger.removeHandler(self.qt_log_handler)

        if self.runner.is_running or self.runner.state == BotState.CONNECTING:
            if not self._force_quit:
                reply = QMessageBox.question(
                    self,
                    "Confirm Exit",
                    "The Discord bot is currently active. Do you want to disconnect the bot and exit?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return

            asyncio.create_task(self._async_close_and_quit())
            event.accept()
        else:
            event.accept()

    async def _async_close_and_quit(self) -> None:
        try:
            await self.runner.stop()
        except Exception as err:
            logger.warning("Error during window close cleanup: %s", err)
