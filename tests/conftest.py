import pytest
from _pytest.fixtures import SubRequest

from leagueScripts import NBALeague
from playerScripts import NBAPlayer
from teamScripts import NBATeam

PLAYERS_TO_TEAM_COUNT = {
    ("Nikola Jokic", '2023-24'): 1,  # MVP
    ("Kevin Durant", '2022-23'): 2,  # Traded once mid-season
    ("Stephen Curry", '2021-22'): 1,  # No trades
    ("Lebron James", '2013-14'): 1,  # Traded twice mid-season
    ("Mike Bibby", '2010-11'): 3,  # Traded twice mid-season
    ("Mark Jackson", '1996-97'): 2,  # Idiot
    ("Michael Jordan", '1992-93'): 1,  # GOAT
    ("Larry Bird", '1985-86'): 1,  # White Hope
    ("Kareem Abdul-Jabbar", '1980-81'): 1,  # Cap
}


@pytest.fixture(scope="module",
                ids=[key[0] for key in PLAYERS_TO_TEAM_COUNT.keys()],
                params=(
                        PLAYERS_TO_TEAM_COUNT.keys()
                ))
def player_object(request: SubRequest) -> NBAPlayer:
    player_name, season = request.param
    yield NBAPlayer(name_or_id=player_name, season=season, initialize_stat_classes=False, initialize_game_objects=False)


@pytest.fixture(scope="module")
def team_object(player_object) -> NBATeam:
    return player_object.current_team_object


@pytest.fixture(scope="module")
def league_object(player_object) -> NBALeague:
    return player_object.current_team_object.current_league_object


@pytest.fixture(scope="module")
def cached_league_object() -> NBALeague:
    return NBALeague.get_cached_league_object()

