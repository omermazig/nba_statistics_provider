import pytest

from my_exceptions import NoStatDashboard


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

    def test_shooters_lineups_df(self, team_object):
        lineups_of_only_good_shooters_count = len(team_object.get_all_shooters_lineups_df(attempts_limit=50))
        lineups_of_only_great_shooters_count = len(team_object.get_all_shooters_lineups_df(attempts_limit=100))
        assert (lineups_of_only_good_shooters_count == lineups_of_only_great_shooters_count == 0 or
                lineups_of_only_good_shooters_count >= lineups_of_only_great_shooters_count)

