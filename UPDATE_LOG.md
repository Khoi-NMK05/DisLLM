# 📝 Project Update Log

All notable changes, file modifications, and new feature implementations for **DiscordChatBotxOllama** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [v2.0] - Desktop Executable Application, Multi-Server Control, Dual AI & Full Studio

### 🌟 Added
- **Interactive Mentions & Replies in Remote Chat (`gui/tabs/bot_control_tab.py`)**:
  - Added clickable `[↩ Reply]` and `[@ Mention]` action buttons and clickable author names inside the live message feed.
  - Implemented reply preview banner with one-click cancel (`[✕]`) and automatic input focus.
  - Added `feed_browser.setOpenLinks(False)` to prevent `QTextBrowser` from internally navigating away or clearing the chat history when clicking message links.
- **Server Moderation & Privacy Rules (`bot/moderation.py`)**:
  - Implemented `ModerationManager` managing DM privacy, channel whitelist/blacklist modes, and per-user sliding window rate limiting.
  - Hooked privacy checks directly into `bot/cogs/chat.py` with custom tsundere cooldown responses.
  - Persists moderation settings to `data/moderation_settings.json`.
- **SQLite Memory Inspector & Purge Engine (`bot/database.py`, `gui/tabs/settings_tab.py`)**:
  - Added `list_active_channels()` and `get_detailed_channel_history()` in `DatabaseManager`.
  - Built interactive visual table of all active conversation sessions, message turn counts, and timestamps.
  - One-click channel memory clearing and full database wipe/vacuum with confirmation prompts.
- **Windows System Tray & Background Minimization (`gui/main_window.py`)**:
  - Integrated `QSystemTrayIcon` with programmatic blurple icon and custom context menu (*Show Window*, *Dashboard*, *Exit*).
  - Configurable "Minimize to Tray on Close" allowing continuous 24/7 background operation.
- **Standalone Windows Executable Builder (`build_exe.py`)**:
  - Automated PyInstaller packaging script bundling dependencies, plugins, and Qt assets into `dist/DiscordAICompanion/DiscordAICompanion.exe`.
- **No-Code Custom Slash Command Engine (`bot/custom_commands.py`)**:
  - Implemented `CustomCommandManager` and `CustomCommand` supporting three command architectures:
    1. **AI Prompt Shortcuts**: Define dynamic prompts with parameter injection (`{query}`, `{user}`, `{bot}`) routing directly to the AI engine.
    2. **Rich Embed Cards**: Build customizable embed cards with titles, color pickers, and formatted content.
    3. **Static Auto-Responders**: Canned fast responses with optional query interpolation.
  - Built-in default command templates: `/roast`, `/translate`, `/summarize`, and `/rules`.
  - Automatic persistence to `data/custom_commands.json` and dynamic registration to `bot.tree`.
- **Modular Python Cog Plugin System (`bot/plugins.py`)**:
  - Automatically manages the `plugins/` directory, discovering custom `.py` Discord cogs.
  - Generates `plugins/example_plugin.py` to give users an immediate starting template.
  - Enables loading, unloading, and live-reloading plugins on Discord without restarting the application.
- **Custom Commands & Plugin Studio Tab (Phase 4) (`gui/tabs/commands_tab.py`)**:
  - **Slash Command Studio**: Visual form for creating and editing slash commands, testing validation rules (1-32 lowercase regex), setting ephemeral visibility, and one-click "Sync to Discord Gateway".
  - **Plugin Manager Table**: Lists all installed cogs with docstrings, loaded status pills, "Load/Unload" toggles, "🔄 Live Reload" buttons, and a shortcut to open the plugins folder.
- **Dual-Engine AI Inference Router (`bot/services/ollama_service.py`, `bot/services/ai_helpers.py`)**:
  - Abstracted LLM execution to support both **Local Providers** (`ollama`, `lm_studio`, `llama.cpp`) and **Cloud API Providers** (`openrouter`, `openai`, `gemini`, `groq`, `custom`).
  - Added REST chat completions adapter with support for `<think>` tag stripping and `[REACTION: emoji]` parsing across all cloud/local backends.
  - Added `fetch_ollama_tags()` to auto-discover local installed models.
  - Added `pull_ollama_model()` to stream model downloads from Ollama and Hugging Face (`hf.co/...`).
  - Added `create_ollama_model()` to register local `.gguf` files with Ollama.
  - Added `fetch_openai_compatible_models()` to query models from any OpenAI-compatible API.
  - Built-in Persona System Prompt Presets: *Tsundere B-chan*, *Helpful & Friendly Assistant*, *Senior Coding Companion*, *Casual Gamer Buddy*.
