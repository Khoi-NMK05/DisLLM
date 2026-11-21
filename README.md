# Discord AI Companion

A self-hosted AI chatbot for Discord with a desktop control panel. Run it on local models through [Ollama](https://ollama.com/), or connect it to any OpenAI-compatible API. Each channel gets persistent conversation memory, image understanding, and a persona you can fully customize.

The bot runs on your own machine. With a local model and web search off, no message content leaves your computer.

---

## Features

**Conversation**
- Replies when mentioned (`@YourBot ...`) or messaged directly.
- Persistent, per-channel conversation memory stored in SQLite, with a configurable history length.
- Natural pacing: long answers can be sent as several short messages with typing indicators. Replies always stay within Discord's 2,000-character limit, and code blocks are kept intact.
- The model can react to messages with an emoji of its choice.
- Reasoning output (`<think>…</think>`) from thinking models is stripped automatically.

**Models**
- **Local:** Ollama, LM Studio, llama.cpp, or any local OpenAI-compatible server.
- **Cloud:** OpenAI, OpenRouter, Groq, Google Gemini, or a custom endpoint.
- Change the provider, model and sampling settings (temperature, top-p, min-p, repeat penalty, context size) on the app's **AI Model & Persona** page. Each setting has a plain-language name and a tooltip that explains it. Changes apply while the bot runs, except a new Ollama host, which needs a restart.
- Download Ollama models (the same as `ollama pull`) or import a local `.gguf` file from inside the app.

**Vision**
- Image attachments are described by a separate vision model (for example `qwen2.5vl` or `moondream`), which also reads text in images.
- Images are downscaled in memory and discarded after analysis. Only the text description is kept in the conversation history.

**Web search** (off by default)
- The bot can look things up on DuckDuckGo when a question needs current information, such as news, releases, prices or scores. With a model that supports tool calling (most recent Qwen, Llama and cloud models), it decides on its own when to search.
- Custom AI commands can have **Search the web first** turned on. They search for `{query}` before answering, which works with any model. The built-in `/search` command does this.
- An optional `Sources:` line lists the links behind a reply.
- The bot is told today's date, so "latest" and "this week" mean the right thing.

**Customization**
- **Personas:** on the **AI Model & Persona** page, pick a built-in persona or write and save your own (stored in `data/personas.json`). The default persona is a playful "tsundere" character; replace it with whatever fits your server.
- **No-code slash commands:** create AI prompt shortcuts, static replies or embed cards from the app, and sync them to Discord in one click.
- **Plugins:** drop a standard `discord.py` cog into `plugins/`, then load, unload or reload it while the bot is running.

**Moderation and privacy**
- Channel whitelist or blacklist, an on/off switch for DMs, and a per-user rate limit (shared by chat and AI slash commands).
- Admin-only commands to clear a channel's memory, erase everything stored about a user, or wipe the whole database.
- A memory inspector in the app shows exactly what is stored.
- The bot cannot ping `@everyone`, `@here` or roles, whatever the model writes.

**Desktop app**
- Windows-friendly PySide6 interface with a Discord-style dark theme.
- Start, stop and restart the bot, stream its logs, and check its connection.
- Change the bot's avatar and status, browse your servers, read channel feeds, and send messages as the bot.
- Can minimize to the system tray and run in the background.
- Can be packaged as a standalone Windows executable.
- A headless mode is available for servers with no display.

---

## Requirements

- **Python 3.10+**
- **A Discord bot application.** Create one in the [Discord Developer Portal](https://discord.com/developers/applications).
- **A model provider**, either:
  - [Ollama](https://ollama.com/download) running locally (recommended), or
  - an API key for a supported cloud provider.

### Discord setup

1. In the Developer Portal, open your application → **Bot** and copy the token.
2. Under **Privileged Gateway Intents**, enable **Message Content Intent**.
3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, plus these permissions: *View Channels*, *Send Messages*, *Read Message History*, *Add Reactions* and *Attach Files*. Open the generated URL to invite the bot to your server.

---

## Quick start

```bash
git clone https://github.com/Khoi-NMK05/DiscordChatBot-x-Ollama.git
cd DiscordChatBot-x-Ollama

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

If you use Ollama, pull a chat model and, optionally, a vision model:

```bash
ollama pull qwen3.5:9b
ollama pull qwen2.5vl:7b-instruct-q4_K_M
```

Start the desktop app:

```bash
python main.py
```

Paste your bot token on the **Dashboard**, click **Save Token**, then click **Start Bot**. Mention the bot in any channel it can see to start chatting.

---

## Running modes

| Mode | Command | Notes |
| :--- | :--- | :--- |
| Desktop app | `python main.py` or `python app.py` | The default. Every setting can be managed from the UI. |
| Headless | `python main.py --cli` | No GUI. Configure everything through `.env`. Needs `DISCORD_BOT_TOKEN`. |
| Windows executable | `python build_exe.py` | Builds `dist/DiscordAICompanion/DiscordAICompanion.exe`. |

---

## Configuration

Settings are read from a `.env` file in the working directory. To start one, copy the template:

```bash
cp .env.example .env
```

The desktop app writes to this same file when you save changes. The headless mode reads only from it. Every setting is optional except the token.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DISCORD_BOT_TOKEN` | *(required)* | Your Discord bot token. |
| `ADMIN_USER_ID` | `0` | The Discord user ID allowed to run admin commands. `0` means nobody. |
| `AI_PROVIDER` | `ollama` | `ollama`, `lm_studio`, `openai`, `openrouter`, `groq`, `gemini` or `custom`. |
| `OLLAMA_MODEL` | `qwen3.5:9b` | Chat model used when the provider is Ollama. |
| `OLLAMA_HOST` | Ollama default | Ollama server URL, for example `http://192.168.1.10:11434`. |
| `OLLAMA_KEEP_ALIVE` | `24h` | How long Ollama keeps the model loaded in memory. |
| `API_KEY` | – | API key for cloud providers. |
| `API_BASE_URL` | Provider default | Override the endpoint of an OpenAI-compatible API. |
| `API_MODEL` | Provider default | Model name for non-Ollama providers. |
| `SYSTEM_PROMPT` | Built-in persona | The bot's persona and instructions. |
| `TEMPERATURE` / `TOP_P` / `MIN_P` / `REPEAT_PENALTY` | `0.80` / `0.90` / `0.07` / `1.08` | Sampling settings. |
| `NUM_PREDICT` / `NUM_CTX` | `512` / `8192` | Maximum reply tokens and context window size. |
| `MAX_HISTORY_TURNS` | `15` | Conversation turns remembered per channel. |
| `SEPARATE_MESSAGES` / `MESSAGE_DELAY` | `true` / `0.4` | Send replies as several short messages, with this delay between them (seconds). |
| `BOT_COMMAND_PREFIX` | `!` | Prefix for text commands. |
| `PRESENCE_TEXT` | `@ me to chat!` | The bot's activity status. |
| `DB_PATH` | `data/chatbot.db` | SQLite database location. |
| `VISION_ENABLED` | `true` | Analyze image attachments. |
| `VISION_MODEL` | `qwen2.5vl:7b-instruct-q4_K_M` | Ollama vision model. |
| `VISION_MAX_DIMENSION` / `VISION_NUM_PREDICT` | `1536` / `1024` | Maximum image size in pixels before analysis, and maximum length of the description in tokens. |
| `SEARCH_ENABLED` | `false` | Let the bot search the web through DuckDuckGo. |
| `SEARCH_SHOW_SOURCES` | `false` | Add a `Sources:` line with up to three links under replies that used search. |
| `SEARCH_MAX_RESULTS` | `5` | Results given to the model per search. |

Moderation rules and custom commands are saved separately, in `data/moderation_settings.json` and `data/custom_commands.json`. If either file can't be read, it is renamed to `.broken` and kept rather than overwritten.

> To find your user ID, turn on Discord's **Developer Mode** (Settings → Advanced), then right-click your name and choose **Copy User ID**. You can also set the admin from **Moderation & Settings → Bot Admin User ID** in the app.

---

## Discord commands

Chat with the bot by mentioning it or sending it a DM. The commands below work both as slash commands and with the text prefix.

| Command | Who can use it | Description |
| :--- | :--- | :--- |
| `/clear_memory` | Admin | Clears the conversation memory for the current channel. |
| `/forget_me user:@member` | Admin | Deletes every stored message involving that user. |
| `/wipe_database` | Admin | Deletes all stored conversations in every channel. |
| `/roast`, `/translate`, `/summarize`, `/rules`, `/search` | Everyone | Built-in custom commands. You can edit or delete them in the app. `/search` needs web search turned on. |

---

## Writing a plugin

Plugins are ordinary [`discord.py` cogs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html). Save a file in `plugins/` and load it from **Commands & Plugins** in the app:

```python
# plugins/hello.py
"""Says hello."""

import discord
from discord import app_commands
from discord.ext import commands


class Hello(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello.")
    async def hello(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Hello, {interaction.user.mention}!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Hello(bot))
```

Plugins run with the same permissions as the bot. Only install plugins you trust.

---

## Project structure

```text
├── main.py                 # Entry point (desktop app by default, --cli for headless)
├── app.py                  # Desktop app launcher (PySide6 + qasync)
├── build_exe.py            # Windows executable build script (PyInstaller)
├── bot/
│   ├── client.py           # Bot client: wires services, cogs, plugins and commands
│   ├── config.py           # Settings loaded from and saved to .env
│   ├── runner.py           # Async start/stop/restart lifecycle used by the GUI
│   ├── database.py         # SQLite conversation storage
│   ├── memory.py           # Per-channel history on top of the database
│   ├── moderation.py       # Channel rules, DM policy, rate limiting
│   ├── custom_commands.py  # No-code slash commands
│   ├── plugins.py          # Plugin discovery and hot reloading
│   ├── cogs/               # Chat handler and admin commands
│   ├── services/           # LLM routing, vision model, provider helpers
│   └── utils/              # Image processing, message splitting
├── gui/
│   ├── main_window.py      # Window, sidebar navigation, system tray
│   ├── theme.py            # Stylesheet and design tokens
│   ├── widgets.py          # Shared UI components
│   └── tabs/               # Dashboard, Bot & Servers, AI Model & Persona, Commands & Plugins, Moderation
├── plugins/                # Your custom cogs
├── data/                   # Database and saved settings (created on first run)
└── tests/                  # Unit tests
```

---

## Privacy and data

- **What is stored:** messages that mention the bot, and the bot's replies, together with the channel, server and user IDs. This lets the bot keep context. Everything is in a local SQLite file (`data/chatbot.db`).
- **Images:** the image itself is never stored, only the text description from the vision model.
- **How to delete data:** use `/forget_me`, `/clear_memory` or `/wipe_database`, or the memory inspector in the app.
- **Cloud providers:** if you choose one, conversation content is sent to that provider under its terms.
- **Web search:** when it's on, search queries the model writes (based on what users asked) are sent to DuckDuckGo and the search engines it falls back to, even with a local model. Search results are not stored; only the bot's reply is.

Let your server members know the bot keeps chat history.

---

## Development

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

The GUI tests need a display. On a headless machine, set `QT_QPA_PLATFORM=offscreen`.

---

## License

Released under the [MIT License](LICENSE).
