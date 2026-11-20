"""
Bot Identity & Multi-Server Chat Tab (Phase 2).
Provides avatar customization, status/activity controls, multi-server channel inspection,
and the ability to send messages/replies through the bot into any accessible Discord channel.
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
from urllib.parse import quote
from typing import TYPE_CHECKING

import discord
from PySide6.QtCore import QObject, Qt, QTimer, QUrl, QUrlQuery, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QImage,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import Card, StatusLabel
from bot.config import BotConfig
from bot.runner import BotRunner, BotState

if TYPE_CHECKING:
    from gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class MessageSignalEmitter(QObject):
    """Bridge for safely dispatching discord.Message events into the Qt GUI thread."""

    message_received = Signal(object)


class BotControlTab(QWidget):
    """Bot Identity (Avatar, Presence) and Multi-Server Remote Chatting Interface."""

    def __init__(self, main_window: MainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.config: BotConfig = main_window.config
        self.runner: BotRunner = main_window.runner

        self.selected_avatar_path: str | None = None
        self.selected_attachment_path: str | None = None
        self.selected_channel_id: int | None = None

        # Message signal bridge
        self.msg_emitter = MessageSignalEmitter(self)
        self.msg_emitter.message_received.connect(self._on_live_message_received)

        # Connect runner message callback
        self.runner.on_message_callback = self._handle_runner_message

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(16)

        # Left Column: Identity & Presence (Width ~340px)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        left_layout.addWidget(self._create_avatar_card())
        left_layout.addWidget(self._create_presence_card())
        left_layout.addStretch()

        # Right Column: Multi-Server Remote Chat & Inspector (Expands)
        right_widget = self._create_server_chat_card()

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    # -------------------------------------------------------------------------
    # Avatar Section
    # -------------------------------------------------------------------------

    def _create_avatar_card(self) -> Card:
        group = Card("Bot Profile & Avatar")
        layout = group.body
        layout.setSpacing(10)

        # Avatar Preview
        preview_row = QHBoxLayout()
        self.avatar_preview = QLabel()
        self.avatar_preview.setFixedSize(88, 88)
        self.avatar_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_preview.setStyleSheet(
            "background-color: #1e1f22; border-radius: 44px; color: #949ba4;"
        )
        self.avatar_preview.setText("No Avatar")

        avatar_info_col = QVBoxLayout()
        self.lbl_avatar_hint = QLabel("Select a PNG, JPG, or GIF to update the bot's avatar.")
        self.lbl_avatar_hint.setWordWrap(True)
        self.lbl_avatar_hint.setProperty("class", "muted")

        self.btn_browse_avatar = QPushButton("Browse Image...")
        self.btn_browse_avatar.clicked.connect(self._on_browse_avatar)

        avatar_info_col.addWidget(self.lbl_avatar_hint)
        avatar_info_col.addWidget(self.btn_browse_avatar)

        preview_row.addWidget(self.avatar_preview)
        preview_row.addLayout(avatar_info_col)
        layout.addLayout(preview_row)

        self.selected_avatar_lbl = StatusLabel("")
        self.selected_avatar_lbl.setWordWrap(True)
        self.selected_avatar_lbl.setProperty("class", "muted")
        layout.addWidget(self.selected_avatar_lbl)

        btn_row = QHBoxLayout()
        self.btn_apply_avatar = QPushButton("Apply Avatar")
        self.btn_apply_avatar.setProperty("class", "primary")
        self.btn_apply_avatar.setEnabled(False)
        self.btn_apply_avatar.clicked.connect(self._on_apply_avatar)

        self.btn_fetch_avatar = QPushButton("Fetch Current")
        self.btn_fetch_avatar.clicked.connect(self._on_fetch_current_avatar)

        btn_row.addWidget(self.btn_apply_avatar)
        btn_row.addWidget(self.btn_fetch_avatar)
        layout.addLayout(btn_row)

        rate_limit_notice = QLabel("Note: Discord limits avatar changes to twice per 10 minutes.")
        rate_limit_notice.setProperty("class", "muted")
        rate_limit_notice.setWordWrap(True)
        layout.addWidget(rate_limit_notice)

        self.avatar_status_lbl = StatusLabel("")
        self.avatar_status_lbl.setWordWrap(True)
        layout.addWidget(self.avatar_status_lbl)

        return group

    def _on_browse_avatar(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Bot Avatar Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif)",
        )
        if file_path:
            self.selected_avatar_path = file_path
            self.selected_avatar_lbl.setText(f"Selected: {os.path.basename(file_path)}")
            self.btn_apply_avatar.setEnabled(self.runner.is_running)

            pix = QPixmap(file_path)
            if not pix.isNull():
                self.avatar_preview.setPixmap(
                    pix.scaled(
                        88,
                        88,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

    def _on_fetch_current_avatar(self) -> None:
        if not self.runner.is_running:
            self.avatar_status_lbl.setText("Start the bot first to fetch current avatar.")
            self.avatar_status_lbl.setStyleSheet("color: #f0b232;")
            return

        async def fetch() -> None:
            self.avatar_status_lbl.setText("Fetching avatar...")
            raw_bytes = await self.runner.fetch_avatar_bytes()
            if raw_bytes:
                pix = QPixmap()
                pix.loadFromData(raw_bytes)
                self.avatar_preview.setPixmap(
                    pix.scaled(
                        88,
                        88,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.avatar_status_lbl.setText("Avatar loaded.")
                self.avatar_status_lbl.setStyleSheet("color: #23a55a;")
            else:
                self.avatar_status_lbl.setText("Bot has default Discord avatar.")
                self.avatar_status_lbl.setStyleSheet("color: #949ba4;")

        asyncio.create_task(fetch())

    def _on_apply_avatar(self) -> None:
        if not self.selected_avatar_path or not os.path.exists(self.selected_avatar_path):
            self.avatar_status_lbl.setText("Please select a valid image file.")
            self.avatar_status_lbl.setStyleSheet("color: #f0b232;")
            return

        if not self.runner.is_running:
            self.avatar_status_lbl.setText("Bot must be online to update avatar.")
            self.avatar_status_lbl.setStyleSheet("color: #f0b232;")
            return

        self.btn_apply_avatar.setEnabled(False)
        self.avatar_status_lbl.setText("Uploading avatar to Discord...")
        self.avatar_status_lbl.setStyleSheet("color: #949ba4;")

        async def upload() -> None:
            try:
                with open(self.selected_avatar_path, "rb") as f:
                    image_bytes = f.read()
                await self.runner.update_avatar(image_bytes)
                self.avatar_status_lbl.setText("Avatar updated successfully!")
                self.avatar_status_lbl.setStyleSheet("color: #23a55a;")
            except discord.HTTPException as err:
                self.avatar_status_lbl.setText(f"Discord Error: {err}")
                self.avatar_status_lbl.setStyleSheet("color: #da373c;")
            except Exception as err:
                self.avatar_status_lbl.setText(f"Error: {err}")
                self.avatar_status_lbl.setStyleSheet("color: #da373c;")
            finally:
                self.btn_apply_avatar.setEnabled(self.runner.is_running)

        asyncio.create_task(upload())

    # -------------------------------------------------------------------------
    # Presence & Status Section
    # -------------------------------------------------------------------------

    def _create_presence_card(self) -> Card:
        group = Card("Status & Activity Presence")
        layout = group.body
        layout.setSpacing(10)

        # Status mode
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Online", "Idle", "Do Not Disturb", "Invisible"])
        status_row.addWidget(self.combo_status, stretch=1)
        layout.addLayout(status_row)

        # Activity Type
        activity_type_row = QHBoxLayout()
        activity_type_row.addWidget(QLabel("Activity:"))
        self.combo_activity = QComboBox()
        self.combo_activity.addItems(["Playing", "Listening", "Watching", "Streaming", "Competing", "Custom"])
        activity_type_row.addWidget(self.combo_activity, stretch=1)
        layout.addLayout(activity_type_row)

        # Activity Text
        layout.addWidget(QLabel("Activity Status Text:"))
        self.txt_activity = QLineEdit()
        self.txt_activity.setPlaceholderText("e.g. @ me to chat! or with Ollama 3.5")
        self.txt_activity.setText(self.config.presence_text)
        layout.addWidget(self.txt_activity)

        self.btn_apply_presence = QPushButton("Apply Presence")
        self.btn_apply_presence.setProperty("class", "primary")
        self.btn_apply_presence.setEnabled(False)  # enabled once the bot is ONLINE
        self.btn_apply_presence.clicked.connect(self._on_apply_presence)
        layout.addWidget(self.btn_apply_presence)

        self.presence_status_lbl = StatusLabel("")
        self.presence_status_lbl.setWordWrap(True)
        layout.addWidget(self.presence_status_lbl)

        return group

    def _on_apply_presence(self) -> None:
        if not self.runner.is_running:
            self.presence_status_lbl.setText("Bot must be online to update presence.")
            self.presence_status_lbl.setStyleSheet("color: #f0b232;")
            return

        status = self.combo_status.currentText()
        act_type = self.combo_activity.currentText()
        text = self.txt_activity.text()

        async def apply() -> None:
            try:
                await self.runner.update_presence(status, act_type, text)
                self.presence_status_lbl.setText(f"Presence set to {status} ({act_type} {text})")
                self.presence_status_lbl.setStyleSheet("color: #23a55a;")
            except Exception as err:
                self.presence_status_lbl.setText(f"Failed: {err}")
                self.presence_status_lbl.setStyleSheet("color: #da373c;")

        asyncio.create_task(apply())

    # -------------------------------------------------------------------------
    # Multi-Server Explorer & Remote Sender
    # -------------------------------------------------------------------------

    def _create_server_chat_card(self) -> Card:
        group = Card("Multi-Server Channel Explorer & Remote Chat")
        layout = group.body
        layout.setSpacing(10)

        # Server & Channel Navigation Header
        nav_box = QFrame()
        nav_box.setProperty("class", "inset")
        nav_layout = QHBoxLayout(nav_box)
        nav_layout.setContentsMargins(10, 8, 10, 8)
        nav_layout.setSpacing(8)

        nav_layout.addWidget(QLabel("Server:"))
        self.combo_guilds = QComboBox()
        self.combo_guilds.setMinimumWidth(180)
        self.combo_guilds.currentIndexChanged.connect(self._on_guild_selected)
        nav_layout.addWidget(self.combo_guilds, stretch=1)

        self.btn_refresh_servers = QPushButton("Refresh")
        self.btn_refresh_servers.clicked.connect(self.refresh_guilds)
        nav_layout.addWidget(self.btn_refresh_servers)

        nav_layout.addWidget(QLabel("Channel:"))
        self.combo_channels = QComboBox()
        self.combo_channels.setMinimumWidth(180)
        self.combo_channels.currentIndexChanged.connect(self._on_channel_selected)
        nav_layout.addWidget(self.combo_channels, stretch=1)

        self.btn_fetch_history = QPushButton("Load Feed")
        self.btn_fetch_history.clicked.connect(self._on_fetch_feed_clicked)
        nav_layout.addWidget(self.btn_fetch_history)

        layout.addWidget(nav_box)

        # Live Message Feed Area
        self.feed_browser = QTextBrowser()
        self.feed_browser.setPlaceholderText("Pick a server and channel, then Load Feed to see recent messages.")
        self.feed_browser.setOpenLinks(False)
        self.feed_browser.setOpenExternalLinks(False)
        self.feed_browser.anchorClicked.connect(self._on_feed_anchor_clicked)
        layout.addWidget(self.feed_browser, stretch=1)

        # Speak-As-Bot Sender Box
        sender_frame = QFrame()
        sender_frame.setProperty("class", "inset")
        sender_layout = QVBoxLayout(sender_frame)
        sender_layout.setContentsMargins(12, 12, 12, 12)
        sender_layout.setSpacing(8)

        # Top tools in sender: Reply ID and Attachments
        tools_row = QHBoxLayout()
        tools_row.addWidget(QLabel("Reply to Msg ID:"))
        self.txt_reply_id = QLineEdit()
        self.txt_reply_id.setPlaceholderText("Click Reply on a feed message")
        self.txt_reply_id.setMaximumWidth(160)
        tools_row.addWidget(self.txt_reply_id)

        self.btn_attach = QPushButton("Attach File")
        self.btn_attach.clicked.connect(self._on_browse_attachment)
        tools_row.addWidget(self.btn_attach)

        self.lbl_attachment_name = StatusLabel("")
        self.lbl_attachment_name.setProperty("class", "muted")
        tools_row.addWidget(self.lbl_attachment_name)

        self.btn_clear_attachment = QPushButton("Remove")
        self.btn_clear_attachment.setVisible(False)
        self.btn_clear_attachment.clicked.connect(self._clear_attachment)
        tools_row.addWidget(self.btn_clear_attachment)

        tools_row.addStretch()
        sender_layout.addLayout(tools_row)

        # Interactive Reply Target Banner
        self.reply_banner = QFrame()
        self.reply_banner.setProperty("class", "replyBanner")
        self.reply_banner.setVisible(False)
        banner_layout = QHBoxLayout(self.reply_banner)
        banner_layout.setContentsMargins(10, 6, 10, 6)
        banner_layout.setSpacing(6)

        self.lbl_reply_info = StatusLabel("")
        self.lbl_reply_info.setTextFormat(Qt.TextFormat.PlainText)  # shows a Discord name; never render it as HTML
        self.lbl_reply_info.setStyleSheet("color: #5865f2; font-weight: bold; font-size: 12px;")
        banner_layout.addWidget(self.lbl_reply_info, stretch=1)

        self.btn_cancel_reply = QPushButton("Cancel Reply")
        self.btn_cancel_reply.setStyleSheet("background-color: transparent; color: #949ba4; font-size: 11px;")
        self.btn_cancel_reply.clicked.connect(self._clear_reply_target)
        banner_layout.addWidget(self.btn_cancel_reply)

        sender_layout.addWidget(self.reply_banner)

        # Message input
        self.txt_message_input = QPlainTextEdit()
        self.txt_message_input.setPlaceholderText("Type a message to send as the bot... (Shift+Enter for new line)")
        self.txt_message_input.setMaximumHeight(80)
        sender_layout.addWidget(self.txt_message_input)

        # Sender Actions
        send_row = QHBoxLayout()
        self.chk_split_messages = QCheckBox("Split newlines into separate messages (natural chat pacing)")
        self.chk_split_messages.setChecked(True)
        send_row.addWidget(self.chk_split_messages)

        send_row.addStretch()

        self.btn_send_message = QPushButton("Send as Bot")
        self.btn_send_message.setProperty("class", "primary")
        self.btn_send_message.setEnabled(False)  # enabled once the bot is ONLINE
        self.btn_send_message.clicked.connect(self._on_send_message_clicked)
        send_row.addWidget(self.btn_send_message)

        sender_layout.addLayout(send_row)
        layout.addWidget(sender_frame)

        self.chat_status_lbl = StatusLabel("")
        layout.addWidget(self.chat_status_lbl)

        return group

    # -------------------------------------------------------------------------
    # Server & Channel Navigation Callbacks
    # -------------------------------------------------------------------------

    def refresh_guilds(self) -> None:
        """Populates server dropdown with servers where the bot is currently joined."""
        self.combo_guilds.blockSignals(True)
        self.combo_guilds.clear()

        guilds = self.runner.get_guilds()
        if not guilds:
            self.combo_guilds.addItem("No connected servers", None)
            self.combo_guilds.blockSignals(False)
            self._on_guild_selected()
            return

        for g in guilds:
            self.combo_guilds.addItem(f"{g.name} ({g.member_count} members)", g.id)

        self.combo_guilds.blockSignals(False)
        self._on_guild_selected()

    def _on_guild_selected(self) -> None:
        """When a server is selected, populate its accessible text channels."""
        self.combo_channels.blockSignals(True)
        self.combo_channels.clear()

        guild_id = self.combo_guilds.currentData()
        if not guild_id:
            self.combo_channels.addItem("No channels available", None)
            self.combo_channels.blockSignals(False)
            self.selected_channel_id = None
            return

        channels = self.runner.get_sendable_channels(guild_id)
        if not channels:
            self.combo_channels.addItem("No sendable channels", None)
            self.combo_channels.blockSignals(False)
            self.selected_channel_id = None
            return

        for ch in channels:
            prefix = "#" if hasattr(ch, "text") or isinstance(ch, discord.TextChannel) else "thread:"
            self.combo_channels.addItem(f"{prefix} {ch.name}", ch.id)

        self.combo_channels.blockSignals(False)
        self._on_channel_selected()

    def _on_channel_selected(self) -> None:
        self.selected_channel_id = self.combo_channels.currentData()
        if self.selected_channel_id:
            self._load_channel_history(self.selected_channel_id)

    def _on_fetch_feed_clicked(self) -> None:
        if self.selected_channel_id:
            self._load_channel_history(self.selected_channel_id)

    def _load_channel_history(self, channel_id: int) -> None:
        if not self.runner.is_running:
            self.feed_browser.setHtml(
                "<p style='color: #949ba4; font-style: italic;'>Start the bot to view live server feeds.</p>"
            )
            return

        self.feed_browser.setHtml("<p style='color: #949ba4;'>Loading recent messages...</p>")

        async def load() -> None:
            msgs = await self.runner.fetch_channel_history(channel_id, limit=30)
            html_parts = []
            for m in msgs:
                html_parts.append(self._format_message_html(m))

            if html_parts:
                self.feed_browser.setHtml("".join(html_parts))
                # Scroll to bottom
                cursor = self.feed_browser.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.feed_browser.setTextCursor(cursor)
            else:
                self.feed_browser.setHtml(
                    "<p style='color: #949ba4; font-style: italic;'>No recent messages found in this channel.</p>"
                )

        asyncio.create_task(load())

    def _format_message_html(self, msg: discord.Message) -> str:
        is_bot = (self.runner.bot and self.runner.bot.user and msg.author.id == self.runner.bot.user.id)
        author_color = "#5865f2" if is_bot else "#23a55a"
        time_str = msg.created_at.strftime("%H:%M:%S")

        # Sanitize HTML in content
        safe_content = html.escape(msg.clean_content, quote=False).replace("\n", "<br>")

        attachment_str = ""
        if msg.attachments:
            att_names = [html.escape(a.filename) for a in msg.attachments]
            attachment_str = f"<br><span style='color: #f0b232; font-size: 11px;'>Attachments: {', '.join(att_names)}</span>"

        reply_str = ""
        if msg.reference and msg.reference.message_id:
            reply_str = f" <span style='color: #949ba4; font-size: 11px;'>(reply to {msg.reference.message_id})</span>"

        # Names and file names come from Discord users: escape them so they can't inject links or markup.
        author_html = html.escape(msg.author.display_name)
        clean_author = quote(msg.author.display_name, safe="")
        author_id = msg.author.id
        msg_id = msg.id

        return (
            f"<div style='margin-bottom: 8px; padding: 4px 6px; border-radius: 6px; background-color: #16171a;'>"
            f"<span style='color: #949ba4; font-size: 11px;'>[{time_str}]</span> "
            f"<a href='action://mention?id={author_id}&name={clean_author}' "
            f"title='Click to mention @{author_html}' "
            f"style='color: {author_color}; font-weight: bold; text-decoration: none;'>{author_html}</a>{reply_str}: "
            f"<span style='color: #dbdee1;'>{safe_content}</span>"
            f"{attachment_str} "
            f"<span style='margin-left: 10px;'>"
            f"<a href='action://reply?id={msg_id}&author={clean_author}' "
            f"title='Click to reply to this message' "
            f"style='color: #5865f2; text-decoration: none; font-size: 11px; background-color: #2b2d31; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>Reply</a> "
            f"<a href='action://mention?id={author_id}&name={clean_author}' "
            f"title='Click to mention @{author_html}' "
            f"style='color: #23a55a; text-decoration: none; font-size: 11px; background-color: #2b2d31; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>@ Mention</a>"
            f"</span>"
            f" <span style='color: #4e5058; font-size: 10px;'>ID: {msg_id}</span>"
            f"</div>"
        )

    def _on_feed_anchor_clicked(self, url: QUrl) -> None:
        """Handles user clicking Reply, @ Mention, or author names in the live feed."""
        scheme = url.scheme()
        if scheme == "action":
            action_type = url.host()
            query = QUrlQuery(url.query())
            if action_type == "reply":
                msg_id = query.queryItemValue("id")
                author = query.queryItemValue("author", QUrl.ComponentFormattingOption.FullyDecoded)
                self._set_reply_target(msg_id, author)
            elif action_type == "mention":
                user_id = query.queryItemValue("id")
                author_name = query.queryItemValue("name", QUrl.ComponentFormattingOption.FullyDecoded)
                self._insert_mention(user_id, author_name)
        elif scheme in ("http", "https"):
            QDesktopServices.openUrl(url)

    def _set_reply_target(self, msg_id: str, author: str) -> None:
        self.txt_reply_id.setText(str(msg_id))
        self.lbl_reply_info.setText(f"Replying to @{author} (Message ID: {msg_id})")
        self.reply_banner.setVisible(True)
        self.txt_message_input.setFocus()

    def _clear_reply_target(self) -> None:
        self.txt_reply_id.clear()
        self.lbl_reply_info.setText("")
        self.reply_banner.setVisible(False)

    def _insert_mention(self, user_id: str, author_name: str) -> None:
        mention_token = f"<@{user_id}> "
        self.txt_message_input.insertPlainText(mention_token)
        self.txt_message_input.setFocus()

    def _handle_runner_message(self, msg: discord.Message) -> None:
        """Dispatched from Discord runner on gateway message."""
        self.msg_emitter.message_received.emit(msg)

    def _on_live_message_received(self, msg: discord.Message) -> None:
        """Runs on Qt GUI thread when a Discord message arrives."""
        if self.selected_channel_id and msg.channel.id == self.selected_channel_id:
            formatted = self._format_message_html(msg)
            self.feed_browser.append(formatted)
            cursor = self.feed_browser.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.feed_browser.setTextCursor(cursor)

    # -------------------------------------------------------------------------
    # Send Message as Bot
    # -------------------------------------------------------------------------

    def _on_browse_attachment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Attachment",
            "",
            "All Files (*.*);;Images (*.png *.jpg *.jpeg *.gif)",
        )
        if path:
            self.selected_attachment_path = path
            self.lbl_attachment_name.setText(os.path.basename(path))
            self.btn_clear_attachment.setVisible(True)

    def _clear_attachment(self) -> None:
        self.selected_attachment_path = None
        self.lbl_attachment_name.setText("")
        self.btn_clear_attachment.setVisible(False)

    def _on_send_message_clicked(self) -> None:
        if not self.runner.is_running:
            self.chat_status_lbl.setText("Start the bot first to send messages.")
            self.chat_status_lbl.setStyleSheet("color: #f0b232;")
            return

        if not self.selected_channel_id:
            self.chat_status_lbl.setText("Please select an active server channel.")
            self.chat_status_lbl.setStyleSheet("color: #f0b232;")
            return

        content = self.txt_message_input.toPlainText().strip()
        attachment = self.selected_attachment_path
        if not content and not attachment:
            self.chat_status_lbl.setText("Cannot send empty message without attachment.")
            self.chat_status_lbl.setStyleSheet("color: #f0b232;")
            return

        reply_id_raw = self.txt_reply_id.text().strip()
        reply_id = int(reply_id_raw) if reply_id_raw.isdigit() else None
        split_lines = self.chk_split_messages.isChecked()

        self.btn_send_message.setEnabled(False)
        self.chat_status_lbl.setText("Sending message as bot...")
        self.chat_status_lbl.setStyleSheet("color: #949ba4;")

        async def send() -> None:
            try:
                sent_msgs = await self.runner.send_message_as_bot(
                    channel_id=self.selected_channel_id,
                    content=content,
                    file_path=attachment,
                    reply_to_id=reply_id,
                    split_lines=split_lines,
                )
                self.chat_status_lbl.setText(f"Sent {len(sent_msgs)} message(s) successfully!")
                self.chat_status_lbl.setStyleSheet("color: #23a55a;")

                # Clear inputs
                self.txt_message_input.clear()
                self._clear_attachment()
                self.txt_reply_id.clear()

            except Exception as err:
                self.chat_status_lbl.setText(f"Failed to send: {err}")
                self.chat_status_lbl.setStyleSheet("color: #da373c;")
            finally:
                self.btn_send_message.setEnabled(self.runner.is_running)

        asyncio.create_task(send())

    def on_bot_state_changed(self, state: BotState, detail: str) -> None:
        """Called when bot connects or disconnects to refresh guild list & buttons."""
        if state == BotState.ONLINE:
            self.btn_apply_presence.setEnabled(True)
            self.btn_send_message.setEnabled(True)
            self.btn_apply_avatar.setEnabled(bool(self.selected_avatar_path))
            # Refresh server dropdown after short gateway sync
            QTimer.singleShot(1500, self.refresh_guilds)
            QTimer.singleShot(1500, self._on_fetch_current_avatar)
        else:
            self.btn_apply_presence.setEnabled(False)
            self.btn_apply_avatar.setEnabled(False)
            self.btn_send_message.setEnabled(False)
            self.combo_guilds.clear()
            self.combo_channels.clear()
