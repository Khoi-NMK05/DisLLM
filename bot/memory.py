from __future__ import annotations

from bot.database import DatabaseManager


class MemoryManager:
    """
    Manages persistent multi-turn conversation history per Discord guild and channel.
    Uses DatabaseManager (SQLite) for durable persistence and provides asynchronous operations.
    """

    def __init__(
        self,
        max_turns: int = 15,
        db_manager: DatabaseManager | None = None,
    ) -> None:
        self.max_turns = max_turns
        self.db_manager = db_manager or DatabaseManager()
        self._in_memory: dict[tuple[int | None, int], list[dict[str, str]]] = {}

    async def get_history(
        self, guild_id: int | None, channel_id: int
    ) -> list[dict[str, str]]:
        """Returns the chronological conversation history for the given channel."""
        if self.db_manager is not None:
            return await self.db_manager.get_recent_history(
                channel_id=channel_id,
                limit_turns=self.max_turns,
            )
        key = (guild_id, channel_id)
        return list(self._in_memory.get(key, []))

    async def add_turn(
        self,
        guild_id: int | None,
        channel_id: int,
        user_content: str,
        assistant_content: str,
        user_id: int = 0,
    ) -> None:
        """Adds a user-assistant conversation turn to persistent storage."""
        if self.db_manager is not None:
            await self.db_manager.save_turn(
                guild_id=guild_id,
                channel_id=channel_id,
                user_id=user_id,
                user_content=user_content,
                assistant_content=assistant_content,
            )
        else:
            key = (guild_id, channel_id)
            if key not in self._in_memory:
                self._in_memory[key] = []
            history = self._in_memory[key]
            history.append({"role": "user", "content": user_content})
            history.append({"role": "assistant", "content": assistant_content})
            max_entries = self.max_turns * 2
            if len(history) > max_entries:
                self._in_memory[key] = history[-max_entries:]

    async def clear(self, guild_id: int | None, channel_id: int) -> bool:
        """Clears conversation history for the given channel."""
        if self.db_manager is not None:
            return await self.db_manager.clear_channel(channel_id)
        key = (guild_id, channel_id)
        return bool(self._in_memory.pop(key, None))

    async def forget_user(self, user_id: int) -> int:
        """Purges all messages associated with a specific user."""
        if self.db_manager is not None:
            return await self.db_manager.delete_user_history(user_id)
        return 0

    async def has_memory(self, guild_id: int | None, channel_id: int) -> bool:
        """Checks whether any history exists for the channel."""
        if self.db_manager is not None:
            return await self.db_manager.has_channel_history(channel_id)
        return bool(self._in_memory.get((guild_id, channel_id)))

    async def wipe_all(self) -> int:
        """Purges all conversation history across all channels and guilds."""
        self._in_memory.clear()
        if self.db_manager is not None:
            return await self.db_manager.clear_all()
        return 0
