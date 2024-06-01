"""
NBATeam object and necessary imports functions and consts
"""
import os
from functools import cached_property
from typing import Optional, Union

from nba_api.stats.endpoints import TeamGameLogs, TeamYearByYearStats, TeamInfoCommon, CommonTeamRoster, \
    TeamDashPtShots, TeamDashPtReb, TeamDashPtPass, TeamDashLineups, TeamPlayerOnOffSummary
from nba_api.stats.library.parameters import Season, MeasureTypeDetailedDefense
from pandas import DataFrame

import gameScripts
import generalStatsScripts
import leagueScripts
import playerScripts
import utilsScripts
from my_exceptions import NoStatDashboard
from playersContainerScripts import PlayersContainer

teams_id_dict = {'pistons': 1610612765,
                 'grizzlies': 1610612763,
                 'bucks': 1610612749,
                 'kings': 1610612758,
                 'sixers': 1610612755,
                 'pelicans': 1610612740,
                 'knicks': 1610612752,
                 'warriors': 1610612744,
                 'hawks': 1610612737,
                 'wizards': 1610612764,
                 'suns': 1610612756,
                 'nuggets': 1610612743,
                 'cavaliers': 1610612739,
                 'jazz': 1610612762,
                 'timberwolves': 1610612750,
                 'clippers': 1610612746,
                 'bulls': 1610612741,
                 'blazers': 1610612757,
                 'celtics': 1610612738,
                 'nets': 1610612751,
                 'magic': 1610612753,
                 'mavericks': 1610612742,
                 'hornets': 1610612766,
                 'heat': 1610612748,
                 'lakers': 1610612747,
                 'pacers': 1610612754,
                 'rockets': 1610612745,
                 'thunder': 1610612760,
                 'raptors': 1610612761,
                 'spurs': 1610612759
                 }
teams_name_dict = {v: k for k, v in teams_id_dict.items()}

nba_teams_all_shooters_lineups_dicts_path_regex = os.path.join(utilsScripts.pickles_folder_path,
                                                               'nba_teams_all_shooters_lineups_dicts_{season}.pickle')


