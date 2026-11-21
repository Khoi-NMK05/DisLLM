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
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import Card, StatusLabel
from bot.config import DEFAULT_SYSTEM_PROMPT, BotConfig
from bot.services.ai_helpers import (
    PROVIDER_PRESETS,
    SYSTEM_PROMPT_PRESETS,
    create_ollama_model,
    fetch_ollama_tags,
    fetch_openai_compatible_models,
    load_custom_personas,
    pull_ollama_model,
    save_custom_personas,
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


def _space_grid(grid: QGridLayout) -> None:
    """Label/control grids inside cards: 12px between columns, 10px between rows."""
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(10)


def _hint_label(text: str, hint: str) -> QLabel:
    """A form label whose tooltip explains the setting in plain language."""
    label = QLabel(text)
    label.setToolTip(hint)
    return label


def _value_label(text: str) -> QLabel:
    """A slider readout with a fixed width, so the slider doesn't shift as the number changes."""
    label = QLabel(text)
    label.setMinimumWidth(label.fontMetrics().horizontalAdvance("0.00") + 4)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return label


class AIModelsTab(QWidget):
    """Configuration interface for local and cloud AI providers and hyperparameters."""

    def __init__(self, main_window: MainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.config: BotConfig = main_window.config

        self._init_ui()
        self._load_config_values()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # The cards are taller than a default-sized window, so they scroll; the action bar stays put.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        scroll.setWidget(content)
        # setWidget() turns on background filling; switch it off so the page's BASE surface shows through.
        scroll.viewport().setAutoFillBackground(False)
        content.setAutoFillBackground(False)
        outer.addWidget(scroll, stretch=1)

        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(20, 20, 20, 16)
        main_layout.setSpacing(16)

        # 1. Provider & Model Card
        main_layout.addWidget(self._create_provider_card())

        # 2. Hyperparameters Section (Universal + Local-only side-by-side)
        self._params_row = params_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        params_row.setSpacing(16)
        params_row.addWidget(self._create_universal_params_card(), stretch=1)
        params_row.addWidget(self._create_local_params_card(), stretch=1)
        main_layout.addLayout(params_row)

        # 3. System Prompt & Vision Section
        self._lower_row = lower_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        lower_row.setSpacing(16)
        lower_row.addWidget(self._create_persona_card(), stretch=2)
        side_col = QVBoxLayout()
        side_col.setSpacing(16)
        side_col.addWidget(self._create_vision_card())
        side_col.addWidget(self._create_search_card())
        lower_row.addLayout(side_col, stretch=1)
        main_layout.addLayout(lower_row)
        main_layout.addStretch(1)

        # 4. Action Bar (outside the scroll area, always visible)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(20, 12, 20, 16)
        action_row.setSpacing(8)
        self.btn_save_settings = QPushButton("Save && Apply Settings")
        self.btn_save_settings.setProperty("class", "primary")
        self.btn_save_settings.clicked.connect(self._on_save_settings)

        self.btn_reset_defaults = QPushButton("Reset to Defaults")
        self.btn_reset_defaults.clicked.connect(self._on_reset_defaults)

        self.lbl_status = StatusLabel("")
        self.lbl_status.setProperty("class", "muted")

        action_row.addWidget(self.btn_save_settings)
        action_row.addWidget(self.btn_reset_defaults)
        action_row.addWidget(self.lbl_status, stretch=1)
        action_row.addStretch(0)  # keeps the buttons compact while the status is empty

        outer.addLayout(action_row)

    # Below this width the side-by-side card rows stack into one column.
    _STACK_BELOW = 820

    def resizeEvent(self, event) -> None:  # Qt override
        super().resizeEvent(event)
        direction = (
            QBoxLayout.Direction.TopToBottom
            if self.width() < self._STACK_BELOW
            else QBoxLayout.Direction.LeftToRight
        )
        for row in (self._params_row, self._lower_row):
            if row.direction() != direction:
                row.setDirection(direction)

    # -------------------------------------------------------------------------
    # Card 1: Provider & Model Selector
    # -------------------------------------------------------------------------

    def _create_provider_card(self) -> Card:
        group = Card("Provider & Model")
        layout = group.body
        layout.setSpacing(10)

        # Provider Selector Row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Provider:"))
        self.combo_provider = QComboBox()
        for key, info in PROVIDER_PRESETS.items():
            self.combo_provider.addItem(info["name"], key)
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        row1.addWidget(self.combo_provider, stretch=1)

        row1.addWidget(QLabel("Server URL:"))
        self.txt_base_url = QLineEdit()
        self.txt_base_url.setPlaceholderText("http://localhost:11434 or https://...")
        row1.addWidget(self.txt_base_url, stretch=2)
        layout.addLayout(row1)

        # API Key & Model Row
        row2 = QHBoxLayout()
        self.lbl_api_key = QLabel("API key:")
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("Paste the API key from your provider's dashboard")

        row2.addWidget(self.lbl_api_key)
        row2.addWidget(self.txt_api_key, stretch=2)

        row2.addWidget(QLabel("Model:"))
        self.combo_model = QComboBox()
        self.combo_model.setEditable(True)
        self.combo_model.setMinimumWidth(200)
        row2.addWidget(self.combo_model, stretch=2)

        self.btn_scan_models = QPushButton("List Models")
        self.btn_scan_models.setToolTip("Ask the server which models it has and fill the Model list.")
        self.btn_scan_models.clicked.connect(lambda: self._on_scan_models())
        row2.addWidget(self.btn_scan_models)

        layout.addLayout(row2)

        # Ollama-only row: download a model, or add a local .gguf file
        self.ollama_tools_frame = QFrame()
        self.ollama_tools_frame.setProperty("class", "inset")
        tools_layout = QHBoxLayout(self.ollama_tools_frame)
        tools_layout.setContentsMargins(10, 8, 10, 8)
        tools_layout.setSpacing(8)

        tools_layout.addWidget(QLabel("Download a model:"))
        self.txt_pull_name = QLineEdit()
        self.txt_pull_name.setPlaceholderText("e.g. mistral or hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF")
        tools_layout.addWidget(self.txt_pull_name, stretch=1)

        self.btn_pull_model = QPushButton("Download")
        self.btn_pull_model.setToolTip(
            "Download a model from the Ollama library or Hugging Face (the same as `ollama pull`)."
        )
        self.btn_pull_model.clicked.connect(self._on_pull_model)
        tools_layout.addWidget(self.btn_pull_model)

        self.btn_import_gguf = QPushButton("Import .gguf File...")
        self.btn_import_gguf.setToolTip("Add a .gguf model file from this computer to Ollama.")
        self.btn_import_gguf.clicked.connect(self._on_import_gguf)
        tools_layout.addWidget(self.btn_import_gguf)

        layout.addWidget(self.ollama_tools_frame)

        self.lbl_model_action_status = StatusLabel("")
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

        # These settings only exist in Ollama; the card title says so.
        self.local_params_group.setEnabled(is_ollama)

    def _on_scan_models(self, done: str = "") -> None:
        """Refresh the model lists. `done` is an earlier success message to keep in front of the result."""
        provider_key = self.combo_provider.currentData()
        base_url = self.txt_base_url.text().strip()
        api_key = self.txt_api_key.text().strip()

        self.btn_scan_models.setEnabled(False)
        self.lbl_model_action_status.setTone(f"{done} Looking for models...".strip(), "neutral")

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

                    found = "Found 1 model." if len(models) == 1 else f"Found {len(models)} models."
                    self.lbl_model_action_status.setTone(f"{done} {found}".strip(), "success")
                else:
                    hint = "Download one below." if provider_key == "ollama" else "Check the Server URL."
                    self.lbl_model_action_status.setTone(f"{done} The server has no models yet. {hint}".strip(), "warning")
            except Exception as err:
                check = "that Ollama is running" if provider_key == "ollama" else "the Server URL and API key"
                self.lbl_model_action_status.setTone(f"Couldn't get the model list: {err}. Check {check}.", "error")
            finally:
                self.btn_scan_models.setEnabled(True)

        asyncio.create_task(scan())

    def _on_pull_model(self) -> None:
        model_name = self.txt_pull_name.text().strip()
        if not model_name:
            self.lbl_model_action_status.setTone(
                "Type a model name to download, such as mistral or a Hugging Face link.", "warning"
            )
            return

        host = self.txt_base_url.text().strip() or "http://localhost:11434"
        self.btn_pull_model.setEnabled(False)
        self.lbl_model_action_status.setTone(f"Downloading '{model_name}'...", "neutral")

        async def pull() -> None:
            try:
                async for update in pull_ollama_model(model_name, host=host):
                    status = update.get("status", "")
                    completed = update.get("completed", 0)
                    total = update.get("total", 0)
                    if total > 0:
                        pct = int((completed / total) * 100)
                        self.lbl_model_action_status.setText(f"Downloading '{model_name}': {status} ({pct}%)")
                    else:
                        self.lbl_model_action_status.setText(f"Downloading '{model_name}': {status}")

                self._on_scan_models(done=f"Downloaded '{model_name}'.")
            except Exception as err:
                self.lbl_model_action_status.setTone(
                    f"Couldn't download '{model_name}': {err}. Check the name and that Ollama is running.", "error"
                )
            finally:
                self.btn_pull_model.setEnabled(True)

        asyncio.create_task(pull())

    def _on_import_gguf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a .gguf Model File",
            "",
            "GGUF models (*.gguf)",
        )
        if not file_path:
            return

        base_name = os.path.splitext(os.path.basename(file_path))[0].lower().replace(" ", "-")
        host = self.txt_base_url.text().strip() or "http://localhost:11434"

        self.btn_import_gguf.setEnabled(False)
        self.lbl_model_action_status.setTone(f"Adding '{base_name}' to Ollama...", "neutral")

        async def do_import() -> None:
            try:
                await create_ollama_model(base_name, file_path, host=host)
                self._on_scan_models(done=f"Added '{base_name}' to Ollama.")
            except Exception as err:
                self.lbl_model_action_status.setTone(
                    f"Couldn't add the .gguf file: {err}. Check that Ollama is running.", "error"
                )
            finally:
                self.btn_import_gguf.setEnabled(True)

        asyncio.create_task(do_import())

    # -------------------------------------------------------------------------
    # Card 2: Universal Generation Parameters
    # -------------------------------------------------------------------------

    def _create_universal_params_card(self) -> Card:
        group = Card("Reply Settings")
        layout = QGridLayout()
        group.body.addLayout(layout)
        _space_grid(layout)

        # Temperature
        layout.addWidget(_hint_label("Creativity (temperature):", "Lower gives focused, predictable replies. Higher gives more creative, surprising ones. Model guides call this temperature."), 0, 0)
        self.slider_temp = QSlider(Qt.Orientation.Horizontal)
        self.slider_temp.setRange(0, 200)  # 0.00 to 2.00
        self.lbl_val_temp = _value_label("0.80")
        self.slider_temp.valueChanged.connect(
            lambda v: self.lbl_val_temp.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.slider_temp, 0, 1)
        layout.addWidget(self.lbl_val_temp, 0, 2)

        # Top-P
        layout.addWidget(_hint_label("Word variety (top-p):", "How wide a range of likely words the model picks from. Lower is safer and plainer, higher is more varied."), 1, 0)
        self.slider_top_p = QSlider(Qt.Orientation.Horizontal)
        self.slider_top_p.setRange(0, 100)  # 0.00 to 1.00
        self.lbl_val_top_p = _value_label("0.90")
        self.slider_top_p.valueChanged.connect(
            lambda v: self.lbl_val_top_p.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.slider_top_p, 1, 1)
        layout.addWidget(self.lbl_val_top_p, 1, 2)

        # Max Tokens
        layout.addWidget(_hint_label("Max reply length (tokens):", "The longest a single reply can be. A token is roughly three quarters of a word."), 2, 0)
        self.spin_max_tokens = QSpinBox()
        self.spin_max_tokens.setRange(64, 4096)
        self.spin_max_tokens.setSingleStep(64)
        self.spin_max_tokens.setValue(512)
        layout.addWidget(self.spin_max_tokens, 2, 1, 1, 2)
        layout.setRowStretch(3, 1)  # keep rows packed at the top

        return group

    # -------------------------------------------------------------------------
    # Card 3: Local-Only Hardware & Sampling Parameters
    # -------------------------------------------------------------------------

    def _create_local_params_card(self) -> Card:
        self.local_params_group = Card("Ollama-Only Settings")
        layout = QGridLayout()
        self.local_params_group.body.addLayout(layout)
        _space_grid(layout)

        # Context Size (num_ctx)
        layout.addWidget(_hint_label("Memory size (tokens):", "How much text the model can look at in one go: the persona, recent messages and the reply. Bigger uses more GPU memory. This is separate from how many messages the bot stores. Ollama calls it num_ctx."), 0, 0)
        self.combo_num_ctx = QComboBox()
        self.combo_num_ctx.addItems(["2048", "4096", "8192", "16384", "32768"])
        self.combo_num_ctx.setCurrentText("8192")
        layout.addWidget(self.combo_num_ctx, 0, 1, 1, 2)

        # Min-P
        layout.addWidget(_hint_label("Stay on topic (min-p):", "Ignores words that are much less likely than the best choice. Higher keeps replies on track, lower allows more variety."), 1, 0)
        self.slider_min_p = QSlider(Qt.Orientation.Horizontal)
        self.slider_min_p.setRange(0, 50)  # 0.00 to 0.50
        self.lbl_val_min_p = _value_label("0.07")
        self.slider_min_p.valueChanged.connect(
            lambda v: self.lbl_val_min_p.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.slider_min_p, 1, 1)
        layout.addWidget(self.lbl_val_min_p, 1, 2)

        # Repeat Penalty
        layout.addWidget(_hint_label("Avoid repetition:", "Discourages the model from repeating itself. 1.00 is off; small values like 1.05 to 1.15 work best. Model guides call this repeat penalty."), 2, 0)
        self.slider_rep_penalty = QSlider(Qt.Orientation.Horizontal)
        self.slider_rep_penalty.setRange(100, 200)  # 1.00 to 2.00
        self.lbl_val_rep = _value_label("1.08")
        self.slider_rep_penalty.valueChanged.connect(
            lambda v: self.lbl_val_rep.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.slider_rep_penalty, 2, 1)
        layout.addWidget(self.lbl_val_rep, 2, 2)

        # Keep-Alive
        layout.addWidget(_hint_label("Keep model loaded for:", "How long Ollama keeps the model in GPU memory after a reply, so the next reply starts fast. 0s frees the memory right away."), 3, 0)
        self.txt_keep_alive = QLineEdit()
        self.txt_keep_alive.setText("24h")
        self.txt_keep_alive.setPlaceholderText("e.g. 24h, 1h, 0s")
        layout.addWidget(self.txt_keep_alive, 3, 1, 1, 2)
        layout.setRowStretch(4, 1)  # keep rows packed at the top

        return self.local_params_group

    # -------------------------------------------------------------------------
    # Card 4: System Prompt & Personas
    # -------------------------------------------------------------------------

    def _create_persona_card(self) -> Card:
        group = Card("Persona")
        layout = group.body

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Persona:"))

        self.custom_personas = load_custom_personas()
        self.combo_presets = QComboBox()
        self.combo_presets.setMinimumContentsLength(20)
        self.combo_presets.currentTextChanged.connect(self._on_preset_changed)
        header_row.addWidget(self.combo_presets, stretch=1)

        self._draft_name: str | None = None  # a "New" persona not saved yet
        self.btn_new_preset = QPushButton("New")
        self.btn_new_preset.setToolTip("Start a new, empty persona. Describe it in the box below, then click Save Persona.")
        self.btn_new_preset.clicked.connect(self._on_new_preset)
        header_row.addWidget(self.btn_new_preset)

        self.btn_save_preset = QPushButton("Save Persona")
        self.btn_save_preset.setToolTip("Save the text below as a persona you can pick later.")
        self.btn_save_preset.clicked.connect(self._on_save_preset)
        header_row.addWidget(self.btn_save_preset)

        self.btn_delete_preset = QPushButton("Delete")
        self.btn_delete_preset.setProperty("class", "danger")
        self.btn_delete_preset.setToolTip("Delete this persona. Built-in personas can't be deleted.")
        self.btn_delete_preset.clicked.connect(self._on_delete_preset)
        header_row.addWidget(self.btn_delete_preset)
        layout.addLayout(header_row)

        self.txt_system_prompt = QPlainTextEdit()
        self.txt_system_prompt.setMinimumHeight(260)
        layout.addWidget(self.txt_system_prompt, stretch=1)

        self._populate_presets()
        return group

    def _preset_prompt(self, name: str) -> str | None:
        if name in SYSTEM_PROMPT_PRESETS:
            return SYSTEM_PROMPT_PRESETS[name] or DEFAULT_SYSTEM_PROMPT
        if name == self._draft_name:
            return ""
        return self.custom_personas.get(name)

    def _populate_presets(self, select: str | None = None) -> None:
        """Rebuilds the dropdown without touching the prompt text. Drops any unsaved draft."""
        self._draft_name = None
        self.txt_system_prompt.setPlaceholderText("")
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        self.combo_presets.addItems(list(SYSTEM_PROMPT_PRESETS))
        self.combo_presets.addItems([n for n in self.custom_personas if n not in SYSTEM_PROMPT_PRESETS])
        if select is not None:
            self.combo_presets.setCurrentIndex(max(0, self.combo_presets.findText(select)))
        self.combo_presets.blockSignals(False)
        self._update_preset_buttons()

    def _update_preset_buttons(self) -> None:
        current = self.combo_presets.currentText()
        self.btn_delete_preset.setEnabled(current in self.custom_personas or current == self._draft_name)

    def _on_new_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "New Persona", "Name for the new persona:")
        name = " ".join(name.split())
        if not ok or not name:
            return
        if name in SYSTEM_PROMPT_PRESETS or name in self.custom_personas:
            self._set_status(f"There's already a persona called '{name}'. Pick another name.", "warning")
            return

        # Replace any earlier unsaved draft with this one.
        if self._draft_name is not None:
            idx = self.combo_presets.findText(self._draft_name)
            if idx >= 0:
                self.combo_presets.removeItem(idx)
        self._draft_name = name
        self.combo_presets.addItem(name)
        self.combo_presets.setCurrentText(name)  # triggers _on_preset_changed -> clears the box
        self.txt_system_prompt.setPlaceholderText(
            f"Describe how '{name}' should talk and behave, then click Save Persona."
        )
        self.txt_system_prompt.setFocus()
        self._set_status(f"Describe '{name}' in the box, then click Save Persona.", "neutral")

    def _on_preset_changed(self, preset_name: str) -> None:
        self._update_preset_buttons()
        prompt = self._preset_prompt(preset_name)
        if prompt is not None:
            self.txt_system_prompt.setPlainText(prompt)

    def _on_save_preset(self) -> None:
        prompt = self.txt_system_prompt.toPlainText().strip()
        if not prompt:
            self._set_status("The persona is empty. Describe how the bot should behave, then save.", "warning")
            return

        current = self.combo_presets.currentText()
        default_name = current if current in self.custom_personas or current == self._draft_name else ""
        name, ok = QInputDialog.getText(self, "Save Persona", "Persona name:", text=default_name)
        name = " ".join(name.split())
        if not ok or not name:
            return
        if name in SYSTEM_PROMPT_PRESETS:
            self._set_status(f"'{name}' is a built-in persona. Pick another name.", "warning")
            return
        if (
            name in self.custom_personas
            and name != current
            and not self._confirm(
                "Replace Persona", f"There's already a persona called '{name}'. Replace it with this one?", "Replace"
            )
        ):
            return

        updated = {**self.custom_personas, name: prompt}
        try:
            save_custom_personas(updated)
        except OSError as err:
            self._set_status(f"Couldn't save the persona: {err}", "error")
            return
        self.custom_personas = updated
        self._populate_presets(select=name)
        self._set_status(
            f"Saved persona '{name}'. Click Save & Apply Settings to make the bot use it.", "success"
        )

    def _on_delete_preset(self) -> None:
        name = self.combo_presets.currentText()
        if name == self._draft_name:
            # Unsaved draft: just discard it, nothing on disk to remove.
            self._populate_presets(select=next(iter(SYSTEM_PROMPT_PRESETS)))
            self._on_preset_changed(self.combo_presets.currentText())
            self._set_status(f"Discarded the unsaved persona '{name}'.", "neutral")
            return
        if name not in self.custom_personas:
            return
        if not self._confirm(
            "Delete Persona",
            f"Delete the persona '{name}'? The bot keeps using its current persona until you pick another.",
            "Delete",
        ):
            return

        updated = {k: v for k, v in self.custom_personas.items() if k != name}
        try:
            save_custom_personas(updated)
        except OSError as err:
            self._set_status(f"Couldn't delete the persona: {err}", "error")
            return
        self.custom_personas = updated
        self._populate_presets(select=next(iter(SYSTEM_PROMPT_PRESETS)))
        self._set_status(f"Deleted persona '{name}'.", "success")

    def _set_status(self, text: str, tone: str) -> None:
        self.lbl_status.setTone(text, tone)

    def _confirm(self, title: str, text: str, action: str) -> bool:
        """Ask before a destructive change. The confirm button is named after the action."""
        box = QMessageBox(QMessageBox.Icon.Question, title, text, parent=self)
        ok = box.addButton(action, QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(QMessageBox.StandardButton.NoButton)
        box.exec()
        return box.clickedButton() is ok

    # -------------------------------------------------------------------------
    # Card 5: Vision Settings
    # -------------------------------------------------------------------------

    def _create_vision_card(self) -> Card:
        group = Card("Vision")
        layout = group.body

        self.chk_vision_enabled = QCheckBox("Let the bot read images")
        self.chk_vision_enabled.setChecked(self.config.vision_enabled)
        layout.addWidget(self.chk_vision_enabled)

        model_col = QVBoxLayout()
        model_col.setSpacing(4)
        model_col.addWidget(QLabel("Vision model:"))
        self.combo_vision_model = QComboBox()
        self.combo_vision_model.setEditable(True)
        self.combo_vision_model.addItems(COMMON_VISION_PRESETS)
        model_col.addWidget(self.combo_vision_model)
        layout.addLayout(model_col)

        dim_row = QHBoxLayout()
        dim_row.addWidget(_hint_label("Max image size (px):", "Images are shrunk so their longest side is at most this many pixels before the vision model reads them. Smaller is faster."))
        self.spin_vision_dim = QSpinBox()
        self.spin_vision_dim.setRange(512, 3840)
        self.spin_vision_dim.setSingleStep(256)
        self.spin_vision_dim.setValue(self.config.vision_max_dimension)
        dim_row.addWidget(self.spin_vision_dim)
        layout.addLayout(dim_row)

        tokens_row = QHBoxLayout()
        tokens_row.addWidget(_hint_label("Description length (tokens):", "The longest the vision model's description of an image can be. It also reads text in images, so longer helps with screenshots."))
        self.spin_vision_tokens = QSpinBox()
        self.spin_vision_tokens.setRange(256, 4096)
        self.spin_vision_tokens.setSingleStep(128)
        self.spin_vision_tokens.setValue(self.config.vision_num_predict)
        tokens_row.addWidget(self.spin_vision_tokens)
        layout.addLayout(tokens_row)

        # The model and limits only matter while vision is on.
        vision_fields = (self.combo_vision_model, self.spin_vision_dim, self.spin_vision_tokens)
        def sync_vision(on: bool) -> None:
            for w in vision_fields:
                w.setEnabled(on)
        self.chk_vision_enabled.toggled.connect(sync_vision)
        sync_vision(self.chk_vision_enabled.isChecked())

        layout.addStretch()
        return group

    def _create_search_card(self) -> Card:
        group = Card("Web Search")
        layout = group.body

        self.chk_search_enabled = QCheckBox("Let the bot search the web")
        self.chk_search_enabled.setChecked(self.config.search_enabled)
        layout.addWidget(self.chk_search_enabled)

        self.chk_search_sources = QCheckBox("Show a Sources line under replies")
        self.chk_search_sources.setChecked(self.config.search_show_sources)
        layout.addWidget(self.chk_search_sources)

        results_row = QHBoxLayout()
        results_row.addWidget(QLabel("Results per search:"))
        self.spin_search_results = QSpinBox()
        self.spin_search_results.setRange(1, 10)
        self.spin_search_results.setValue(self.config.search_max_results)
        results_row.addWidget(self.spin_search_results)
        layout.addLayout(results_row)

        note = QLabel(
            "Uses DuckDuckGo. Search queries leave your computer even with a local model. "
            "The model decides when to search if it supports tool calling; custom AI commands with "
            "web search turned on always search."
        )
        note.setWordWrap(True)
        note.setProperty("class", "muted")
        layout.addWidget(note)
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

        # Prompt: show the preset that matches the saved prompt, if any.
        self.txt_system_prompt.setPlainText(self.config.system_prompt)
        saved = self.config.system_prompt.strip()
        match = next(
            (n for n in [*SYSTEM_PROMPT_PRESETS, *self.custom_personas]
             if (self._preset_prompt(n) or "").strip() == saved),
            None,
        )
        self._populate_presets(select=match)

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
        self.config.search_enabled = self.chk_search_enabled.isChecked()
        self.config.search_show_sources = self.chk_search_sources.isChecked()
        self.config.search_max_results = self.spin_search_results.value()

        # Save to .env file
        self.config.save_ai_settings()

        # The bot shares this config object, so everything applies live except the host:
        # the Ollama clients are built once when the bot starts.
        needs_key = PROVIDER_PRESETS.get(provider, {}).get("requires_key", False)
        if needs_key and not self.config.api_key:
            self.lbl_status.setTone(
                f"Settings saved, but {self.combo_provider.currentText()} needs an API key before the bot can reply.",
                "warning",
            )
        elif not self.main_window.runner.bot:
            self.lbl_status.setTone("Settings saved. They'll be used when you start the bot.", "success")
        elif self.config.ollama_host != old_host:
            self.lbl_status.setTone("Settings saved. Restart the bot to connect to the new Ollama host.", "warning")
        else:
            self.lbl_status.setTone("Settings saved and applied to the running bot.", "success")

    def _on_reset_defaults(self) -> None:
        if not self._confirm(
            "Reset to Defaults",
            "Reset the reply and Ollama settings and the vision model, and switch to the default persona? "
            "Unsaved changes to the persona text are lost. Saved personas aren't affected.",
            "Reset",
        ):
            return
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
        self.lbl_status.setTone("Defaults restored. Click Save & Apply Settings to keep them.", "neutral")
