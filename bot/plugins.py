"""
Modular Plugin & Cog Extension Manager for Discord AI Companion.
Scans the `plugins/` directory, discovers Python cogs, and allows dynamic
loading, unloading, and live-reloading without restarting the bot.
"""

from __future__ import annotations

import ast
import importlib
import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)

PLUGINS_DIR = "plugins"

EXAMPLE_PLUGIN_CODE = '''"""
Example Discord Cog Plugin for Discord AI Companion.
Drop any custom .py cog into the plugins/ directory to extend the bot!
"""

import discord
from discord import app_commands
from discord.ext import commands


class ExamplePlugin(commands.Cog, name="ExamplePlugin"):
    """An example custom extension demonstrating slash commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping_companion", description="Check companion bot response latency.")
    async def ping_companion(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000, 1)
        await interaction.response.send_message(f"🏓 Pong! Gateway latency is {latency_ms}ms.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Standard discord.py extension setup entrypoint."""
    await bot.add_cog(ExamplePlugin(bot))
'''


class PluginManager:
    """Manages discovery and dynamic lifecycle of custom cogs in the plugins/ folder."""

    def __init__(self, plugins_dir: str = PLUGINS_DIR) -> None:
        self.plugins_dir = plugins_dir
        self.ensure_plugins_directory()

    def ensure_plugins_directory(self) -> None:
        """Ensures plugins/ directory and an example plugin file exist."""
        os.makedirs(self.plugins_dir, exist_ok=True)
        init_file = os.path.join(self.plugins_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w", encoding="utf-8") as f:
                f.write('"""Plugins package."""\n')

        example_file = os.path.join(self.plugins_dir, "example_plugin.py")
        if not os.path.exists(example_file):
            with open(example_file, "w", encoding="utf-8") as f:
                f.write(EXAMPLE_PLUGIN_CODE)

    def list_plugins(self, bot: commands.Bot | None = None) -> list[dict[str, str | bool]]:
        """Returns metadata for all .py files in plugins/ directory."""
        self.ensure_plugins_directory()
        plugins = []

        for item in sorted(os.listdir(self.plugins_dir)):
            if item.endswith(".py") and item != "__init__.py":
                name = item[:-3]
                full_path = os.path.join(self.plugins_dir, item)
                ext_name = f"plugins.{name}"

                is_loaded = False
                if bot is not None:
                    is_loaded = ext_name in bot.extensions

                # Extract module docstring
                description = "Custom Cog Plugin"
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                        doc = ast.get_docstring(tree)
                        if doc:
                            description = doc.strip().split("\n")[0]
                except Exception:
                    pass

                plugins.append(
                    {
                        "name": name,
                        "ext_name": ext_name,
                        "file_path": full_path,
                        "description": description,
                        "is_loaded": is_loaded,
                    }
                )

        return plugins

    async def load_plugin(self, bot: commands.Bot, name: str) -> None:
        """Dynamically loads a cog extension."""
        ext_name = f"plugins.{name}"
        logger.info("Loading plugin: %s", ext_name)
        await bot.load_extension(ext_name)

    async def unload_plugin(self, bot: commands.Bot, name: str) -> None:
        """Dynamically unloads a cog extension."""
        ext_name = f"plugins.{name}"
        logger.info("Unloading plugin: %s", ext_name)
        await bot.unload_extension(ext_name)

    async def reload_plugin(self, bot: commands.Bot, name: str) -> None:
        """Dynamically reloads a cog extension."""
        ext_name = f"plugins.{name}"
        logger.info("Reloading plugin: %s", ext_name)
        await bot.reload_extension(ext_name)

    async def load_all_plugins(self, bot: commands.Bot) -> int:
        """Attempts to load all plugins on bot startup."""
        count = 0
        for p in self.list_plugins():
            name = str(p["name"])
            ext_name = str(p["ext_name"])
            try:
                await bot.load_extension(ext_name)
                count += 1
                logger.info("Loaded custom plugin: %s", name)
            except Exception as err:
                logger.warning("Failed to load plugin '%s': %s", name, err)
        return count