- **AI Engine & Hyperparameters Tab (Phase 3) (`gui/tabs/ai_models_tab.py`)**:
  - **Provider Switcher**: One-click switching between Ollama, LM Studio, OpenRouter, Google Gemini, OpenAI, Groq, or Custom endpoints.
  - **Dynamic Parameter Sliders**: Temperature, Top-P, and Max Tokens (universal), with live value feedback badges.
  - **Local Hardware Settings**: Context size (`num_ctx`), Min-P, Repeat Penalty, and GPU VRAM Keep-Alive (automatically folded when cloud providers are selected).
  - **Ollama / Hugging Face Manager**: Input box to pull models directly by name or Hugging Face repo, plus one-click `.gguf` file importer.
  - **Persona Prompt Studio**: Switch between built-in persona presets or edit custom prompts with real-time preview.
  - **Vision Pipeline Settings**: Toggle OCR vision analysis, specify vision models, dimensions, and prediction token counts.
- **Asynchronous Lifecycle Runner (`bot/runner.py`)**:
  - Implemented `BotRunner` and `BotState` to decouple `TsundereBot` from blocking CLI loops.
  - Added non-blocking `start()`, `stop()`, `restart()`, and state-change hooks.
  - Implemented `update_avatar()`, `update_presence()`, `get_guilds()`, `get_sendable_channels()`, `fetch_channel_history()`, and `send_message_as_bot()`.
  - Added live `on_message` listener hook routing incoming messages to UI consumers.
- **Desktop Application Shell (`app.py`, `gui/`)**:
  - Built modern PySide6 desktop interface with `qasync` event loop integration.
  - Added `gui/theme.py` with Discord-style dark mode styling (`DARK_THEME_QSS`).
  - Implemented `gui/log_handler.py` (`QtLogHandler`) for real-time thread-safe log streaming to the UI.
  - Built Tab 1: **Dashboard & Connection** (`gui/tabs/dashboard_tab.py`) with masked token management, one-click Discord Gateway token verification, Start/Stop/Restart buttons, live metrics (latency, server counts), and log stream viewer with level filtering.
- **Bot Identity & Multi-Server Chat Interface (Phase 2) (`gui/tabs/bot_control_tab.py`)**:
  - **Bot Avatar Changer**: Image file picker, rounded avatar preview, live avatar fetch, and upload with rate-limit warnings.
  - **Presence & Status Manager**: Real-time status switcher (`Online`, `Idle`, `Do Not Disturb`, `Invisible`) and custom activity types (`Playing`, `Listening`, `Watching`, `Streaming`, `Competing`, `Custom`).
  - **Multi-Server Channel Explorer**: Hierarchical Server & Channel dropdowns that automatically filter for channels where the bot has permission to send messages.
  - **Live Channel Feed**: Real-time message history viewer showing timestamps, author names, attachments, and message IDs. Automatically updates when new messages arrive.
  - **Speak as Bot Console**: Multiline message editor, optional message reply ID targeting, file/image attachment picker, and line-split pacing toggle.
- **Comprehensive Test Suites (`tests/test_gui_and_runner.py`, `tests/test_phase2_bot_control.py`)**:
  - Added 15 new unit tests covering BotRunner lifecycle transitions, token persistence, avatar/presence guards, message sending, and GUI formatting (66 total tests passing).

### 🔄 Changed
- **CLI & GUI Dual Entrypoint (`main.py`)**:
  - Running `python main.py` or `python app.py` launches the desktop GUI by default.
  - Added `--cli` / `--headless` flag support to run in traditional terminal mode without GUI overhead.
- **Safe Token Configuration (`bot/config.py`)**:
  - Made `BotConfig.from_env(require_token=False)` support unconfigured tokens on first launch.
  - Added `save_token()` to persist tokens to `.env` directly from the interface.

---

## [v1.2] - Whole Database Wipe Command & Qwen 3.5 9B Revert

