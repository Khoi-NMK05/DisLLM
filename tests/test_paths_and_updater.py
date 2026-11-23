"""Unit tests for persistent user-data paths, legacy migration, and GitHub auto-updater."""

from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bot import paths, updater


class TestPathsAndMigration(unittest.TestCase):
    def test_env_override_controls_all_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"DISLLM_DATA_DIR": tmp}, clear=False):
                root = Path(tmp).resolve()
                self.assertEqual(paths.get_app_data_dir(), root)
                self.assertEqual(Path(paths.get_env_path()), root / ".env")
                self.assertEqual(Path(paths.get_db_path()), root / "data" / "chatbot.db")
                self.assertEqual(Path(paths.get_personas_path()), root / "data" / "personas.json")
                self.assertEqual(Path(paths.get_custom_commands_path()), root / "data" / "custom_commands.json")
                self.assertEqual(
                    Path(paths.get_moderation_settings_path()),
                    root / "data" / "moderation_settings.json",
                )
                self.assertEqual(Path(paths.get_plugins_dir()), root / "plugins")

    def test_frozen_windows_uses_appdata(self) -> None:
        with tempfile.TemporaryDirectory() as fake_appdata, tempfile.TemporaryDirectory() as fake_exe_dir:
            env = {k: v for k, v in os.environ.items() if k != "DISLLM_DATA_DIR"}
            env["APPDATA"] = fake_appdata
            with (
                patch.dict(os.environ, env, clear=True),
                patch.object(paths, "is_frozen", return_value=True),
                patch.object(paths, "get_exe_dir", return_value=Path(fake_exe_dir)),
                patch.object(paths.sys, "platform", "win32"),
                patch.object(paths.sys, "argv", ["DisLLM.exe"]),
            ):
                self.assertEqual(paths.get_app_data_dir(), Path(fake_appdata) / "DisLLM")

    def test_portable_flag_keeps_data_beside_exe(self) -> None:
        with tempfile.TemporaryDirectory() as fake_exe_dir:
            (Path(fake_exe_dir) / "portable.flag").write_text("", encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "DISLLM_DATA_DIR"}
            with (
                patch.dict(os.environ, env, clear=True),
                patch.object(paths, "is_frozen", return_value=True),
                patch.object(paths, "get_exe_dir", return_value=Path(fake_exe_dir)),
                patch.object(paths.sys, "argv", ["DisLLM.exe"]),
            ):
                self.assertEqual(paths.get_app_data_dir(), Path(fake_exe_dir))

    def test_migrate_legacy_data_is_non_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as legacy_dir, tempfile.TemporaryDirectory() as target_dir:
            legacy = Path(legacy_dir)
            target = Path(target_dir)

            (legacy / ".env").write_text("DISCORD_BOT_TOKEN=legacy_tok\n", encoding="utf-8")
            (legacy / "data").mkdir()
            (legacy / "data" / "personas.json").write_text('{"Miku": "prompt"}', encoding="utf-8")
            (legacy / "data" / "chatbot.db").write_bytes(b"sqlite-legacy")
            (legacy / "plugins").mkdir()
            (legacy / "plugins" / "my_cog.py").write_text("# custom cog\n", encoding="utf-8")

            # Pre-existing personas.json in target should NOT be overwritten
            (target / "data").mkdir()
            (target / "data" / "personas.json").write_text('{"Existing": "keep"}', encoding="utf-8")

            migrated = paths.migrate_legacy_data_if_needed(legacy_root=legacy, target_root=target)

            self.assertIn(".env", migrated)
            self.assertIn("data/chatbot.db", migrated)
            self.assertIn("plugins/my_cog.py", migrated)
            self.assertNotIn("data/personas.json", migrated)

            self.assertEqual((target / ".env").read_text(encoding="utf-8"), "DISCORD_BOT_TOKEN=legacy_tok\n")
            self.assertEqual((target / "data" / "personas.json").read_text(encoding="utf-8"), '{"Existing": "keep"}')
            self.assertEqual((target / "plugins" / "my_cog.py").read_text(encoding="utf-8"), "# custom cog\n")


class TestUpdater(unittest.TestCase):
    def test_version_comparison(self) -> None:
        self.assertEqual(updater.parse_version("v1.2.10"), (1, 2, 10))
        self.assertTrue(updater.is_newer_version("v1.0.1", "1.0.0"))
        self.assertTrue(updater.is_newer_version("1.10.0", "1.2.9"))
        self.assertFalse(updater.is_newer_version("1.0.0", "1.0.0"))
        self.assertFalse(updater.is_newer_version("v0.9.9", "1.0.0"))

    def test_checksum_parsing_and_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "DisLLM-Setup-v1.0.1.exe"
            payload = b"disllm installer bytes"
            sample.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()

            parsed = updater.parse_checksums(f"{digest}  DisLLM-Setup-v1.0.1.exe\n# comment\n")
            self.assertEqual(parsed["DisLLM-Setup-v1.0.1.exe"], digest)
            self.assertTrue(updater.verify_sha256(sample, digest))
            self.assertFalse(updater.verify_sha256(sample, "0" * 64))

    def test_asset_selection(self) -> None:
        assets = [
            {"name": "DisLLM-Setup-v1.1.0.exe", "browser_download_url": "https://example.com/setup.exe"},
            {"name": "DisLLM-v1.1.0-win64.zip", "browser_download_url": "https://example.com/portable.zip"},
            {"name": "checksums.txt", "browser_download_url": "https://example.com/checksums.txt"},
        ]
        inst_url, inst_name, zip_url, zip_name, sums_url = updater._select_assets(assets)
        self.assertEqual(inst_url, "https://example.com/setup.exe")
        self.assertEqual(inst_name, "DisLLM-Setup-v1.1.0.exe")
        self.assertEqual(zip_url, "https://example.com/portable.zip")
        self.assertEqual(zip_name, "DisLLM-v1.1.0-win64.zip")
        self.assertEqual(sums_url, "https://example.com/checksums.txt")

    def test_detect_install_mode(self) -> None:
        with patch.object(updater, "is_frozen", return_value=False):
            self.assertEqual(updater.detect_install_mode(), "source")

        with tempfile.TemporaryDirectory() as tmp:
            exe_dir = Path(tmp)
            with (
                patch.object(updater, "is_frozen", return_value=True),
                patch.object(updater, "is_portable_mode", return_value=False),
                patch.object(updater, "get_exe_dir", return_value=exe_dir),
            ):
                self.assertEqual(updater.detect_install_mode(), "portable")
                (exe_dir / "unins000.exe").write_bytes(b"")
                self.assertEqual(updater.detect_install_mode(), "installer")


if __name__ == "__main__":
    unittest.main()
