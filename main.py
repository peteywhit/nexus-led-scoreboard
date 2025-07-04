import json
import os
import sys
import logging

# --- Adjust Python path to include 'src' directory for imports ---
# This allows us to import modules like nexus_led_scoreboard.logger
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from nexus_led_scoreboard.logger import setup_logging
# Assuming scoreboard_manager.py is correctly located in src/nexus_led_scoreboard/
from nexus_led_scoreboard.scoreboard_manager import ScoreboardManager


def main():
    """
    Main entry point for the Nexus LED Scoreboard application.
    Loads configuration, sets up logging, and initializes ScoreboardManager.
    """
    app_config = {}
    config_path = os.path.join(project_root, 'config', 'config.json')

    # 1. Load Configuration
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            app_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}.")
        print("Please run 'python setup.py' first to create your configuration.")
        sys.exit(1) # Exit if config file is missing
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse config.json. It might be corrupted. Details: {e}")
        print("Please check your config/config.json file or re-run 'python setup.py'.")
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

    # 3. Initialize and Run ScoreboardManager with the loaded config
    # NOTE: You will need to update the ScoreboardManager's __init__
    # method to accept this 'app_config' argument in the next step.
    manager = ScoreboardManager(app_config)
    manager.run()

if __name__ == "__main__":
    main()
