"""
Main application window for the Discord AI Companion Desktop app.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from bot.config import BotConfig
from bot.runner import BotRunner, BotState
from bot.version import APP_NAME, APP_VERSION
from gui.log_handler import QtLogHandler
from gui.tabs import (
    AIModelsTab,
    BotControlTab,
    CommandsTab,
    DashboardTab,
    SettingsTab,
)

logger = logging.getLogger(__name__)

# Discord presence colors: online, idle (busy transitioning), dnd (error), offline.
_PRESENCE: dict[BotState, tuple[str, str]] = {
    BotState.ONLINE: ("Online", "#23a55a"),
    BotState.CONNECTING: ("Connecting...", "#f0b232"),
    BotState.STOPPING: ("Stopping...", "#f0b232"),
    BotState.ERROR: ("Error - see Dashboard", "#f23f43"),
    BotState.DISCONNECTED: ("Disconnected", "#80848e"),
}


def _glyph_icon(char: str, color: str = "#80848e") -> QIcon:
    """A monochrome text glyph rendered as an icon (Discord's channel '#')."""
    pix = QPixmap(20, 20)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor(color))
    font = painter.font()
    font.setPixelSize(17)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, char)
    painter.end()
    return QIcon(pix)


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
        self._schedule_startup_update_check()

    def _schedule_startup_update_check(self) -> None:
        """Runs a quiet background update check shortly after launch if enabled."""
        if not self.settings_tab.mod_manager.settings.auto_check_updates:
            return

        def _trigger() -> None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            loop.create_task(self.settings_tab.check_for_updates_async(silent=True))

        QTimer.singleShot(2500, _trigger)

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
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "D")
        painter.end()

        self.tray_icon = QSystemTrayIcon(QIcon(pix), self)
        self.tray_icon.setToolTip(f"{APP_NAME} v{APP_VERSION}")

        tray_menu = QMenu()
        act_show = QAction("Show Window", self)
        act_show.triggered.connect(self._restore_from_tray)

        act_dashboard = QAction("Dashboard", self)
        act_dashboard.triggered.connect(lambda: (self.tabs.setCurrentIndex(0), self._restore_from_tray()))

        act_exit = QAction("Exit && Disconnect", self)
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
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1180, 760)
        self.setMinimumSize(960, 620)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        root = QHBoxLayout(central_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.dashboard_tab = DashboardTab(main_window=self)
        self.bot_control_tab = BotControlTab(main_window=self)
        self.ai_models_tab = AIModelsTab(main_window=self)
        self.commands_tab = CommandsTab(main_window=self)
        self.settings_tab = SettingsTab(main_window=self)

        # Pages; kept as `tabs` so callers can still use count()/setCurrentIndex().
        self.tabs = QStackedWidget()
        pages = [
            (self.dashboard_tab, "Dashboard"),
            (self.bot_control_tab, "Bot & Multi-Server"),
            (self.ai_models_tab, "AI Model & Persona"),
            (self.commands_tab, "Commands & Plugins"),
            (self.settings_tab, "Moderation & Settings"),
        ]
        for page, _ in pages:
            self.tabs.addWidget(page)

        root.addWidget(self._create_sidebar([title for _, title in pages]))
        root.addWidget(self.tabs, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Add your Discord bot token on the Dashboard to begin.")

    def _create_sidebar(self, titles: list[str]) -> QFrame:
        """Discord-style channel list: server header, section label, nav items, pinned status panel."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel(APP_NAME)
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)

        section = QLabel("CONTROL CENTER")
        section.setObjectName("sidebarSection")
        layout.addWidget(section)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setTextElideMode(Qt.TextElideMode.ElideRight)
        hash_icon = _glyph_icon("#")
        for title in titles:
            self.nav.addItem(QListWidgetItem(hash_icon, title))
        self.nav.currentRowChanged.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.nav.setCurrentRow)  # tray "Dashboard" action
        self.nav.setCurrentRow(0)
        layout.addWidget(self.nav, stretch=1)

        layout.addWidget(self._create_status_panel())
        return sidebar

    def _create_status_panel(self) -> QFrame:
        """Pinned bot identity + presence, modeled on Discord's bottom-left user panel."""
        panel = QFrame()
        panel.setObjectName("statusPanel")
        row = QHBoxLayout(panel)
        row.setContentsMargins(10, 10, 10, 10)
        row.setSpacing(10)

        avatar = QLabel("D")
        avatar.setObjectName("statusAvatar")
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Presence dot overlaps the avatar corner, cut out by a ring in the panel color.
        self.status_dot = QLabel(avatar)
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setGeometry(22, 22, 14, 14)
        row.addWidget(avatar)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        self.status_name = QLabel("Discord Bot")
        self.status_name.setObjectName("statusName")
        self.status_state = QLabel("Disconnected")
        self.status_state.setObjectName("statusState")
        text_col.addWidget(self.status_name)
        text_col.addWidget(self.status_state)
        row.addLayout(text_col, stretch=1)

        self._update_status_panel(BotState.DISCONNECTED)
        return panel

    def _update_status_panel(self, state: BotState) -> None:
        label, color = _PRESENCE[state]
        self.status_state.setText(label)
        self.status_dot.setStyleSheet(f"background-color: {color};")
        bot = self.runner.bot
        if state == BotState.ONLINE and bot and bot.user:
            self.status_name.setText(bot.user.name)
        elif state in (BotState.DISCONNECTED, BotState.ERROR):
            self.status_name.setText("Discord Bot")

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
        self._update_status_panel(state)
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
                APP_NAME,
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

    async def prepare_for_update_exit(self) -> None:
        """Gracefully disconnects the bot and closes SQLite before launching an update."""
        self._force_quit = True
        if self.runner.is_running or self.runner.state == BotState.CONNECTING:
            try:
                await self.runner.stop()
            except Exception as err:
                logger.warning("Error stopping bot before update: %s", err)
        try:
            await self.settings_tab.db_manager.close()
        except Exception as err:
            logger.warning("Error closing database before update: %s", err)
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

    def quit_for_update(self) -> None:
        """Exits the Qt application so the external updater can replace app binaries."""
        self._force_quit = True
        app = QApplication.instance()
        if app is not None:
            app.quit()
