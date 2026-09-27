# 📝 Project Update Log

All notable changes, file modifications, and new feature implementations for **DiscordChatBotxOllama** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
