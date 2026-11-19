import logging
import sys

from bot import BotConfig, TsundereBot


def setup_logging() -> None:
    """Configures application-wide logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    """Main application entrypoint. Supports both GUI desktop app (default) and CLI headless mode."""
    if "--cli" in sys.argv or "--headless" in sys.argv:
        setup_logging()
        logger = logging.getLogger("main")

        try:
            config = BotConfig.from_env()
        except ValueError as e:
            logger.error("Configuration Error: %s", e)
            sys.exit(1)

        logger.info("Initializing TsundereBot in CLI mode...")
        bot = TsundereBot(config=config)

        logger.info("Starting bot...")
        bot.run_bot()
    else:
        # Launch modern PySide6 desktop GUI
        from app import main as launch_gui
        launch_gui()



if __name__ == "__main__":
    main()
