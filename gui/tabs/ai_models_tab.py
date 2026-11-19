"""
AI Engine & Model Inference Settings Tab (Phase 3).
Supports switching between Local (Ollama, LM Studio, Hugging Face GGUF) and
Cloud API providers (OpenRouter, Google Gemini, OpenAI, Groq), with dynamic parameter sliders,
Ollama model scanner/puller, and persona prompt presets.
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
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from bot.config import DEFAULT_SYSTEM_PROMPT, BotConfig
from bot.services.ai_helpers import (
    PROVIDER_PRESETS,
    SYSTEM_PROMPT_PRESETS,
    create_ollama_model,
    fetch_ollama_tags,
    fetch_openai_compatible_models,
    pull_ollama_model,
)

if TYPE_CHECKING:
    from gui.main_window import MainWindow

logger = logging.getLogger(__name__)


COMMON_VISION_PRESETS = [
    "qwen2.5vl:7b-instruct-q4_K_M",
    "qwen2.5vl:7b",
    "qwen2.5vl:3b",
    "moondream",
    "moondream:latest",
    "llava",
    "llava:7b",
    "llava:13b",
    "minicpm-v",
    "llama3.2-vision",
]


class AIModelsTab(QWidget):
    """Configuration interface for local and cloud AI providers and hyperparameters."""

    def __init__(self, main_window: MainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.config: BotConfig = main_window.config

        self._init_ui()
        self._load_config_values()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. Provider & Model Card
        main_layout.addWidget(self._create_provider_card())

        # 2. Hyperparameters Section (Universal + Local-only side-by-side)
        params_row = QHBoxLayout()
        params_row.setSpacing(12)
        params_row.addWidget(self._create_universal_params_card(), stretch=1)
        params_row.addWidget(self._create_local_params_card(), stretch=1)
        main_layout.addLayout(params_row)

        # 3. System Prompt & Vision Section
        lower_row = QHBoxLayout()
        lower_row.setSpacing(12)
        lower_row.addWidget(self._create_persona_card(), stretch=2)
        lower_row.addWidget(self._create_vision_card(), stretch=1)
        main_layout.addLayout(lower_row)

        # 4. Action Bar
        action_row = QHBoxLayout()
        self.btn_save_settings = QPushButton("💾 Save & Apply Settings")
        self.btn_save_settings.setProperty("class", "primary")
        self.btn_save_settings.clicked.connect(self._on_save_settings)

        self.btn_reset_defaults = QPushButton("Reset Defaults")
        self.btn_reset_defaults.clicked.connect(self._on_reset_defaults)

        self.lbl_status = QLabel("")
        self.lbl_status.setProperty("class", "muted")

        action_row.addWidget(self.btn_save_settings)
        action_row.addWidget(self.btn_reset_defaults)
        action_row.addWidget(self.lbl_status)
        action_row.addStretch()

        main_layout.addLayout(action_row)

    # -------------------------------------------------------------------------
    # Card 1: Provider & Model Selector
    # -------------------------------------------------------------------------

    def _create_provider_card(self) -> QGroupBox:
        group = QGroupBox("AI Provider & Model Engine")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Provider Selector Row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("AI Provider:"))
        self.combo_provider = QComboBox()
        for key, info in PROVIDER_PRESETS.items():
            self.combo_provider.addItem(info["name"], key)
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        row1.addWidget(self.combo_provider, stretch=1)

        row1.addWidget(QLabel("Endpoint URL:"))
        self.txt_base_url = QLineEdit()
        self.txt_base_url.setPlaceholderText("http://localhost:11434 or https://...")
        row1.addWidget(self.txt_base_url, stretch=2)
        layout.addLayout(row1)

        # API Key & Model Row
        row2 = QHBoxLayout()
        self.lbl_api_key = QLabel("API Key:")
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("Paste provider API key (sk-... or gsk_...)")

        row2.addWidget(self.lbl_api_key)
        row2.addWidget(self.txt_api_key, stretch=2)

        row2.addWidget(QLabel("Model Identifier:"))
        self.combo_model = QComboBox()
        self.combo_model.setEditable(True)
        self.combo_model.setMinimumWidth(200)
        row2.addWidget(self.combo_model, stretch=2)

        self.btn_scan_models = QPushButton("🔄 Scan Models")
        self.btn_scan_models.clicked.connect(self._on_scan_models)
        row2.addWidget(self.btn_scan_models)

        layout.addLayout(row2)

        # Local Ollama Tools Row (Pull from HF, Import GGUF)
        self.ollama_tools_frame = QFrame()
        self.ollama_tools_frame.setStyleSheet(
            "background-color: #111214; border-radius: 6px; padding: 6px;"
        )
        tools_layout = QHBoxLayout(self.ollama_tools_frame)
        tools_layout.setContentsMargins(6, 4, 6, 4)
        tools_layout.setSpacing(8)

        tools_layout.addWidget(QLabel("Pull Model (Ollama / Hugging Face):"))
        self.txt_pull_name = QLineEdit()
        self.txt_pull_name.setPlaceholderText("e.g. hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF or mistral")
        tools_layout.addWidget(self.txt_pull_name, stretch=1)

        self.btn_pull_model = QPushButton("📥 Pull")
        self.btn_pull_model.clicked.connect(self._on_pull_model)
        tools_layout.addWidget(self.btn_pull_model)

        self.btn_import_gguf = QPushButton("📂 Import .GGUF File")
        self.btn_import_gguf.clicked.connect(self._on_import_gguf)
        tools_layout.addWidget(self.btn_import_gguf)

        layout.addWidget(self.ollama_tools_frame)

        self.lbl_model_action_status = QLabel("")
        self.lbl_model_action_status.setProperty("class", "muted")
        layout.addWidget(self.lbl_model_action_status)

        return group

    def _on_provider_changed(self) -> None:
        provider_key = self.combo_provider.currentData()
        preset = PROVIDER_PRESETS.get(provider_key, {})

        is_ollama = (provider_key == "ollama")
        is_cloud = preset.get("requires_key", False)

        # Set default base URL if empty or changing from default
        self.txt_base_url.setText(preset.get("default_url", ""))
        self.lbl_api_key.setVisible(is_cloud or provider_key == "custom")
        self.txt_api_key.setVisible(is_cloud or provider_key == "custom")
        self.ollama_tools_frame.setVisible(is_ollama)

        # Enable/Disable local hardware parameters
        self.local_params_group.setEnabled(is_ollama)
        if is_ollama:
            self.local_params_group.setTitle("Local-Only Hardware & Sampling (Active)")
        else:
            self.local_params_group.setTitle("Local-Only Hardware & Sampling (N/A for Cloud)")

    def _on_scan_models(self) -> None:
        provider_key = self.combo_provider.currentData()
        base_url = self.txt_base_url.text().strip()
        api_key = self.txt_api_key.text().strip()

        self.btn_scan_models.setEnabled(False)
        self.lbl_model_action_status.setText("Scanning available models...")
        self.lbl_model_action_status.setStyleSheet("color: #949ba4;")

        async def scan() -> None:
            try:
                models: list[str] = []
                if provider_key == "ollama":
                    models = await fetch_ollama_tags(base_url or "http://localhost:11434")
                else:
                    models = await fetch_openai_compatible_models(base_url, api_key)

                if models:
                    current_chat = self.combo_model.currentText().strip()
                    self.combo_model.clear()
                    self.combo_model.addItems(models)
                    idx = self.combo_model.findText(current_chat)
                    if idx >= 0:
                        self.combo_model.setCurrentIndex(idx)
                    elif current_chat:
                        self.combo_model.setEditText(current_chat)

                    # Update vision models dropdown with scanned models
                    curr_vision = self.combo_vision_model.currentText().strip()
                    vision_candidates = [
                        m
                        for m in models
                        if any(k in m.lower() for k in ("vl", "vision", "llava", "moondream", "minicpm", "bakllava"))
                    ]
                    merged_vision = list(dict.fromkeys(vision_candidates + COMMON_VISION_PRESETS + models))
                    self.combo_vision_model.clear()
                    self.combo_vision_model.addItems(merged_vision)
                    idx_v = self.combo_vision_model.findText(curr_vision)
                    if idx_v >= 0:
                        self.combo_vision_model.setCurrentIndex(idx_v)
                    elif curr_vision:
                        self.combo_vision_model.setEditText(curr_vision)

                    self.lbl_model_action_status.setText(
                        f"✅ Found {len(models)} model(s). Selected: {self.combo_model.currentText()}"
                    )
                    self.lbl_model_action_status.setStyleSheet("color: #23a55a;")
                else:
                    self.lbl_model_action_status.setText("⚠️ No models detected at this endpoint.")
                    self.lbl_model_action_status.setStyleSheet("color: #f0b232;")
            except Exception as err:
                self.lbl_model_action_status.setText(f"❌ Scan failed: {err}")
                self.lbl_model_action_status.setStyleSheet("color: #da373c;")
            finally:
                self.btn_scan_models.setEnabled(True)

        asyncio.create_task(scan())

    def _on_pull_model(self) -> None:
        model_name = self.txt_pull_name.text().strip()
        if not model_name:
            self.lbl_model_action_status.setText("⚠️ Enter a model name or Hugging Face repo ID to pull.")
            self.lbl_model_action_status.setStyleSheet("color: #f0b232;")
            return

        host = self.txt_base_url.text().strip() or "http://localhost:11434"
        self.btn_pull_model.setEnabled(False)
        self.lbl_model_action_status.setText(f"Pulling '{model_name}' from Ollama/Hugging Face...")
        self.lbl_model_action_status.setStyleSheet("color: #5865f2;")

        async def pull() -> None:
            try:
                async for update in pull_ollama_model(model_name, host=host):
                    status = update.get("status", "")
                    completed = update.get("completed", 0)
                    total = update.get("total", 0)
                    if total > 0:
                        pct = int((completed / total) * 100)
                        self.lbl_model_action_status.setText(f"Pulling '{model_name}': {status} ({pct}%)")
                    else:
                        self.lbl_model_action_status.setText(f"Pulling '{model_name}': {status}")

                self.lbl_model_action_status.setText(f"✅ Successfully pulled '{model_name}'!")
                self.lbl_model_action_status.setStyleSheet("color: #23a55a;")
                self._on_scan_models()
            except Exception as err:
                self.lbl_model_action_status.setText(f"❌ Pull failed: {err}")
                self.lbl_model_action_status.setStyleSheet("color: #da373c;")
            finally:
                self.btn_pull_model.setEnabled(True)

        asyncio.create_task(pull())

    def _on_import_gguf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select GGUF Model File",
            "",
            "GGUF Models (*.gguf)",
        )
        if not file_path:
            return

        base_name = os.path.splitext(os.path.basename(file_path))[0].lower().replace(" ", "-")
        host = self.txt_base_url.text().strip() or "http://localhost:11434"

        self.lbl_model_action_status.setText(f"Registering GGUF model '{base_name}' in Ollama...")
        self.lbl_model_action_status.setStyleSheet("color: #5865f2;")

        async def do_import() -> None:
            try:
                await create_ollama_model(base_name, file_path, host=host)
                self.lbl_model_action_status.setText(f"✅ Registered GGUF model as '{base_name}' in Ollama!")
                self.lbl_model_action_status.setStyleSheet("color: #23a55a;")
                self._on_scan_models()
            except Exception as err:
                self.lbl_model_action_status.setText(f"❌ GGUF registration failed: {err}")
                self.lbl_model_action_status.setStyleSheet("color: #da373c;")

        asyncio.create_task(do_import())

    # -------------------------------------------------------------------------
    # Card 2: Universal Generation Parameters
    # -------------------------------------------------------------------------

    def _create_universal_params_card(self) -> QGroupBox:
        group = QGroupBox("Universal Generation Hyperparameters")
        layout = QGridLayout(group)
        layout.setSpacing(8)

        # Temperature
        layout.addWidget(QLabel("Temperature:"), 0, 0)
        self.slider_temp = QSlider(Qt.Orientation.Horizontal)
        self.slider_temp.setRange(0, 200)  # 0.00 to 2.00
        self.lbl_val_temp = QLabel("0.80")
        self.slider_temp.valueChanged.connect(
            lambda v: self.lbl_val_temp.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.slider_temp, 0, 1)
        layout.addWidget(self.lbl_val_temp, 0, 2)

        # Top-P
        layout.addWidget(QLabel("Top-P (Nucleus):"), 1, 0)
        self.slider_top_p = QSlider(Qt.Orientation.Horizontal)
        self.slider_top_p.setRange(0, 100)  # 0.00 to 1.00
        self.lbl_val_top_p = QLabel("0.90")
        self.slider_top_p.valueChanged.connect(
            lambda v: self.lbl_val_top_p.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.slider_top_p, 1, 1)
        layout.addWidget(self.lbl_val_top_p, 1, 2)

        # Max Tokens
        layout.addWidget(QLabel("Max Tokens (Predict):"), 2, 0)
        self.spin_max_tokens = QSpinBox()
        self.spin_max_tokens.setRange(64, 4096)
        self.spin_max_tokens.setSingleStep(64)
        self.spin_max_tokens.setValue(512)
        layout.addWidget(self.spin_max_tokens, 2, 1, 1, 2)

        return group

    # -------------------------------------------------------------------------
    # Card 3: Local-Only Hardware & Sampling Parameters
    # -------------------------------------------------------------------------

    def _create_local_params_card(self) -> QGroupBox:
        self.local_params_group = QGroupBox("Local-Only Hardware & Sampling")
        layout = QGridLayout(self.local_params_group)
        layout.setSpacing(8)

        # Context Size (num_ctx)
        layout.addWidget(QLabel("Context Size (num_ctx):"), 0, 0)
        self.combo_num_ctx = QComboBox()
        self.combo_num_ctx.addItems(["2048", "4096", "8192", "16384", "32768"])
        self.combo_num_ctx.setCurrentText("8192")
        layout.addWidget(self.combo_num_ctx, 0, 1, 1, 2)

        # Min-P
        layout.addWidget(QLabel("Min-P Sampling:"), 1, 0)
        self.slider_min_p = QSlider(Qt.Orientation.Horizontal)
        self.slider_min_p.setRange(0, 50)  # 0.00 to 0.50
        self.lbl_val_min_p = QLabel("0.07")
        self.slider_min_p.valueChanged.connect(
            lambda v: self.lbl_val_min_p.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.slider_min_p, 1, 1)
        layout.addWidget(self.lbl_val_min_p, 1, 2)

        # Repeat Penalty
        layout.addWidget(QLabel("Repeat Penalty:"), 2, 0)
        self.slider_rep_penalty = QSlider(Qt.Orientation.Horizontal)
        self.slider_rep_penalty.setRange(100, 200)  # 1.00 to 2.00
        self.lbl_val_rep = QLabel("1.08")
        self.slider_rep_penalty.valueChanged.connect(
            lambda v: self.lbl_val_rep.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.slider_rep_penalty, 2, 1)
        layout.addWidget(self.lbl_val_rep, 2, 2)

        # Keep-Alive
        layout.addWidget(QLabel("GPU VRAM Keep-Alive:"), 3, 0)
        self.txt_keep_alive = QLineEdit()
        self.txt_keep_alive.setText("24h")
        self.txt_keep_alive.setPlaceholderText("e.g. 24h, 1h, 0s")
        layout.addWidget(self.txt_keep_alive, 3, 1, 1, 2)

        return self.local_params_group

    # -------------------------------------------------------------------------
    # Card 4: System Prompt & Personas
    # -------------------------------------------------------------------------

    def _create_persona_card(self) -> QGroupBox:
        group = QGroupBox("System Prompt & Persona Engine")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Persona Preset:"))

        self.combo_presets = QComboBox()
        self.combo_presets.addItems(list(SYSTEM_PROMPT_PRESETS.keys()))
        self.combo_presets.currentTextChanged.connect(self._on_preset_changed)
        header_row.addWidget(self.combo_presets, stretch=1)
        layout.addLayout(header_row)

        self.txt_system_prompt = QPlainTextEdit()
        self.txt_system_prompt.setMaximumHeight(110)
        self.txt_system_prompt.setStyleSheet(
            "background-color: #111214; color: #dbdee1; font-size: 12px;"
        )
        layout.addWidget(self.txt_system_prompt)

        return group

    def _on_preset_changed(self, preset_name: str) -> None:
        template = SYSTEM_PROMPT_PRESETS.get(preset_name)
        if template is None:
            self.txt_system_prompt.setPlainText(DEFAULT_SYSTEM_PROMPT)
        else:
            self.txt_system_prompt.setPlainText(template)

    # -------------------------------------------------------------------------
    # Card 5: Vision Settings
    # -------------------------------------------------------------------------

    def _create_vision_card(self) -> QGroupBox:
        group = QGroupBox("Vision & Multimodal OCR")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.chk_vision_enabled = QCheckBox("Enable Vision Perception")
        self.chk_vision_enabled.setChecked(self.config.vision_enabled)
        layout.addWidget(self.chk_vision_enabled)

        layout.addWidget(QLabel("Vision Model Name:"))
        self.combo_vision_model = QComboBox()
        self.combo_vision_model.setEditable(True)
        self.combo_vision_model.addItems(COMMON_VISION_PRESETS)
        layout.addWidget(self.combo_vision_model)

        dim_row = QHBoxLayout()
        dim_row.addWidget(QLabel("Max Dim:"))
        self.spin_vision_dim = QSpinBox()
        self.spin_vision_dim.setRange(512, 3840)
        self.spin_vision_dim.setSingleStep(256)
        self.spin_vision_dim.setValue(self.config.vision_max_dimension)
        dim_row.addWidget(self.spin_vision_dim)
        layout.addLayout(dim_row)

        tokens_row = QHBoxLayout()
        tokens_row.addWidget(QLabel("Vision Tokens:"))
        self.spin_vision_tokens = QSpinBox()
        self.spin_vision_tokens.setRange(256, 4096)
        self.spin_vision_tokens.setSingleStep(128)
        self.spin_vision_tokens.setValue(self.config.vision_num_predict)
        tokens_row.addWidget(self.spin_vision_tokens)
        layout.addLayout(tokens_row)

        layout.addStretch()
        return group

    # -------------------------------------------------------------------------
    # Save & Reset Handlers
    # -------------------------------------------------------------------------

    def _load_config_values(self) -> None:
        # Provider
        idx = self.combo_provider.findData(self.config.ai_provider)
        if idx >= 0:
            self.combo_provider.setCurrentIndex(idx)
        else:
            self.combo_provider.setCurrentIndex(0)

        self.txt_base_url.setText(self.config.api_base_url or self.config.ollama_host or "")
        self.txt_api_key.setText(self.config.api_key or "")

        current_model = self.config.api_model or self.config.ollama_model
        idx_m = self.combo_model.findText(current_model)
        if idx_m >= 0:
            self.combo_model.setCurrentIndex(idx_m)
        else:
            self.combo_model.setEditText(current_model)

        current_vision = self.config.vision_model or "qwen2.5vl:7b-instruct-q4_K_M"
        idx_v = self.combo_vision_model.findText(current_vision)
        if idx_v >= 0:
            self.combo_vision_model.setCurrentIndex(idx_v)
        else:
            self.combo_vision_model.setEditText(current_vision)

        # Universal
        self.slider_temp.setValue(int(self.config.temperature * 100))
        self.slider_top_p.setValue(int(self.config.top_p * 100))
        self.spin_max_tokens.setValue(self.config.num_predict)

        # Local
        self.combo_num_ctx.setCurrentText(str(self.config.num_ctx))
        self.slider_min_p.setValue(int(self.config.min_p * 100))
        self.slider_rep_penalty.setValue(int(self.config.repeat_penalty * 100))
        self.txt_keep_alive.setText(self.config.keep_alive)

        # Prompt
        self.txt_system_prompt.setPlainText(self.config.system_prompt)

        # Trigger visibility update
        self._on_provider_changed()

    def _on_save_settings(self) -> None:
        # Update config fields
        provider = self.combo_provider.currentData()
        old_host = self.config.ollama_host
        self.config.ai_provider = provider
        self.config.api_base_url = self.txt_base_url.text().strip()
        self.config.api_key = self.txt_api_key.text().strip()

        model_name = self.combo_model.currentText().strip()
        if provider == "ollama":
            self.config.ollama_model = model_name or "qwen3.5:9b"
            if self.config.api_base_url:
                self.config.ollama_host = self.config.api_base_url
        else:
            self.config.api_model = model_name

        self.config.temperature = self.slider_temp.value() / 100.0
        self.config.top_p = self.slider_top_p.value() / 100.0
        self.config.num_predict = self.spin_max_tokens.value()

        if self.combo_num_ctx.currentText().isdigit():
            self.config.num_ctx = int(self.combo_num_ctx.currentText())

        self.config.min_p = self.slider_min_p.value() / 100.0
        self.config.repeat_penalty = self.slider_rep_penalty.value() / 100.0
        self.config.keep_alive = self.txt_keep_alive.text().strip() or "24h"

        self.config.system_prompt = self.txt_system_prompt.toPlainText().strip()
        self.config.vision_enabled = self.chk_vision_enabled.isChecked()
        self.config.vision_model = self.combo_vision_model.currentText().strip()
        self.config.vision_max_dimension = self.spin_vision_dim.value()
        self.config.vision_num_predict = self.spin_vision_tokens.value()

        # Save to .env file
        self.config.save_ai_settings()

        # The bot shares this config object, so everything applies live except the host:
        # the Ollama clients are built once when the bot starts.
        if self.main_window.runner.bot and self.config.ollama_host != old_host:
            self.lbl_status.setText("✅ AI settings saved. Restart the bot to use the new Ollama host.")
        else:
            self.lbl_status.setText("✅ AI settings saved and applied to bot runtime!")
        self.lbl_status.setStyleSheet("color: #23a55a;")

    def _on_reset_defaults(self) -> None:
        self.slider_temp.setValue(80)
        self.slider_top_p.setValue(90)
        self.spin_max_tokens.setValue(512)
        self.slider_min_p.setValue(7)
        self.slider_rep_penalty.setValue(108)
        self.combo_num_ctx.setCurrentText("8192")
        self.txt_keep_alive.setText("24h")
        self.combo_presets.setCurrentIndex(0)
        self.txt_system_prompt.setPlainText(DEFAULT_SYSTEM_PROMPT)
        idx_v = self.combo_vision_model.findText("qwen2.5vl:7b-instruct-q4_K_M")
        if idx_v >= 0:
            self.combo_vision_model.setCurrentIndex(idx_v)
        else:
            self.combo_vision_model.setEditText("qwen2.5vl:7b-instruct-q4_K_M")
        self.lbl_status.setText("Reset to default tsundere parameters.")
        self.lbl_status.setStyleSheet("color: #949ba4;")