class NBATeam(generalStatsScripts.NBAStatObject, PlayersContainer):
    """
    An object that represent a single nba team in a single season.
    """

    def __init__(
            self, name_or_id: Union[int, str], season: str = Season.current_season,
            initialize_stat_classes: bool = True, initialize_game_objects: bool = False
    ):
        """
        NBA team object

        :param name_or_id:
        :param season: Season to initialize team's data by
        :param initialize_stat_classes: Whether to initialize team's stat classes or not (takes a little time)
        :return: An NBA team object
        """
        self.team_name_or_id = name_or_id
        super(NBATeam, self).__init__(season=season, initialize_stat_classes=initialize_stat_classes,
                                      initialize_game_objects=initialize_game_objects)

    @property
    def _object_indicator(self) -> str:
        return "team"

    @property
    def name(self) -> str:
        if type(self.team_name_or_id) is str:
            return self.team_name_or_id.lower()
        elif type(self.team_name_or_id) is int:
            return teams_name_dict[self.id]
        else:
            raise Exception('Constructor only receives string or integer')

    @property
    def id(self) -> int:
        """

        :return:
        :rtype: str
        """
        if type(self.team_name_or_id) is int:
            return self.team_name_or_id
        elif type(self.team_name_or_id) is str:
            return teams_id_dict[self.team_name_or_id]
        else:
            raise Exception('Constructor only receives string or integer')

    @cached_property
    def stats_df(self):
        if int(self.season[:4]) < 1990:
            raise NoStatDashboard("Team stats are accurate only after about 1990")
        df = self.year_by_year_stats.team_stats.get_data_frame()
        return df[df['YEAR'] == self.season]

    @property
    def first_year(self):
        """

        :return: The first year that the object existed
        :rtype: int
        """
        return int(self.team_info.team_info_common.get_data_frame()['MIN_YEAR'].item())

    @property
    def last_year(self):
        """

        :return: The first year that the object existed
        :rtype: int
        """
        return int(self.team_info.team_info_common.get_data_frame()['MAX_YEAR'].item())

    def get_stat_classes_names(self):
        return generalStatsScripts.NBAStatObject.get_stat_classes_names(self) + [
            'team_info',
            'team_roster',
            'lineups',
            'on_off_court',
        ]

    @cached_property
    def current_league_object(self):
        """

        :return:A generated object for the team that the player is currently playing for
        :rtype: leagueScripts.NBALeague
        """
        return leagueScripts.NBALeague(
            season=self.season,
            initialize_stat_classes=self._initialize_stat_classes,
            initialize_game_objects=self._initialize_game_objects
        )

    @cached_property
    def current_players_objects(self):
        """

        :return:
        :rtype: list[playerScripts.NBAPlayer]
        """
        return self._generate_current_players_objects(initialize_stat_classes=False)

    @cached_property
    def team_info(self) -> TeamInfoCommon:
        kwargs = {
            'team_id': self.id,
            'season_nullable': self.season
        }
        return self.get_stat_class(stat_class_class_object=TeamInfoCommon, **kwargs)

    @cached_property
    def team_roster(self) -> CommonTeamRoster:
        kwargs = {
            'team_id': self.id,
            'season': self.season
        }
        return self.get_stat_class(stat_class_class_object=CommonTeamRoster, **kwargs)

    @cached_property
    def lineups(self) -> TeamDashLineups:
        # TODO - THIS IS WRONG - Because I can only get 250 lineups at a time. Find a way to fix.
        kwargs = {
            'team_id': self.id,
            'season': self.season
        }
        # custom_filters = [
        #     ("MIN", "LE", "0"),
        # ]
        # return self.get_stat_class(stat_class_class_object=TeamDashLineups, custom_filters=custom_filters, **kwargs)
        return self.get_stat_class(stat_class_class_object=TeamDashLineups, **kwargs)

    @cached_property
    def on_off_court(self) -> TeamPlayerOnOffSummary:
        if int(self.season[:4]) < 2007:
            raise NoStatDashboard(f'No on-off data in {self.season[:4]} - Only since 2013')
        kwargs = {
            'team_id': self.id,
            'season': self.season
        }
        return self.get_stat_class(stat_class_class_object=TeamPlayerOnOffSummary, **kwargs)

    @cached_property
    def year_by_year_stats(self) -> TeamYearByYearStats:
        kwargs = {
            'team_id': self.id
        }
        return self.get_stat_class(stat_class_class_object=TeamYearByYearStats, **kwargs)

    @cached_property
    def game_logs(self) -> TeamGameLogs:
        return super().game_logs

    @cached_property
    def shot_dashboard(self) -> TeamDashPtShots:
        return super().shot_dashboard

    @cached_property
    def rebound_dashboard(self) -> TeamDashPtReb:
        return super().rebound_dashboard

    @cached_property
    def passing_dashboard(self) -> TeamDashPtPass:
        return super().passing_dashboard

    def _generate_current_players_objects(self, initialize_stat_classes):
        """
        Returns a list of player objects for players on the team's roster
        :param initialize_stat_classes:
        :type initialize_stat_classes: bool
        :return:
        :rtype: list[playerScripts.NBAPlayer]
        """
        # TODO - Check
        players_objects_list = []
        for row in self.team_roster.common_team_roster.get_data_frame()[["PLAYER", "PLAYER_ID"]].itertuples(
                index=False):
            player_name = row.PLAYER
            player_id = row.PLAYER_ID
            try:
                nba_player_object = playerScripts.NBAPlayer(name_or_id=player_id,
                                                            season=self.season,
                                                            initialize_stat_classes=initialize_stat_classes)
                nba_player_object.current_team_object = self
                players_objects_list.append(nba_player_object)
            except playerScripts.NoSuchPlayer:
                self.logger.warning(
                    "{player_name} was not found in leagues players, even though he's on the team roster".format(
                        player_name=player_name))
            except Exception as e:
                raise e
        return players_objects_list

    def get_filtered_lineup_df(
            self,
            lineups_df: DataFrame = DataFrame(),
            ids_white_list: Optional[set[int]] = None,
            ids_black_list: Optional[set[int]] = None
    ) -> DataFrame:
        """

        :param lineups_df: lineups list to filter valid lineups from. If None, uses all team's lineups from reg season
        :param ids_white_list: player objects white list
        :param ids_black_list: player objects black list
        :return: Filtered dict based on the parameters given
        """
        if not ids_white_list:
            ids_white_list = set()
        if not ids_black_list:
            ids_black_list = set()

        if lineups_df.empty:
            with self.reinitialize_class_with_new_parameters(
                    'lineups', measure_type_detailed_defense=MeasureTypeDetailedDefense.advanced
            ):
                lineups_df = self.lineups.lineups.get_data_frame()
        valid_lineups_idx = (
            lineups_df.apply(
                lambda lineup_row: utilsScripts.is_lineup_valid(lineup_row, ids_white_list, ids_black_list), axis=1
            )
        )
        return lineups_df[valid_lineups_idx]

    def get_all_shooters_lineups_df(self, attempts_limit: int = 50) -> DataFrame:
        non_shooter_player_ids = {player_object.id for player_object in self.current_players_objects
                                  if not player_object.is_three_point_shooter(attempts_limit=attempts_limit)}
        all_shooters_lineup_dicts = self.get_filtered_lineup_df(ids_black_list=non_shooter_player_ids)
        return all_shooters_lineup_dicts

    def get_all_time_game_objects(self, initialize_stat_classes=False):
        """

        :param initialize_stat_classes: Whether or not to initialize the stat classes for the game objects
        :type initialize_stat_classes: bool
        :return:
        :rtype: list[NBAGamePlayer]
        """
        # TODO - Check
        player_all_time_game_logs = [game_log for game_log in self.get_all_time_game_logs()]
        player_all_time_game_objects = [gameScripts.NBAGameTeam(game_log, initialize_stat_classes) for game_log in
                                        player_all_time_game_logs]
        return player_all_time_game_objects

    def get_pace(self):
        return self.year_by_year_stats.team_stats.get_data_frame()['PACE']

    def get_pace_adjustment(self):
        """

        :return: League's pace divided by team's pace. Used for PER calculation
        :rtype: float
        """
        pace_def = self.current_league_object.get_league_pace_info()
        league_pace = (pace_def["POSS"].sum() / pace_def["MIN"].sum()) * 48
        team_pace = pace_def[pace_def["TEAM_ID"] == self.id]["PACE"]
        return league_pace / team_pace

    def get_assist_percentage(self) -> float:
        """ The portion of the team's field goals which was assisted """
        df = self.stats_df
        return df['AST'] / df['FGM']


if __name__ == "__main__":
    # suns = NBATeam('suns')
    # only_shooters_suns_lineups = suns.get_all_shooters_lineups_df()
    # suns_all_shooters_advanced_stats = join_advanced_lineup_dicts(only_shooters_suns_lineups)
    #
    # bobcats = NBATeam('bobcats')
    # only_shooters_bobcats_lineups = bobcats.get_all_shooters_lineups_df()
    # bobcats_all_shooters_advanced_stats = join_advanced_lineup_dicts(only_shooters_bobcats_lineups)
    my_season = '2015-16'
    warriors = NBATeam('warriors', season='2015-16')
    all_time_per_game_stats = warriors.get_all_time_per_game_stats()
    print(all_time_per_game_stats)
