import questionary
import json
import os
import sys
from datetime import timedelta
import requests
import logging


# --- Add src directory to Python path to import our internal modules ---
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from nexus_led_scoreboard.data.data_fetcher import ESPNAPIFetcher
from nexus_led_scoreboard.logger import setup_logging # <--- ADD THIS IMPORT

# Global for setup.py - will be initialized after logging setup
api_fetcher = None
logger = logging.getLogger(__name__) # <--- GET LOGGER INSTANCE FOR SETUP.PY

# --- Pre-defined Sports and Leagues with their ESPN IDs ---
SPORTS_AND_LEAGUES = [
    {"name": "Football 🏈", "value": "football", "leagues": [
        {"name": "NFL", "value": "nfl"},
        {"name": "College Football", "value": "college-football"},
        {"name": "UFL", "value": "ufl"}
    ]},
    {"name": "Baseball ⚾", "value": "baseball", "leagues": [
        {"name": "MLB", "value": "mlb"},
        {"name": "College Baseball", "value": "college-baseball"}
    ]},
    {"name": "Hockey 🏒", "value": "hockey", "leagues": [
        {"name": "NHL", "value": "nhl"}
    ]},
    {"name": "Basketball 🏀", "value": "basketball", "leagues": [
        {"name": "NBA", "value": "nba"},
        {"name": "College Basketball", "value": "college-basketball"}
    ]},
    {"name": "Soccer ⚽", "value": "soccer", "leagues": [
        {"name": "MLS", "value": "usa.1"},
        {"name": "Eng. Premier League", "value": "eng.1"},
        {"name": "Eng. League Championship", "value": "eng.2"},
        {"name": "Eng. League One", "value": "eng.3"},
        {"name": "Eng. League Two", "value": "eng.4"},
        {"name": "Spanish LALIGA", "value": "esp.1"}
    ]}
]

def get_teams_for_league(sport_value: str, league_value: str) -> list:
    logger.info(f"Fetching teams for {sport_value.upper()} / {league_value.upper()}...") # <--- CHANGED FROM PRINT
    teams_data = api_fetcher.get_teams(sport_value, league_value, limit=1000)

    team_choices = []
    if teams_data and 'sports' in teams_data and teams_data['sports']:
        for sport_entry in teams_data['sports']:
            if 'leagues' in sport_entry:
                for league_entry in sport_entry['leagues']:
                    if league_entry.get('id') == league_value or league_entry.get('slug') == league_value:
                        for team_group in league_entry.get('teams', []):
                            team = team_group['team']
                            team_choices.append({
                                "name": f"{team.get('displayName', team.get('name'))} ({team.get('abbreviation')})",
                                "value": team['id']
                            })
                        break
                if team_choices:
                    break
    if not team_choices:
        logger.warning(f"Could not fetch teams for {sport_value}/{league_value}. Please ensure the league ID is correct and there's internet connectivity.") # <--- CHANGED FROM PRINT
        return []
    return sorted(team_choices, key=lambda x: x['name'])

def test_weather_api(location: str, api_key: str) -> bool:
    """Tests the OpenWeatherMap API key and location by making a simple current weather request."""
    if not location or not api_key:
        return False

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': location,
        'appid': api_key,
        'units': 'imperial'
    }
    logger.info(f"Testing OpenWeatherMap API for '{location}'...") # <--- CHANGED FROM PRINT
    logger.debug(f"  Constructed API URL (for debugging): {requests.Request('GET', base_url, params=params).prepare().url}") # Keep this for debugging
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('cod') == '404' and data.get('message') == 'city not found':
            logger.error("  Error: City not found. Please check your location spelling.") # <--- CHANGED FROM PRINT
            return False

        logger.info("  OpenWeatherMap API key and location validated successfully!") # <--- CHANGED FROM PRINT
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logger.error("  Error: Invalid OpenWeatherMap API Key. Please check your key.") # <--- CHANGED FROM PRINT
        elif e.response.status_code == 404:
            logger.error("  Error: City not found. Please check your location spelling.") # <--- CHANGED FROM PRINT
        else:
            logger.error(f"  An HTTP error occurred during weather API test: {e} (Status: {e.response.status_code})") # <--- CHANGED FROM PRINT
        return False
    except requests.exceptions.ConnectionError:
        logger.error("  Error: Could not connect to OpenWeatherMap API. Check your internet connection.") # <--- CHANGED FROM PRINT
        return False
    except requests.exceptions.Timeout:
        logger.error("  Error: OpenWeatherMap API request timed out. Check your internet connection.") # <--- CHANGED FROM PRINT
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"  An unexpected error occurred during weather API test: {e}") # <--- CHANGED FROM PRINT
        return False
    except json.JSONDecodeError:
        logger.error("  Error: Received unreadable response from OpenWeatherMap API.") # <--- CHANGED FROM PRINT
        return False


