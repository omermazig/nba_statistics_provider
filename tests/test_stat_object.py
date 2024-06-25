from copy import deepcopy

import numpy as np
import pytest

from generalStatsScripts import NBAStatObject
from my_exceptions import NoStatDashboard
from teamScripts import NBATeam


@pytest.fixture(scope="module",
                params=["player", "team"],
                ids=["player_object", "team_object"])
def player_or_team_object(request, player_object, team_object) -> NBAStatObject:
    if request.param == "player":
        return player_object
    elif request.param == "team":
        return team_object


def test_equal(player_or_team_object):
    player_or_team_deepcopy = deepcopy(player_or_team_object)
    assert player_or_team_deepcopy == player_or_team_object
    player_or_team_deepcopy.season = '1789-90'
    assert not player_or_team_deepcopy == player_or_team_object


def test_stat_dict_sanity(player_or_team_object):
    try:
        df = player_or_team_object.stats_df
    except NoStatDashboard as e:
        pytest.skip(e.message)
    for prefix in ["FG", "FG3", "FT"]:
        assert df[f"{prefix}A"].item() >= df[f"{prefix}M"].item()


class TestStatClass:

    def test_shot_chart(self, player_or_team_object):
        try:
            df = player_or_team_object.shot_chart.shot_chart_detail.get_data_frame()
        except NoStatDashboard as e:
            pytest.skip(e.message)

        assert np.isclose(player_or_team_object.stats_df["FGA"].item(), len(df), atol=2)
        assert len(df[f"{player_or_team_object._object_indicator.upper()}_NAME"].value_counts()) == 1
        assert np.isclose(
            df["EVENT_TYPE"].value_counts()['Made Shot'], player_or_team_object.stats_df["FGM"].item(), atol=2
        )

    def test_game_logs(self, request, player_or_team_object):
        team_or_player = request.node.callspec.params['player_or_team_object']
        if team_or_player == "team" and int(player_or_team_object.season[:4]) < 1990:
            pytest.skip("Team stats are accurate only after about 1990")
        try:
            df = getattr(player_or_team_object.game_logs, f"{team_or_player}_game_logs").get_data_frame()
        except NoStatDashboard as e:
            pytest.skip(e.message)
        assert player_or_team_object.stats_df["GP"].item() == len(df)
        stats_to_compare = ["PTS", "REB", "AST", "FGA", "FG3A", "FTA"]
        # Wrong type identification. Don't know way.
        # noinspection PyUnresolvedReferences
        assert (np.isclose(df[stats_to_compare].sum(), player_or_team_object.stats_df[stats_to_compare], atol=2)).all()

    def test_shot_dashboard(self, player_or_team_object):
        try:
            dashboard = player_or_team_object.shot_dashboard
        except NoStatDashboard as e:
            pytest.skip(e.message)
        closest_defender_fga = dashboard.closest_defender_shooting.get_data_frame()["FGA"].sum()
        dribble_fga = dashboard.dribble_shooting.get_data_frame()["FGA"].sum()
        shot_clock_fga = dashboard.shot_clock_shooting.get_data_frame()["FGA"].sum()
        touch_time_fga = dashboard.touch_time_shooting.get_data_frame()["FGA"].sum()
        assert closest_defender_fga == dribble_fga == shot_clock_fga == touch_time_fga
        # Maybe add == player_object.stats_df["FGA"].item()

    def test_rebound_dashboard(self, player_or_team_object):
        try:
            dashboard = player_or_team_object.rebound_dashboard
        except NoStatDashboard as e:
            pytest.skip(e.message)
        shot_distance_rebounding = dashboard.shot_distance_rebounding.get_data_frame()[['C_REB', 'UC_REB']].sum().sum()
        shot_type_rebounding = dashboard.shot_type_rebounding.get_data_frame()[['C_REB', 'UC_REB']].sum().sum()
        assert shot_distance_rebounding == shot_type_rebounding
        # Maybe add == player_object.stats_df["REB"].item()

    def test_passing_dashboard(self, player_or_team_object):
        try:
            dashboard = player_or_team_object.passing_dashboard
        except NoStatDashboard as e:
            pytest.skip(e.message)
        passes_made_fga = dashboard.passes_made.get_data_frame()
        passes_received_fga = dashboard.passes_received.get_data_frame()
        if isinstance(player_or_team_object, NBATeam):
            assert np.isclose(passes_made_fga["AST"].sum(), passes_received_fga["AST"].sum(), atol=1)
            assert np.isclose(passes_made_fga["PASS"].sum(), passes_received_fga["PASS"].sum(), atol=1)
        else:
            # This is not exact for some reason
            assert np.isclose(passes_made_fga["AST"].sum(), player_or_team_object.stats_df["AST"].item(), atol=30)

