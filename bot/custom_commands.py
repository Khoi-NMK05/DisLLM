"""
Custom Command Engine for Discord AI Companion.
Allows defining No-Code AI Prompt Shortcuts, Static Auto-Responders, and Rich Embed commands,
persisting them to JSON, and dynamically registering them with discord.py's app_commands tree.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.text import TextSplitter, format_sources

logger = logging.getLogger(__name__)

DEFAULT_COMMANDS_PATH = "data/custom_commands.json"

DEFAULT_BUILTIN_COMMANDS = [
    {
        "name": "roast",
        "description": "Playfully roast a user or topic with tsundere sass.",
        "command_type": "ai_prompt",
        "prompt_template": "Roast '{query}' in your signature tsundere style! Keep it playful, sharp, and funny.",
        "static_content": "",
        "embed_title": "",
        "embed_color": "#da373c",
        "ephemeral": False,
        "enabled": True,
    },
    {
        "name": "translate",
        "description": "Translate any text into natural conversational English.",
        "command_type": "ai_prompt",
        "prompt_template": "Translate the following text into casual, natural English: {query}",
        "static_content": "",
        "embed_title": "",
        "embed_color": "#5865f2",
        "ephemeral": False,
        "enabled": True,
    },
    {
        "name": "summarize",
        "description": "Summarize text or a discussion concisely for Discord.",
        "command_type": "ai_prompt",
        "prompt_template": "Summarize the key points of the following text concisely using bullet points: {query}",
        "static_content": "",
        "embed_title": "",
        "embed_color": "#23a55a",
        "ephemeral": False,
        "enabled": True,
    },
    {
        "name": "search",
        "description": "Look something up on the web and answer with the latest info.",
        "command_type": "ai_prompt",
        "prompt_template": "Answer this using the web search results: {query}",
        "static_content": "",
        "embed_title": "",
        "embed_color": "#5865f2",
        "ephemeral": False,
        "enabled": True,
        "web_search": True,
    },
    {
        "name": "rules",
        "description": "Display the community rules and guidelines.",
        "command_type": "rich_embed",
        "prompt_template": "",
        "static_content": (
            "1. Be respectful to all members.\n"
            "2. No spamming or unsolicited advertising.\n"
            "3. Keep discussions in the appropriate channels.\n"
            "4. Have fun and enjoy your stay!"
        ),
        "embed_title": "📜 Server Rules & Guidelines",
        "embed_color": "#5865f2",
        "ephemeral": True,
        "enabled": True,
    },
]


@dataclass
class CustomCommand:
    """Specification for a user-defined custom Discord command."""

    name: str
    description: str
    command_type: str = "ai_prompt"  # "ai_prompt", "static_text", "rich_embed"
    prompt_template: str = ""
    static_content: str = ""
    embed_title: str = ""
    embed_color: str = "#5865f2"
    ephemeral: bool = False
    enabled: bool = True
    web_search: bool = False  # AI prompts only: search the web for {query} before answering.

    def validate(self) -> None:
        """Validates command name and parameters according to Discord standards."""
        if not self.name or not re.match(r"^[a-z0-9_-]{1,32}$", self.name):
            raise ValueError(
                f"Invalid command name '{self.name}'. Discord slash commands must be 1-32 lowercase characters (a-z, 0-9, _, -)."
            )
        if not self.description:
            self.description = f"Custom command /{self.name}"
        if len(self.description) > 100:
            self.description = self.description[:100]


class CustomCommandManager:
    """Manages creation, serialization, and dynamic registration of custom commands."""

    def __init__(self, file_path: str = DEFAULT_COMMANDS_PATH) -> None:
        self.file_path = file_path
        self.commands: list[CustomCommand] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                known = CustomCommand.__dataclass_fields__
                self.commands = [CustomCommand(**{k: v for k, v in item.items() if k in known}) for item in data]
                return
            except Exception as err:
                # Move the broken file aside instead of overwriting the user's commands with defaults.
                os.replace(self.file_path, self.file_path + ".broken")
                logger.error("Failed to load %s (kept as .broken), using defaults: %s", self.file_path, err)

        self.commands = [CustomCommand(**item) for item in DEFAULT_BUILTIN_COMMANDS]
        self.save()

    def save(self) -> None:
        """Persists custom commands to local JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
        data = [asdict(cmd) for cmd in self.commands]
        # Write a temp file and swap it in, so a crash mid-save can't leave a half-written file.
        tmp = f"{self.file_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.file_path)

    def add_command(self, cmd: CustomCommand) -> None:
        cmd.validate()
        # Remove existing if same name
        self.commands = [c for c in self.commands if c.name != cmd.name]
        self.commands.append(cmd)
        self.save()

    def remove_command(self, name: str) -> bool:
        initial_len = len(self.commands)
        self.commands = [c for c in self.commands if c.name != name]
        if len(self.commands) < initial_len:
            self.save()
            return True
        return False

    def get_command(self, name: str) -> CustomCommand | None:
        for c in self.commands:
            if c.name == name:
                return c
        return None

    def create_slash_callback(
        self, cmd: CustomCommand, bot: commands.Bot
    ) -> Callable[[discord.Interaction, str], Any]:
        """Creates the async callback function for a slash command."""
        if cmd.command_type == "ai_prompt":

            async def ai_callback(interaction: discord.Interaction, query: str = "") -> None:
                # Same channel rules and anti-spam limit as chat pings.
                moderation_mgr = getattr(bot, "moderation_manager", None)
                if moderation_mgr:
                    if not moderation_mgr.is_channel_allowed(interaction.guild_id, interaction.channel_id):
                        await interaction.response.send_message("I don't respond in this channel.", ephemeral=True)
                        return
                    if not moderation_mgr.check_rate_limit(interaction.user.id):
                        await interaction.response.send_message(
                            "ちょっと待って... You're talking way too fast! Give me a second! 💢", ephemeral=True
                        )
                        return

                await interaction.response.defer(ephemeral=cmd.ephemeral)
                try:
                    ollama_service = getattr(bot, "ollama_service", None)
                    if not ollama_service:
                        await interaction.followup.send("⚠️ AI Service is not configured.", ephemeral=True)
                        return

                    # Plain replace, not str.format: templates may contain other braces, like JSON examples.
                    target_prompt = (
                        cmd.prompt_template.replace("{query}", query)
                        .replace("{user}", interaction.user.display_name)
                        .replace("{bot}", bot.user.display_name if bot.user else "Bot")
                    )
                    # Searching up front works even with models that can't call tools.
                    search_query = (query or target_prompt) if cmd.web_search else None
                    resp = await ollama_service.generate_response([], target_prompt, search_query=search_query)
                    # Discord rejects empty messages and anything over 2000 chars.
                    chunks = TextSplitter().split(resp.content) or ["…"]
                    if ollama_service.config.search_show_sources and resp.sources:
                        chunks.append(format_sources(resp.sources))
                    for chunk in chunks:
                        await interaction.followup.send(chunk, ephemeral=cmd.ephemeral)
                except Exception:
                    # Provider errors can be long or internal; keep them in the log, not in Discord.
                    logger.exception("Error executing custom AI command /%s", cmd.name)
                    await interaction.followup.send(
                        "❌ Something went wrong while generating a reply. Check the bot's logs.", ephemeral=True
                    )

            return ai_callback

        elif cmd.command_type == "rich_embed":

            async def embed_callback(interaction: discord.Interaction, query: str = "") -> None:
                try:
                    color_int = 0x5865F2
                    if cmd.embed_color and cmd.embed_color.startswith("#"):
                        try:
                            color_int = int(cmd.embed_color.lstrip("#"), 16)
                        except ValueError:
                            pass

                    desc = cmd.static_content
                    if "{query}" in desc:
                        desc = desc.replace("{query}", query)

                    embed = discord.Embed(
                        title=cmd.embed_title or cmd.name,
                        description=desc,
                        color=color_int,
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=cmd.ephemeral)
                except Exception as err:
                    logger.error("Error executing custom embed command /%s: %s", cmd.name, err)
                    await interaction.response.send_message(f"❌ Error: {err}", ephemeral=True)

            return embed_callback

        else:  # static_text

            async def static_callback(interaction: discord.Interaction, query: str = "") -> None:
                try:
                    text = cmd.static_content
                    if "{query}" in text:
                        text = text.replace("{query}", query)
                    await interaction.response.send_message(text, ephemeral=cmd.ephemeral)
                except Exception as err:
                    logger.error("Error executing custom static command /%s: %s", cmd.name, err)
                    await interaction.response.send_message(f"❌ Error: {err}", ephemeral=True)

            return static_callback

    async def register_commands_to_bot(self, bot: commands.Bot) -> int:
        """Registers all enabled custom commands into the bot's application command tree."""
        # Drop commands registered earlier that were since deleted or disabled.
        enabled = {cmd.name for cmd in self.commands if cmd.enabled}
        for name in getattr(bot, "custom_command_names", set()) - enabled:
            bot.tree.remove_command(name)
        bot.custom_command_names = enabled

        count = 0
        for cmd in self.commands:
            if not cmd.enabled:
                continue

            try:
                callback = self.create_slash_callback(cmd, bot)
                slash_cmd = app_commands.Command(
                    name=cmd.name,
                    description=cmd.description,
                    callback=callback,
                )
                bot.tree.add_command(slash_cmd, override=True)
                count += 1
                logger.info("Registered custom slash command: /%s", cmd.name)
            except Exception as err:
                logger.warning("Failed to register custom command /%s: %s", cmd.name, err)

        return count
