"""
Dashboard & Connection Tab for Discord AI Companion.
Provides token configuration, bot lifecycle controls, diagnostics, and real-time logs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import Card, StatusLabel
from bot.config import BotConfig
from bot.runner import BotRunner, BotState

if TYPE_CHECKING:
    from gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class DashboardTab(QWidget):
    """Connection settings, bot lifecycle controls, metrics, and live logs."""

    def __init__(self, main_window: MainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.config: BotConfig = main_window.config
        self.runner: BotRunner = main_window.runner

        self._all_logs: list[tuple[str, str, str]] = []  # (time, level, full_message)

        self._init_ui()
        self._setup_metrics_timer()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Top section: 2 columns (Credentials & Controls)
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        top_row.addWidget(self._create_credentials_card(), stretch=1)
        top_row.addWidget(self._create_controls_card(), stretch=1)
        layout.addLayout(top_row)

        # Bottom section: Real-time Live Log Stream
        layout.addWidget(self._create_logs_card(), stretch=1)

    def _create_credentials_card(self) -> Card:
        group = Card("Bot Authentication & Gateway")
        layout = group.body
        layout.setSpacing(10)

        desc = QLabel("Enter your Discord Bot Token to authenticate. Tokens are saved locally to your .env file.")
        desc.setWordWrap(True)
        desc.setProperty("class", "muted")
        layout.addWidget(desc)

        token_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste bot token here (e.g. MTIzNDU2...)")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setText(self.config.discord_token)

        self.toggle_show_btn = QPushButton("Show")
        self.toggle_show_btn.clicked.connect(self._toggle_token_visibility)

        token_row.addWidget(self.token_input)
        token_row.addWidget(self.toggle_show_btn)
        layout.addLayout(token_row)

        actions_row = QHBoxLayout()
        self.save_token_btn = QPushButton("Save Token")
        self.save_token_btn.clicked.connect(self._on_save_token_clicked)

        self.test_token_btn = QPushButton("Test Connection")
        self.test_token_btn.clicked.connect(self._on_test_token_clicked)

        actions_row.addWidget(self.save_token_btn)
        actions_row.addWidget(self.test_token_btn)
        actions_row.addStretch()
        layout.addLayout(actions_row)

        self.token_status_label = StatusLabel("")
        self.token_status_label.setWordWrap(True)
        layout.addWidget(self.token_status_label)
        layout.addStretch()

        return group

    def _create_controls_card(self) -> Card:
        group = Card("Bot Status & Control")
        layout = group.body
        layout.setSpacing(10)

        # Status badge row
        status_row = QHBoxLayout()
        status_label_title = QLabel("Gateway Status:")
        status_label_title.setStyleSheet("font-weight: bold;")

        self.status_badge = QLabel("DISCONNECTED")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setFixedSize(130, 28)
        self._update_status_badge(BotState.DISCONNECTED, "Ready to start")

        status_row.addWidget(status_label_title)
        status_row.addWidget(self.status_badge)
        status_row.addStretch()
        layout.addLayout(status_row)

        # Control buttons
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Bot")
        self.start_btn.setProperty("class", "primary")
        self.start_btn.clicked.connect(self._on_start_clicked)

        self.stop_btn = QPushButton("Stop Bot")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)

        self.restart_btn = QPushButton("Restart")
        self.restart_btn.setEnabled(False)
        self.restart_btn.clicked.connect(self._on_restart_clicked)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.restart_btn)
        layout.addLayout(btn_row)

        # Metrics grid
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(6)

        metrics_grid.addWidget(QLabel("Logged-in As:"), 0, 0)
        self.lbl_bot_user = QLabel("None")
        self.lbl_bot_user.setStyleSheet("color: #5865f2; font-weight: bold;")
        metrics_grid.addWidget(self.lbl_bot_user, 0, 1)

        metrics_grid.addWidget(QLabel("Active Guilds:"), 1, 0)
        self.lbl_guilds_count = QLabel("0 servers")
        metrics_grid.addWidget(self.lbl_guilds_count, 1, 1)

        metrics_grid.addWidget(QLabel("Gateway Ping:"), 2, 0)
        self.lbl_ping = QLabel("N/A")
        metrics_grid.addWidget(self.lbl_ping, 2, 1)

        metrics_grid.addWidget(QLabel("Active AI Model:"), 3, 0)
        self.lbl_ai_model = QLabel(self.config.ollama_model)
        metrics_grid.addWidget(self.lbl_ai_model, 3, 1)

        layout.addLayout(metrics_grid)
        layout.addStretch()

        return group

    def _create_logs_card(self) -> Card:
        group = Card("Live Activity & Event Stream")
        layout = group.body
        layout.setSpacing(8)

        # Filter bar
        bar_row = QHBoxLayout()
        bar_row.addWidget(QLabel("Filter Level:"))

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["ALL", "INFO", "WARNING", "ERROR"])
        self.filter_combo.currentTextChanged.connect(self._reapply_log_filters)
        bar_row.addWidget(self.filter_combo)

        self.auto_scroll_chk = QCheckBox("Auto-Scroll")
        self.auto_scroll_chk.setChecked(True)
        bar_row.addWidget(self.auto_scroll_chk)

        bar_row.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_logs)

        copy_btn = QPushButton("Copy All")
        copy_btn.clicked.connect(self._copy_logs)

        bar_row.addWidget(clear_btn)
        bar_row.addWidget(copy_btn)
        layout.addLayout(bar_row)

        # Log text area
        self.log_view = QPlainTextEdit()
        self.log_view.setPlaceholderText("Bot activity and logs will stream here once you start the bot.")
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 12px;"
        )
        layout.addWidget(self.log_view)

        return group

    def _toggle_token_visibility(self) -> None:
        if self.token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_show_btn.setText("Hide")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_show_btn.setText("Show")

    def _on_save_token_clicked(self) -> None:
        new_token = self.token_input.text().strip()
        self.config.save_token(new_token)
        self.token_status_label.setText("Token saved to local environment.")
        self.token_status_label.setStyleSheet("color: #23a55a;")

    def _on_test_token_clicked(self) -> None:
        token = self.token_input.text().strip()
        if not token:
            self.token_status_label.setText("Token is empty. Please enter a token.")
            self.token_status_label.setStyleSheet("color: #f0b232;")
            return

        self.test_token_btn.setEnabled(False)
        self.token_status_label.setText("Verifying token with Discord Gateway...")
        self.token_status_label.setStyleSheet("color: #949ba4;")

        async def verify() -> None:
            client = discord.Client(intents=discord.Intents.default())
            try:
                await client.login(token)
                name = client.user.name if client.user else "Unknown"
                discrim = client.user.discriminator if client.user else "0000"
                self.token_status_label.setText(f"Success! Token valid for bot: @{name}#{discrim}")
                self.token_status_label.setStyleSheet("color: #23a55a;")
            except discord.LoginFailure:
                self.token_status_label.setText("Login Failed: Invalid token provided.")
                self.token_status_label.setStyleSheet("color: #da373c;")
            except Exception as err:
                self.token_status_label.setText(f"Connection Error: {err}")
                self.token_status_label.setStyleSheet("color: #da373c;")
            finally:
                await client.close()
                self.test_token_btn.setEnabled(True)

        asyncio.create_task(verify())

    def _on_start_clicked(self) -> None:
        token = self.token_input.text().strip()
        if not token:
            self.token_status_label.setText("Please provide a valid bot token before starting.")
            self.token_status_label.setStyleSheet("color: #f0b232;")
            return

        self.config.save_token(token)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.restart_btn.setEnabled(True)

        asyncio.create_task(self.runner.start())

    def _on_stop_clicked(self) -> None:
        self.stop_btn.setEnabled(False)
        asyncio.create_task(self.runner.stop())

    def _on_restart_clicked(self) -> None:
        self.restart_btn.setEnabled(False)
        asyncio.create_task(self.runner.restart())

    def on_bot_state_changed(self, state: BotState, detail: str) -> None:
        self._update_status_badge(state, detail)

        if state == BotState.ONLINE:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.restart_btn.setEnabled(True)
            if self.runner.bot and self.runner.bot.user:
                self.lbl_bot_user.setText(f"{self.runner.bot.user.name} ({self.runner.bot.user.id})")
        elif state == BotState.CONNECTING:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.restart_btn.setEnabled(False)
        elif state == BotState.STOPPING:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.restart_btn.setEnabled(False)
        elif state in (BotState.DISCONNECTED, BotState.ERROR):
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.restart_btn.setEnabled(False)
            self.lbl_bot_user.setText("None")
            self.lbl_guilds_count.setText("0 servers")
            self.lbl_ping.setText("N/A")

    def _update_status_badge(self, state: BotState, detail: str) -> None:
        self.status_badge.setText(state.value)
        color_map = {
            BotState.DISCONNECTED: ("#35373c", "#949ba4"),
            BotState.CONNECTING: ("#8a6508", "#f0b232"),
            BotState.ONLINE: ("#18522e", "#23a55a"),
            BotState.STOPPING: ("#8a6508", "#f0b232"),
            BotState.ERROR: ("#5c1b1f", "#da373c"),
        }
        bg, fg = color_map.get(state, ("#35373c", "#dbdee1"))
        self.status_badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; font-weight: bold; border-radius: 6px; border: 1px solid {fg};"
        )
        if detail:
            self.main_window.statusBar().showMessage(f"Status: {state.value} - {detail}")

    def append_log_record(self, timestamp: str, level: str, message: str) -> None:
        self._all_logs.append((timestamp, level, message))
        if len(self._all_logs) > 3000:
            self._all_logs.pop(0)

        current_filter = self.filter_combo.currentText()
        if current_filter != "ALL" and level != current_filter:
            return

        self._render_log_entry(level, message)

    def _render_log_entry(self, level: str, message: str) -> None:
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        color_map = {
            "INFO": QColor("#23a55a"),
            "WARNING": QColor("#f0b232"),
            "ERROR": QColor("#da373c"),
            "CRITICAL": QColor("#f23f43"),
            "DEBUG": QColor("#949ba4"),
        }
        fmt = QTextCharFormat()
        fmt.setForeground(color_map.get(level, QColor("#dbdee1")))

        cursor.insertText(message + "\n", fmt)

        if self.auto_scroll_chk.isChecked():
            self.log_view.setTextCursor(cursor)
            self.log_view.ensureCursorVisible()

    def _reapply_log_filters(self) -> None:
        self.log_view.clear()
        current_filter = self.filter_combo.currentText()
        for _, level, msg in self._all_logs:
            if current_filter == "ALL" or level == current_filter:
                self._render_log_entry(level, msg)

    def _clear_logs(self) -> None:
        self._all_logs.clear()
        self.log_view.clear()

    def _copy_logs(self) -> None:
        from PySide6.QtGui import QGuiApplication

        clipboard = QGuiApplication.clipboard()
        all_text = "\n".join(entry[2] for entry in self._all_logs)
        clipboard.setText(all_text)
        self.main_window.statusBar().showMessage("Logs copied to clipboard!", 3000)

    def _setup_metrics_timer(self) -> None:
        self.metrics_timer = QTimer(self)
        self.metrics_timer.setInterval(2000)
        self.metrics_timer.timeout.connect(self._refresh_metrics)
        self.metrics_timer.start()

    def _refresh_metrics(self) -> None:
        if self.runner.bot and self.runner.bot.is_ready():
            guilds = len(self.runner.bot.guilds)
            ping_ms = round(self.runner.bot.latency * 1000, 1)
            self.lbl_guilds_count.setText(f"{guilds} server(s)")
            self.lbl_ping.setText(f"{ping_ms} ms")
