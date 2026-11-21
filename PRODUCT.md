# Product

<!-- impeccable:product-schema 1 -->

## Platform

desktop

Cross-platform desktop app built with PySide6 (Qt). Windows is the main target and has a packaged `.exe` (`build_exe.py`), but macOS and Linux should keep working, so avoid Windows-only assumptions in UI and behaviour. There is also a headless mode (`python main.py --cli`) with no GUI. Impeccable's web-only tools (live, generate, detect) don't apply.

## Users

Hobbyist self-hosters: people who find the repo or the `.exe` and want their own AI bot on their Discord server. Many aren't developers. They set it up by following the README (create a bot in the Discord Developer Portal, paste a token, install Ollama, pull a model), then keep the app running in the background, often in the system tray, while their server uses the bot.

## Product Purpose

Discord AI Companion is a self-hosted AI chatbot for Discord with a desktop control panel. The bot replies when mentioned or DMed, keeps per-channel memory, understands images through a separate vision model, can search the web, and plays a persona the owner fully controls. The control panel handles everything else: starting and stopping the bot, switching models and providers, editing personas, building slash commands, moderation, inspecting memory, and chatting as the bot.

Success means a non-developer gets a working bot running on their own hardware and can manage it entirely from the app, without editing files.

## Positioning

Local and private. The bot runs on the owner's own machine, on local models through Ollama (or LM Studio, llama.cpp, any local OpenAI-compatible server). With a local model and web search off, no message content leaves the computer. Hosted Discord AI bots can't truthfully make that claim. Cloud providers are supported as an option, not the default.

## Operating Context

- Setup: Discord Developer Portal (token, Message Content intent, OAuth invite URL), Ollama install and `ollama pull`, then the Dashboard (save token, Start Bot).
- Daily use: the app runs for long stretches, minimized to the tray. The owner comes back to check status and logs, change settings, or moderate.
- Settings live in `.env` and in `data/` (`personas.json`, `custom_commands.json`, `moderation_settings.json`, SQLite memory). The GUI is the main way to edit them. Headless users edit `.env` directly.
- Many changes apply while the bot is running. A new Ollama host needs a restart.

## Capabilities and Constraints

- Tabs: Dashboard, Bot Control (avatar, status, servers, channel feeds, send or reply as the bot), AI Models (provider, model, sampling, pull models or register a `.gguf` file, persona, vision, web search), Commands (no-code slash commands, plugin manager), Settings (moderation, memory inspector, data purge, tray behaviour).
- Bot state (Disconnected, Connecting, Online, Stopping, Error) controls which actions are available.
- Discord limits: replies capped at 2,000 characters, avatar changes limited to twice per 10 minutes, slash command names must be 1–32 lowercase characters. The bot can never ping `@everyone`, `@here` or roles.
- Web search uses DuckDuckGo, is off by default, and works best with models that support tool calling.
- Plugins are standard `discord.py` cogs in `plugins/` and can be loaded, unloaded or reloaded while the bot runs.
- Privacy: images are processed in memory and discarded, and only the text description is kept. Admins can erase a user's data or wipe the database.
- Default persona: a playful tsundere character, meant to be replaced.

## Brand Commitments

- Name: Discord AI Companion (repo: DiscordChatBot-x-Ollama). MIT licensed, © 2026 PotatoViv.
- Voice in docs and UI: plain and direct, written for non-developers.

## Evidence on Hand

- `README.md`: features, setup, running modes, privacy notes.
- `UPDATE_LOG.md`: change history.
- No user counts, testimonials, benchmarks or press exist. Don't invent any.

## Product Principles

1. Private by default. Local models and no outbound content are the default path. Anything that sends data off the machine (cloud providers, web search) is opt-in and clearly labelled.
2. No files required. Every setting a self-hoster needs is reachable from the app, with clear feedback on what applied live and what needs a restart.
3. Explain Discord and model terms in plain language. Assume a capable hobbyist, not an engineer: tokens, intents, num_ctx and similar terms need context.
4. Built to run in the background. The owner should see the bot's state at a glance after hours away, and the app should stay out of the way otherwise.
5. Owner stays in control. The persona, commands, moderation and stored memory are all visible and editable, and destructive actions ask for confirmation.
