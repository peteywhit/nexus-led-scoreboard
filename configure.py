import json
import os
import sys
import questionary
import requests
import logging
from dotenv import load_dotenv, set_key  # Added set_key for writing to .env

# --- Add src directory to Python path to import our internal modules ---
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, "src"))

from nexus_led_scoreboard.data.data_fetcher import ESPNAPIFetcher  # noqa: E402
from nexus_led_scoreboard.logger import setup_logging  # noqa: E402

# Define paths for configuration and environment variables
CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DOTENV_FILE = ".env"

# Global for setup.py - will be initialized after logging setup
api_fetcher = None
logger = logging.getLogger(__name__)

# --- Pre-defined Sports and Leagues with their ESPN IDs ---
SPORTS_AND_LEAGUES = [
    {
        "name": "Football 🏈",
        "value": "football",
        "leagues": [
            {"name": "NFL", "value": "nfl"},
            {"name": "College Football", "value": "college-football"},
            {"name": "UFL", "value": "ufl"},
        ],
    },
    {
        "name": "Baseball ⚾",
        "value": "baseball",
        "leagues": [
            {"name": "MLB", "value": "mlb"},
            {"name": "College Baseball", "value": "college-baseball"},
        ],
    },
    {
        "name": "Hockey 🏒",
        "value": "hockey",
        "leagues": [{"name": "NHL", "value": "nhl"}],
    },
    {
        "name": "Basketball 🏀",
        "value": "basketball",
        "leagues": [
            {"name": "NBA", "value": "nba"},
            {"name": "College Basketball", "value": "college-basketball"},
        ],
    },
    {
        "name": "Soccer ⚽",
        "value": "soccer",
        "leagues": [
            {"name": "MLS", "value": "usa.1"},
            {"name": "Eng. Premier League", "value": "eng.1"},
            {"name": "Eng. League Championship", "value": "eng.2"},
            {"name": "Eng. League One", "value": "eng.3"},
            {"name": "Eng. League Two", "value": "eng.4"},
            {"name": "Spanish LALIGA", "value": "esp.1"},
        ],
    },
]


def get_teams_for_league(sport_value: str, league_value: str) -> list:
    """Fetches and returns a list of teams for a given sport and league from ESPN API."""
    logger.info(f"Fetching teams for {sport_value.upper()} / {league_value.upper()}...")
    teams_data = api_fetcher.get_teams(sport_value, league_value, limit=1000)

    team_choices = []
    if teams_data and "sports" in teams_data and teams_data["sports"]:
        for sport_entry in teams_data["sports"]:
            if "leagues" in sport_entry:
                for league_entry in sport_entry["leagues"]:
                    # Match by 'id' (numeric) or 'slug' (e.g., 'nfl', 'mlb')
                    if (
                        league_entry.get("id") == league_value
                        or league_entry.get("slug") == league_value
                    ):
                        for team_group in league_entry.get("teams", []):
                            team = team_group["team"]
                            team_choices.append(
                                {
                                    "name": f"{team.get('displayName', team.get('name'))} ({team.get('abbreviation')})",
                                    "value": team["id"],  # Store the ESPN team ID
                                }
                            )
                        break
                if team_choices:
                    break
    if not team_choices:
        logger.warning(
            f"Could not fetch teams for {sport_value}/{league_value}. Please ensure the league ID is correct and there's internet connectivity."
        )
        return []
    return sorted(team_choices, key=lambda x: x["name"])


def test_weather_api(location: str, api_key: str) -> bool:
    """Tests the OpenWeatherMap API key and location by making a simple current weather request."""
    if not location or not api_key:
        logger.error("API Key or Location is empty for validation.")
        return False

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": api_key, "units": "imperial"}
    logger.info(f"Testing OpenWeatherMap API for '{location}'...")
    # For debugging, construct the full URL without the API key
    debug_params = {k: v for k, v in params.items() if k != "appid"}
    logger.debug(
        f"  Constructed API URL (for debugging, no key): {requests.Request('GET', base_url, params=debug_params).prepare().url}"
    )
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if response.status_code == 200:
            logger.info("  OpenWeatherMap API key and location validated successfully!")
            return True
        elif data.get("cod") == "404" and data.get("message") == "city not found":
            logger.error(
                "  Error: City not found. Please check your location spelling."
            )
            return False
        else:
            logger.error(
                f"  API Key validation failed with status {response.status_code}. Response: {data.get('message', 'Unknown error')}"
            )
            return False
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logger.error(
                "  Error: Invalid OpenWeatherMap API Key. Please check your key."
            )
        elif e.response.status_code == 404:
            logger.error(
                "  Error: City not found. Please check your location spelling."
            )
        else:
            logger.error(
                f"  An HTTP error occurred during weather API test: {e} (Status: {e.response.status_code})"
            )
        return False
    except requests.exceptions.ConnectionError:
        logger.error(
            "  Error: Could not connect to OpenWeatherMap API. Check your internet connection."
        )
        return False
    except requests.exceptions.Timeout:
        logger.error(
            "  Error: OpenWeatherMap API request timed out. Check your internet connection."
        )
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"  An unexpected error occurred during weather API test: {e}")
        return False
    except json.JSONDecodeError:
        logger.error(
            "  Error: Received unreadable response from OpenWeatherMap API. Check if the response is valid JSON."
        )
        return False


