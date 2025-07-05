# src/nexus_led_scoreboard/scoreboard_manager.py
import logging
import time
import json
from datetime import datetime

from nexus_led_scoreboard.data.data_fetcher import ESPNAPIFetcher

# from nexus_led_scoreboard.data.data_parser import ESPNDataParser # Will add this next
# from nexus_led_scoreboard.display.display_handler import DisplayHandler # Will add this later

logger = logging.getLogger(__name__)


class ScoreboardManager:
    """
    Manages the overall scoreboard application flow, including data fetching,
    determining display modes, and orchestrating content display.
    """

    def __init__(self, config: dict):
        """
        Initializes the ScoreboardManager with the application configuration.

        Args:
            config (dict): The loaded application configuration.
        """
        self.config = config
        self.sports_config = config.get("sports", {})
        self.refresh_intervals = config.get("refresh_intervals", {})
        self.display_settings = config.get("display_settings", {})
        self.display_modes_config = config.get("display_modes", {})
        self.custom_messages = config.get("custom_messages", [])
        self.weather_config = config.get("weather", {})

        self.api_fetcher = ESPNAPIFetcher()
        # self.data_parser = ESPNDataParser() # Placeholder: Will be initialized here
        # self.display_handler = DisplayHandler(self.display_settings) # Placeholder: Will be initialized here

        # State variables
        self.current_display_mode = "no_games_today"  # Default mode
        self.last_data_fetch_time = None
        self.all_games_data = {}  # Stores raw fetched data for all enabled sports
        logger.info("ScoreboardManager initialized with configuration.")
        logger.debug(
            f"Manager Config: {json.dumps(self.config, indent=2)}"
        )  # For full config review

    def run(self):
        """
        Runs the main scoreboard application loop.
        Continuously fetches data, determines display mode, and orchestrates display.
        """
        logger.info("ScoreboardManager main loop started.")
        while True:
            try:
                # 1. Fetch Data
                self._fetch_all_sport_data()

                # 2. Determine Current Display Mode
                self.current_display_mode = self._determine_overall_display_mode(
                    self.all_games_data
                )
                logger.info(
                    f"Current overall display mode: '{self.current_display_mode}'"
                )

                # 3. Get Boards for Current Mode
                boards_to_display = self.display_modes_config.get(
                    self.current_display_mode, {}
                ).get("boards", [])
                logger.debug(
                    f"Boards selected for mode '{self.current_display_mode}': {boards_to_display}"
                )

                # 4. (Future) Orchestrate Display of Boards
                # This is where we'd call display_handler to show relevant content
                # For now, we'll just log
                if not boards_to_display:
                    logger.warning(
                        f"No display boards configured for mode '{self.current_display_mode}'. Displaying nothing."
                    )
                else:
                    logger.info(
                        f"Would now display content for boards: {boards_to_display}"
                    )
                    # Example: self.display_handler.render_boards(boards_to_display, self.all_games_data, self.custom_messages, self.weather_data)

                # 5. Determine Next Refresh Interval based on Current Mode
                refresh_interval = self._get_current_refresh_interval()
                logger.info(
                    f"Next data refresh in {refresh_interval} seconds (due to mode '{self.current_display_mode}')."
                )

                time.sleep(refresh_interval)

            except Exception as e:
                logger.exception(
                    f"An unhandled error occurred in the main scoreboard loop: {e}"
                )
                logger.info("Attempting to restart loop after 30 seconds...")
                time.sleep(30)  # Wait before retrying to prevent rapid error looping

    def _fetch_all_sport_data(self):
        """
        Fetches live game data for all enabled sports and leagues from ESPN API.
        Updates self.all_games_data.
        """
        logger.info("Fetching all sport data...")
        fetched_data = {}
        for sport_value, sport_data in self.sports_config.items():
            if sport_data.get(
                "enabled"
            ):  # Check if the sport is enabled (if you re-added this check)
                for league_config in sport_data.get("leagues", []):
                    league_id = league_config.get("id")
                    if league_id:
                        logger.debug(
                            f"Fetching events for sport '{sport_value}', league '{league_id}'"
                        )
                        try:
                            # Note: ESPNAPIFetcher's get_events is designed to fetch live/upcoming events.
                            # It might need adjustments or specific parameters to fetch all game states.
                            events = self.api_fetcher.get_events(sport_value, league_id)
                            if events:
                                fetched_data[f"{sport_value}_{league_id}"] = events
                                logger.debug(
                                    f"Fetched {len(events)} events for {sport_value}/{league_id}."
                                )
                            else:
                                logger.debug(
                                    f"No events found for {sport_value}/{league_id}."
                                )
                        except Exception as e:
                            logger.error(
                                f"Error fetching events for {sport_value}/{league_id}: {e}"
                            )
        self.all_games_data = fetched_data
        self.last_data_fetch_time = datetime.now()
        logger.info("Finished fetching all sport data.")

    def _determine_overall_display_mode(self, all_games_data: dict) -> str:
        """
        Determines the current high-level display mode based on fetched game data.
        Prioritizes modes based on active games, then scheduled, then no games.

        Args:
            all_games_data (dict): Raw game data fetched from ESPN API.

        Returns:
            str: The name of the determined display mode (e.g., "live_favorites", "no_games_today").
        """
        # Placeholder for parsed game data
        parsed_games = []  # noqa: F841
        # TODO: Here, we would use self.data_parser to parse the raw all_games_data
        # into a more structured format (e.g., a list of Game objects with status, teams, scores)
        # For now, we'll just check the raw data presence

        has_live_favorite_game = False
        has_any_live_game = False
        has_any_pregame_scheduled = False
        has_any_postgame_finished = False  # New state for completed games

        # This logic needs to iterate through 'all_games_data'
        # and check the status of each game relative to configured favorite teams.
        # This will be more robust once data_parser is implemented.

        # Simplified check for demonstration:
        # For now, just check if any data came back.
        # In real implementation, you'd iterate parsed_games
        for sport_league_key, events in all_games_data.items():
            for event in events:
                # Assuming 'event' has a structure we can check for status and teams
                # This is highly simplified and will be robust after data parsing.
                if (
                    event.get("status", {}).get("type", {}).get("state")
                    == "in_progress"
                ):
                    has_any_live_game = True
                    # Check if it's a favorite team game
                    # Needs team ID matching logic using config.sports[sport_value][league_id]["favorite_team_ids"]
                    # For now, we'll assume any live game could be a favorite
                    # Example: if self._is_favorite_team_playing(event):
                    #     has_live_favorite_game = True

                elif event.get("status", {}).get("type", {}).get("state") == "pre":
                    has_any_pregame_scheduled = True

                elif event.get("status", {}).get("type", {}).get("state") == "post":
                    has_any_postgame_finished = True

        # Determine priority:
        # 1. Live games involving favorite teams
        if self.display_settings.get("live_mode_enabled") and has_live_favorite_game:
            return "live_favorites"

        # 2. Any other live games
        if has_any_live_game:
            return "in_progress_games"

        # 3. Games scheduled for today (pre-game)
        if has_any_pregame_scheduled:
            return "pre_game_scheduled"

        # 4. Games that recently finished (post-game)
        if has_any_postgame_finished:
            # Need to distinguish between favorite and all if different boards
            # For now, just a general "post_game_finished"
            return "post_game_finished_all"  # Or "post_game_finished_favorite" if a favorite team was involved

        # 5. No games today
        return "no_games_today"

    def _get_current_refresh_interval(self) -> int:
        """
        Returns the appropriate refresh interval based on the current display mode.
        """
        # Map display modes to refresh intervals from config
        interval_map = {
            "live_favorites": self.refresh_intervals.get(
                "in_progress_favorite_team", 30
            ),
            "in_progress_games": self.refresh_intervals.get(
                "in_progress_other_games", 60
            ),
            "pre_game_scheduled": self.refresh_intervals.get("pre_game_post_game", 300),
            "post_game_finished_favorite": self.refresh_intervals.get(
                "pre_game_post_game", 300
            ),  # Using same for now
            "post_game_finished_all": self.refresh_intervals.get(
                "pre_game_post_game", 300
            ),  # Using same for now
            "no_games_today": self.refresh_intervals.get("no_games", 900),
            # Add other custom modes if they have specific intervals
        }
        return interval_map.get(
            self.current_display_mode, self.refresh_intervals.get("no_games", 900)
        )  # Default to no_games interval