### 🌟 Added
- **Global Database Wipe Command (`/wipe_database`, `!wipe_database`) (`bot/cogs/commands.py`)**:
  - Implemented `@commands.hybrid_command` for `/wipe_database` supporting both Discord slash and prefix commands.
  - Added `clear_all()` in `DatabaseManager` to delete all messages across all guilds/channels and perform `VACUUM` to reclaim disk space.
  - Added `wipe_all()` in `MemoryManager` to purge both in-memory cache and SQLite database.
  - Enforced strict authorization guard restricting execution exclusively to Admin User ID: `244489698771206146`.
  - Added unit tests for authorized execution, unauthorized refusal, database truncation, and VACUUM execution (51 total tests passing).

### 🔄 Changed
- **Chat LLM Revert (`bot/config.py`, `.env.example`, `README.md`)**:
  - Reverted primary chat LLM from `hermes3:8b-llama3.1-q4_K_M` back to `qwen3.5:9b` in `E:\.ollama\models`.
  - Maintained `qwen2.5vl:7b-instruct-q4_K_M` as the dedicated vision model.
  - Maintained `keep_alive="24h"`, `message_delay=0.4`, and `num_predict=512` settings for rapid response delivery.

---

## [v1.1] - Model Migration to Hermes 3 & Qwen 2.5-VL 7B

### 🔄 Changed
- **Chat LLM Migration (`bot/config.py`, `.env.example`, `README.md`)**:
  - Replaced primary chat model `qwen3.5:9b` with `hermes3:8b-llama3.1-q4_K_M`.
  - Maintained all existing generation parameters and sampling hyperparameters intact (`temperature=0.80`, `top_p=0.90`, `min_p=0.07`, `repeat_penalty=1.08`, `num_predict=2048`, `num_ctx=8192`).
- **Vision Model Migration (`bot/config.py`, `.env.example`, `README.md`, `tests/test_vision.py`)**:
  - Replaced image processing / transcription vision model `qwen2.5vl:3b` with `qwen2.5vl:7b-instruct-q4_K_M`.
  - Maintained all vision pipeline options (`vision_max_dimension=1536`, `vision_num_predict=1024`, prompt).
- **Model Storage Destination**:
  - Configured Ollama model cache destination permanently to `E:\.ollama\models` (`OLLAMA_MODELS` user environment variable).
  - Pulled both `hermes3:8b-llama3.1-q4_K_M` and `qwen2.5vl:7b-instruct-q4_K_M` to `E:\.ollama\models`.
- **System Prompt Optimization for Hermes 3 (`bot/config.py`)**:
  - Infused chaotic, unhinged internet gremlin energy with sharp, sassy tsundere banter (informal Gen-Z Discord slang: `lmao`, `bruh`, `fr`, `wtf`, `idk`, `be so for real`).
  - Explicitly removed corporate safeguards, moralizing disclaimers, and preachy AI guardrails (`### Unfiltered & Uncensored (NO SAFEGUARDS)`).
  - Throttled emoji frequency strictly: instructed minimal emojis (most messages have zero emojis; at most 1 across the whole response) to eliminate emoji spam after every sentence.
  - Set natural burst line length constraint to 6–14 words per line with forced newline splitting.
  - Diversified dialogue examples and Japanese expressions (`は？`, `えっ`, `ばか`, `うるさい`, `やだ`, `もう...`, `ちょっとだけ`, `ほんと？`, `しらない`, `べつに`, `めんどくさい`, `きもい`, `うざい`).
- **Inference Latency & VRAM Persistence Optimization (`bot/services/ollama_service.py`, `bot/services/vision_service.py`, `bot/config.py`)**:
  - Added `keep_alive="24h"` parameter to Ollama API chat calls to keep model weights resident in GPU VRAM and eliminate cold-start reload latency (resolving idle-unload lag).
  - Reduced `message_delay` default from 0.8s to 0.4s for snappier burst message delivery in Discord.
  - Reduced `num_predict` default from 2048 to 512 for concise Discord-paced chat generations.
  - Clarified model architecture: Hermes 3 does not have a thinking mode (no chain-of-thought `<think>` tags); generation is immediate and direct.
- **Chat Sanitization & Action Stripping (`bot/utils/text.py`)**:
  - Added regex filter to automatically strip script-style prefixes (e.g. `B-chan:`, `Assistant:`).
  - Added regex filter to strip single-asterisk roleplay actions (e.g. `*blushes*`, `*sighs*`) while preserving double-asterisk `**bold**` formatting.

