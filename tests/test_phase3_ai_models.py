"""
Unit tests for Phase 3: Dual-Engine AI Inference (Local & Cloud APIs).
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from PySide6.QtWidgets import QApplication

from bot.config import DEFAULT_SYSTEM_PROMPT, BotConfig
from bot.services.ai_helpers import (
    SYSTEM_PROMPT_PRESETS,
    fetch_ollama_tags,
    fetch_openai_compatible_models,
    load_custom_personas,
    save_custom_personas,
)
from bot.services.ollama_service import LLMResponse, OllamaService
from gui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestPhase3AIService(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_provider_routes_to_ollama_client(self):
        cfg = BotConfig(discord_token="fake_token", ai_provider="ollama", ollama_model="qwen3.5:9b")
        client_mock = AsyncMock()
        client_mock.chat.return_value = {
            "message": {"content": "[REACTION: ❤️] hello there from ollama"}
        }

        service = OllamaService(config=cfg, client=client_mock)
        resp = await service.generate_response([], "hi")

        self.assertEqual(resp.content, "hello there from ollama")
        self.assertEqual(resp.reaction, "❤️")
        client_mock.chat.assert_awaited_once()

    async def test_cloud_openai_compatible_routes_to_rest_api(self):
        cfg = BotConfig(
            discord_token="fake_token",
            ai_provider="openai",
            api_key="sk-fake-key",
            api_model="gpt-4o-mini",
        )
        service = OllamaService(config=cfg)

        mock_json_response = {
            "choices": [
                {
                    "message": {
                        "content": "<think>some internal chain of thought</think>[REACTION: 🔥] hello from cloud!"
                    }
                }
            ]
        }

        class MockResponse:
            status = 200

            async def json(self):
                return mock_json_response

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        class MockSession:
            def post(self, url, **kwargs):
                return MockResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch("aiohttp.ClientSession", return_value=MockSession()):
            resp = await service.generate_response([], "hi from test")
            self.assertEqual(resp.content, "hello from cloud!")
            self.assertEqual(resp.reaction, "🔥")


class TestAIHelpers(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_ollama_tags(self):
        class MockResponse:
            status = 200

            async def json(self):
                return {"models": [{"name": "qwen3.5:9b"}, {"name": "mistral:latest"}]}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        class MockSession:
            def __init__(self, **kwargs):
                pass

            def get(self, url):
                return MockResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch("aiohttp.ClientSession", side_effect=MockSession):
            tags = await fetch_ollama_tags("http://localhost:11434")
            self.assertEqual(tags, ["qwen3.5:9b", "mistral:latest"])

    async def test_fetch_openai_models(self):
        class MockResponse:
            status = 200

            async def json(self):
                return {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        class MockSession:
            def __init__(self, **kwargs):
                pass

            def get(self, url, headers=None):
                return MockResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch("aiohttp.ClientSession", side_effect=MockSession):
            models = await fetch_openai_compatible_models("https://api.openai.com/v1", api_key="sk-test")
            self.assertEqual(models, ["gpt-4o", "gpt-4o-mini"])


class TestCustomPersonaStorage(unittest.TestCase):
    def test_round_trip_and_bad_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "personas.json")
            self.assertEqual(load_custom_personas(path), {})
            save_custom_personas({"Pirate": "Arr. ✨"}, path)
            self.assertEqual(load_custom_personas(path), {"Pirate": "Arr. ✨"})
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertEqual(load_custom_personas(path), {})


class TestAIModelsTabUI(unittest.TestCase):
    def setUp(self):
        self.config = BotConfig(discord_token="fake_token", temperature=0.75, top_p=0.85)
        self.window = MainWindow(config=self.config)
        self.tab = self.window.ai_models_tab

    def tearDown(self):
        import logging

        logging.getLogger().removeHandler(self.window.qt_log_handler)
        self.window.close()

    def test_ui_loaded_values_from_config(self):
        self.assertEqual(self.tab.slider_temp.value(), 75)
        self.assertEqual(self.tab.slider_top_p.value(), 85)
        self.assertEqual(self.tab.lbl_val_temp.text(), "0.75")
        self.assertEqual(self.tab.lbl_val_top_p.text(), "0.85")

    def test_preset_changes_system_prompt(self):
        self.tab.combo_presets.setCurrentText("Senior Coding Companion")
        self.assertIn("expert senior software engineer", self.tab.txt_system_prompt.toPlainText())

        self.tab.combo_presets.setCurrentText("Tsundere B-chan (Default)")
        self.assertEqual(self.tab.txt_system_prompt.toPlainText(), DEFAULT_SYSTEM_PROMPT)

    def test_save_and_delete_custom_preset(self):
        self.tab.txt_system_prompt.setPlainText("You are a pirate.")
        with patch("gui.tabs.ai_models_tab.save_custom_personas") as mock_save, patch(
            "gui.tabs.ai_models_tab.QInputDialog.getText", return_value=("  Pirate   Captain ", True)
        ):
            self.tab._on_save_preset()
        mock_save.assert_called_once()
        self.assertEqual(self.tab.custom_personas["Pirate Captain"], "You are a pirate.")
        self.assertEqual(self.tab.combo_presets.currentText(), "Pirate Captain")
        self.assertTrue(self.tab.btn_delete_preset.isEnabled())

        # Picking another preset and coming back restores the saved prompt.
        self.tab.combo_presets.setCurrentText("Senior Coding Companion")
        self.assertFalse(self.tab.btn_delete_preset.isEnabled())
        self.tab.combo_presets.setCurrentText("Pirate Captain")
        self.assertEqual(self.tab.txt_system_prompt.toPlainText(), "You are a pirate.")

        with patch("gui.tabs.ai_models_tab.save_custom_personas"), patch.object(
            self.tab, "_confirm", return_value=True
        ) as confirm:
            self.tab._on_delete_preset()
        self.assertEqual(confirm.call_args.args[2], "Delete")  # the button names the action
        self.assertNotIn("Pirate Captain", self.tab.custom_personas)
        self.assertEqual(self.tab.combo_presets.findText("Pirate Captain"), -1)

    def test_new_preset_starts_empty_draft(self):
        with patch("gui.tabs.ai_models_tab.QInputDialog.getText", return_value=("Pirate", True)):
            self.tab._on_new_preset()
        self.assertEqual(self.tab.combo_presets.currentText(), "Pirate")
        self.assertEqual(self.tab.txt_system_prompt.toPlainText(), "")
        self.assertTrue(self.tab.btn_delete_preset.isEnabled())

        # Save keeps the draft's name and turns it into a real preset.
        self.tab.txt_system_prompt.setPlainText("Arr.")
        with patch("gui.tabs.ai_models_tab.save_custom_personas"), patch(
            "gui.tabs.ai_models_tab.QInputDialog.getText", return_value=("Pirate", True)
        ) as mock_dialog:
            self.tab._on_save_preset()
        self.assertEqual(mock_dialog.call_args.kwargs["text"], "Pirate")
        self.assertEqual(self.tab.custom_personas["Pirate"], "Arr.")
        self.assertEqual(self.tab.combo_presets.findText("Pirate"), self.tab.combo_presets.currentIndex())

    def test_new_preset_draft_can_be_discarded(self):
        with patch("gui.tabs.ai_models_tab.QInputDialog.getText", return_value=("Ghost", True)):
            self.tab._on_new_preset()
        with patch("gui.tabs.ai_models_tab.save_custom_personas") as mock_save:
            self.tab._on_delete_preset()
        mock_save.assert_not_called()
        self.assertEqual(self.tab.combo_presets.findText("Ghost"), -1)
        self.assertEqual(self.tab.txt_system_prompt.toPlainText(), DEFAULT_SYSTEM_PROMPT)

    def test_builtin_preset_names_are_protected(self):
        self.tab.txt_system_prompt.setPlainText("x")
        with patch("gui.tabs.ai_models_tab.save_custom_personas") as mock_save, patch(
            "gui.tabs.ai_models_tab.QInputDialog.getText", return_value=("Casual Gamer Buddy", True)
        ):
            self.tab._on_save_preset()
        mock_save.assert_not_called()

    def test_save_settings_persists_to_file(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            temp_env = f.name

        try:
            self.tab.slider_temp.setValue(95)
            self.tab.slider_top_p.setValue(99)
            self.tab.combo_provider.setCurrentIndex(self.tab.combo_provider.findData("openai"))
            self.tab.txt_api_key.setText("sk-saved-key-123")

            # Save into the temp file, never the real .env; restore os.environ afterwards.
            real_save = self.tab.config.save_ai_settings
            with patch.dict(os.environ), patch.object(
                self.tab.config, "save_ai_settings", side_effect=lambda: real_save(env_path=temp_env)
            ) as mock_save:
                self.tab.combo_vision_model.setEditText("moondream:latest")
                self.tab._on_save_settings()
                self.assertEqual(self.tab.config.temperature, 0.95)
                self.assertEqual(self.tab.config.top_p, 0.99)
                self.assertEqual(self.tab.config.ai_provider, "openai")
                self.assertEqual(self.tab.config.api_key, "sk-saved-key-123")
                self.assertEqual(self.tab.config.vision_model, "moondream:latest")
                mock_save.assert_called_once()
                with open(temp_env, encoding="utf-8") as f:
                    self.assertIn("API_KEY=sk-saved-key-123", f.read())
        finally:
            if os.path.exists(temp_env):
                os.remove(temp_env)


if __name__ == "__main__":
    unittest.main()
