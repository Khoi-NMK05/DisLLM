import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.memory import MemoryManager

logger = logging.getLogger(__name__)


class GeneralCog(commands.Cog, name="General"):
    """
    Discord Application Commands (Hybrid commands supporting both Slash commands
    and prefix commands) for memory administration and privacy.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _is_authorized(self, author_id: int) -> bool:
        """Verifies if the command invoker matches the authorized admin ID."""
        admin_id = getattr(getattr(self.bot, "config", None), "admin_user_id", 0)
        return bool(admin_id) and author_id == admin_id

    async def clear_memory_action(self, ctx: commands.Context) -> None:
        """Core execution logic for clearing channel conversation memory."""
        if not self._is_authorized(ctx.author.id):
            await ctx.send(
                "べつに... Who said you could tell me what to do?! Only my owner can run this command! 💢",
                ephemeral=True,
            )
            return

        guild_id = ctx.guild.id if ctx.guild else None
        memory_manager: MemoryManager | None = getattr(self.bot, "memory_manager", None)

        if memory_manager is not None:
            cleared = await memory_manager.clear(guild_id, ctx.channel.id)
            if cleared:
                await ctx.send("🧹 Memory for this channel has been wiped clean!", ephemeral=True)
            else:
                await ctx.send("べつに... Memory was already empty here anyway.", ephemeral=True)
        else:
            await ctx.send("⚠️ Memory manager is not configured.", ephemeral=True)

    @commands.hybrid_command(
        name="clear_memory",
        description="Clear conversation history in the current channel (Admin only).",
    )
    async def clear_memory(self, ctx: commands.Context) -> None:
        """Clears the conversation history in the current channel."""
        await self.clear_memory_action(ctx)

    async def forget_me_action(self, ctx: commands.Context, user: discord.User) -> None:
        """Core execution logic for purging all stored memory of a specific user."""
        if not self._is_authorized(ctx.author.id):
            await ctx.send(
                "べつに... Who said you could tell me what to do?! Only my owner can run this command! 💢",
                ephemeral=True,
            )
            return

        memory_manager: MemoryManager | None = getattr(self.bot, "memory_manager", None)

        if memory_manager is not None:
            deleted_count = await memory_manager.forget_user(user.id)
            if deleted_count > 0:
                await ctx.send(
                    f"🗑️ Successfully erased {deleted_count} messages for {user.mention}.",
                    ephemeral=True,
                )
            else:
                await ctx.send(
                    f"No stored messages were found for {user.mention}.",
                    ephemeral=True,
                )
        else:
            await ctx.send("⚠️ Memory manager is not configured.", ephemeral=True)

    @commands.hybrid_command(
        name="forget_me",
        description="Purge all stored messages and memories for a specified user (Admin only).",
    )
    @app_commands.describe(user="The user whose stored data should be completely deleted")
    async def forget_me(self, ctx: commands.Context, user: discord.User) -> None:
        """Purges all stored history and messages for a specific mentioned user."""
        await self.forget_me_action(ctx, user)

    @forget_me.error
    async def forget_me_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handles missing arguments or invalid users for forget_me command."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "⚠️ You must mention a user to forget! (Usage: `!forget_me @user` or `/forget_me user:@user`)",
                ephemeral=True,
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                "⚠️ Could not resolve that user. Please mention a valid user or provide their ID.",
                ephemeral=True,
            )
        else:
            logger.error("Unexpected error in forget_me: %s", error)
            await ctx.send("⚠️ An error occurred while processing the command.", ephemeral=True)

    async def wipe_database_action(self, ctx: commands.Context) -> None:
        """Core execution logic for completely wiping all records from the database."""
        if not self._is_authorized(ctx.author.id):
            await ctx.send(
                "べつに... Who said you could tell me what to do?! Only my owner can run this command! 💢",
                ephemeral=True,
            )
            return

        memory_manager: MemoryManager | None = getattr(self.bot, "memory_manager", None)

        if memory_manager is not None:
            deleted_count = await memory_manager.wipe_all()
            await ctx.send(
                f"💥 Complete database wipe finished! Erased {deleted_count} messages across all channels.",
                ephemeral=True,
            )
        else:
            await ctx.send("⚠️ Memory manager is not configured.", ephemeral=True)

    @commands.hybrid_command(
        name="wipe_database",
        description="Permanently wipe all stored messages from the database across all channels (Admin only).",
    )
    async def wipe_database(self, ctx: commands.Context) -> None:
        """Completely purges all conversation history across all channels."""
        await self.wipe_database_action(ctx)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GeneralCog(bot))
