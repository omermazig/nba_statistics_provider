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


def test_shooters_lineups_df(cached_league_object):
    lineups_of_only_good_shooters_count = len(cached_league_object.get_league_all_shooters_lineups(attempts_limit=50))
    lineups_of_only_great_shooters_count = len(cached_league_object.get_league_all_shooters_lineups(attempts_limit=100))
    assert (lineups_of_only_good_shooters_count == lineups_of_only_great_shooters_count == 0 or
            lineups_of_only_good_shooters_count >= lineups_of_only_great_shooters_count)


def test_league_shooters_lineups_stats_per_team(cached_league_object):
    good_shooters_lineups = cached_league_object.get_league_all_shooters_lineups_stats_per_team(attempts_limit=100)
    good_shooters_lineups_minutes = good_shooters_lineups['TOTAL_MIN'].sum()
    great_shooters_lineups = cached_league_object.get_league_all_shooters_lineups_stats_per_team(attempts_limit=300)
    great_shooters_lineups_minutes = great_shooters_lineups['TOTAL_MIN'].sum()
    assert good_shooters_lineups_minutes >= great_shooters_lineups_minutes
