from __future__ import annotations

import logging
import os
from typing import Any

import aiosqlite

from bot.paths import get_db_path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages persistent SQLite storage for chatbot conversation history,
    user-specific data, and channel context using asynchronous I/O.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path if db_path is not None else get_db_path()
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """
        Initializes the database connection, creates parent directories if needed,
        and ensures the necessary tables and indexes exist.
        """
        if self._conn is not None:
            return

        # Ensure directory exists if not an in-memory database
        if self.db_path != ":memory:":
            dirname = os.path.dirname(self.db_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)

        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id, id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id)"
        )
        await self._conn.commit()
        logger.info("DatabaseManager initialized at '%s'", self.db_path)

    async def _get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            await self.initialize()
        assert self._conn is not None
        return self._conn

    async def save_turn(
        self,
        guild_id: int | None,
        channel_id: int,
        user_id: int,
        user_content: str,
        assistant_content: str,
    ) -> None:
        """Saves a user-assistant conversation turn into the database."""
        conn = await self._get_conn()
        # One call, so another reply's rows can't land between this user message and its answer.
        # The assistant row keeps the user's ID so /forget_me removes both.
        await conn.executemany(
            """
            INSERT INTO messages (guild_id, channel_id, user_id, role, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (guild_id, channel_id, user_id, "user", user_content),
                (guild_id, channel_id, user_id, "assistant", assistant_content),
            ],
        )
        await conn.commit()

    async def get_recent_history(
        self, channel_id: int, limit_turns: int = 15
    ) -> list[dict[str, str]]:
        """
        Retrieves the most recent messages for a channel in chronological order.
        Fetches up to (limit_turns * 2) entries.
        """
        conn = await self._get_conn()
        limit_entries = limit_turns * 2
        async with conn.execute(
            """
            SELECT role, content FROM messages
            WHERE channel_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (channel_id, limit_entries),
        ) as cursor:
            rows = await cursor.fetchall()

        # Rows were retrieved newest-first; reverse them for chronological context
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    async def clear_channel(self, channel_id: int) -> bool:
        """
        Deletes all messages for a specific channel.
        Returns True if any rows were deleted, False if already empty.
        """
        conn = await self._get_conn()
        cursor = await conn.execute(
            "DELETE FROM messages WHERE channel_id = ?",
            (channel_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def delete_user_history(self, user_id: int) -> int:
        """
        Deletes all messages associated with a specific user ID across all channels.
        Returns the count of deleted messages.
        """
        conn = await self._get_conn()
        cursor = await conn.execute(
            "DELETE FROM messages WHERE user_id = ?",
            (user_id,),
        )
        await conn.commit()
        return cursor.rowcount

    async def has_channel_history(self, channel_id: int) -> bool:
        """Checks whether any stored messages exist for the channel."""
        conn = await self._get_conn()
        async with conn.execute(
            "SELECT 1 FROM messages WHERE channel_id = ? LIMIT 1",
            (channel_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

    async def clear_all(self) -> int:
        """
        Deletes all messages in the database across all channels and guilds.
        Runs VACUUM to reclaim disk space.
        Returns the count of deleted messages.
        """
        conn = await self._get_conn()
        cursor = await conn.execute("DELETE FROM messages")
        deleted_count = cursor.rowcount
        await conn.commit()
        await conn.execute("VACUUM")
        return deleted_count

    async def list_active_channels(self) -> list[dict[str, Any]]:
        """Lists all channels that have stored conversation history with message counts."""
        conn = await self._get_conn()
        async with conn.execute(
            """
            SELECT channel_id, guild_id, COUNT(*) as msg_count, MAX(timestamp) as last_active
            FROM messages
            GROUP BY channel_id
            ORDER BY last_active DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "channel_id": row["channel_id"],
                    "guild_id": row["guild_id"],
                    "msg_count": row["msg_count"],
                    "last_active": row["last_active"],
                }
                for row in rows
            ]

    async def get_detailed_channel_history(
        self, channel_id: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Retrieves detailed message records for inspection in the GUI."""
        conn = await self._get_conn()
        async with conn.execute(
            """
            SELECT id, guild_id, channel_id, user_id, role, content, timestamp
            FROM messages
            WHERE channel_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (channel_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "guild_id": row["guild_id"],
                    "channel_id": row["channel_id"],
                    "user_id": row["user_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                }
                for row in reversed(rows)
            ]

    async def close(self) -> None:
        """Closes the active database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("DatabaseManager connection closed.")
