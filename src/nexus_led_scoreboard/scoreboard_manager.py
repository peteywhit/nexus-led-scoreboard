from datetime import datetime
from .data.data_parser import Game  # Import Game class too
import logging

# Get a logger instance for this module.
# It will use the logging configuration set up in main.py.
logger = logging.getLogger(__name__)


class ScoreboardManager:
    """
    Manages the overall scoreboard application flow,
    fetching data, processing it, and displaying it.
    """

    def __init__(self, app_config: dict):
        """
        Initializes the ScoreboardManager with the application configuration.

        Args:
            app_config (dict): The loaded configuration from config.json.
        """
        self.config = app_config
        logger.info("ScoreboardManager initialized with configuration.")
        logger.debug(f"ScoreboardManager received config: {self.config}")

        # You can now access configuration settings like this:
        self.sports_config = self.config.get("sports", {})
        self.refresh_intervals = self.config.get("refresh_intervals", {})
        self.display_settings = self.config.get("display", {})
        self.weather_settings = self.config.get("weather")  # Can be None if disabled

        # Example: Log some specific config values
        logger.info(f"Configured {len(self.sports_config)} sports.")
        logger.info(
            f"Refresh interval for in-progress favorite games: {self.refresh_intervals.get('in_progress_favorite_team')} seconds."
        )
        if self.weather_settings:
            logger.info(
                f"Weather display enabled for: {self.weather_settings.get('location')}"
            )
        else:
            logger.info("Weather display is disabled in configuration.")

    def _should_fetch_full_scoreboard(self, current_time: datetime) -> bool:
        """Determines if the full day's scoreboard should be fetched."""
        # Fetch if it's the first time, or if the daily interval has passed
        return (
            current_time - self.last_full_scoreboard_fetch_time
            >= self.REFRESH_INTERVAL_DAILY_FULL_SCOREBOARD
        )

    def _should_fetch_game_by_id(self, game: Game, current_time: datetime) -> bool:
        """Determines if a specific game should be fetched by its ID based on its status and favorite status."""
        last_fetch = self.game_last_fetch_times.get(game.id, datetime.min)

        if game.is_completed:
            return current_time - last_fetch >= self.REFRESH_INTERVAL_COMPLETED
        elif game.is_in_progress:
            is_favorite_game = any(
                team.id in self.FAVORITE_TEAM_IDS
                for team in [game.home_team, game.away_team]
            )
            if is_favorite_game:
                return (
                    current_time - last_fetch
                    >= self.REFRESH_INTERVAL_IN_PROGRESS_FAVORITE
                )
            else:
                return current_time - last_fetch >= self.REFRESH_INTERVAL_IN_PROGRESS
        elif game.is_pregame:
            # For pre-game, we might only fetch individual game if it's very close to start,
            # otherwise rely on the full scoreboard update.
            # For now, let's just use the pre-game interval.
            return current_time - last_fetch >= self.REFRESH_INTERVAL_PREGAME
        return False  # Should not happen if game has a valid status

    def run(self):
        """
        Starts the main loop of the scoreboard application.
        This method will contain the core logic for fetching,
        processing, and displaying data.
        """
        logger.info("ScoreboardManager started its main execution loop.")

        # --- Placeholder for main application logic ---
        # In the future, this is where you'll implement:
        # - Continuous data fetching based on refresh intervals
        # - Game state management
        # - Display updates for your LED matrix
        # - Switching between game and weather displays

        logger.info(
            "ScoreboardManager running (this is a placeholder for the main application logic)."
        )
        # For now, we'll just let it run briefly and then exit.
        # You might add a small sleep here, or it will just exit immediately.
        # time.sleep(5) # Uncomment later if you want it to run for a bit
        logger.info("ScoreboardManager placeholder execution complete.")
