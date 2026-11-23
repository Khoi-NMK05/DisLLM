"""
Centralized runtime path resolution for DisLLM.

When packaged as a standalone executable (PyInstaller), all user data
(.env, SQLite history, AI personas, custom commands, moderation settings,
and user plugins) is stored under %APPDATA%\\DisLLM so rebuilding or
updating the application binary never wipes user state.

When running from source during development, paths resolve relative to the
current working directory so dev runs and unit tests stay isolated.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

from bot.version import APP_NAME

logger = logging.getLogger(__name__)

_LEGACY_DATA_FILES = (
    "chatbot.db",
    "personas.json",
    "custom_commands.json",
    "moderation_settings.json",
)


def is_frozen() -> bool:
    """Returns True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def get_exe_dir() -> Path:
    """Returns the directory containing the executable (or repo root when running from source)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def is_portable_mode() -> bool:
    """Returns True if portable mode was requested via --portable or a portable.flag file."""
    if not is_frozen():
        return False
    if "--portable" in sys.argv:
        return True
    return (get_exe_dir() / "portable.flag").exists()


def get_app_data_dir() -> Path:
    """
    Returns the root directory where DisLLM stores user configuration and data.

    Priority:
      1. DISLLM_DATA_DIR environment variable (explicit override)
      2. %APPDATA%\\DisLLM (or OS equivalent) when running as a packaged exe
      3. Exe directory when running in portable mode
      4. Current working directory when running from source
    """
    override = os.environ.get("DISLLM_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if is_frozen():
        if is_portable_mode():
            return get_exe_dir()
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            base = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
            return base / APP_NAME
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / APP_NAME
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else (Path.home() / ".config")
        return base / APP_NAME

    return Path.cwd()


def get_env_path() -> str:
    return str(get_app_data_dir() / ".env")


def get_data_dir() -> str:
    return str(get_app_data_dir() / "data")


def get_db_path() -> str:
    return str(get_app_data_dir() / "data" / "chatbot.db")


def get_personas_path() -> str:
    return str(get_app_data_dir() / "data" / "personas.json")


def get_custom_commands_path() -> str:
    return str(get_app_data_dir() / "data" / "custom_commands.json")


def get_moderation_settings_path() -> str:
    return str(get_app_data_dir() / "data" / "moderation_settings.json")


def get_plugins_dir() -> str:
    return str(get_app_data_dir() / "plugins")


def ensure_runtime_dirs() -> Path:
    """
    Creates the user data/ and plugins/ directories and ensures the app data
    root is on sys.path so discord.py can import `plugins.<name>` from it.
    """
    root = get_app_data_dir()
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "plugins").mkdir(parents=True, exist_ok=True)

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    return root


def migrate_legacy_data_if_needed(
    legacy_root: Path | None = None,
    target_root: Path | None = None,
) -> list[str]:
    """
    One-time, non-destructive migration for users upgrading from an older build
    that stored .env, data/, and plugins/ beside the executable.

    Existing files in target_root are never overwritten.
    Returns a list of relative paths that were copied.
    """
    src_root = (legacy_root or get_exe_dir()).resolve()
    dst_root = (target_root or get_app_data_dir()).resolve()
    if src_root == dst_root:
        return []

    migrated: list[str] = []
    (dst_root / "data").mkdir(parents=True, exist_ok=True)
    (dst_root / "plugins").mkdir(parents=True, exist_ok=True)

    # 1. Migrate .env
    src_env = src_root / ".env"
    dst_env = dst_root / ".env"
    if src_env.is_file() and not dst_env.exists():
        shutil.copy2(src_env, dst_env)
        migrated.append(".env")

    # 2. Migrate known data files (SQLite DB, personas, commands, moderation)
    for filename in _LEGACY_DATA_FILES:
        src_file = src_root / "data" / filename
        dst_file = dst_root / "data" / filename
        if src_file.is_file() and not dst_file.exists():
            shutil.copy2(src_file, dst_file)
            migrated.append(f"data/{filename}")

    # 3. Migrate user-added plugin .py files
    src_plugins = src_root / "plugins"
    if src_plugins.is_dir():
        for py_file in sorted(src_plugins.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            dst_plugin = dst_root / "plugins" / py_file.name
            if not dst_plugin.exists():
                shutil.copy2(py_file, dst_plugin)
                migrated.append(f"plugins/{py_file.name}")

    if migrated:
        logger.info("Migrated legacy user data from %s to %s: %s", src_root, dst_root, ", ".join(migrated))

    return migrated
