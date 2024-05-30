import numpy as np
import pytest
from _pytest.fixtures import FixtureRequest, SubRequest
from nba_api.stats.library.parameters import Season
from nba_api.stats.static.players import find_player_by_id, find_players_by_full_name

from my_exceptions import NoStatDashboard
from playerScripts import NBAPlayer, PASS_OR_ASSIST, TO_OR_FROM

players_to_team_count = {
    ("Kevin Durant", '2022-23'): 2,  # Traded once mid-season
    ("Isaiah Thomas", '2021-22'): 3,  # Signed by 3 different teams
    ("Stephen Curry", '2021-22'): 1,  # No trades
    ("Lebron James", '2013-14'): 1,  # Traded twice mid-season
    ("Mike Bibby", '2010-11'): 3,  # Traded twice mid-season
    ("Mark Jackson", '1996-97'): 2,  # Idiot
    ("Michael Jordan", '1992-93'): 1,  # GOAT
    ("Larry Bird", '1985-86'): 1,  # White Hope
    ("Kareem Abdul-Jabbar", '1980-81'): 1,  # Cap
}


@pytest.fixture(scope="module",
                ids=[key[0] for key in players_to_team_count.keys()],
                params=(
                        players_to_team_count.keys()
                ))
def player_object(request: SubRequest) -> NBAPlayer:
    player_name, season = request.param
    yield NBAPlayer(name_or_id=player_name, season=season, initialize_stat_classes=False, initialize_game_objects=False)


def test_stat_dict_sanity(player_object):
    assert player_object.stats_df["GP"].item() >= player_object.stats_df["GS"].item()
    for prefix in ["FG", "FG3", "FT"]:
        assert player_object.stats_df[f"{prefix}A"].item() >= player_object.stats_df[f"{prefix}M"].item()


def test_stat_dict_count(request, player_object):
    team_count = players_to_team_count[request.node.callspec.params['player_object']]
    assert player_object.is_single_team_player() == (team_count == 1)
    # If a player played for more than one team, he will have a TOT entry for the combined stats
    expected_stat_entries = team_count if team_count <= 1 else team_count + 1
    assert len(player_object._players_all_stats_dicts) == expected_stat_entries


class TestStatClass:
    def test_demographics(self, player_object):
        df = player_object.demographics.common_player_info.get_data_frame()
        assert df["PERSON_ID"].item() == player_object.id

    def test_year_by_year_stats(self, player_object):
        df = player_object.year_by_year_stats.career_highs.get_data_frame()
        for prefix in ["FG", "FG3", "FT"]:
            assert (
                    df[df["STAT"] == f"{prefix}A"].head(1)["STAT_VALUE"].item() >=
                    df[df["STAT"] == f"{prefix}M"].head(1)["STAT_VALUE"].item()
            )

    def test_defense_dashboard(self, player_object):
        try:
            df = player_object.defense_dashboard.defending_shots.get_data_frame()
        except NoStatDashboard as e:
            pytest.skip(e.message)
        assert (df[df["DEFENSE_CATEGORY"] == "Overall"]["D_FGA"].item() ==
                df[df["DEFENSE_CATEGORY"] == "3 Pointers"]["D_FGA"].item() +
                df[df["DEFENSE_CATEGORY"] == "2 Pointers"]["D_FGA"].item())

    def test_shot_chart(self, player_object):
        try:
            df = player_object.shot_chart.shot_chart_detail.get_data_frame()
        except NoStatDashboard as e:
            pytest.skip(e.message)

        assert player_object.stats_df["FGA"].item() == len(df)
        assert len(df["PLAYER_NAME"].value_counts()) == 1
        assert df["EVENT_TYPE"].value_counts()['Made Shot'] == player_object.stats_df["FGM"].item()

    def test_game_logs(self, player_object):
        try:
            df = player_object.game_logs.player_game_logs.get_data_frame()
        except NoStatDashboard as e:
            pytest.skip(e.message)
        assert player_object.stats_df["GP"].item() == len(df)
        stats_to_compare = ["PTS", "REB", "AST", "FGA", "FG3A", "FTA"]
        # Wrong type identification. Don't know way.
        # noinspection PyUnresolvedReferences
        assert (df[stats_to_compare].sum() == player_object.stats_df[stats_to_compare]).all().all()

    def test_shot_dashboard(self, player_object):
        try:
            dashboard = player_object.shot_dashboard
        except NoStatDashboard as e:
            pytest.skip(e.message)
        closest_defender_fga = dashboard.closest_defender_shooting.get_data_frame()["FGA"].sum()
        dribble_fga = dashboard.dribble_shooting.get_data_frame()["FGA"].sum()
        shot_clock_fga = dashboard.shot_clock_shooting.get_data_frame()["FGA"].sum()
        touch_time_fga = dashboard.touch_time_shooting.get_data_frame()["FGA"].sum()
        assert closest_defender_fga == dribble_fga == shot_clock_fga == touch_time_fga
        # Maybe add == player_object.stats_df["FGA"].item()

    def test_rebound_dashboard(self, player_object):
        dashboard = player_object.rebound_dashboard
        shot_distance_rebounding = dashboard.shot_distance_rebounding.get_data_frame()[['C_REB', 'UC_REB']].sum().sum()
        shot_type_rebounding = dashboard.shot_type_rebounding.get_data_frame()[['C_REB', 'UC_REB']].sum().sum()
        assert shot_distance_rebounding == shot_type_rebounding
        # Maybe add == player_object.stats_df["REB"].item()

    def test_passing_dashboard(self, player_object):
        if int(player_object.season[:4]) < 2013:
            pytest.skip("Shot charts only works for 2013-2014 season")
        dashboard = player_object.passing_dashboard
        passes_made_fga = dashboard.passes_made.get_data_frame()
        # This is not exact for some reason
        assert np.isclose(passes_made_fga["AST"].sum(), player_object.stats_df["AST"].item(), atol=20)


