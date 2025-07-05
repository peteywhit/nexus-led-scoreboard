import requests
import json
import os
import time
import logging


logger = logging.getLogger(__name__)


class ESPNAPIFetcher:
    """
    A class to fetch and cache data from the ESPN API endpoints.
    Implements basic rate limiting.
    """
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"

    CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
    MIN_REQUEST_INTERVAL_SECONDS = 2

    def __init__(self):
        logger.info("ESPNAPIFetcher initialized.")
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self._last_request_time = 0

    def _get_cache_path(self, endpoint_url: str, params: dict = None, game_id: str = None, teams_endpoint: bool = False) -> str:
        """
        Generates a unique file path for caching based on the URL, parameters,
        optional game ID, or indicating it's a teams endpoint.
        """
        if game_id:
            filename = f"game_{game_id}.json"
        elif teams_endpoint:
            # For teams endpoint, generate a filename specific to sport/league
            # endpoint_url format: .../sports/{sport}/{league}/teams
            parts = endpoint_url.split('/')
            sport = parts[-3] if len(parts) >= 3 else "unknown_sport"
            league = parts[-2] if len(parts) >= 2 else "unknown_league"

            # Include parameters (like 'limit') in the cache filename for teams endpoint
            param_str = "_".join(f"{k}-{v}" for k, v in sorted(params.items())) if params else ""
            if param_str:
                filename = f"teams_{sport}_{league}_{param_str}.json"
            else:
                filename = f"teams_{sport}_{league}.json"
        else:
            param_str = "_".join(f"{k}-{v}" for k, v in sorted(params.items())) if params else ""
            filename = f"{endpoint_url.replace('https://', '').replace('/', '_').replace('.', '_')}_{param_str}.json"
            filename = filename[:200] # truncate to avoid excessively long names
        return os.path.join(self.CACHE_DIR, filename)

    def _load_from_cache(self, cache_path: str) -> dict | None:
        """Loads data from cache if the file exists."""
        if os.path.exists(cache_path):
            logger.debug(f"Loading from cache: {cache_path}")
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from cache {cache_path}: {e}")
                return None
        return None

    def _save_to_cache(self, cache_path: str, data: dict):
        """Saves data to cache."""
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved to cache: {cache_path}")
        except IOError as e:
            logger.error(f"Error saving to cache {cache_path}: {e}")

    def _apply_rate_limit(self):
        """Applies a minimum delay between requests."""
        elapsed_time = time.time() - self._last_request_time
        if elapsed_time < self.MIN_REQUEST_INTERVAL_SECONDS:
            wait_time = self.MIN_REQUEST_INTERVAL_SECONDS - elapsed_time
            logger.info(f"Applying rate limit, waiting for {wait_time:.2f} seconds...")
            time.sleep(wait_time)
        self._last_request_time = time.time()

    def get_scoreboard(self, sport: str, league: str, date: str = None) -> dict:
        """
        Fetches scoreboard data for a given sport and league, using cache and rate limiting.

        Args:
            sport (str): The sport (e.g., 'football', 'basketball').
            league (str): The league (e.g., 'nfl', 'nba', 'mlb').
            date (str, optional): Date in YYYYMMDD format. Defaults to today.

        Returns:
            dict: The JSON response as a dictionary, or an empty dict on error.
        """
        endpoint_base = f"{self.BASE_URL}/{sport}/{league}/scoreboard"
        params = {}
        if date:
            params['dates'] = date

        cache_path = self._get_cache_path(endpoint_base, params=params)
        cached_data = self._load_from_cache(cache_path)

        if cached_data:
            return cached_data

        self._apply_rate_limit()

        logger.info(f"Fetching new data for scoreboard from: {endpoint_base} with params: {params}")
        try:
            response = requests.get(endpoint_base, params=params)
            response.raise_for_status()
            json_data = response.json()
            self._save_to_cache(cache_path, json_data)
            return json_data
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err} (Status: {response.status_code})")
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An error occurred during the request: {req_err}")
        return {}

    def get_game_by_id(self, sport: str, league: str, game_id: str) -> dict | None:
        """
        Fetches data for a specific game by its ID.

        Args:
            sport (str): The sport (e.g., 'football', 'basketball').
            league (str): The league (e.g., 'nfl', 'nba', 'mlb').
            game_id (str): The unique ID of the game.

        Returns:
            dict: The JSON response as a dictionary, or None on error.
        """
        endpoint = f"{self.BASE_URL}/{sport}/{league}/scoreboard/{game_id}"

        cache_path = self._get_cache_path(endpoint, game_id=game_id)
        cached_data = self._load_from_cache(cache_path)

        if cached_data:
            return cached_data

        self._apply_rate_limit()

        logger.info(f"Fetching new data for game ID {game_id} from: {endpoint}")
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            json_data = response.json()
            self._save_to_cache(cache_path, json_data)
            return json_data
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err} (Status: {response.status_code})")
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An error occurred during the request: {req_err}")
        return None

    def get_teams(self, sport: str, league: str, limit: int = 1000) -> dict:
        """
        Fetches team data for a given sport and league.

        Args:
            sport (str): The sport (e.g., 'football', 'baseball').
            league (str): The league (e.g., 'nfl', 'mlb').
            limit (int): The maximum number of teams to return. Default to 1000.

        Returns:
            dict: The JSON response containing team data, or an empty dict on error.
        """
        endpoint = f"{self.BASE_URL}/{sport}/{league}/teams"
        params = {'limit': limit} # Add the limit parameter

        # Use a specific cache path for teams data, including the limit in filename
        cache_path = self._get_cache_path(endpoint, params=params, teams_endpoint=True)
        cached_data = self._load_from_cache(cache_path)

        if cached_data:
            return cached_data

        self._apply_rate_limit()

        logger.info(f"Fetching team data from: {endpoint} with limit={limit}")
        try:
            response = requests.get(endpoint, params=params) # Pass params to requests.get
            response.raise_for_status()
            json_data = response.json()
            self._save_to_cache(cache_path, json_data)
            return json_data
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err} (Status: {response.status_code})")
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An error occurred during the request: {req_err}")
        return {}
