"""
Main Desktop Application Launcher for Discord AI Companion.
Runs PySide6 GUI with an integrated qasync asyncio event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

# When bundled as a standalone frozen executable, ensure exe directory is in sys.path
if getattr(sys, "frozen", False):
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if exe_dir not in sys.path:
        sys.path.insert(0, exe_dir)

from PySide6.QtWidgets import QApplication
import qasync

from bot.config import BotConfig
from gui.main_window import MainWindow
from gui.theme import DARK_THEME_QSS


def main() -> None:
    """Initializes and runs the Qt + Asyncio desktop application."""
    # Ensure stdout/stderr logging works smoothly
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Discord AI Companion")
    app.setOrganizationName("TsundereBot")
    app.setStyleSheet(DARK_THEME_QSS)

    # Integrate Qt event loop with Python asyncio
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Safe config loading (doesn't fail if token isn't yet set)
    try:
        config = BotConfig.from_env(require_token=False)
    except Exception as err:
        logging.warning("Falling back to default configuration: %s", err)
        config = BotConfig(discord_token="")

    window = MainWindow(config=config)
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
