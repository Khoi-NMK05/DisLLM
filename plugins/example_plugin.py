"""
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