# To make this file runnable for testing initialization
# if __name__ == "__main__":
#     # This block is for local testing of ScoreboardManager directly
#     # In actual use, main.py will initialize it.
#     # Create a dummy config for testing
#     test_config = {
#         "logging": {"console_level": "DEBUG", "file_level": "DEBUG"},
#         "sports": {
#             "football": {
#                 "leagues": [
#                     {"id": "nfl", "favorite_team_ids": ["1", "2"]} # Example team IDs
#                 ]
#             }
#         },
#         "refresh_intervals": {
#             "in_progress_favorite_team": 5,
#             "in_progress_other_games": 10,
#             "pre_game_post_game": 30,
#             "no_games": 60
#         },
#         "display_settings": {
#             "live_mode_enabled": True,
#             "matrix_rows": 32,
#             "matrix_cols": 64
#         },
#         "display_modes": {
#             "live_favorites": {"boards": ["live_game_favorite_team"]},
#             "in_progress_games": {"boards": ["live_game_all_sports"]},
#             "pre_game_scheduled": {"boards": ["game_preview_favorite", "clock"]},
#             "no_games_today": {"boards": ["clock", "weather", "custom_message"]},
#             "post_game_finished_all": {"boards": ["final_game_all_sports"]},
#         },
#         "custom_messages": [
#             {"id": "msg1", "text": "Hello World!", "duration_sec": 5}
#         ],
#         "weather": {
#             "enabled": True,
#             "location": "Crystal Springs, MS, US",
#             "api_key": os.getenv("OPENWEATHER_API_KEY") # Load from .env if running directly
#         }
#     }
#
#     # Ensure logging is set up for this test block
#     setup_logging(console_level="DEBUG", file_level="DEBUG")
#     logger.info("Running ScoreboardManager directly for testing purposes.")
#
#     manager = ScoreboardManager(test_config)
#     manager.run() # This will run indefinitely
