"""
Unit tests for BotRunner and GUI components (Phase 1).
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from PySide6.QtWidgets import QApplication

from bot.config import BotConfig
from bot.runner import BotRunner, BotState
from gui.log_handler import QtLogHandler
from gui.main_window import MainWindow

# Ensure offscreen Qt platform for headless test execution
app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestBotConfigEnv(unittest.TestCase):
    def test_from_env_require_token_false(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            empty_path = f.name

        try:
            with patch.dict(os.environ, {}, clear=True):
                cfg = BotConfig.from_env(env_path=empty_path, require_token=False)
                self.assertEqual(cfg.discord_token, "")
        finally:
            if os.path.exists(empty_path):
                os.remove(empty_path)

    def test_from_env_require_token_true_raises(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            empty_path = f.name

        try:
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ValueError):
                    BotConfig.from_env(env_path=empty_path, require_token=True)
        finally:
            if os.path.exists(empty_path):
                os.remove(empty_path)

    def test_from_env_bad_number_falls_back_without_losing_token(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            empty_path = f.name
        try:
            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "tok", "TEMPERATURE": "0,8"}, clear=True):
                cfg = BotConfig.from_env(env_path=empty_path)
            self.assertEqual(cfg.discord_token, "tok")
            self.assertEqual(cfg.temperature, 0.80)
            self.assertEqual(cfg.admin_user_id, 0)
        finally:
            os.remove(empty_path)

    def test_save_token_persists_to_file(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            temp_path = f.name
            f.write("SOME_KEY=123\n")

        try:
            cfg = BotConfig(discord_token="")
            cfg.save_token("test_secret_token_abc", env_path=temp_path)
            self.assertEqual(cfg.discord_token, "test_secret_token_abc")

            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("DISCORD_BOT_TOKEN=test_secret_token_abc", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_save_ai_settings_roundtrips_prompt_and_host(self):
        from dotenv import dotenv_values

        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            temp_path = f.name

        prompt = 'line one "quoted"\nべつに, back\\slash\n\nlast'
        try:
            with patch.dict(os.environ, {}, clear=True):
                cfg = BotConfig(system_prompt=prompt, ollama_host="http://10.0.0.5:11434")
                cfg.save_ai_settings(env_path=temp_path)
                self.assertEqual(os.environ["SYSTEM_PROMPT"], prompt)
            values = dotenv_values(temp_path, encoding="utf-8")
            self.assertEqual(values["SYSTEM_PROMPT"], prompt)
            self.assertEqual(values["OLLAMA_HOST"], "http://10.0.0.5:11434")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestBotRunner(unittest.IsolatedAsyncioTestCase):
    async def test_bot_runner_state_transitions(self):
        cfg = BotConfig(discord_token="fake_token")
        states_seen: list[BotState] = []

        def on_state(state: BotState, detail: str) -> None:
            states_seen.append(state)

        runner = BotRunner(config=cfg, on_state_change=on_state)
        self.assertEqual(runner.state, BotState.DISCONNECTED)

        # Mock start loop to avoid real network call
        with patch.object(runner, "_run_loop", new_callable=AsyncMock) as mock_loop:
            await runner.start()
            self.assertEqual(runner.state, BotState.CONNECTING)
            self.assertIn(BotState.CONNECTING, states_seen)

            await runner.stop()
            self.assertEqual(runner.state, BotState.DISCONNECTED)
            self.assertIn(BotState.DISCONNECTED, states_seen)

    async def test_bot_runner_empty_token_error(self):
        cfg = BotConfig(discord_token="")
        runner = BotRunner(config=cfg)
        with self.assertRaises(ValueError):
            await runner.start()
        self.assertEqual(runner.state, BotState.ERROR)


class TestGUIComponents(unittest.TestCase):
    def setUp(self):
        self.cfg = BotConfig(discord_token="dummy_token_123")
        self.window = MainWindow(config=self.cfg)

    def tearDown(self):
        import logging
        logging.getLogger().removeHandler(self.window.qt_log_handler)
        self.window.close()

    def test_window_tabs_initialized(self):
        self.assertEqual(self.window.tabs.count(), 5)
        self.assertEqual(self.window.dashboard_tab.token_input.text(), "dummy_token_123")

    def test_log_handler_dispatches_to_dashboard(self):
        dashboard = self.window.dashboard_tab
        initial_log_count = len(dashboard._all_logs)

        # Emit log through QtLogHandler
        self.window.qt_log_handler.emitter.log_record_received.emit(
            "12:00:00", "INFO", "Test log dispatch message"
        )
        self.assertEqual(len(dashboard._all_logs), initial_log_count + 1)
        self.assertEqual(dashboard._all_logs[-1][2], "Test log dispatch message")

    def test_dashboard_token_visibility_toggle(self):
        dashboard = self.window.dashboard_tab
        from PySide6.QtWidgets import QLineEdit

        self.assertEqual(dashboard.token_input.echoMode(), QLineEdit.EchoMode.Password)
        dashboard.toggle_show_btn.click()
        self.assertEqual(dashboard.token_input.echoMode(), QLineEdit.EchoMode.Normal)
        dashboard.toggle_show_btn.click()
        self.assertEqual(dashboard.token_input.echoMode(), QLineEdit.EchoMode.Password)


if __name__ == "__main__":
    unittest.main()