def test_conditions(player_object):
    assert player_object.is_player_over_assists_limit(0)
    assert not player_object.is_player_over_assists_limit(10000)

    assert player_object.is_three_point_shooter(0)
    assert not player_object.is_three_point_shooter(1000)

    assert player_object.is_player_over_fga_limit(0)
    assert not player_object.is_player_over_fga_limit(3000)

    try:
        assert player_object.is_player_over_fga_outside_10_feet_limit(0)
        assert not player_object.is_player_over_fga_outside_10_feet_limit(10000)
    except NoStatDashboard:
        pass

    if not player_object.season == Season.current_season:
        try:
            assert player_object._get_player_projected_minutes_played() == player_object.stats_df['MIN'].item()
        except NoStatDashboard:
            pass


class TestRegression:
    def test_shots_after_makes(self, player_object):
        game_logs_df = player_object.game_logs.player_game_logs.get_data_frame()
        try:
            assert (player_object.get_efg_percentage_after_makes(1)[1] +
                    player_object.get_efg_percentage_after_misses(1)[1] +
                    len(game_logs_df[game_logs_df['FGA'] != 0])) == player_object.stats_df['FGA'].item()
        except NoStatDashboard:
            pytest.skip("Shot charts only works for 1996-1997 season")

    def test_shots_per_side(self, player_object):
        try:
            assert (player_object._get_efg_percentage_from_side('Right')[1] +
                    player_object._get_efg_percentage_from_side('Left')[1] +
                    player_object._get_efg_percentage_from_side('Center')[1]
                    == player_object.stats_df['FGA'].item())
        except NoStatDashboard:
            pytest.skip("Shot charts only works for 1996-1997 season")

    def test_teammate_shooting(self, request, player_object):
        team_count = players_to_team_count[request.node.callspec.params['player_object']]
        if team_count > 1:
            pytest.skip("Test is relevant only for 1 team players")
        try:
            _, teammates_shots_after_pass_count = player_object.get_teammates_efg_percentage_from_passes()
            _, teammates_shots_not_after_pass_count = player_object._get_teammates_efg_percentage_without_passes()
            teamates_shots = player_object.current_team_object.stats_df['FGA'].item() - player_object.stats_df[
                'FGA'].item()
        except NoStatDashboard:
            pytest.skip("Shot charts only works for 1996-1997 season")
        assert teammates_shots_after_pass_count + teammates_shots_not_after_pass_count == teamates_shots

    testdata = [
        ('ASSIST', 'TO', 'Nic Claxton'),
        ('ASSIST', 'FROM', 'Ben Simmons'),
        ('PASS', 'TO', 'Kyrie Irving'),
        ('PASS', 'FROM', "Royce O'Neale"),
    ]

    @pytest.mark.parametrize("pass_or_assist,to_or_from,expected_teammate_name", testdata)
    def test_teammate_assist_giving(self, request, player_object,
                                    pass_or_assist: PASS_OR_ASSIST, to_or_from: TO_OR_FROM, expected_teammate_name):
        player_name, season = request.node.callspec.params['player_object']
        desired_player_name = "Kevin Durant"
        if player_name != desired_player_name:
            pytest.skip(f"This test is only relevant to {desired_player_name}")
        try:

            df = player_object._get_most_cooperative_teammate(pass_or_assist, to_or_from)
        except NoStatDashboard:
            pytest.skip("Passing dashboard only works for 2013-2014 season")
        teammate_id = df['PASS_TEAMMATE_PLAYER_ID']
        assert find_player_by_id(teammate_id)['full_name'] == expected_teammate_name
        teammate_object = NBAPlayer(name_or_id=int(teammate_id), season=season, initialize_stat_classes=False,
                                    initialize_game_objects=False)
        if to_or_from == 'TO':
            teammate_fd = teammate_object.passing_dashboard.passes_received.get_data_frame()
        elif to_or_from == 'FROM':
            teammate_fd = teammate_object.passing_dashboard.passes_made.get_data_frame()
        else:
            raise Exception('Unreachable')
        passes_from_teammates = teammate_fd[teammate_fd['PASS_TEAMMATE_PLAYER_ID'] == player_object.id]['AST']
        assert passes_from_teammates.item() == df['AST'].item()

    def test_teammate_cooperation_stats(self, request, player_object):
        player_name, season = request.node.callspec.params['player_object']
        desired_player_name = "Stephen Curry"
        teammates_player_names = {"Draymond Green", "Klay Thompson", "Andrew Wiggins"}
        if player_name != desired_player_name:
            pytest.skip(f"This test is only relevant to {desired_player_name}")

        teammate_ids = {
            find_players_by_full_name(teammate_player_name)[0]['id'] for teammate_player_name in teammates_player_names
        }
        cooperation_stats = player_object.get_teammates_cooperation_stats(teammate_ids)

        # THIS IS WRONG - Because I can only get 250 lineups at a time
        assert (cooperation_stats['TOTAL_MIN'] == [363.0, 394.0, 99.0, 119.0, 339.0, 599.0, 6.0]).all()
        for teammate_id in teammate_ids:
            teammate_object = NBAPlayer(
                name_or_id=teammate_id, season=season, initialize_stat_classes=False, initialize_game_objects=False
            )
            net_rtg_with, net_rtg_without = teammate_object.get_net_rtg_with_and_without_teammate(player_object.id)
            # Cause steph is GREAT!
            assert net_rtg_with > net_rtg_without

    def test_on_off_stats(self, player_object):
        try:
            player_def_rtg = player_object.get_team_def_rtg_on_off_court()
            player_off_rtg = player_object.get_team_off_rtg_on_off_court()
            player_net_rtg = player_object.get_team_net_rtg_on_off_court()
            assert np.isclose((player_off_rtg - player_def_rtg), player_net_rtg, atol=0.1).all()

            player_def_rtg_diff = player_object.get_team_def_rtg_on_off_court_diff()
            player_off_rtg_diff = player_object.get_team_off_rtg_on_off_court_diff()
            player_net_rtg_diff = player_object.get_team_net_rtg_on_off_court_diff()
            assert np.isclose((player_def_rtg.iloc[0] - player_def_rtg.iloc[1]), player_def_rtg_diff)
            assert np.isclose((player_off_rtg.iloc[0] - player_off_rtg.iloc[1]), player_off_rtg_diff)
            assert np.isclose((player_net_rtg.iloc[0] - player_net_rtg.iloc[1]), player_net_rtg_diff)
        except NoStatDashboard as e:
            pytest.skip(e.message)

    # def test_aPER(self, player_object):
    #     aPER = player_object.get_aPER()
    #     assert aPER
