from datetime import datetime, timedelta


class Team:
    """Represents a sports team."""
    def __init__(self, id: str, name: str, display_name: str, abbreviation: str, logo: str = None, color: str = None):
        self.id = id
        self.name = name
        self.display_name = display_name
        self.abbreviation = abbreviation
        self.logo = logo
        self.color = color

    def __repr__(self):
        return f"Team({self.abbreviation})"

class Score:
    """Represents a team's score."""
    def __init__(self, value: int):
        self.value = value

    def __repr__(self):
        return f"Score({self.value})"

class Game:
    """Represents a single game."""
    def __init__(self,
                 id: str,
                 date: datetime,
                 name: str,
                 short_name: str,
                 status_type_id: str, # e.g., '1' for pre, '2' for in, '3' for post
                 status_display_clock: float, # seconds left in period/game
                 status_display_period: int,
                 home_team: Team,
                 away_team: Team,
                 home_score: Score,
                 away_score: Score,
                 competitors_detail: list, # Raw competitor details for more info
                 event_link: str = None,
                 is_completed: bool = False,
                 is_in_progress: bool = False,
                 is_pregame: bool = False
                 ):
        self.id = id
        self.date = date # datetime object of game start
        self.name = name
        self.short_name = short_name
        self.status_type_id = status_type_id
        self.status_display_clock = status_display_clock
        self.status_display_period = status_display_period
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = home_score
        self.away_score = away_score
        self.competitors_detail = competitors_detail # Keep raw for future parsing needs
        self.event_link = event_link

        # Simplified status flags for convenience
        self.is_completed = (status_type_id == '3') or is_completed
        self.is_in_progress = (status_type_id == '2') or is_in_progress
        self.is_pregame = (status_type_id == '1') or is_pregame

    @property
    def current_period_and_clock(self):
        """Returns formatted period and clock, e.g., 'Q3 5:30' or 'Final'."""
        if self.is_completed:
            return "Final"
        elif self.is_in_progress:
            minutes = int(self.status_display_clock // 60)
            seconds = int(self.status_display_clock % 60)
            return f"Q{self.status_display_period} {minutes}:{seconds:02d}"
        else: # Pregame
            return self.date.strftime("%I:%M %p").lstrip('0') # e.g., "7:00 PM"

    def __repr__(self):
        status = ""
        if self.is_completed: status = "Final"
        elif self.is_in_progress: status = "Live"
        else: status = self.date.strftime("%I:%M %p").lstrip('0')
        return (f"Game({self.away_team.abbreviation} {self.away_score.value} vs "
                f"{self.home_team.abbreviation} {self.home_score.value} | {status})")


class ESPNDataParser:
    """
    Parses raw JSON data from ESPN API into structured Python objects.
    """
    def parse_scoreboard_data(self, raw_json: dict) -> list[Game]:
        """
        Parses the raw JSON response from the scoreboard endpoint into a list of Game objects.
        """
        games = []
        if not raw_json or 'events' not in raw_json:
            print("Warning: No events found in raw scoreboard JSON.")
            return games

        for event in raw_json['events']:
            try:
                # Basic Event Info
                game_id = event['id']
                game_date_str = event['date'] # e.g., '2025-07-03T18:05Z'
                # Parse date string to datetime object. Handle timezone if needed.
                # For simplicity, assuming UTC if 'Z' is present, otherwise naive.
                if game_date_str.endswith('Z'):
                    game_date = datetime.strptime(game_date_str, "%Y-%m-%dT%H:%MZ")
                else:
                    game_date = datetime.strptime(game_date_str, "%Y-%m-%dT%H:%M")

                game_name = event.get('name', 'N/A')
                game_short_name = event.get('shortName', 'N/A')

                # Status Info
                status_type_id = event['status']['type']['id'] # '1':pre, '2':in, '3':post
                status_display_clock = event['status']['clock']
                status_display_period = event['status']['period']

                # Competitors (Teams and Scores)
                competitors_data = event['competitions'][0]['competitors']
                home_competitor_data = next((c for c in competitors_data if c['homeAway'] == 'home'), None)
                away_competitor_data = next((c for c in competitors_data if c['homeAway'] == 'away'), None)

                if not home_competitor_data or not away_competitor_data:
                    print(f"Warning: Could not find home/away competitors for game ID {game_id}")
                    continue

                home_team_data = home_competitor_data['team']
                away_team_data = away_competitor_data['team']

                home_team = Team(
                    id=home_team_data['id'],
                    name=home_team_data['name'],
                    display_name=home_team_data.get('displayName', home_team_data['name']),
                    abbreviation=home_team_data['abbreviation'],
                    logo=home_team_data.get('logo'),
                    color=home_team_data.get('color')
                )
                away_team = Team(
                    id=away_team_data['id'],
                    name=away_team_data['name'],
                    display_name=away_team_data.get('displayName', away_team_data['name']),
                    abbreviation=away_team_data['abbreviation'],
                    logo=away_team_data.get('logo'),
                    color=away_team_data.get('color')
                )

                home_score = Score(int(home_competitor_data.get('score', 0)))
                away_score = Score(int(away_competitor_data.get('score', 0)))

                event_link = next((link['href'] for link in event.get('links', []) if link.get('rel') == ['summary', 'boxscore']), None)


                game = Game(
                    id=game_id,
                    date=game_date,
                    name=game_name,
                    short_name=game_short_name,
                    status_type_id=status_type_id,
                    status_display_clock=status_display_clock,
                    status_display_period=status_display_period,
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    competitors_detail=event['competitions'][0]['competitors'], # Store raw details
                    event_link=event_link
                )
                games.append(game)

            except KeyError as e:
                print(f"Error parsing game data (missing key: {e}) for event: {event.get('id', 'N/A')}. Skipping.")
            except Exception as e:
                print(f"An unexpected error occurred parsing game data for event: {event.get('id', 'N/A')}. Error: {e}. Skipping.")

        return games
