import logging
import time
import json
from datetime import datetime, timedelta, timezone
from typing import List

from nexus_led_scoreboard.data.data_fetcher import ESPNAPIFetcher
from nexus_led_scoreboard.data.data_parser import ESPNDataParser, Game
# from nexus_led_scoreboard.display.display_handler import DisplayHandler

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

        # Prepare favorite_team_ids map for the parser
        favorite_team_ids_map = {}
        for sport_value, sport_data in self.sports_config.items():
            for league_config in sport_data.get("leagues", []):
                league_id = league_config.get("id")
                fav_ids = [str(x) for x in league_config.get("favorite_team_ids", [])]
                if league_id and fav_ids:
                    favorite_team_ids_map[league_id] = fav_ids

        self.data_parser = ESPNDataParser(favorite_team_ids=favorite_team_ids_map)
        # self.display_handler = DisplayHandler(self.display_settings) # Placeholder: Will be initialized here

        self.current_display_mode = "no_games_today"  # Default mode
        self.last_data_fetch_time = None
        self.all_games_data: List[Game] = []
        self.last_daily_schedule_check_date = None

        logger.info("ScoreboardManager initialized with configuration.")
        logger.debug(f"Manager Config: {json.dumps(self.config, indent=2)}")

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

                # 2. Determine Current Display Mode and Next Refresh Time
                self.current_display_mode, next_refresh_interval = (
                    self._determine_overall_display_mode(self.all_games_data)
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
                if not boards_to_display:
                    logger.warning(
                        f"No display boards configured for mode '{self.current_display_mode}'. Displaying nothing."
                    )
                else:
                    logger.info(
                        f"Would now display content for boards: {boards_to_display}"
                    )
                    # Example: self.display_handler.render_boards(boards_to_display, self.all_games_data, self.custom_messages, self.weather_data)

                logger.info(
                    f"Next data refresh in {next_refresh_interval} seconds (determined by mode/schedule)."
                )
                time.sleep(next_refresh_interval)

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
        all_parsed_games: List[Game] = []

        # Logic for daily schedule check
        current_date = datetime.now().date()
        daily_check_time_str = self.refresh_intervals.get(
            "daily_schedule_check_time", "05:00"
        )  # Default 5 AM
        try:
            check_hour, check_minute = map(int, daily_check_time_str.split(":"))
        except ValueError:
            logger.error(
                f"Invalid daily_schedule_check_time format: '{daily_check_time_str}'. Using 05:00."
            )
            check_hour, check_minute = 5, 0

        # Create a datetime object for today's daily check time
        today_check_dt = datetime.combine(
            current_date,
            datetime.min.time().replace(hour=check_hour, minute=check_minute),
        )

        # Determine if we need to do a full daily refresh
        is_new_day_for_check = (
            self.last_daily_schedule_check_date is None
            or self.last_daily_schedule_check_date < current_date
            or (
                self.last_daily_schedule_check_date == current_date
                and datetime.now() >= today_check_dt
                and not self.all_games_data  # If no games were found last check for today
            )
        )

        if is_new_day_for_check or not self.all_games_data:
            logger.info("Performing full daily schedule fetch.")
            self.last_daily_schedule_check_date = current_date

            date_str = datetime.now().strftime("%Y%m%d")
            logger.debug(f"Fetching games for date: {date_str}")

            for sport_value, sport_data in self.sports_config.items():
                for league_config in sport_data.get("leagues", []):
                    league_id = league_config.get("id")
                    if league_id:
                        logger.debug(
                            f"Fetching events for sport '{sport_value}', league '{league_id}'"
                        )
                        try:
                            raw_events = self.api_fetcher.get_scoreboard(
                                sport_value, league_id, date_str
                            )
                            if "sport" not in raw_events:
                                raw_events["sport"] = {"slug": sport_value}
                            if "leagues" not in raw_events:
                                raw_events["leagues"] = [{"slug": league_id}]

                            parsed_games_for_league = self.data_parser.parse_events(
                                raw_events
                            )
                            all_parsed_games.extend(parsed_games_for_league)
                            logger.debug(
                                f"Fetched and parsed {len(parsed_games_for_league)} games for {sport_value}/{league_id}."
                            )
                        except Exception as e:
                            logger.error(
                                f"Error fetching/parsing events for {sport_value}/{league_id}: {e}",
                                exc_info=True,
                            )
            self.all_games_data = all_parsed_games
        else:
            logger.debug(
                "Skipping full daily schedule fetch. Using existing data and specific refreshes."
            )
            # Even if not a full daily fetch, we still refresh existing games to get latest scores
            # This ensures live scores are updated.
            # We still pass the current date to ensure we're getting today's specific events.
            date_str = datetime.now().strftime("%Y%m%d")

            for sport_value, sport_data in self.sports_config.items():
                for league_config in sport_data.get("leagues", []):
                    league_id = league_config.get("id")
                    if league_id:
                        try:
                            raw_events = self.api_fetcher.get_scoreboard(
                                sport_value, league_id, date_str
                            )
                            if "sport" not in raw_events:
                                raw_events["sport"] = {"slug": sport_value}
                            if "leagues" not in raw_events:
                                raw_events["leagues"] = [{"slug": league_id}]
                            parsed_games_for_league = self.data_parser.parse_events(
                                raw_events
                            )
                            # This currently re-adds all games. For robustness, one might update existing
                            # games in self.all_games_data by ID and add new ones.
                            # For simplicity, we'll just re-populate all_parsed_games each time for now.
                            all_parsed_games.extend(parsed_games_for_league)
                        except Exception as e:
                            logger.error(
                                f"Error refreshing events for {sport_value}/{league_id}: {e}",
                                exc_info=True,
                            )
            self.all_games_data = all_parsed_games

        self.last_data_fetch_time = datetime.now()
        logger.info(
            f"Finished fetching and parsing data. Total games: {len(self.all_games_data)}"
        )

    def _determine_overall_display_mode(
        self, parsed_games: List[Game]
    ) -> tuple[str, int]:
        """
        Determines the current high-level display mode based on parsed game data.
        Prioritizes modes based on active games, then scheduled, then no games.
        Also calculates the next appropriate refresh interval.

        Args:
            parsed_games (List[Game]): List of parsed Game objects.

        Returns:
            tuple[str, int]: (mode_name, next_refresh_interval_seconds)
        """
        now = datetime.now(timezone.utc)  # Use UTC for comparison with ESPN times

        live_favorite_games = [g for g in parsed_games if g.is_live and g.is_favorite]
        live_other_games = [g for g in parsed_games if g.is_live and not g.is_favorite]

        pregame_games = sorted(
            [g for g in parsed_games if g.is_pregame and g.start_time > now],
            key=lambda g: g.start_time,
        )

        postgame_favorite_games = [
            g for g in parsed_games if g.is_postgame and g.is_favorite
        ]
        postgame_other_games = [
            g for g in parsed_games if g.is_postgame and not g.is_favorite
        ]

        # Get configured refresh intervals
        fav_live_interval = self.refresh_intervals.get("in_progress_favorite_team", 5)
        other_live_interval = self.refresh_intervals.get("in_progress_other_games", 15)
        pre_post_interval = self.refresh_intervals.get("pre_game_post_game", 300)
        no_games_interval = self.refresh_intervals.get("no_games", 900)

        # Determine mode based on priority
        # 1. Live games involving favorite teams
        if self.display_settings.get("live_mode_enabled") and live_favorite_games:
            logger.debug(f"Found {len(live_favorite_games)} live favorite games.")
            return "live_favorites", fav_live_interval

        # 2. Any other live games
        if live_other_games:
            logger.debug(f"Found {len(live_other_games)} live non-favorite games.")
            return "in_progress_games", other_live_interval

        # 3. Games scheduled for today (pre-game) - look for the next game
        if pregame_games:
            earliest_game = pregame_games[0]
            time_until_earliest_game = (earliest_game.start_time - now).total_seconds()
            logger.debug(
                f"Earliest pre-game: {earliest_game.away_team_abbrev} vs {earliest_game.home_team_abbrev} at {earliest_game.start_time}. Time until: {time_until_earliest_game}s"
            )

            # If game is within next 5 minutes, refresh quickly. Otherwise, sleep until closer.
            if (
                time_until_earliest_game < 300 and time_until_earliest_game > 0
            ):  # within 5 min, but not in the past
                return "pre_game_scheduled", pre_post_interval
            elif (
                time_until_earliest_game <= 0
            ):  # Game should have started, refresh quicker
                logger.info(
                    "Earliest pre-game is now or in the past, refreshing quickly to catch live status."
                )
                return "pre_game_scheduled", min(
                    pre_post_interval, 60
                )  # Refresh within 1 minute
            else:  # Game is later, sleep until 5 minutes before or until regular pre_post_interval
                # Cap the sleep to not be excessively long, e.g., max 1 hour, or min configured pre_post
                # Use max to ensure we don't return 0 or negative sleep, min for a ceiling
                calculated_sleep = max(
                    min(time_until_earliest_game - 60, pre_post_interval), 30
                )
                return "pre_game_scheduled", int(calculated_sleep)

        # 4. Games that recently finished (post-game) - Prioritize favorite post-games
        # We might want to show these for a certain period after they finish
        if postgame_favorite_games:
            logger.debug(
                f"Found {len(postgame_favorite_games)} post-game favorite games."
            )
            return "post_game_finished_favorite", pre_post_interval

        if postgame_other_games:
            logger.debug(
                f"Found {len(postgame_other_games)} post-game non-favorite games."
            )
            return "post_game_finished_all", pre_post_interval

        # 5. No games today/finished (or no relevant games right now)
        logger.debug(
            "No live, pre-game, or recent post-game events found. Defaulting to 'no_games_today' mode."
        )

        # Calculate time until next daily check (for long sleep overnight)
        current_date = now.date()

        # Get and parse the daily check time here where it's actually used
        check_hour, check_minute = 5, 0  # Default values
        try:
            daily_time_cfg = self.refresh_intervals.get(
                "daily_schedule_check_time", "05:00"
            )
            check_hour, check_minute = map(int, daily_time_cfg.split(":"))
        except ValueError:
            logger.error(
                f"Invalid daily_schedule_check_time format in _determine_overall_display_mode: '{daily_time_cfg}'. Using 05:00."
            )

        next_check_dt_today = datetime.combine(
            current_date,
            datetime.min.time().replace(hour=check_hour, minute=check_minute),
            tzinfo=timezone.utc,
        )
        if now < next_check_dt_today:  # If before today's check time
            time_until_next_check = (next_check_dt_today - now).total_seconds()
        else:  # If after today's check time, calculate for tomorrow
            next_check_dt_tomorrow = datetime.combine(
                current_date + timedelta(days=1),
                datetime.min.time().replace(hour=check_hour, minute=check_minute),
                tzinfo=timezone.utc,
            )
            time_until_next_check = (next_check_dt_tomorrow - now).total_seconds()

        # Ensure sleep is not negative or zero, and at least 30s for responsiveness
        # Also cap it to configured no_games_interval or until next check
        calculated_no_game_sleep = max(
            min(time_until_next_check, no_games_interval), 30
        )

        return "no_games_today", int(calculated_no_game_sleep)

    # (Optional: Test block for ScoreboardManager using parsed data)
    # if __name__ == "__main__":
    #     import sys
    #     project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    #     sys.path.insert(0, project_root)
    #     from nexus_led_scoreboard.logger import setup_logging
    #     from dotenv import load_dotenv
    #
    #     setup_logging(console_level="DEBUG", file_level="DEBUG")
    #     load_dotenv(os.path.join(project_root, ".env")) # Load .env for testing
    #
    #     # Dummy config mimicking what configure.py would save
    #     test_config = {
    #         "logging": {"console_level": "DEBUG", "file_level": "DEBUG"},
    #         "sports": {
    #             "football": {
    #                 "leagues": [
    #                     {"id": "nfl", "favorite_team_ids": ["25", "29"]} # Example: Green Bay Packers, New Orleans Saints
    #                 ]
    #             },
    #             "baseball": {
    #                 "leagues": [
    #                     {"id": "mlb", "favorite_team_ids": ["12", "19"]} # Example: Atlanta Braves, Los Angeles Dodgers
    #                 ]
    #             }
    #         },
    #         "refresh_intervals": {
    #             "in_progress_favorite_team": 5,
    #             "in_progress_other_games": 15,
    #             "pre_game_post_game": 60, # Reduced for testing
    #             "no_games": 300, # Reduced for testing
    #             "daily_schedule_check_time": "05:00" # Test with 5 AM
    #         },
    #         "display_settings": {
    #             "live_mode_enabled": True,
    #             "matrix_rows": 32,
    #             "matrix_cols": 64,
    #             "default_display_time_per_board_sec": 10
    #         },
    #         "display_modes": {
    #             "live_favorites": {"boards": ["live_game_favorite_team"]},
    #             "in_progress_games": {"boards": ["live_game_all_sports"]},
    #             "pre_game_scheduled": {"boards": ["game_preview_favorite", "game_preview_all", "clock", "weather"]},
    #             "no_games_today": {"boards": ["clock", "weather", "custom_message"]},
    #             "post_game_finished_favorite": {"boards": ["final_game_favorite_team"]},
    #             "post_game_finished_all": {"boards": ["final_game_all_sports"]},
    #         },
    #         "custom_messages": [{"id": "welcome", "text": "GO SPORTS!", "duration_sec": 10}],
    #         "weather": {"enabled": True, "location": "New York, NY", "units": "imperial", "refresh_interval_sec": 300}
    #     }
    #
    #     manager = ScoreboardManager(test_config)
    #     manager.run()
