"""
Asynchronous BotRunner module that decouples the Discord bot lifecycle
from the CLI, enabling control via GUI, tests, or background workers.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Callable

import discord

from bot.client import TsundereBot
from bot.config import BotConfig

logger = logging.getLogger(__name__)


class BotState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    ONLINE = "ONLINE"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


class BotRunner:
    """
    Manages the lifecycle of TsundereBot asynchronously.
    Provides non-blocking start, stop, restart, and state event hooks.
    """

    def __init__(
        self,
        config: BotConfig,
        on_state_change: Callable[[BotState, str], None] | None = None,
        on_ready_callback: Callable[[TsundereBot], None] | None = None,
        on_message_callback: Callable[[discord.Message], None] | None = None,
    ) -> None:
        self.config = config
        self.on_state_change = on_state_change
        self.on_ready_callback = on_ready_callback
        self.on_message_callback = on_message_callback

        self.bot: TsundereBot | None = None
        self.state: BotState = BotState.DISCONNECTED
        self._bot_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    def _set_state(self, new_state: BotState, detail: str = "") -> None:
        self.state = new_state
        logger.info("BotRunner state changed to %s: %s", new_state.value, detail)
        if self.on_state_change:
            try:
                self.on_state_change(new_state, detail)
            except Exception as err:
                logger.error("Error in on_state_change callback: %s", err)

    async def start(self) -> None:
        """Starts the Discord bot as a managed asyncio task."""
        async with self._lock:
            if self.state in (BotState.CONNECTING, BotState.ONLINE):
                logger.warning("Bot is already running or connecting.")
                return

            if not self.config.discord_token or not self.config.discord_token.strip():
                self._set_state(BotState.ERROR, "Discord token is empty.")
                raise ValueError("Discord token is required to start the bot.")

            self._set_state(BotState.CONNECTING, "Connecting to Discord Gateway...")

            # Initialize bot instance
            self.bot = TsundereBot(config=self.config)

            # Register internal hook for on_ready
            original_on_ready = self.bot.on_ready

            async def patched_on_ready() -> None:
                await original_on_ready()
                self._set_state(
                    BotState.ONLINE,
                    f"Logged in as {self.bot.user.name} ({self.bot.user.id})" if self.bot.user else "Ready",
                )
                if self.on_ready_callback and self.bot:
                    self.on_ready_callback(self.bot)

            self.bot.on_ready = patched_on_ready

            # Register message listener for GUI channel stream
            @self.bot.listen("on_message")
            async def _on_message_listener(msg: discord.Message) -> None:
                if self.on_message_callback:
                    try:
                        self.on_message_callback(msg)
                    except Exception as err:
                        logger.error("Error in on_message_callback: %s", err)

            # Spawn task
            self._bot_task = asyncio.create_task(self._run_loop(), name="TsundereBot_Task")

    async def _run_loop(self) -> None:
        """Internal execution loop for discord.py client."""
        assert self.bot is not None
        try:
            await self.bot.start(self.config.discord_token)
        except asyncio.CancelledError:
            logger.info("Bot execution task cancelled.")
        except discord.LoginFailure as err:
            logger.error("Discord login failure: %s", err)
            self._set_state(BotState.ERROR, f"Invalid token or login failure: {err}")
        except Exception as err:
            logger.exception("Unexpected error in bot run loop: %s", err)
            self._set_state(BotState.ERROR, f"Runtime error: {err}")
        finally:
            if self.state != BotState.ERROR:
                self._set_state(BotState.DISCONNECTED, "Bot stopped.")

    async def stop(self) -> None:
        """Stops the Discord bot cleanly."""
        async with self._lock:
            if self.state in (BotState.DISCONNECTED, BotState.STOPPING):
                return

            self._set_state(BotState.STOPPING, "Stopping bot...")

            if self.bot and not self.bot.is_closed():
                try:
                    await self.bot.close()
                except Exception as err:
                    logger.warning("Error during bot.close(): %s", err)

            if self._bot_task and not self._bot_task.done():
                self._bot_task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(self._bot_task), timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                    pass

            self.bot = None
            self._bot_task = None
            self._set_state(BotState.DISCONNECTED, "Bot disconnected successfully.")

    async def restart(self) -> None:
        """Restarts the bot cleanly."""
        await self.stop()
        await asyncio.sleep(1.0)
        await self.start()

    @property
    def is_running(self) -> bool:
        return self.state == BotState.ONLINE

    async def fetch_avatar_bytes(self) -> bytes | None:
        """Fetches current bot avatar bytes if available."""
        if not self.bot or not self.bot.user:
            return None
        try:
            return await self.bot.user.display_avatar.read()
        except Exception as err:
            logger.warning("Failed to fetch bot avatar: %s", err)
            return None

    async def update_avatar(self, image_bytes: bytes) -> None:
        """Updates the bot's avatar on Discord."""
        if not self.bot or not self.bot.user:
            raise RuntimeError("Bot is not online.")
        await self.bot.user.edit(avatar=image_bytes)
        logger.info("Bot avatar updated successfully.")

    async def update_presence(self, status: str, activity_type: str, text: str) -> None:
        """Updates the bot presence and status on Discord Gateway."""
        if not self.bot or not self.bot.is_ready():
            raise RuntimeError("Bot is not online.")

        status_enum = {
            "Online": discord.Status.online,
            "Idle": discord.Status.idle,
            "Do Not Disturb": discord.Status.dnd,
            "Invisible": discord.Status.invisible,
        }.get(status, discord.Status.online)

        text = text.strip()
        activity: discord.BaseActivity | None = None
        if text:
            if activity_type == "Playing":
                activity = discord.Game(name=text)
            elif activity_type == "Listening":
                activity = discord.Activity(type=discord.ActivityType.listening, name=text)
            elif activity_type == "Watching":
                activity = discord.Activity(type=discord.ActivityType.watching, name=text)
            elif activity_type == "Streaming":
                activity = discord.Streaming(name=text, url="https://twitch.tv")
            elif activity_type == "Competing":
                activity = discord.Activity(type=discord.ActivityType.competing, name=text)
            elif activity_type == "Custom":
                activity = discord.CustomActivity(name=text)

        await self.bot.change_presence(status=status_enum, activity=activity)
        self.config.presence_text = text
        logger.info("Updated presence to status=%s, activity=%s: '%s'", status, activity_type, text)

    def get_guilds(self) -> list[discord.Guild]:
        """Returns a list of guilds the bot is currently in."""
        if not self.bot:
            return []
        return list(self.bot.guilds)

    def get_sendable_channels(self, guild_id: int) -> list[discord.abc.GuildChannel | discord.Thread]:
        """Returns channels in the guild where the bot has permission to send messages."""
        if not self.bot:
            return []
        guild = self.bot.get_guild(guild_id)
        if not guild or not guild.me:
            return []

        channels: list[discord.abc.GuildChannel | discord.Thread] = []
        for ch in guild.text_channels:
            perms = ch.permissions_for(guild.me)
            if perms.send_messages and perms.view_channel:
                channels.append(ch)

        for thread in guild.threads:
            perms = thread.permissions_for(guild.me)
            if perms.send_messages and perms.view_channel:
                channels.append(thread)

        return sorted(channels, key=lambda c: getattr(c, "position", 9999))

    async def fetch_channel_history(self, channel_id: int, limit: int = 25) -> list[discord.Message]:
        """Fetches the most recent messages from a channel."""
        if not self.bot:
            return []
        channel = self.bot.get_channel(channel_id)
        if not channel or not hasattr(channel, "history"):
            return []

        messages: list[discord.Message] = []
        try:
            async for msg in channel.history(limit=limit, oldest_first=False):
                messages.append(msg)
            messages.reverse()
        except Exception as err:
            logger.error("Failed to fetch history for channel %d: %s", channel_id, err)
        return messages

    async def send_message_as_bot(
        self,
        channel_id: int,
        content: str,
        file_path: str | None = None,
        reply_to_id: int | None = None,
        split_lines: bool = False,
    ) -> list[discord.Message]:
        """Sends a message or list of messages as the bot into the given channel."""
        if not self.bot:
            raise RuntimeError("Bot is not online.")
        channel = self.bot.get_channel(channel_id)
        if not channel or not hasattr(channel, "send"):
            raise ValueError(f"Channel {channel_id} not found or is not sendable.")

        reference = None
        if reply_to_id:
            try:
                reference = await channel.fetch_message(reply_to_id)
            except Exception as err:
                logger.warning("Could not fetch message to reply to (%s): %s", reply_to_id, err)

        sent_messages: list[discord.Message] = []

        if split_lines:
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            for idx, line in enumerate(lines):
                ref = reference if idx == 0 else None
                file = (
                    discord.File(file_path)
                    if file_path and idx == len(lines) - 1
                    else None
                )
                sent = await channel.send(content=line, reference=ref, file=file)
                sent_messages.append(sent)
                if idx < len(lines) - 1:
                    await asyncio.sleep(0.4)
        else:
            file = discord.File(file_path) if file_path else None
            sent = await channel.send(content=content, reference=reference, file=file)
            sent_messages.append(sent)

        return sent_messages

