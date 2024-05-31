import numpy as np
import pytest
from nba_api.stats.library.parameters import Season
from nba_api.stats.static.players import find_player_by_id, find_players_by_full_name

from my_exceptions import NoStatDashboard
from playerScripts import NBAPlayer, PASS_OR_ASSIST, TO_OR_FROM
from tests.conftest import PLAYERS_TO_TEAM_COUNT


class TestStatClass:
    def test_team_roster(self, player_object):
        df = player_object.current_team_object.team_roster.common_team_roster.get_data_frame()
        assert player_object.id in df["PLAYER_ID"].values

    def test_team_info(self, team_object):
        df = team_object.team_info.team_info_common.get_data_frame()
        try:
            assert team_object.stats_df["WINS"].item() == df['W'].item()
        except NoStatDashboard as e:
            pytest.skip(e.message)

    def test_defense_dashboard(self, team_object):
        try:
            df = team_object.defense_dashboard.league_dash_pt_team_defend.get_data_frame()
        except NoStatDashboard as e:
            pytest.skip(e.message)
        assert (df[df["DEFENSE_CATEGORY"] == "Overall"]["D_FGA"].item() ==
                df[df["DEFENSE_CATEGORY"] == "3 Pointers"]["D_FGA"].item() +
                df[df["DEFENSE_CATEGORY"] == "2 Pointers"]["D_FGA"].item())

