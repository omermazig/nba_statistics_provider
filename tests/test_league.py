import pytest

from leagueScripts import NBALeague
from my_exceptions import NoStatDashboard
from utilsScripts import get_all_seasons_of_pickle_files


@pytest.mark.parametrize("season", get_all_seasons_of_pickle_files())
def test_cached_league_object(season):
    cached_league_object = NBALeague.get_cached_league_object(season)
    actual_league_object = NBALeague(season=season)
    assert cached_league_object.get_league_ppp() == actual_league_object.get_league_ppp()


def test_ppp(league_object):
    try:
        ppp = league_object.get_league_ppp()
    except NoStatDashboard as e:
        pytest.skip(e.message)
    assert ppp > 1, f"Expected PPP to be greater than 1, but got {ppp}"
