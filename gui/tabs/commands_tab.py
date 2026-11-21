"""
Custom Commands & Plugin Studio Tab (Phase 4).
Enables users to build No-Code AI Prompt Shortcuts, Rich Embeds, and Static Commands,
as well as manage external Python Cog plugins with live reloading.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
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
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import Card, StatusLabel
from bot.custom_commands import CustomCommand, CustomCommandManager
from bot.plugins import PluginManager

if TYPE_CHECKING:
    from gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class CommandsTab(QWidget):
    """Custom Command Builder & Python Cog Plugin Management Studio."""

    def __init__(self, main_window: MainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.cmd_manager = CustomCommandManager()
        self.plugin_manager = PluginManager()

        self.selected_cmd: CustomCommand | None = None

        self._init_ui()
        self._refresh_command_list()
        self._refresh_plugins_table()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(16)

        # Left Column: No-Code Command Studio (55% width)
        left_box = self._create_command_studio_card()

        # Right Column: Python Cog Plugin Manager (45% width)
        right_box = self._create_plugin_manager_card()

        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 11)
        splitter.setStretchFactor(1, 9)

        layout.addWidget(splitter)

    # -------------------------------------------------------------------------
    # Left Column: Custom Command Studio
    # -------------------------------------------------------------------------

    def _create_command_studio_card(self) -> Card:
        group = Card("No-Code Custom Slash Command Studio")
        layout = group.body
        layout.setSpacing(10)

        # Top Bar: List & New/Delete buttons
        list_nav_row = QHBoxLayout()
        list_nav_row.addWidget(QLabel("Registered Custom Commands:"))
        list_nav_row.addStretch()

        self.btn_new_cmd = QPushButton("New Command")
        self.btn_new_cmd.clicked.connect(self._on_new_command_clicked)
        list_nav_row.addWidget(self.btn_new_cmd)

        self.btn_del_cmd = QPushButton("Delete")
        self.btn_del_cmd.setProperty("class", "danger")
        self.btn_del_cmd.clicked.connect(self._on_delete_command_clicked)
        list_nav_row.addWidget(self.btn_del_cmd)

        layout.addLayout(list_nav_row)

        self.cmd_list_widget = QListWidget()
        self.cmd_list_widget.setMaximumHeight(110)
        self.cmd_list_widget.currentRowChanged.connect(self._on_command_selected_from_list)
        layout.addWidget(self.cmd_list_widget)

        # Editor Form Frame
        editor_frame = QFrame()
        editor_layout = QVBoxLayout(editor_frame)
        editor_layout.setContentsMargins(0, 4, 0, 0)
        editor_layout.setSpacing(8)

        # Command Name & Type
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Command Name (/):"))
        self.txt_cmd_name = QLineEdit()
        self.txt_cmd_name.setPlaceholderText("e.g. roast or translate")
        row1.addWidget(self.txt_cmd_name, stretch=1)

        row1.addWidget(QLabel("Type:"))
        self.combo_cmd_type = QComboBox()
        self.combo_cmd_type.addItem("AI Prompt Shortcut", "ai_prompt")
        self.combo_cmd_type.addItem("Rich Embed Card", "rich_embed")
        self.combo_cmd_type.addItem("Static Text Response", "static_text")
        self.combo_cmd_type.currentIndexChanged.connect(self._on_command_type_changed)
        row1.addWidget(self.combo_cmd_type, stretch=1)
        editor_layout.addLayout(row1)

        # Description
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Description:"))
        self.txt_cmd_desc = QLineEdit()
        self.txt_cmd_desc.setPlaceholderText("Brief description visible in Discord's slash command menu")
        row2.addWidget(self.txt_cmd_desc)
        editor_layout.addLayout(row2)

        # Dynamic Field: Prompt Template / Static Text
        self.lbl_content_title = QLabel("Prompt Template:")
        editor_layout.addWidget(self.lbl_content_title)

        self.txt_cmd_content = QPlainTextEdit()
        self.txt_cmd_content.setPlaceholderText(
            "Enter prompt template. You can use {query} for user input, {user} for user name, and {bot} for bot name."
        )
        editor_layout.addWidget(self.txt_cmd_content, stretch=1)

        # Embed Fields Row (Hidden unless rich_embed)
        self.embed_fields_row = QHBoxLayout()
        self.embed_fields_row.addWidget(QLabel("Embed Title:"))
        self.txt_embed_title = QLineEdit()
        self.txt_embed_title.setPlaceholderText("e.g. Server Rules")
        self.embed_fields_row.addWidget(self.txt_embed_title, stretch=2)

        self.embed_fields_row.addWidget(QLabel("Color:"))
        self.txt_embed_color = QLineEdit()
        self.txt_embed_color.setText("#5865f2")
        self.txt_embed_color.setMaximumWidth(90)
        self.embed_fields_row.addWidget(self.txt_embed_color, stretch=1)
        editor_layout.addLayout(self.embed_fields_row)

        # Options Row: Ephemeral & Enabled
        opt_row = QHBoxLayout()
        self.chk_ephemeral = QCheckBox("Ephemeral (only visible to command user)")
        self.chk_enabled = QCheckBox("Command Enabled")
        self.chk_enabled.setChecked(True)
        self.chk_web_search = QCheckBox("Search the web for {query} first")
        self.chk_web_search.setToolTip(
            "Looks up {query} before the AI answers. Works with any model. Needs Web Search turned on in AI Models."
        )

        opt_row.addWidget(self.chk_ephemeral)
        opt_row.addWidget(self.chk_web_search)
        opt_row.addWidget(self.chk_enabled)
        opt_row.addStretch()
        editor_layout.addLayout(opt_row)

        # Actions Row
        action_row = QHBoxLayout()
        self.btn_save_cmd = QPushButton("Save Command")
        self.btn_save_cmd.setProperty("class", "primary")
        self.btn_save_cmd.clicked.connect(self._on_save_command_clicked)

        self.btn_sync_tree = QPushButton("Sync to Discord Gateway")
        self.btn_sync_tree.clicked.connect(self._on_sync_discord_tree)

        action_row.addWidget(self.btn_save_cmd)
        action_row.addWidget(self.btn_sync_tree)
        action_row.addStretch()
        editor_layout.addLayout(action_row)

        layout.addWidget(editor_frame, stretch=1)

        self.lbl_cmd_status = StatusLabel("")
        self.lbl_cmd_status.setWordWrap(True)
        self.lbl_cmd_status.setProperty("class", "muted")
        layout.addWidget(self.lbl_cmd_status)

        return group

    # -------------------------------------------------------------------------
    # Right Column: Modular Plugin Manager
    # -------------------------------------------------------------------------

    def _create_plugin_manager_card(self) -> Card:
        group = Card("Modular Python Cog Plugins")
        layout = group.body
        layout.setSpacing(10)

        desc = QLabel(
            "Drop custom <code>.py</code> Discord cogs into the <code>plugins/</code> directory. "
            "Manage and reload them live on the gateway without restarting the application!"
        )
        desc.setWordWrap(True)
        desc.setProperty("class", "muted")
        layout.addWidget(desc)

        # Table of plugins
        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(3)
        self.plugin_table.setHorizontalHeaderLabels(["Plugin Name", "Status", "Actions"])
        self.plugin_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.plugin_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.plugin_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.plugin_table.verticalHeader().setVisible(False)
        self.plugin_table.verticalHeader().setDefaultSectionSize(44)  # room for the Load/Reload buttons
        layout.addWidget(self.plugin_table, stretch=1)

        # Plugin Tools Row
        tool_row = QHBoxLayout()
        self.btn_open_folder = QPushButton("Open Plugins Folder")
        self.btn_open_folder.clicked.connect(self._on_open_plugins_folder)

        self.btn_refresh_plugins = QPushButton("Refresh Plugins")
        self.btn_refresh_plugins.clicked.connect(self._refresh_plugins_table)

        tool_row.addWidget(self.btn_open_folder)
        tool_row.addWidget(self.btn_refresh_plugins)
        tool_row.addStretch()
        layout.addLayout(tool_row)

        self.lbl_plugin_status = StatusLabel("")
        self.lbl_plugin_status.setWordWrap(True)
        self.lbl_plugin_status.setProperty("class", "muted")
        layout.addWidget(self.lbl_plugin_status)

        return group

    # -------------------------------------------------------------------------
    # Command Studio Logic
    # -------------------------------------------------------------------------

    def _refresh_command_list(self) -> None:
        self.cmd_list_widget.clear()
        for cmd in self.cmd_manager.commands:
            type_tag = {
                "ai_prompt": "AI",
                "rich_embed": "Embed",
                "static_text": "Static",
            }.get(cmd.command_type, "Custom")
            status_tag = " [DISABLED]" if not cmd.enabled else ""
            item = QListWidgetItem(f"/{cmd.name}  [{type_tag}]{status_tag} — {cmd.description}")
            item.setData(Qt.ItemDataRole.UserRole, cmd.name)
            self.cmd_list_widget.addItem(item)

        if self.cmd_manager.commands:
            self.cmd_list_widget.setCurrentRow(0)

    def _on_command_selected_from_list(self, row: int) -> None:
        if row < 0 or row >= len(self.cmd_manager.commands):
            return
        cmd = self.cmd_manager.commands[row]
        self.selected_cmd = cmd

        self.txt_cmd_name.setText(cmd.name)
        self.txt_cmd_desc.setText(cmd.description)

        idx = self.combo_cmd_type.findData(cmd.command_type)
        if idx >= 0:
            self.combo_cmd_type.setCurrentIndex(idx)

        if cmd.command_type == "ai_prompt":
            self.txt_cmd_content.setPlainText(cmd.prompt_template)
        else:
            self.txt_cmd_content.setPlainText(cmd.static_content)

        self.txt_embed_title.setText(cmd.embed_title)
        self.txt_embed_color.setText(cmd.embed_color)
        self.chk_ephemeral.setChecked(cmd.ephemeral)
        self.chk_enabled.setChecked(cmd.enabled)
        self.chk_web_search.setChecked(cmd.web_search)

        self._on_command_type_changed()

    def _on_command_type_changed(self) -> None:
        cmd_type = self.combo_cmd_type.currentData()
        is_embed = (cmd_type == "rich_embed")
        is_ai = (cmd_type == "ai_prompt")
        self.chk_web_search.setVisible(is_ai)

        # Toggle embed fields
        for i in range(self.embed_fields_row.count()):
            widget = self.embed_fields_row.itemAt(i).widget()
            if widget:
                widget.setVisible(is_embed)

        if is_ai:
            self.lbl_content_title.setText("AI Prompt Template ({query}, {user}, {bot}):")
            self.txt_cmd_content.setPlaceholderText("e.g. Roast '{query}' playfully in tsundere style...")
        elif is_embed:
            self.lbl_content_title.setText("Embed Body Description:")
            self.txt_cmd_content.setPlaceholderText("Enter the content of the embed card...")
        else:
            self.lbl_content_title.setText("Static Message Text:")
            self.txt_cmd_content.setPlaceholderText("Enter the exact message to reply with...")

    def _on_new_command_clicked(self) -> None:
        self.cmd_list_widget.clearSelection()
        self.selected_cmd = None
        self.txt_cmd_name.setText("")
        self.txt_cmd_desc.setText("")
        self.combo_cmd_type.setCurrentIndex(0)
        self.txt_cmd_content.setPlainText("")
        self.txt_embed_title.setText("")
        self.txt_embed_color.setText("#5865f2")
        self.chk_ephemeral.setChecked(False)
        self.chk_enabled.setChecked(True)
        self.chk_web_search.setChecked(False)
        self.txt_cmd_name.setFocus()
        self.lbl_cmd_status.setText("Fill in the fields above and click 'Save Command'.")
        self.lbl_cmd_status.setStyleSheet("color: #949ba4;")

    def _on_delete_command_clicked(self) -> None:
        row = self.cmd_list_widget.currentRow()
        if row < 0 or row >= len(self.cmd_manager.commands):
            return

        cmd = self.cmd_manager.commands[row]
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete custom command '/{cmd.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cmd_manager.remove_command(cmd.name)
            self._refresh_command_list()
            self.lbl_cmd_status.setText(f"Command '/{cmd.name}' deleted. Sync to update Discord.")
            self.lbl_cmd_status.setStyleSheet("color: #23a55a;")

    def _on_save_command_clicked(self) -> None:
        name = self.txt_cmd_name.text().strip().lower()
        desc = self.txt_cmd_desc.text().strip()
        cmd_type = self.combo_cmd_type.currentData()
        content = self.txt_cmd_content.toPlainText().strip()
        embed_title = self.txt_embed_title.text().strip()
        embed_color = self.txt_embed_color.text().strip()
        ephemeral = self.chk_ephemeral.isChecked()
        enabled = self.chk_enabled.isChecked()

        cmd = CustomCommand(
            name=name,
            description=desc,
            command_type=cmd_type,
            prompt_template=content if cmd_type == "ai_prompt" else "",
            static_content=content if cmd_type != "ai_prompt" else "",
            embed_title=embed_title,
            embed_color=embed_color,
            ephemeral=ephemeral,
            enabled=enabled,
            web_search=cmd_type == "ai_prompt" and self.chk_web_search.isChecked(),
        )

        try:
            self.cmd_manager.add_command(cmd)
            self._refresh_command_list()
            self.lbl_cmd_status.setText(f"Saved command '/{cmd.name}'! Click 'Sync to Discord Gateway' to activate.")
            self.lbl_cmd_status.setStyleSheet("color: #23a55a;")
        except ValueError as err:
            self.lbl_cmd_status.setText(f"Validation error: {err}")
            self.lbl_cmd_status.setStyleSheet("color: #f0b232;")

    def _on_sync_discord_tree(self) -> None:
        if not self.main_window.runner.is_running:
            self.lbl_cmd_status.setText("Start the bot first to sync commands with Discord Gateway.")
            self.lbl_cmd_status.setStyleSheet("color: #f0b232;")
            return

        bot = self.main_window.runner.bot
        if not bot:
            return

        self.btn_sync_tree.setEnabled(False)
        self.lbl_cmd_status.setText("Registering and syncing commands with Discord...")
        self.lbl_cmd_status.setStyleSheet("color: #5865f2;")

        async def sync() -> None:
            try:
                count = await self.cmd_manager.register_commands_to_bot(bot)
                synced = await bot.tree.sync()
                self.lbl_cmd_status.setText(f"Successfully synced {len(synced)} command(s) with Discord!")
                self.lbl_cmd_status.setStyleSheet("color: #23a55a;")
            except Exception as err:
                self.lbl_cmd_status.setText(f"Gateway sync failed: {err}")
                self.lbl_cmd_status.setStyleSheet("color: #da373c;")
            finally:
                self.btn_sync_tree.setEnabled(True)

        asyncio.create_task(sync())

    # -------------------------------------------------------------------------
    # Plugin Manager Logic
    # -------------------------------------------------------------------------

    def _refresh_plugins_table(self) -> None:
        bot = self.main_window.runner.bot
        plugins = self.plugin_manager.list_plugins(bot)
        self.plugin_table.setRowCount(len(plugins))

        for row, p in enumerate(plugins):
            name = str(p["name"])
            is_loaded = bool(p["is_loaded"])
            desc = str(p["description"])

            # Column 0: Name & Doc
            item_name = QTableWidgetItem(f"{name}\n{desc}")
            item_name.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.plugin_table.setItem(row, 0, item_name)

            # Column 1: Status badge
            status_text = "LOADED" if is_loaded else "UNLOADED"
            status_color = "#23a55a" if is_loaded else "#949ba4"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(Qt.GlobalColor.white)
            self.plugin_table.setItem(row, 1, item_status)

            # Column 2: Actions Frame
            btn_frame = QWidget()
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            btn_toggle = QPushButton("Unload" if is_loaded else "Load")
            btn_toggle.clicked.connect(lambda _, n=name, loaded=is_loaded: self._on_toggle_plugin(n, loaded))

            btn_reload = QPushButton("Reload")
            btn_reload.setEnabled(is_loaded)
            btn_reload.clicked.connect(lambda _, n=name: self._on_reload_plugin(n))

            btn_layout.addWidget(btn_toggle)
            btn_layout.addWidget(btn_reload)
            self.plugin_table.setCellWidget(row, 2, btn_frame)

    def _on_toggle_plugin(self, name: str, is_loaded: bool) -> None:
        if not self.main_window.runner.is_running:
            self.lbl_plugin_status.setText("Start the bot first to load/unload cogs.")
            self.lbl_plugin_status.setStyleSheet("color: #f0b232;")
            return

        bot = self.main_window.runner.bot
        if not bot:
            return

        async def toggle() -> None:
            try:
                if is_loaded:
                    await self.plugin_manager.unload_plugin(bot, name)
                    self.lbl_plugin_status.setText(f"Unloaded plugin '{name}'.")
                else:
                    await self.plugin_manager.load_plugin(bot, name)
                    self.lbl_plugin_status.setText(f"Loaded plugin '{name}'.")
                self.lbl_plugin_status.setStyleSheet("color: #23a55a;")
                self._refresh_plugins_table()
            except Exception as err:
                self.lbl_plugin_status.setText(f"Plugin action failed: {err}")
                self.lbl_plugin_status.setStyleSheet("color: #da373c;")

        asyncio.create_task(toggle())

    def _on_reload_plugin(self, name: str) -> None:
        if not self.main_window.runner.is_running:
            return
        bot = self.main_window.runner.bot
        if not bot:
            return

        async def reload() -> None:
            try:
                await self.plugin_manager.reload_plugin(bot, name)
                self.lbl_plugin_status.setText(f"Reloaded plugin '{name}' successfully!")
                self.lbl_plugin_status.setStyleSheet("color: #23a55a;")
                self._refresh_plugins_table()
            except Exception as err:
                self.lbl_plugin_status.setText(f"Reload failed: {err}")
                self.lbl_plugin_status.setStyleSheet("color: #da373c;")

        asyncio.create_task(reload())

    def _on_open_plugins_folder(self) -> None:
        abs_path = os.path.abspath(self.plugin_manager.plugins_dir)
        QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