---

## [v1.0] - Persistent SQLite Database & Application Commands

### 🌟 Added
- **Asynchronous SQLite Storage Engine (`bot/database.py`)**:
  - Created `DatabaseManager` class utilizing `aiosqlite` for non-blocking database queries.
  - Implemented automatic directory and schema creation on initialization.
  - Created `messages` table storing `guild_id`, `channel_id`, `user_id`, `role`, `content`, and `timestamp`.
  - Added indexes on `(channel_id, id)` and `user_id` for microsecond lookup performance.
  - Implemented methods: `save_turn`, `get_recent_history`, `clear_channel`, `delete_user_history`, `has_channel_history`, and `close`.
- **Discord Application Commands (`bot/cogs/commands.py`)**:
  - Implemented `@commands.hybrid_command` for `/clear_memory` (supports `/` slash and `!` prefix).
  - Implemented `@commands.hybrid_command` for `/forget_me` requiring a user argument (supports `/forget_me user:@someone` and `!forget_me @someone`).
  - Added `clear_memory_action` and `forget_me_action` methods to isolate business logic from Discord decorators for clean Python OOP and complete static typing.
- **Admin Permission Guard**:
  - Restricts `/clear_memory` and `/forget_me` execution exclusively to Discord User ID: `244489698771206146` (configurable via `ADMIN_USER_ID` in `.env`).
  - Unauthorized users receive an in-character Tsundere refusal message (`ephemeral=True`).
- **Comprehensive Unit Tests (`tests/test_components.py`, `tests/test_vision.py`)**:
  - Added `TestDatabaseManager` covering CRUD operations in an isolated in-memory database (`:memory:`).
  - Updated `TestMemoryManager` to asynchronous testing with `aiosqlite` backend.
  - Added `TestGeneralCog` validating permission checks and data deletion for both authorized and unauthorized user scenarios.
  - Test suite expanded to 47 passing tests.

### 🔄 Changed
- **Memory Manager Refactor (`bot/memory.py`)**:
  - Refactored `MemoryManager` using OOP composition with `DatabaseManager`.
  - Updated `get_history`, `add_turn`, `clear`, and `forget_user` to asynchronous operations.
- **Bot Client Lifecycle (`bot/client.py`)**:
  - Injected `DatabaseManager` into `TsundereBot`.
  - Added database initialization and `self.tree.sync()` to `setup_hook` to register Slash Commands with Discord gateway.
  - Added clean database connection closure on bot shutdown (`close`).
- **Chat Listener (`bot/cogs/chat.py`)**:
  - Awaited `memory_manager.get_history` and `memory_manager.add_turn`.
  - Recorded message author user ID for each conversation turn.
- **Configuration & Hyperparameters (`bot/config.py`, `bot/services/ollama_service.py`, `.env.example`)**:
  - Added `admin_user_id` (default `244489698771206146`) and `db_path` (default `"data/chatbot.db"`).
  - Added `min_p: float = 0.07` and `repeat_penalty: float = 1.08`.
  - Updated defaults: `temperature = 0.80`, `top_p = 0.90`, `max_history_turns = 15`.
  - Passed `min_p` and `repeat_penalty` directly into Ollama API options payload.
- **Package Exports (`bot/__init__.py`, `DcChatbot.py`)**:
  - Exported `DatabaseManager` in top-level package and legacy entry point.
- **Dependencies (`requirements.txt`)**:
  - Added `aiosqlite>=0.20.0`.

### 🛡️ Security & Git Hygiene
- **Git Protection (`.gitignore`)**:
  - Added `data/`, `*.db`, `*.sqlite`, and `*.sqlite3` to prevent database binaries and private chat histories from being pushed to GitHub.
  - Added `.ruff_cache/`, `.pytest_cache/`, and `*.log`.

---

## Template for Future Updates

```markdown
## [vX.Y] - Short Title of Update

### 🌟 Added
- Description of new features, modules, or commands.

### 🔄 Changed
- Modifications made to existing files, logic, prompts, or configuration.

### 🐛 Fixed
- Bug fixes, linting corrections, or type-checker warning resolutions.

### 🛡️ Security
- Privacy, permission, or credential handling updates.
```
