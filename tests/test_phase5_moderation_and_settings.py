"""
Unit tests for Phase 5: Moderation Rules, SQLite Memory Inspector & Desktop Preferences.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from PySide6.QtWidgets import QApplication

from bot.config import BotConfig
from bot.database import DatabaseManager
from bot.moderation import ModerationManager, ModerationSettings
from gui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestModerationManager(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile("w+", delete=False)
        self.temp_file.close()
        self.mgr = ModerationManager(file_path=self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_dm_permission_filter(self):
        self.mgr.settings.allow_dms = True
        self.assertTrue(self.mgr.is_channel_allowed(guild_id=None, channel_id=12345))

        self.mgr.settings.allow_dms = False
        self.assertFalse(self.mgr.is_channel_allowed(guild_id=None, channel_id=12345))

    def test_whitelist_mode(self):
        self.mgr.settings.channel_rule_mode = "whitelist"
        self.mgr.settings.whitelisted_channels = [100, 200]

        self.assertTrue(self.mgr.is_channel_allowed(guild_id=999, channel_id=100))
        self.assertFalse(self.mgr.is_channel_allowed(guild_id=999, channel_id=300))

    def test_blacklist_mode(self):
        self.mgr.settings.channel_rule_mode = "blacklist"
        self.mgr.settings.blacklisted_channels = [300]

        self.assertTrue(self.mgr.is_channel_allowed(guild_id=999, channel_id=100))
        self.assertFalse(self.mgr.is_channel_allowed(guild_id=999, channel_id=300))

    def test_rate_limiter(self):
        self.mgr.settings.rate_limit_per_minute = 3
        user_id = 9999

        # First 3 should pass
        self.assertTrue(self.mgr.check_rate_limit(user_id))
        self.assertTrue(self.mgr.check_rate_limit(user_id))
        self.assertTrue(self.mgr.check_rate_limit(user_id))

        # 4th should be blocked
        self.assertFalse(self.mgr.check_rate_limit(user_id))


class TestDatabaseManagerPhase5(unittest.IsolatedAsyncioTestCase):
    async def test_active_channels_and_detailed_history(self):
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()

        await db.save_turn(
            guild_id=111,
            channel_id=222,
            user_id=333,
            user_content="Hello bot",
            assistant_content="Hello user",
        )

        channels = await db.list_active_channels()
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["channel_id"], 222)
        self.assertEqual(channels[0]["msg_count"], 2)

        detailed = await db.get_detailed_channel_history(channel_id=222)
        self.assertEqual(len(detailed), 2)
        self.assertEqual(detailed[0]["role"], "user")
        self.assertEqual(detailed[1]["role"], "assistant")

        await db.close()


class TestSettingsTabUI(unittest.TestCase):
    def setUp(self):
        self.config = BotConfig(discord_token="fake_token")
        self.window = MainWindow(config=self.config)
        self.tab = self.window.settings_tab

    def tearDown(self):
        import logging

        logging.getLogger().removeHandler(self.window.qt_log_handler)
        self.window.close()

    def test_ui_preferences_save(self):
        # Save into temp files, never the real data/moderation_settings.json or .env.
        tmp_dir = tempfile.mkdtemp()
        self.tab.mod_manager.file_path = os.path.join(tmp_dir, "moderation.json")
        self.tab.txt_admin_id.setText("123456789")
        self.tab.chk_allow_dms.setChecked(False)
        self.tab.spin_rate_limit.setValue(15)
        self.tab.chk_minimize_to_tray.setChecked(True)

        real_save_admin = self.config.save_admin_id
        env_path = os.path.join(tmp_dir, ".env")
        with patch.dict(os.environ), patch.object(
            self.config, "save_admin_id", side_effect=lambda uid: real_save_admin(uid, env_path=env_path)
        ):
            self.tab._on_save_preferences()

        self.assertEqual(self.config.admin_user_id, 123456789)
        with open(env_path, encoding="utf-8") as f:
            self.assertIn("ADMIN_USER_ID=123456789", f.read())

        self.assertFalse(self.tab.mod_manager.settings.allow_dms)
        self.assertEqual(self.tab.mod_manager.settings.rate_limit_per_minute, 15)
        self.assertTrue(self.tab.mod_manager.settings.minimize_to_tray_on_close)


if __name__ == "__main__":
    unittest.main()
