"""
Unit tests for Phase 4: Custom Commands & Python Cog Plugin Studio.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from PySide6.QtWidgets import QApplication

from bot.config import BotConfig
from bot.custom_commands import CustomCommand, CustomCommandManager
from bot.plugins import PluginManager
from bot.services.ollama_service import LLMResponse
from gui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestCustomCommandManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile("w+", delete=False)
        self.temp_file.close()
        self.manager = CustomCommandManager(file_path=self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_add_and_validate_command(self):
        cmd = CustomCommand(
            name="test_cmd",
            description="A test command",
            command_type="ai_prompt",
            prompt_template="Test {query}",
        )
        self.manager.add_command(cmd)
        retrieved = self.manager.get_command("test_cmd")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.description, "A test command")

        # Test invalid command names
        invalid_cmd = CustomCommand(name="Invalid Name!", description="bad")
        with self.assertRaises(ValueError):
            self.manager.add_command(invalid_cmd)

    def test_broken_file_is_kept_not_overwritten(self):
        with open(self.temp_file.name, "w", encoding="utf-8") as f:
            f.write('[{"name": "mine", "description": "x"},')  # truncated JSON
        manager = CustomCommandManager(file_path=self.temp_file.name)
        broken = self.temp_file.name + ".broken"
        try:
            with open(broken, encoding="utf-8") as f:
                self.assertIn('"mine"', f.read())
            self.assertIsNotNone(manager.get_command("roast"))  # defaults loaded for this session
        finally:
            os.remove(broken)

    def test_remove_command(self):
        cmd = CustomCommand(name="remove_me", description="to be removed")
        self.manager.add_command(cmd)
        self.assertIsNotNone(self.manager.get_command("remove_me"))

        removed = self.manager.remove_command("remove_me")
        self.assertTrue(removed)
        self.assertIsNone(self.manager.get_command("remove_me"))

    async def test_ai_prompt_callback_execution(self):
        cmd = CustomCommand(
            name="roast_test",
            description="Roast target",
            command_type="ai_prompt",
            prompt_template="Roast {query} now!",
            ephemeral=True,
        )

        bot_mock = MagicMock()
        ollama_mock = AsyncMock()
        ollama_mock.generate_response.return_value = LLMResponse(content="Burn!", reaction=None)
        bot_mock.ollama_service = ollama_mock
        bot_mock.user.display_name = "TsundereBot"

        interaction_mock = AsyncMock(spec=discord.Interaction)
        interaction_mock.user.display_name = "Khoi"
        interaction_mock.response.defer = AsyncMock()
        interaction_mock.followup.send = AsyncMock()

        callback = self.manager.create_slash_callback(cmd, bot_mock)
        await callback(interaction_mock, query="noob")

        interaction_mock.response.defer.assert_awaited_once_with(ephemeral=True)
        ollama_mock.generate_response.assert_awaited_once_with([], "Roast noob now!")
        interaction_mock.followup.send.assert_awaited_once_with("Burn!", ephemeral=True)

    async def test_static_and_embed_callbacks(self):
        cmd_static = CustomCommand(
            name="faq",
            description="FAQ",
            command_type="static_text",
            static_content="Hello {query}",
        )
        cmd_embed = CustomCommand(
            name="rules_embed",
            description="Rules",
            command_type="rich_embed",
            embed_title="Rules Card",
            static_content="Rule 1",
            embed_color="#23a55a",
        )

        bot_mock = MagicMock()
        interaction_mock = AsyncMock(spec=discord.Interaction)
        interaction_mock.response.send_message = AsyncMock()

        # Test static
        cb_static = self.manager.create_slash_callback(cmd_static, bot_mock)
        await cb_static(interaction_mock, query="World")
        interaction_mock.response.send_message.assert_awaited_with("Hello World", ephemeral=False)

        # Test embed
        cb_embed = self.manager.create_slash_callback(cmd_embed, bot_mock)
        await cb_embed(interaction_mock)
        interaction_mock.response.send_message.assert_awaited()
        embed_sent = interaction_mock.response.send_message.call_args[1].get("embed")
        self.assertIsNotNone(embed_sent)
        self.assertEqual(embed_sent.title, "Rules Card")


class TestPluginManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mgr = PluginManager(plugins_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_plugins_discovery(self):
        plugins = self.mgr.list_plugins()
        self.assertTrue(len(plugins) >= 1)
        self.assertEqual(plugins[0]["name"], "example_plugin")

    async def test_plugin_lifecycle_methods(self):
        bot_mock = MagicMock()
        bot_mock.load_extension = AsyncMock()
        bot_mock.unload_extension = AsyncMock()
        bot_mock.reload_extension = AsyncMock()

        await self.mgr.load_plugin(bot_mock, "example_plugin")
        bot_mock.load_extension.assert_awaited_once_with("plugins.example_plugin")

        await self.mgr.unload_plugin(bot_mock, "example_plugin")
        bot_mock.unload_extension.assert_awaited_once_with("plugins.example_plugin")

        await self.mgr.reload_plugin(bot_mock, "example_plugin")
        bot_mock.reload_extension.assert_awaited_once_with("plugins.example_plugin")


class TestCommandsTabUI(unittest.TestCase):
    def setUp(self):
        self.config = BotConfig(discord_token="fake_token")
        self.window = MainWindow(config=self.config)
        self.tab = self.window.commands_tab

    def tearDown(self):
        import logging

        logging.getLogger().removeHandler(self.window.qt_log_handler)
        self.window.close()

    def test_ui_list_populated(self):
        self.assertTrue(self.tab.cmd_list_widget.count() >= 1)

    def test_new_command_workflow(self):
        self.tab._on_new_command_clicked()
        self.assertEqual(self.tab.txt_cmd_name.text(), "")

        self.tab.txt_cmd_name.setText("test_ui_cmd")
        self.tab.txt_cmd_desc.setText("UI Test Description")
        self.tab.combo_cmd_type.setCurrentIndex(0)  # AI
        self.tab.txt_cmd_content.setPlainText("Prompt for {query}")

        self.tab._on_save_command_clicked()
        self.assertIsNotNone(self.tab.cmd_manager.get_command("test_ui_cmd"))

        # Clean up
        self.tab.cmd_manager.remove_command("test_ui_cmd")


if __name__ == "__main__":
    unittest.main()
