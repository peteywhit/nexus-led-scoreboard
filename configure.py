import json
import os
import questionary
import requests  # Keep requests for API key validation

# Adjust path for local imports if needed, though for configure.py it's usually at root.
# project_root = os.path.dirname(os.path.abspath(__file__))
# sys.path.insert(0, os.path.join(project_root, 'src'))
# No need for nexus_led_scoreboard.logger or ScoreboardManager in configure.py itself.

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DOTENV_FILE = ".env"  # New: for sensitive environment variables


def get_user_input(config: dict):
    # ... (keep existing setup_logging_config, setup_sports_config, etc.) ...

    # --- New: Weather API Key and Location Handling ---
    questionary.confirm(
        "Do you want to enable Weather display?",
        default=config.get("weather", {}).get("enabled", False),
    ).ask()
    if questionary.confirm(
        "Do you want to enable Weather display?",
        default=config.get("weather", {}).get("enabled", False),
    ).ask():
        weather_location = questionary.text(
            "Enter default weather location (e.g., 'New York, NY, US' or 'London, UK'):",
            default=config.get("weather", {}).get("location", ""),
            validate=lambda text: "Location cannot be empty."
            if not text.strip()
            else True,
        ).ask()

        # New: Get API Key and store in .env
        api_key = questionary.password(
            "Enter your OpenWeatherMap API Key (this will be saved in a .env file and NOT committed to Git):",
            validate=lambda text: "API Key cannot be empty."
            if not text.strip()
            else True,
        ).ask()

        # Validate the API Key
        if not validate_openweathermap_api_key(api_key, weather_location):
            print(
                "Error: Invalid OpenWeatherMap API Key or location. Please try again."
            )
            # You might want to loop here or exit, for now, we'll just continue
            config["weather"] = {
                "enabled": False
            }  # Disable weather if validation fails
            api_key = None  # Clear key if invalid
        else:
            # Save API key to .env file
            with open(DOTENV_FILE, "a") as f:  # Use "a" to append, not overwrite
                f.write(f"OPENWEATHER_API_KEY={api_key}\n")

            # config.json will only store whether weather is enabled and the location
            config["weather"] = {
                "enabled": True,
                "location": weather_location,
                "units": questionary.select(
                    "Select temperature units:",
                    choices=["metric", "imperial"],
                    default=config.get("weather", {}).get("units", "imperial"),
                ).ask(),
                "refresh_interval_sec": questionary.text(
                    "Weather refresh interval (seconds):",
                    default=str(
                        config.get("weather", {}).get("refresh_interval_sec", 600)
                    ),
                    validate=lambda text: text.isdigit()
                    and int(text) > 0
                    or "Must be a positive number.",
                ).ask(),
            }
    else:
        config["weather"] = {"enabled": False}

    # ... (rest of get_user_input function, including display modes etc.) ...
    return config


def validate_openweathermap_api_key(api_key, location):
    if not api_key or not location:
        return False
    try:
        # Test the API key with a simple request
        test_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}"
        response = requests.get(test_url, timeout=5)
        data = response.json()
        if response.status_code == 200:
            print("OpenWeatherMap API Key validated successfully!")
            return True
        else:
            print(
                f"API Key validation failed. Response: {data.get('message', 'Unknown error')}"
            )
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error validating API Key: {e}")
        return False


def main():
    print("Starting Nexus LED Scoreboard Configuration...")

    # Ensure config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)

    current_config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                current_config = json.load(f)
                print(f"Existing configuration loaded from {CONFIG_FILE}.")
            except json.JSONDecodeError:
                print(
                    f"Warning: Could not parse {CONFIG_FILE}. Starting with empty configuration."
                )
                current_config = {}

    # Get user input
    updated_config = get_user_input(current_config)

    # Save configuration to config.json
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_config, f, indent=4)
    print(f"\nConfiguration saved to {CONFIG_FILE}.")
    print("Remember to add .env to your .gitignore file!")


if __name__ == "__main__":
    main()
