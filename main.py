import json
import os
import sys
import logging
from dotenv import load_dotenv

# --- Adjust Python path to include 'src' directory for imports ---
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from nexus_led_scoreboard.logger import setup_logging  # noqa: E402
from nexus_led_scoreboard.scoreboard_manager import ScoreboardManager  # noqa: E402


def main():
    """
    Main entry point for the Nexus LED Scoreboard application.
    Loads configuration, sets up logging, and initializes ScoreboardManager.
    """
    # Load environment variables from .env file
    load_dotenv()

    app_config = {}
    config_path = os.path.join(project_root, 'config', 'config.json')

    # 1. Load Configuration
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            app_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}.")
        print("Please run 'python configure.py' first to create your configuration.")
        sys.exit(1) # Exit if config file is missing
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse config.json. It might be corrupted. Details: {e}")
        print("Please check your config/config.json file or re-run 'python configure.py'.")
        sys.exit(1) # Exit if config file is corrupted

    # 2. Setup Logging based on loaded configuration
    logging_config = app_config.get("logging", {})
    console_level = logging_config.get("console_level", "INFO") # Default to INFO if not in config
    file_level = logging_config.get("file_level", "DEBUG")     # Default to DEBUG if not in config

    setup_logging(console_level=console_level, file_level=file_level)

    # Get a logger for the main application entry point
    logger = logging.getLogger(__name__)
    logger.info("Application starting...")
    logger.debug(f"Loaded configuration: {json.dumps(app_config, indent=2)}")

    # 3. Add sensitive data from environment variables to config
    # Ensure 'weather' section exists if weather is enabled, otherwise get() will fail.
    if app_config.get("weather", {}).get("enabled"):
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            logger.error("OPENWEATHER_API_KEY not found in environment variables. Weather display may not work.")
            # You might want to disable weather display if key is missing
            app_config["weather"]["enabled"] = False
        else:
            app_config["weather"]["api_key"] = api_key  # Add key to config for ScoreboardManager

    # 4. Initialize and Run ScoreboardManager with the loaded config
    manager = ScoreboardManager(app_config)
    manager.run()

if __name__ == "__main__":
    main()