def run_setup():
    global api_fetcher, logger

    # --- Initial welcome messages (still using print for initial user facing output) ---
    print("Welcome to the Nexus LED Scoreboard Configuration Wizard!")
    print("This interactive guide will help you configure your scoreboard preferences.")

    # --- Ask for Logging Levels FIRST ---
    print("\n--- Configure Logging Levels ---")
    console_log_level_str = questionary.select(
        "Select minimum logging level for terminal output:",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    ).ask()
    file_log_level_str = questionary.select(
        "Select minimum logging level for log file (recommended: DEBUG):",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="DEBUG",
    ).ask()

    # Setup logging based on user's choices
    setup_logging(console_level=console_log_level_str, file_level=file_log_level_str)
    logger = logging.getLogger(
        __name__
    )  # Re-get logger after setup_logging to ensure config is applied
    logger.info(
        f"Logging configured: Console={console_log_level_str}, File={file_log_level_str}"
    )

    # Now initialize api_fetcher after logging is set up
    api_fetcher = ESPNAPIFetcher()

    config = {}

    # Load existing configuration if it exists
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                current_config = json.load(f)
                logger.info(f"Existing configuration loaded from {CONFIG_FILE}.")
                config.update(current_config)  # Merge existing config
            except json.JSONDecodeError:
                logger.warning(
                    f"Could not parse {CONFIG_FILE}. Starting with empty configuration."
                )

    # --- SAVE LOGGING CONFIGURATION TO THE DICTIONARY ---
    config["logging"] = {
        "console_level": console_log_level_str,
        "file_level": file_log_level_str,
    }
    logger.debug("Added logging configuration to config dictionary.")

    # --- 1. Select Sports and Leagues ---
    logger.info("\n--- Selecting Sports and Leagues ---")
    # Get previously selected sports/leagues to pre-check
    prev_selected_sports_values = config.get("sports", {}).keys()
    prev_selected_sport_names = [
        s["name"]
        for s in SPORTS_AND_LEAGUES
        if s["value"] in prev_selected_sports_values
    ]

    selected_sport_choices = questionary.checkbox(
        "Select your favorite sports:",
        choices=[
            questionary.Choice(
                s["name"], checked=(s["name"] in prev_selected_sport_names)
            )
            for s in SPORTS_AND_LEAGUES
        ],
    ).ask()

    config["sports"] = {}
    for sport_name in selected_sport_choices:
        sport_info = next(s for s in SPORTS_AND_LEAGUES if s["name"] == sport_name)
        sport_value = sport_info["value"]

        prev_selected_league_ids = [
            L.get("id")
            for league_entry in config.get("sports", {})
            .get(sport_value, {})
            .get("leagues", [])
            for L in sport_info["leagues"]
            if league_entry.get("id") == L.get("id")
        ]
        prev_selected_league_names = [
            L["name"]
            for L in sport_info["leagues"]
            if L["value"] in prev_selected_league_ids
        ]

        selected_league_choices = questionary.checkbox(
            f"Select leagues for {sport_name}:",
            choices=[
                questionary.Choice(
                    L["name"], checked=(L["name"] in prev_selected_league_names)
                )
                for L in sport_info["leagues"]
            ],
        ).ask()

        config["sports"][sport_value] = {"leagues": []}

        for league_name in selected_league_choices:
            league_info = next(
                L for L in sport_info["leagues"] if L["name"] == league_name
            )
            league_value = league_info["value"]

            selected_team_ids = []

            # Get previously selected team IDs for this league
            prev_favorite_team_ids = []
            for existing_league in (
                config.get("sports", {}).get(sport_value, {}).get("leagues", [])
            ):
                if existing_league.get("id") == league_value:
                    prev_favorite_team_ids = existing_league.get(
                        "favorite_team_ids", []
                    )
                    break

            if questionary.confirm(
                f"Do you want to select favorite teams for {league_name}?",
                default=bool(prev_favorite_team_ids),
            ).ask():
                teams_for_league = get_teams_for_league(sport_value, league_value)
                if teams_for_league:
                    logger.info(
                        f"--- Selecting favorite teams for {league_name} ({sport_name}) ---"
                    )

                    # Create questionary choices with pre-checked teams
                    team_options = []
                    for team in teams_for_league:
                        is_checked = str(team["value"]) in [
                            str(x) for x in prev_favorite_team_ids
                        ]  # Ensure string comparison
                        team_options.append(
                            questionary.Choice(
                                title=team["name"],
                                value=team["value"],
                                checked=is_checked,
                            )
                        )

                    selected_team_ids = questionary.checkbox(
                        f"Select your favorite teams in {league_name}:",
                        choices=team_options,
                    ).ask()
                else:
                    logger.info(
                        f"Skipping favorite team selection for {league_name} due to no teams found or fetch error."
                    )

            config["sports"][sport_value]["leagues"].append(
                {"id": league_value, "favorite_team_ids": selected_team_ids}
            )

    # --- 2. Refresh Intervals ---
    logger.info("\n--- Configuring Data Refresh Intervals (in seconds) ---")
    config["refresh_intervals"] = config.get(
        "refresh_intervals", {}
    )  # Ensure dict exists

    config["refresh_intervals"]["in_progress_favorite_team"] = int(
        questionary.text(
            "Refresh interval for in-progress favorite team games (seconds):",
            default=str(
                config["refresh_intervals"].get("in_progress_favorite_team", 30)
            ),  # Was 5s
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )
    config["refresh_intervals"]["in_progress_other_games"] = int(
        questionary.text(
            "Refresh interval for in-progress non-favorite games (seconds):",
            default=str(
                config["refresh_intervals"].get("in_progress_other_games", 60)
            ),  # Was 15s
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )
    config["refresh_intervals"]["pre_game_post_game"] = int(
        questionary.text(
            "Refresh interval for pre-game/post-game updates (seconds):",
            default=str(
                config["refresh_intervals"].get("pre_game_post_game", 300)
            ),  # Was 30m
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )
    config["refresh_intervals"]["no_games"] = int(
        questionary.text(
            "Refresh interval when no games are on (for weather/clock) (seconds):",
            default=str(config["refresh_intervals"].get("no_games", 900)),  # Was 1h
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )

    # --- 3. Display Settings ---
    logger.info("\n--- Configuring LED Matrix Display Settings ---")
    config["display_settings"] = config.get(
        "display_settings", {}
    )  # Ensure dict exists

    config["display_settings"]["matrix_rows"] = int(
        questionary.select(
            "LED Matrix Rows (Height):",
            choices=["16", "32", "64"],
            default=str(config["display_settings"].get("matrix_rows", 32)),
        ).ask()
    )
    config["display_settings"]["matrix_cols"] = int(
        questionary.select(
            "LED Matrix Columns (Width):",
            choices=["32", "64", "96", "128"],
            default=str(config["display_settings"].get("matrix_cols", 64)),
        ).ask()
    )
    # Re-adding these from your previous setup
    config["display_settings"]["matrix_series"] = int(
        questionary.text(
            "Number of chained matrices (if applicable, default 1):",
            default=str(config["display_settings"].get("matrix_series", 1)),
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )
    config["display_settings"]["matrix_parallel"] = int(
        questionary.text(
            "Number of parallel chains (if applicable, default 1):",
            default=str(config["display_settings"].get("matrix_parallel", 1)),
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )
    config["display_settings"]["hardware_mapping"] = questionary.text(
        "Hardware Mapping (e.g., 'adafruit-hat-pwm', 'rpi-rgb-led-matrix'):",
        default=config["display_settings"].get("hardware_mapping", "adafruit-hat-pwm"),
    ).ask()
    config["display_settings"]["emulator_pixel_size"] = int(
        questionary.text(
            "Pixel size for emulator (only if not on Pi, default 16):",
            default=str(config["display_settings"].get("emulator_pixel_size", 16)),
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )

    config["display_settings"]["default_display_time_per_board_sec"] = int(
        questionary.text(
            "Default time (seconds) each board is shown during rotation:",
            default=str(
                config["display_settings"].get("default_display_time_per_board_sec", 10)
            ),
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )

    # --- New: Advanced Display Modes Configuration (retained from last step) ---
    logger.info("\n--- Advanced Display Mode Configuration ---")
    config["display_settings"]["live_mode_enabled"] = questionary.confirm(
        "Enable 'Live Mode' (prioritize only in-progress favorite team games)?",
        default=config["display_settings"].get("live_mode_enabled", True),
    ).ask()

    config["display_modes"] = config.get("display_modes", {})
    config["display_modes"]["active_game_rotation_time_sec"] = int(
        questionary.text(
            "Time (seconds) each active game board shows during rotation:",
            default=str(
                config["display_modes"].get("active_game_rotation_time_sec", 10)
            ),
            validate=lambda text: text.isdigit()
            and int(text) > 0
            or "Must be a positive number.",
        ).ask()
    )

    # Define available board types for selection (will be implemented later)
    # Ensure this list is comprehensive for future display boards
    available_board_types = [
        "clock",
        "weather",
        "custom_message",
        "game_preview_favorite",
        "game_preview_all",
        "live_game_favorite_team",
        "live_game_all_sports",
        "final_game_favorite_team",
        "final_game_all_sports",  # Added final game types
    ]

    def select_boards(prompt_text, default_boards_list):
        return questionary.checkbox(
            prompt_text,
            choices=[
                questionary.Choice(b, checked=(b in default_boards_list))
                for b in available_board_types
            ],
        ).ask()

    logger.info(
        "\nConfigure 'Pre-Game Scheduled' Mode (Games scheduled but not yet started):"
    )
    default_pre_game_boards = (
        config["display_modes"]
        .get("pre_game_scheduled", {})
        .get(
            "boards", ["clock", "weather", "game_preview_favorite", "game_preview_all"]
        )
    )
    config["display_modes"]["pre_game_scheduled"] = {
        "priority": 3,
        "boards": select_boards(
            "Select boards for 'Pre-Game Scheduled' mode (order not guaranteed yet):",
            default_pre_game_boards,
        ),
    }

    logger.info("\nConfigure 'No Games Today' Mode (No games scheduled for the day):")
    default_no_games_boards = (
        config["display_modes"]
        .get("no_games_today", {})
        .get("boards", ["clock", "weather", "custom_message"])
    )
    config["display_modes"]["no_games_today"] = {
        "priority": 4,
        "boards": select_boards(
            "Select boards for 'No Games Today' mode (order not guaranteed yet):",
            default_no_games_boards,
        ),
    }

    # Initialize other display modes (live_favorites, in_progress_games, etc.)
    # These will be fixed, as they refer to specific game types tied to game states
    config["display_modes"]["live_favorites"] = config["display_modes"].get(
        "live_favorites",
        {
            "priority": 1,
            "boards": ["live_game_favorite_team"],
            "transition_to_next_sport_when_no_favorites": False,  # Default to not transition
        },
    )
    config["display_modes"]["in_progress_games"] = config["display_modes"].get(
        "in_progress_games", {"priority": 2, "boards": ["live_game_all_sports"]}
    )
    config["display_modes"]["post_game_finished_favorite"] = config[
        "display_modes"
    ].get(
        "post_game_finished_favorite",
        {
            "priority": 5,
            # Example priority
            "boards": ["final_game_favorite_team"],
            "display_duration_sec": 30,
            # How long to show after game finishes (e.g., for an hour)
        },
    )
    config["display_modes"]["post_game_finished_all"] = config["display_modes"].get(
        "post_game_finished_all",
        {
            "priority": 6,  # Example priority
            "boards": ["final_game_all_sports"],
            "display_duration_sec": 60,  # How long to show after game finishes (e.g., for an hour)
        },
    )

    # --- Custom Messages ---
    logger.info("\n--- Custom Messages (e.g., for 'No Games Today' mode) ---")
    current_messages = config.get("custom_messages", [])
    new_messages = []

    if current_messages:
        logger.info("Existing custom messages found:")
        for i, msg in enumerate(current_messages):
            if questionary.confirm(
                f"Keep existing message '{msg.get('text', '')}' (Duration: {msg.get('duration_sec', 'N/A')}s)?",
                default=True,
            ).ask():
                new_messages.append(msg)
            else:
                logger.info(f"Removed message: '{msg.get('text', '')}'")

    while questionary.confirm("Add a new custom message?").ask():
        msg_text = questionary.text("Enter custom message text:").ask()
        if msg_text:
            msg_duration = int(
                questionary.text(
                    "Duration to display message (seconds):",
                    default="10",
                    validate=lambda text: text.isdigit()
                    and int(text) > 0
                    or "Must be a positive number.",
                ).ask()
            )
            # Generate a simple ID, could be more robust
            msg_id = f"custom_message_{len(new_messages) + 1}"
            new_messages.append(
                {"id": msg_id, "text": msg_text, "duration_sec": msg_duration}
            )
            logger.info(f"Added new message: '{msg_text}'")
        else:
            logger.info("No message text entered. Skipping.")

    config["custom_messages"] = new_messages

    # --- Weather API Key and Location Handling (API Key now in .env) ---
    logger.info("\n--- Weather Configuration ---")
    config["weather"] = config.get("weather", {})

    enable_weather = questionary.confirm(
        "Do you want to enable Weather display?",
        default=config["weather"].get("enabled", False),
    ).ask()
    config["weather"]["enabled"] = enable_weather

    if enable_weather:
        weather_location = questionary.text(
            "Enter default weather location (e.g., 'Crystal Springs, MS' or 'London, UK'):",
            default=config["weather"].get("location", ""),
            validate=lambda text: "Location cannot be empty."
            if not text.strip()
            else True,
        ).ask()
        config["weather"]["location"] = (
            weather_location  # Location still goes to config.json
        )

        # Try to load existing API key from .env for default value
        load_dotenv(dotenv_path=DOTENV_FILE)
        existing_api_key = os.getenv("OPENWEATHER_API_KEY")

        api_key = questionary.password(
            "Enter your OpenWeatherMap API Key (this will be saved in a .env file and NOT committed to Git):",
            default=existing_api_key or "",
            validate=lambda text: "API Key cannot be empty."
            if not text.strip()
            else True,
        ).ask()

        # Validate the API Key with the chosen location
        if not test_weather_api(weather_location, api_key):
            logger.error(
                "Invalid OpenWeatherMap API Key or location. Disabling weather display."
            )
            config["weather"]["enabled"] = False  # Disable weather if validation fails
            # Do NOT save invalid key to .env, or remove it if it was there
            if os.path.exists(DOTENV_FILE):
                # Simple removal, assumes single key per line. For robust, use dotenv.unset_key
                # As per python-dotenv docs, set_key with empty value removes it.
                set_key(
                    dotenv_path=DOTENV_FILE,
                    key_to_set="OPENWEATHER_API_KEY",
                    value_to_set="",
                    quote_mode="never",
                )
                logger.info(
                    f"Removed OPENWEATHER_API_KEY from {DOTENV_FILE} due to validation failure."
                )

        else:
            # Save valid API key to .env file
            # Using set_key ensures proper handling of existing file and quoting
            set_key(
                dotenv_path=DOTENV_FILE,
                key_to_set="OPENWEATHER_API_KEY",
                value_to_set=api_key,
                quote_mode="never",
            )
            logger.info(f"OpenWeatherMap API Key saved to {DOTENV_FILE}.")

            config["weather"]["units"] = questionary.select(
                "Select temperature units:",
                choices=["metric", "imperial"],
                default=config["weather"].get("units", "imperial"),
            ).ask()
            config["weather"]["refresh_interval_sec"] = int(
                questionary.text(
                    "Weather refresh interval (seconds):",
                    default=str(config["weather"].get("refresh_interval_sec", 600)),
                    validate=lambda text: text.isdigit()
                    and int(text) > 0
                    or "Must be a positive number.",
                ).ask()
            )
    else:
        logger.info("Weather display disabled by user.")
        # If weather is disabled, ensure related settings are cleared or default
        # No need to touch .env if weather is disabled, but can explicitly unset
        if os.path.exists(DOTENV_FILE) and os.getenv("OPENWEATHER_API_KEY"):
            set_key(
                dotenv_path=DOTENV_FILE,
                key_to_set="OPENWEATHER_API_KEY",
                value_to_set="",
                quote_mode="never",
            )
            logger.info(
                f"Removed OPENWEATHER_API_KEY from {DOTENV_FILE} as weather is disabled."
            )

    # --- Save Configuration to config.json ---
    os.makedirs(CONFIG_DIR, exist_ok=True)  # Ensure config directory exists

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    logger.info(f"\nConfiguration saved to {CONFIG_FILE}.")
    logger.info(
        f"Remember to add `{DOTENV_FILE}` to your `.gitignore` file if you haven't already to keep your API key secure!"
    )
    logger.info("Configuration complete. You can now run 'python main.py'.")


if __name__ == "__main__":
    run_setup()