def run_setup():
    global api_fetcher # Declare that we're using the global api_fetcher

    print("Welcome to the Nexus LED Scoreboard Setup!") # This initial print can remain
    print("This interactive guide will help you configure your scoreboard preferences.") # This initial print can remain

    # --- Ask for Logging Levels FIRST ---
    print("\n--- Configure Logging Levels ---")
    console_log_level = questionary.select(
        "Select minimum logging level for terminal output:",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO'
    ).ask()
    file_log_level = questionary.select(
        "Select minimum logging level for log file (recommended: DEBUG):",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='DEBUG'
    ).ask()

    # Setup logging based on user's choices
    setup_logging(console_level=console_log_level, file_level=file_log_level)
    logger.info(f"Logging configured: Console={console_log_level}, File={file_log_level}")

    # Now initialize api_fetcher after logging is set up
    api_fetcher = ESPNAPIFetcher()

    config = {}

    config["logging"] = {
        "console_level": console_log_level,
        "file_level": file_log_level
    }
    logger.debug("Added logging configuration to config dictionary.")  # New debug log

    # --- 1. Select Sports and Leagues ---
    logger.info("\n--- Selecting Sports and Leagues ---")
    selected_sport_names = questionary.checkbox(
        "Select your favorite sports:",
        choices=[s["name"] for s in SPORTS_AND_LEAGUES]
    ).ask()

    config["sports"] = {}
    for sport_name in selected_sport_names:
        sport_info = next(s for s in SPORTS_AND_LEAGUES if s["name"] == sport_name)
        sport_value = sport_info["value"]

        selected_league_names = questionary.checkbox(
            f"Select leagues for {sport_name}:",
            choices=[l["name"] for l in sport_info["leagues"]]
        ).ask()

        config["sports"][sport_value] = {"leagues": []}

        for league_name in selected_league_names:
            league_info = next(l for l in sport_info["leagues"] if l["name"] == league_name)
            league_value = league_info["value"]

            selected_team_ids = []

            if questionary.confirm(f"Do you want to select favorite teams for {league_name}?").ask():
                teams_for_league = get_teams_for_league(sport_value, league_value)
                if teams_for_league:
                    logger.info(f"--- Selecting favorite teams for {league_name} ({sport_name}) ---") # <--- CHANGED FROM PRINT
                    selected_team_ids = questionary.checkbox(
                        f"Select your favorite teams in {league_name}:",
                        choices=[
                            questionary.Choice(title=team["name"], value=team["value"])
                            for team in teams_for_league
                        ]
                    ).ask()
                else:
                    logger.info(f"Skipping favorite team selection for {league_name} due to no teams found or fetch error.") # <--- CHANGED FROM PRINT

            config["sports"][sport_value]["leagues"].append({
                "id": league_value,
                "favorite_team_ids": selected_team_ids
            })

    # --- 2. Refresh Intervals ---
    logger.info("\n--- Configuring Data Refresh Intervals (in seconds) ---") # <--- CHANGED FROM PRINT
    config["refresh_intervals"] = {}
    config["refresh_intervals"]["pregame"] = int(questionary.text(
        "Refresh pre-game scoreboards (e.g., check for updates before game start):",
        default=str(int(timedelta(minutes=30).total_seconds()))
    ).ask())
    config["refresh_intervals"]["in_progress_all_games"] = int(questionary.text(
        "Refresh all in-progress games:",
        default=str(int(timedelta(seconds=15).total_seconds()))
    ).ask())
    config["refresh_intervals"]["in_progress_favorite_team"] = int(questionary.text(
        "Refresh in-progress favorite team games (faster updates):",
        default=str(int(timedelta(seconds=5).total_seconds()))
    ).ask())
    config["refresh_intervals"]["completed_games"] = int(questionary.text(
        "Refresh completed games (e.g., final score confirmation):",
        default=str(int(timedelta(hours=6).total_seconds()))
    ).ask())
    config["refresh_intervals"]["full_scoreboard_daily"] = int(questionary.text(
        "Refresh full daily scoreboard (to discover new games):",
        default=str(int(timedelta(hours=1).total_seconds()))
    ).ask())

    # --- 3. Display Settings ---
    logger.info("\n--- Configuring LED Matrix Display Settings ---") # <--- CHANGED FROM PRINT
    config["display"] = {}
    config["display"]["matrix_rows"] = int(questionary.text("Number of rows for your LED matrix (e.g., 32):", default="32").ask() or "32")
    config["display"]["matrix_cols"] = int(questionary.text("Number of columns for your LED matrix (e.g., 64):", default="64").ask() or "64")
    config["display"]["matrix_series"] = int(questionary.text("Number of chained matrices (if applicable, default 1):", default="1").ask() or "1")
    config["display"]["matrix_parallel"] = int(questionary.text("Number of parallel chains (if applicable, default 1):", default="1").ask() or "1")
    config["display"]["emulator_pixel_size"] = int(questionary.text("Pixel size for emulator (only if not on Pi, default 16):", default="16").ask() or "16")

    # --- 4. Weather Configuration ---
    logger.info("\n--- Configuring Weather Display ---") # <--- CHANGED FROM PRINT
    show_weather = questionary.confirm("Do you want to display weather when no games are on?").ask()
    if show_weather:
        weather_config_successful = False
        while not weather_config_successful:
            logger.info("To get weather data, you'll need an OpenWeatherMap API key.") # <--- CHANGED FROM PRINT
            logger.info("You can get one for free from: https://openweathermap.org/api") # <--- CHANGED FROM PRINT
            weather_api_key = questionary.password("Enter your OpenWeatherMap API key:").ask()
            weather_location = questionary.text("Enter your city name for weather (e.g., 'New York, NY, US' or 'London'):").ask()

            if test_weather_api(weather_location, weather_api_key):
                config["weather"] = {"location": weather_location, "api_key": weather_api_key}
                weather_config_successful = True
            else:
                retry = questionary.confirm("Weather API validation failed. Do you want to try again?").ask()
                if not retry:
                    config["weather"] = None
                    break
    else:
        config["weather"] = None

    # --- Save Configuration ---
    config_dir = os.path.join(project_root, "config")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "config.json")

    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

    logger.info(f"\nConfiguration saved to: {config_path}") # <--- CHANGED FROM PRINT
    logger.info("Setup complete! You can now run the scoreboard application.") # <--- CHANGED FROM PRINT

if __name__ == "__main__":
    run_setup()
