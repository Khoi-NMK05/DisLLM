"""
Moderation and Server Rules Engine for Discord AI Companion.
Manages channel whitelists/blacklists, DM privacy rules, per-user rate limits,
and desktop application preferences.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field

from bot.paths import get_moderation_settings_path

logger = logging.getLogger(__name__)

MODERATION_SETTINGS_PATH = "data/moderation_settings.json"


@dataclass
class ModerationSettings:
    allow_dms: bool = True
    channel_rule_mode: str = "all"  # "all", "whitelist", "blacklist"
    whitelisted_channels: list[int] = field(default_factory=list)
    blacklisted_channels: list[int] = field(default_factory=list)
    rate_limit_per_minute: int = 10
    minimize_to_tray_on_close: bool = True
    start_minimized: bool = False
    auto_check_updates: bool = True


class ModerationManager:
    """Controls server privacy filtering, rate limiting, and app preferences."""

    def __init__(self, file_path: str | None = None) -> None:
        self.file_path = file_path or get_moderation_settings_path()
        self.settings = ModerationSettings()
        self._user_call_timestamps: dict[int, list[float]] = {}
        self.load()

    def load(self) -> None:
        """Loads settings from local JSON file."""
        if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                known = ModerationSettings.__dataclass_fields__
                self.settings = ModerationSettings(**{k: v for k, v in data.items() if k in known})
                return
            except Exception as err:
                # Move the broken file aside instead of overwriting the user's rules with defaults.
                os.replace(self.file_path, self.file_path + ".broken")
                logger.error("Failed to load %s (kept as .broken), using defaults: %s", self.file_path, err)

        self.save()

    def save(self) -> None:
        """Persists settings to local JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
        # Write a temp file and swap it in, so a crash mid-save can't leave a half-written file.
        tmp = f"{self.file_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(self.settings), f, indent=2)
        os.replace(tmp, self.file_path)

    def is_channel_allowed(self, guild_id: int | None, channel_id: int) -> bool:
        """Evaluates whether the bot is permitted to respond in the given channel/DM context."""
        # Check Direct Messages
        if guild_id is None:
            return self.settings.allow_dms

        mode = self.settings.channel_rule_mode.lower()
        if mode == "all":
            return True
        elif mode == "whitelist":
            return channel_id in self.settings.whitelisted_channels
        elif mode == "blacklist":
            return channel_id not in self.settings.blacklisted_channels

        return True

    def check_rate_limit(self, user_id: int) -> bool:
        """
        Sliding-window rate limiter. Returns True if the user is allowed to proceed,
        or False if they exceeded rate_limit_per_minute.
        """
        if self.settings.rate_limit_per_minute <= 0:
            return True

        now = time.time()
        window_start = now - 60.0

        timestamps = self._user_call_timestamps.setdefault(user_id, [])
        # Prune older timestamps
        self._user_call_timestamps[user_id] = [t for t in timestamps if t > window_start]

        if len(self._user_call_timestamps[user_id]) >= self.settings.rate_limit_per_minute:
            return False

        self._user_call_timestamps[user_id].append(now)
        return True
