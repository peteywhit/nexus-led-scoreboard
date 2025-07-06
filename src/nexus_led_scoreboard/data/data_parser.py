import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class Game:
    """
    Represents a single parsed game event with key attributes for display logic.
    """

    def __init__(
        self,
        game_id: str,
        sport: str,
        league: str,
        start_time: datetime,
        status_state: str,  # e.g., 'pre', 'in_progress', 'post'
        status_detail: str,  # e.g., 'Final', 'In Progress, 3rd Quarter'
        home_team_id: str,
        home_team_name: str,
        home_team_abbrev: str,
        home_score: Optional[int],
        away_team_id: str,
        away_team_name: str,
        away_team_abbrev: str,
        away_score: Optional[int],
        is_favorite: bool = False,
    ):
        self.game_id = game_id
        self.sport = sport
        self.league = league
        self.start_time = start_time
        self.status_state = status_state
        self.status_detail = status_detail
        self.home_team_id = home_team_id
        self.home_team_name = home_team_name
        self.home_team_abbrev = home_team_abbrev
        self.home_score = home_score
        self.away_team_id = away_team_id
        self.away_team_name = away_team_name
        self.away_team_abbrev = away_team_abbrev
        self.away_score = away_score
        self.is_favorite = is_favorite

    @property
    def is_live(self) -> bool:
        return self.status_state == "in_progress"

    @property
    def is_pregame(self) -> bool:
        return self.status_state == "pre"

    @property
    def is_postgame(self) -> bool:
        return self.status_state == "post"

    def __repr__(self):
        fav_str = "(Fav) " if self.is_favorite else ""
        score_str = (
            f" ({self.away_score}-{self.home_score})"
            if self.is_live or self.is_postgame
            else ""
        )
        return (
            f"Game({fav_str}{self.away_team_abbrev} vs {self.home_team_abbrev} "
            f"[{self.sport}/{self.league}] - {self.status_detail}{score_str} "
            f"starts: {self.start_time.strftime('%H:%M')})"
        )


class ESPNDataParser:
    """
    Parses raw ESPN API JSON response into a list of Game objects.
    """

    def __init__(self, favorite_team_ids: Dict[str, List[str]]):
        """
        Args:
            favorite_team_ids (Dict[str, List[str]]): A dictionary mapping league_id to
                                                        a list of favorite team IDs in that league.
                                                        E.g., {"nfl": ["1", "2"], "mlb": ["3"]}
        """
        self.favorite_team_ids = favorite_team_ids
        logger.info("ESPNDataParser initialized.")

    def parse_events(self, raw_data: Dict[str, Any]) -> List[Game]:
        """
        Parses raw ESPN API event data into a list of Game objects.

        Args:
            raw_data (Dict[str, Any]): The raw JSON response from ESPNAPIFetcher.get_events().

        Returns:
            List[Game]: A list of parsed Game objects.
        """
        games: List[Game] = []
        if not raw_data or "events" not in raw_data:
            logger.debug("No 'events' found in raw data for parsing.")
            return []

        sport_slug = None
        if raw_data and "sport" in raw_data and isinstance(raw_data["sport"], dict):
            sport_slug = raw_data["sport"].get("slug")

        league_slug = None
        if (
            raw_data
            and "leagues" in raw_data
            and isinstance(raw_data["leagues"], list)
            and len(raw_data["leagues"]) > 0
        ):
            first_league = raw_data["leagues"][0]
            if isinstance(first_league, dict):
                league_slug = first_league.get("slug")

        for event_data in raw_data["events"]:
            try:
                game_id = event_data.get("id")
                start_time_str = event_data.get("date")
                start_time = (
                    datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    if start_time_str
                    else None
                )

                status_info = event_data.get("status", {}).get("type", {})
                status_state = status_info.get("state")  # 'pre', 'in_progress', 'post'
                status_detail = status_info.get(
                    "detail"
                )  # 'Final', 'In Progress', 'Scheduled', etc.

                competitions = event_data.get("competitions", [])
                if not competitions:
                    logger.warning(
                        f"No competitions found for event {game_id}. Skipping."
                    )
                    continue

                competition_data = competitions[0]
                competitors = competition_data.get("competitors", [])

                home_team_data = next(
                    (comp for comp in competitors if comp.get("homeAway") == "home"), {}
                )
                away_team_data = next(
                    (comp for comp in competitors if comp.get("homeAway") == "away"), {}
                )

                home_team_info = home_team_data.get("team", {})
                away_team_info = away_team_data.get("team", {})

                home_team_id = home_team_info.get("id")
                home_team_name = home_team_info.get(
                    "displayName", home_team_info.get("name")
                )
                home_team_abbrev = home_team_info.get("abbreviation")
                raw_home_score = home_team_data.get("score")
                if isinstance(raw_home_score, dict) and "value" in raw_home_score:
                    home_score = raw_home_score.get("value")
                else:
                    home_score = raw_home_score

                away_team_id = away_team_info.get("id")
                away_team_name = away_team_info.get(
                    "displayName", away_team_info.get("name")
                )
                away_team_abbrev = away_team_info.get("abbreviation")
                raw_away_score = away_team_data.get("score")
                if isinstance(raw_away_score, dict) and "value" in raw_away_score:
                    away_score = raw_away_score.get("value")
                else:
                    away_score = raw_away_score

                # Determine if it's a favorite game
                is_favorite = False
                if league_slug:
                    favorite_ids_for_league = self.favorite_team_ids.get(
                        league_slug, []
                    )
                    is_favorite = (
                        str(home_team_id) in favorite_ids_for_league
                        or str(away_team_id) in favorite_ids_for_league
                    )
                else:
                    logger.warning(
                        f"Could not determine league slug for event {game_id}. Skipping favorite check."
                    )

                # Check if all required fields are present
                if all([game_id, start_time, status_state, home_team_id, away_team_id]):
                    games.append(
                        Game(
                            game_id=game_id,
                            sport=sport_slug,
                            league=league_slug,
                            start_time=start_time,
                            status_state=status_state,
                            status_detail=status_detail,
                            home_team_id=home_team_id,
                            home_team_name=home_team_name,
                            home_team_abbrev=home_team_abbrev,
                            home_score=home_score,
                            away_team_id=away_team_id,
                            away_team_name=away_team_name,
                            away_team_abbrev=away_team_abbrev,
                            away_score=away_score,
                            is_favorite=is_favorite,
                        )
                    )
                else:
                    logger.warning(
                        f"Skipping game {game_id} due to missing critical data: {event_data.keys()}"
                    )

            except Exception as e:
                logger.error(
                    f"Error parsing event data: {e} - Raw event: {event_data}",
                    exc_info=True,
                )

        logger.debug(f"Parsed {len(games)} games from raw data.")
        return games
