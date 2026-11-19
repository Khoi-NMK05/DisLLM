"""
Unit tests for Phase 2: Bot Identity, Presence, Multi-Server Explorer, and Remote Chat.
"""

from __future__ import annotations

import asyncio
import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from PySide6.QtWidgets import QApplication

from bot.config import BotConfig
from bot.runner import BotRunner, BotState
from gui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestBotRunnerPhase2Methods(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = BotConfig(discord_token="dummy_token")
        self.runner = BotRunner(config=self.config)

    async def test_offline_guards_raise_error(self):
        with self.assertRaises(RuntimeError):
            await self.runner.update_avatar(b"fake_image_bytes")

        with self.assertRaises(RuntimeError):
            await self.runner.update_presence("Online", "Playing", "Game")

        with self.assertRaises(RuntimeError):
            await self.runner.send_message_as_bot(12345, "hello")

    async def test_update_presence_success(self):
        bot_mock = MagicMock()
        bot_mock.is_ready.return_value = True
        bot_mock.change_presence = AsyncMock()
        self.runner.bot = bot_mock

        await self.runner.update_presence("Do Not Disturb", "Listening", "Lofi Beats")

        bot_mock.change_presence.assert_awaited_once()
        call_kwargs = bot_mock.change_presence.call_args[1]
        self.assertEqual(call_kwargs["status"], discord.Status.dnd)
        self.assertEqual(call_kwargs["activity"].type, discord.ActivityType.listening)
        self.assertEqual(call_kwargs["activity"].name, "Lofi Beats")

    async def test_send_message_as_bot_single(self):
        bot_mock = MagicMock()
        channel_mock = MagicMock()
        channel_mock.send = AsyncMock(return_value=MagicMock(spec=discord.Message))
        bot_mock.get_channel.return_value = channel_mock
        self.runner.bot = bot_mock

        sent = await self.runner.send_message_as_bot(12345, "Single message test", split_lines=False)
        self.assertEqual(len(sent), 1)
        channel_mock.send.assert_awaited_once_with(content="Single message test", reference=None, file=None)

    async def test_send_message_as_bot_split_lines(self):
        bot_mock = MagicMock()
        channel_mock = MagicMock()
        channel_mock.send = AsyncMock(return_value=MagicMock(spec=discord.Message))
        bot_mock.get_channel.return_value = channel_mock
        self.runner.bot = bot_mock

        multiline = "Line 1\nLine 2\nLine 3"
        sent = await self.runner.send_message_as_bot(12345, multiline, split_lines=True)
        self.assertEqual(len(sent), 3)
        self.assertEqual(channel_mock.send.await_count, 3)

    def test_get_sendable_channels_filters_permissions(self):
        bot_mock = MagicMock()
        guild_mock = MagicMock()
        bot_mock.get_guild.return_value = guild_mock
        self.runner.bot = bot_mock

        # Channel 1: Allowed text channel
        ch1 = MagicMock(spec=discord.TextChannel)
        ch1.name = "general"
        ch1.position = 1
        perms1 = MagicMock()
        perms1.send_messages = True
        perms1.view_channel = True
        ch1.permissions_for.return_value = perms1

        # Channel 2: No send permission
        ch2 = MagicMock(spec=discord.TextChannel)
        ch2.name = "announcements"
        ch2.position = 0
        perms2 = MagicMock()
        perms2.send_messages = False
        perms2.view_channel = True
        ch2.permissions_for.return_value = perms2

        guild_mock.text_channels = [ch1, ch2]
        guild_mock.threads = []

        sendable = self.runner.get_sendable_channels(999)
        self.assertEqual(len(sendable), 1)
        self.assertEqual(sendable[0].name, "general")


class TestBotControlTabUI(unittest.TestCase):
    def setUp(self):
        self.config = BotConfig(discord_token="dummy_token")
        self.window = MainWindow(config=self.config)
        self.tab = self.window.bot_control_tab

    def tearDown(self):
        import logging

        logging.getLogger().removeHandler(self.window.qt_log_handler)
        self.window.close()

    def test_format_message_html(self):
        msg = MagicMock(spec=discord.Message)
        msg.author.display_name = "UserKhoi"
        msg.author.id = 12345
        msg.clean_content = "Hello there <world> & friends"
        msg.created_at = datetime.datetime(2026, 11, 20, 12, 30, 0)
        msg.attachments = []
        msg.reference = None
        msg.id = 987654321

        html = self.tab._format_message_html(msg)
        self.assertIn("UserKhoi", html)
        self.assertIn("Hello there &lt;world&gt; &amp; friends", html)
        self.assertIn("ID: 987654321", html)
        self.assertIn("12:30:00", html)

    def test_refresh_guilds_populates_combobox(self):
        guild1 = MagicMock()
        guild1.name = "Gaming Server"
        guild1.id = 111
        guild1.member_count = 42

        guild2 = MagicMock()
        guild2.name = "Anime Club"
        guild2.id = 222
        guild2.member_count = 100

        with patch.object(self.window.runner, "get_guilds", return_value=[guild1, guild2]):
            with patch.object(self.window.runner, "get_sendable_channels", return_value=[]):
                self.tab.refresh_guilds()
                self.assertEqual(self.tab.combo_guilds.count(), 2)
                self.assertEqual(self.tab.combo_guilds.itemData(0), 111)
                self.assertEqual(self.tab.combo_guilds.itemData(1), 222)

    def test_reply_and_mention_actions(self):
        from PySide6.QtCore import QUrl

        # Ensure openLinks is disabled so clicking anchors does not clear chat history
        self.assertFalse(self.tab.feed_browser.openLinks())
        self.tab.feed_browser.setHtml("<p>Initial Chat Message</p>")

        # 1. Test set reply target
        self.tab._set_reply_target("987654321", "TestAuthor")
        self.assertFalse(self.tab.reply_banner.isHidden())
        self.assertEqual(self.tab.txt_reply_id.text(), "987654321")
        self.assertIn("TestAuthor", self.tab.lbl_reply_info.text())

        # 2. Test clear reply target
        self.tab._clear_reply_target()
        self.assertTrue(self.tab.reply_banner.isHidden())
        self.assertEqual(self.tab.txt_reply_id.text(), "")

        # 3. Test insert mention
        self.tab.txt_message_input.clear()
        self.tab._insert_mention("123456789", "UserKhoi")
        self.assertEqual(self.tab.txt_message_input.toPlainText(), "<@123456789> ")

        # 4. Test anchor click - reply
        self.tab._on_feed_anchor_clicked(QUrl("action://reply?id=456&author=Alice"))
        self.assertFalse(self.tab.reply_banner.isHidden())
        self.assertEqual(self.tab.txt_reply_id.text(), "456")
        self.assertIn("Alice", self.tab.lbl_reply_info.text())

        # 5. Test anchor click - mention
        self.tab.txt_message_input.clear()
        self.tab._on_feed_anchor_clicked(QUrl("action://mention?id=999&name=Bob"))
        self.assertEqual(self.tab.txt_message_input.toPlainText(), "<@999> ")

        # Chat history in browser must remain completely intact
        self.assertIn("Initial Chat Message", self.tab.feed_browser.toPlainText())


if __name__ == "__main__":
    unittest.main()
