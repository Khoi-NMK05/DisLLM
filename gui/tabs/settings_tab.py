"""
Settings, Memory Inspector & Server Moderation Tab (Phase 5).
Manages channel whitelists/blacklists, DM privacy, user rate limits,
SQLite conversation memory exploration and purging, and system tray preferences.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import Card, StatusLabel
from bot.database import DatabaseManager
from bot.moderation import ModerationManager

if TYPE_CHECKING:
    from gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class SettingsTab(QWidget):
    """Server Moderation, SQLite Memory Inspector & Desktop Preferences."""

    def __init__(self, main_window: MainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.mod_manager = ModerationManager()
        self.db_manager = DatabaseManager(db_path=main_window.config.db_path)

        self.selected_memory_channel_id: int | None = None

        self._init_ui()
        self._load_mod_settings()
        self._refresh_active_memory_channels()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(16)

        # Left Column: Moderation Rules & App Preferences
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        left_layout.addWidget(self._create_moderation_card())
        left_layout.addWidget(self._create_app_preferences_card())
        left_layout.addStretch()

        # Right Column: SQLite Memory Inspector
        right_widget = self._create_memory_inspector_card()

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 9)
        splitter.setStretchFactor(1, 11)

        layout.addWidget(splitter)

    # -------------------------------------------------------------------------
    # Left Column: Moderation & App Settings
    # -------------------------------------------------------------------------

    def _create_moderation_card(self) -> Card:
        group = Card("Server Privacy & Channel Moderation")
        layout = group.body
        layout.setSpacing(10)

        # DM Toggle
        self.chk_allow_dms = QCheckBox("Allow Direct Messages (DMs)")
        layout.addWidget(self.chk_allow_dms)

        # Mode Selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Channel Rule Mode:"))
        self.combo_rule_mode = QComboBox()
        self.combo_rule_mode.addItem("Respond in All Channels", "all")
        self.combo_rule_mode.addItem("Whitelist Only (Respond only in selected)", "whitelist")
        self.combo_rule_mode.addItem("Blacklist Only (Ignore selected channels)", "blacklist")
        self.combo_rule_mode.currentIndexChanged.connect(self._on_rule_mode_changed)
        mode_row.addWidget(self.combo_rule_mode, stretch=1)
        layout.addLayout(mode_row)

        # Server selector for channel checklist
        server_row = QHBoxLayout()
        server_row.addWidget(QLabel("Server:"))
        self.combo_mod_guilds = QComboBox()
        self.combo_mod_guilds.currentIndexChanged.connect(self._on_mod_guild_selected)
        server_row.addWidget(self.combo_mod_guilds, stretch=1)

        self.btn_refresh_mod_guilds = QPushButton("Refresh")
        self.btn_refresh_mod_guilds.clicked.connect(self._refresh_mod_guilds)
        server_row.addWidget(self.btn_refresh_mod_guilds)
        layout.addLayout(server_row)

        # Channel Checkbox List
        layout.addWidget(QLabel("Select Channels for Whitelist / Blacklist:"))
        self.channels_checklist = QListWidget()
        self.channels_checklist.setMaximumHeight(130)
        self.channels_checklist.itemChanged.connect(self._on_channel_check_changed)
        layout.addWidget(self.channels_checklist)

        # Rate Limiting
        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("Anti-Spam Rate Limit:"))
        self.spin_rate_limit = QSpinBox()
        self.spin_rate_limit.setRange(0, 60)
        self.spin_rate_limit.setValue(10)
        self.spin_rate_limit.setSuffix(" msgs/min per user")
        rate_row.addWidget(self.spin_rate_limit, stretch=1)
        layout.addLayout(rate_row)

        # Bot admin: the one Discord user allowed to run /clear_memory, /forget_me, /wipe_database
        admin_row = QHBoxLayout()
        admin_row.addWidget(QLabel("Bot Admin User ID:"))
        self.txt_admin_id = QLineEdit()
        self.txt_admin_id.setPlaceholderText("Discord Developer Mode > right-click yourself > Copy User ID")
        admin_row.addWidget(self.txt_admin_id, stretch=1)
        layout.addLayout(admin_row)

        return group

    def _create_app_preferences_card(self) -> Card:
        group = Card("Application Preferences & System Tray")
        layout = group.body
        layout.setSpacing(10)

        self.chk_minimize_to_tray = QCheckBox("Minimize to Windows System Tray on close [X]")
        self.chk_start_minimized = QCheckBox("Start application minimized to System Tray")

        layout.addWidget(self.chk_minimize_to_tray)
        layout.addWidget(self.chk_start_minimized)

        # Save Button
        self.btn_save_settings = QPushButton("Save Moderation && Preferences")
        self.btn_save_settings.setProperty("class", "primary")
        self.btn_save_settings.clicked.connect(self._on_save_preferences)
        layout.addWidget(self.btn_save_settings)

        self.lbl_pref_status = StatusLabel("")
        self.lbl_pref_status.setProperty("class", "muted")
        layout.addWidget(self.lbl_pref_status)

        return group

    # -------------------------------------------------------------------------
    # Right Column: Memory Inspector
    # -------------------------------------------------------------------------

    def _create_memory_inspector_card(self) -> Card:
        group = Card("SQLite Conversation Memory Inspector")
        layout = group.body
        layout.setSpacing(10)

        # Table of active channels
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Active Conversation Sessions:"))
        top_row.addStretch()

        self.btn_refresh_memory = QPushButton("Refresh Sessions")
        self.btn_refresh_memory.clicked.connect(self._refresh_active_memory_channels)
        top_row.addWidget(self.btn_refresh_memory)

        layout.addLayout(top_row)

        self.table_channels = QTableWidget()
        self.table_channels.setColumnCount(3)
        self.table_channels.setHorizontalHeaderLabels(["Channel ID", "Messages", "Last Active"])
        self.table_channels.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_channels.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_channels.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_channels.verticalHeader().setVisible(False)
        self.table_channels.setMaximumHeight(140)
        self.table_channels.itemSelectionChanged.connect(self._on_memory_channel_selected)
        layout.addWidget(self.table_channels)

        # Detailed message viewer
        layout.addWidget(QLabel("Stored Context Turns for Selected Channel:"))
        self.table_messages = QTableWidget()
        self.table_messages.setColumnCount(3)
        self.table_messages.setHorizontalHeaderLabels(["Role", "Content", "Timestamp"])
        self.table_messages.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_messages.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_messages.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_messages.verticalHeader().setVisible(False)
        layout.addWidget(self.table_messages, stretch=1)

        # Actions Row
        actions_row = QHBoxLayout()
        self.btn_clear_channel = QPushButton("Clear Selected Channel")
        self.btn_clear_channel.clicked.connect(self._on_clear_channel_memory)

        self.btn_wipe_all = QPushButton("Wipe Entire Memory DB")
        self.btn_wipe_all.setProperty("class", "danger")
        self.btn_wipe_all.clicked.connect(self._on_wipe_entire_database)

        actions_row.addWidget(self.btn_clear_channel)
        actions_row.addWidget(self.btn_wipe_all)
        actions_row.addStretch()
        layout.addLayout(actions_row)

        self.lbl_memory_status = StatusLabel("")
        self.lbl_memory_status.setProperty("class", "muted")
        layout.addWidget(self.lbl_memory_status)

        return group

    # -------------------------------------------------------------------------
    # Moderation Logic & Callbacks
    # -------------------------------------------------------------------------

    def _load_mod_settings(self) -> None:
        s = self.mod_manager.settings
        self.chk_allow_dms.setChecked(s.allow_dms)
        idx = self.combo_rule_mode.findData(s.channel_rule_mode)
        if idx >= 0:
            self.combo_rule_mode.setCurrentIndex(idx)
        self.spin_rate_limit.setValue(s.rate_limit_per_minute)
        self.chk_minimize_to_tray.setChecked(s.minimize_to_tray_on_close)
        self.chk_start_minimized.setChecked(s.start_minimized)
        admin_id = self.main_window.config.admin_user_id
        self.txt_admin_id.setText(str(admin_id) if admin_id else "")

    def _on_rule_mode_changed(self) -> None:
        mode = self.combo_rule_mode.currentData()
        self.channels_checklist.setEnabled(mode != "all")

    def _refresh_mod_guilds(self) -> None:
        self.combo_mod_guilds.blockSignals(True)
        self.combo_mod_guilds.clear()

        guilds = self.main_window.runner.get_guilds()
        if not guilds:
            self.combo_mod_guilds.addItem("No connected servers", None)
            self.combo_mod_guilds.blockSignals(False)
            self._on_mod_guild_selected()
            return

        for g in guilds:
            self.combo_mod_guilds.addItem(f"{g.name}", g.id)

        self.combo_mod_guilds.blockSignals(False)
        self._on_mod_guild_selected()

    def _on_mod_guild_selected(self) -> None:
        self.channels_checklist.blockSignals(True)
        self.channels_checklist.clear()

        guild_id = self.combo_mod_guilds.currentData()
        if not guild_id:
            self.channels_checklist.blockSignals(False)
            return

        channels = self.main_window.runner.get_sendable_channels(guild_id)
        mode = self.combo_rule_mode.currentData()
        target_list = (
            self.mod_manager.settings.whitelisted_channels
            if mode == "whitelist"
            else self.mod_manager.settings.blacklisted_channels
        )

        for ch in channels:
            item = QListWidgetItem(f"#{ch.name} ({ch.id})")
            item.setData(Qt.ItemDataRole.UserRole, ch.id)
            item.setCheckState(
                Qt.CheckState.Checked if ch.id in target_list else Qt.CheckState.Unchecked
            )
            self.channels_checklist.addItem(item)

        self.channels_checklist.blockSignals(False)

    def _on_channel_check_changed(self, item: QListWidgetItem) -> None:
        channel_id = item.data(Qt.ItemDataRole.UserRole)
        is_checked = item.checkState() == Qt.CheckState.Checked
        mode = self.combo_rule_mode.currentData()

        if mode == "whitelist":
            if is_checked and channel_id not in self.mod_manager.settings.whitelisted_channels:
                self.mod_manager.settings.whitelisted_channels.append(channel_id)
            elif not is_checked and channel_id in self.mod_manager.settings.whitelisted_channels:
                self.mod_manager.settings.whitelisted_channels.remove(channel_id)
        elif mode == "blacklist":
            if is_checked and channel_id not in self.mod_manager.settings.blacklisted_channels:
                self.mod_manager.settings.blacklisted_channels.append(channel_id)
            elif not is_checked and channel_id in self.mod_manager.settings.blacklisted_channels:
                self.mod_manager.settings.blacklisted_channels.remove(channel_id)

    def _on_save_preferences(self) -> None:
        admin_text = self.txt_admin_id.text().strip()
        if admin_text and not admin_text.isdigit():
            self.lbl_pref_status.setText("Bot Admin User ID must be digits only (or empty for no admin).")
            self.lbl_pref_status.setStyleSheet("color: #f0b232;")
            return
        admin_id = int(admin_text or 0)
        if admin_id != self.main_window.config.admin_user_id:
            # The bot shares this config object, so the new admin applies immediately.
            self.main_window.config.save_admin_id(admin_id)

        self.mod_manager.settings.allow_dms = self.chk_allow_dms.isChecked()
        self.mod_manager.settings.channel_rule_mode = self.combo_rule_mode.currentData()
        self.mod_manager.settings.rate_limit_per_minute = self.spin_rate_limit.value()
        self.mod_manager.settings.minimize_to_tray_on_close = self.chk_minimize_to_tray.isChecked()
        self.mod_manager.settings.start_minimized = self.chk_start_minimized.isChecked()

        self.mod_manager.save()

        # Update bot instance if running
        if self.main_window.runner.bot and hasattr(self.main_window.runner.bot, "moderation_manager"):
            self.main_window.runner.bot.moderation_manager = self.mod_manager

        self.lbl_pref_status.setText("Settings saved successfully.")
        self.lbl_pref_status.setStyleSheet("color: #23a55a;")

    # -------------------------------------------------------------------------
    # Memory Inspector Logic
    # -------------------------------------------------------------------------

    def _refresh_active_memory_channels(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        async def fetch() -> None:
            try:
                channels = await self.db_manager.list_active_channels()
            except Exception as err:
                self._show_memory_error(err)
                return
            self.table_channels.setRowCount(len(channels))
            for row, c in enumerate(channels):
                ch_id = str(c["channel_id"])
                msgs = str(c["msg_count"])
                last = str(c["last_active"]) or "N/A"

                item_id = QTableWidgetItem(ch_id)
                item_id.setData(Qt.ItemDataRole.UserRole, c["channel_id"])
                item_msgs = QTableWidgetItem(msgs)
                item_msgs.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_last = QTableWidgetItem(last)

                self.table_channels.setItem(row, 0, item_id)
                self.table_channels.setItem(row, 1, item_msgs)
                self.table_channels.setItem(row, 2, item_last)

        loop.create_task(fetch())

    def _on_memory_channel_selected(self) -> None:
        selected = self.table_channels.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        item = self.table_channels.item(row, 0)
        if not item:
            return

        channel_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_memory_channel_id = channel_id

        async def load_details() -> None:
            try:
                turns = await self.db_manager.get_detailed_channel_history(channel_id, limit=40)
            except Exception as err:
                self._show_memory_error(err)
                return
            self.table_messages.setRowCount(len(turns))
            for r, t in enumerate(turns):
                role = t["role"].upper()
                content = t["content"]
                timestamp = str(t["timestamp"])

                item_role = QTableWidgetItem(role)
                item_role.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if role == "ASSISTANT":
                    item_role.setForeground(Qt.GlobalColor.cyan)
                else:
                    item_role.setForeground(Qt.GlobalColor.green)

                item_content = QTableWidgetItem(content)
                item_time = QTableWidgetItem(timestamp)

                self.table_messages.setItem(r, 0, item_role)
                self.table_messages.setItem(r, 1, item_content)
                self.table_messages.setItem(r, 2, item_time)

        asyncio.create_task(load_details())

    def _show_memory_error(self, err: Exception) -> None:
        logger.error("Memory inspector action failed: %s", err)
        self.lbl_memory_status.setText(f"Database error: {err}")
        self.lbl_memory_status.setStyleSheet("color: #da373c;")

    def _on_clear_channel_memory(self) -> None:
        if not self.selected_memory_channel_id:
            self.lbl_memory_status.setText("Select a channel session from the table first.")
            self.lbl_memory_status.setStyleSheet("color: #f0b232;")
            return

        channel_id = self.selected_memory_channel_id
        reply = QMessageBox.question(
            self,
            "Confirm Clear Channel Memory",
            f"Are you sure you want to delete all stored conversation history for channel {channel_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            async def clear() -> None:
                try:
                    await self.db_manager.clear_channel(channel_id)
                except Exception as err:
                    self._show_memory_error(err)
                    return
                self._refresh_active_memory_channels()
                self.table_messages.setRowCount(0)
                self.selected_memory_channel_id = None
                self.lbl_memory_status.setText(f"Cleared memory for channel {channel_id}.")
                self.lbl_memory_status.setStyleSheet("color: #23a55a;")

            asyncio.create_task(clear())

    def _on_wipe_entire_database(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Confirm Full Database Wipe",
            "DANGER: This will permanently purge ALL conversation history and VACUUM the database.\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            async def wipe() -> None:
                try:
                    deleted = await self.db_manager.clear_all()
                except Exception as err:
                    self._show_memory_error(err)
                    return
                self._refresh_active_memory_channels()
                self.table_messages.setRowCount(0)
                self.selected_memory_channel_id = None
                self.lbl_memory_status.setText(f"Wiped {deleted} messages. Database is now completely empty.")
                self.lbl_memory_status.setStyleSheet("color: #23a55a;")

            asyncio.create_task(wipe())
