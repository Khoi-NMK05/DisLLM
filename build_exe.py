"""
Automated PyInstaller Build Script for Discord AI Companion.
Packages the entire Python application into a standalone Windows executable.
Usage: python build_exe.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def build() -> None:
    print("=" * 60)
    print(" Building Discord AI Companion Standalone Windows Executable ")
    print("=" * 60)

    # Ensure required runtime folders exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("plugins", exist_ok=True)

    # Terminate any previously running test instance so files are not locked
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/IM", "DiscordAICompanion.exe"], capture_output=True)

    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=DiscordAICompanion",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--add-data=plugins;plugins",
        "--collect-all=bot",
        "--hidden-import=bot",
        "--hidden-import=bot.cogs",
        "--hidden-import=bot.cogs.chat",
        "--hidden-import=bot.cogs.commands",
        "--hidden-import=aiohttp",
        "--hidden-import=aiosqlite",
        "--hidden-import=discord",
        "--hidden-import=discord.ext.commands",
        "--hidden-import=ollama",
        "--hidden-import=PySide6",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=qasync",
        "app.py",
    ]

    print("\nRunning PyInstaller build command:")
    print(" ".join(pyinstaller_cmd))
    print("-" * 60)

    result = subprocess.run(pyinstaller_cmd)
    if result.returncode == 0:
        dist_dir = os.path.join("dist", "DiscordAICompanion")
        if os.path.isdir(dist_dir):
            plugins_dest = os.path.join(dist_dir, "plugins")
            shutil.copytree("plugins", plugins_dest, dirs_exist_ok=True)
            os.makedirs(os.path.join(dist_dir, "data"), exist_ok=True)

        print("\n" + "=" * 60)
        print(" BUILD SUCCESSFUL! ")
        print(" Executable located at: dist/DiscordAICompanion/DiscordAICompanion.exe")
        print("=" * 60)
    else:
        print("\n" + "!" * 60)
        print(f" BUILD FAILED with exit code: {result.returncode}")
        print("!" * 60)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
