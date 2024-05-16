"""
NBAPlayer object and necessary imports functions and consts
"""
import typing
from functools import cached_property
from nba_api.stats.endpoints import PlayerDashPtShotDefend, PlayerProfileV2, CommonPlayerInfo, ShotChartDetail, \
    PlayerGameLogs, PlayerDashPtReb, PlayerDashPtPass, PlayerDashPtShots
from nba_api.stats.library.parameters import ContextMeasureSimple, Season
from nba_api.stats.static.players import find_players_by_full_name
from pandas import DataFrame
from pandas.core.groupby import DataFrameGroupBy
from typing import Union, Optional, List, Literal

import gameScripts
import generalStatsScripts
import teamScripts
import utilsScripts
from my_exceptions import NoSuchPlayer, TooMuchPlayers, PlayerHasNoTeam, PlayerHasMoreThenOneTeam

SIDE_OF_FLOOR = Literal['Right', 'Left', 'Center']


def must_have_one_team_wrapper(func1):
    """
    A wrapper that verifies that the player has only one team.
    :param func1: Function to wrap
    :type func1: lambda
    :return:
    :rtype:
    """

    def wrapper(*args):
        """

        :param args: a list that contains only self
        :type args: tuple(self)
        :return:
        :rtype:
        """
        if not args[0].is_single_team_player():
            raise PlayerHasMoreThenOneTeam(f"{args[0].name} played on more than one team in {args[0].season}")
        else:
            return func1(*args)

    return wrapper


class NBAPlayer(generalStatsScripts.NBAStatObject):
    """
    An object that represent a single nba player in a single season.
    """

    def __init__(self, name_or_id: Union[int, str], season: str = Season.current_season,
                 initialize_stat_classes: bool = True, initialize_game_objects: bool = False):
        """
        NBA player object

        :param name_or_id: can be a player id or full name with an underline ('steph_curry').
        :param season: Season to initialize player's data by
        :param initialize_stat_classes: Whether to initialize player's stat classes or not (takes a little time)
        :return: An NBA player object
        """
        self._id = name_or_id if isinstance(name_or_id, int) else NBAPlayer._get_player_id_from_name(name_or_id)
        super(NBAPlayer, self).__init__(season=season, initialize_stat_classes=initialize_stat_classes,
                                        initialize_game_objects=initialize_game_objects)

    @property
    def id(self) -> int:
        return self._id

    @staticmethod
    def _get_player_id_from_name(player_name: str) -> int:
        matching_players_info = find_players_by_full_name(player_name)
        number_of_matching_player_dicts = len(matching_players_info) if matching_players_info else 0
        if number_of_matching_player_dicts == 0:
            raise NoSuchPlayer('There was no player matching the given parameters')
        elif number_of_matching_player_dicts > 1:
            raise TooMuchPlayers('There were %s dicts for %s...' % (number_of_matching_player_dicts, player_name))
        else:
            return matching_players_info[0]['id']

    @property
    def player_info(self) -> DataFrame:
        return self.demographics.common_player_info.get_data_frame()

    @property
    def _object_indicator(self) -> str:
        return "player"

    @property
    def name(self) -> str:
        return self.player_info["PLAYERCODE"].item()

    @cached_property
    def current_team_object(self):
        """ A generated object for the team that the player is currently playing for """
        if self.team_id:
            return teamScripts.NBATeam(self.team_id, season=self.season)
        else:
            return None

    @property
    def team_id(self) -> Optional[int]:
        """ Last team player played for in the given season """
        df = self._players_all_stats_dicts
        num_of_matching_dicts = len(df)
        if num_of_matching_dicts == 0:
            return None
        else:
            # In case of multiple teams, last stat dict is the TOTAL one and has team_id=0, so this is necessary
            return df[df['TEAM_ID'] != 0].tail(1)['TEAM_ID'].item()

    @staticmethod
    def _get_relevant_stat_dict_for_list_of_stat_dicts(stats_df) -> Optional[DataFrame]:
        """
        NOTE: If a player had more then 1 team in season, the stats dict will be for his combined stats from all teams.
        :return: A dict that represent the player's basic total stats for the given season
        """
        num_of_matching_dicts = len(stats_df)
        if num_of_matching_dicts == 0:
            return None
        elif num_of_matching_dicts == 1:
            return stats_df
        else:
            return stats_df[stats_df['TEAM_ABBREVIATION'] == 'TOT']

    @cached_property
    def _players_all_stats_dicts(self) -> DataFrame:
        """
        A list of dicts that represents the player's basic total stats for the given season.
        Every df row represents a team (or TOTAL, if the player had more than one)
        """
        self.logger.info("Initializes all of %s stats dfs" % self.name)
        df = self.year_by_year_stats.season_totals_regular_season.get_data_frame()
        filtered_list_of_player_stats_dicts = df[df['SEASON_ID'] == self.season]
        return filtered_list_of_player_stats_dicts

    @property
    def stats_df(self) -> DataFrame:
        """
        NOTE: If a player had more then 1 team in season, the stats dict will be for his combined stats from all teams
        :return: A df that represent the player's basic total stats for the given season
        """
        return self._get_relevant_stat_dict_for_list_of_stat_dicts(self._players_all_stats_dicts)

    @property
    def _players_all_stats_dicts_per_game(self):
        """
        :return: A list of dicts that represents the player's basic per game stats for the given season. Every dict
        represents a team (or TOTAL, if the player had more then one)
        :rtype: list[dict]
        """
        return utilsScripts.get_per_game_from_total_stats(self._players_all_stats_dicts)

    @property
    def player_stats_dict_per_game(self):
        """
        NOTE: If a player had more then 1 team in season, the stats dict will be for his combined stats from all teams
        :return: A dict that represent the player's basic total stats for the given season
        :rtype: dict
        """
        return self._get_relevant_stat_dict_for_list_of_stat_dicts(self._players_all_stats_dicts_per_game)

    @property
    def first_year(self) -> int:
        """ The first year that the object existed """
        return int(self.player_info['FROM_YEAR'].item())

    @property
    def last_year(self) -> int:
        """ The first year that the object existed """
        return int(self.player_info['TO_YEAR'].item())

    def get_stat_classes_names(self) -> List[str]:
        return generalStatsScripts.NBAStatObject.get_stat_classes_names(self) + [
            'demographics',
        ]

    @cached_property
    def demographics(self) -> CommonPlayerInfo:
        kwargs = {
            'player_id': self.id
        }
        return utilsScripts.get_stat_class(stat_class_class_object=CommonPlayerInfo, **kwargs)

    @cached_property
    def year_by_year_stats(self) -> PlayerProfileV2:
        kwargs = {
            'player_id': self.id
        }
        return utilsScripts.get_stat_class(stat_class_class_object=PlayerProfileV2, **kwargs)

    @cached_property
    def defense_dashboard(self) -> PlayerDashPtShotDefend:
        kwargs = {
            'player_id': self.id,
            # This is to get the results against every team
            'team_id': 0,
            'season': self.season,
        }
        return utilsScripts.get_stat_class(stat_class_class_object=PlayerDashPtShotDefend, **kwargs)

    @cached_property
    def shot_chart(self) -> ShotChartDetail:
        kwargs = {
            'player_id': self.id,
            # This is to get the results against every team
            'team_id': 0,
            'season_nullable': self.season,
            # Default value makes it only return FGM, so changed to FGA. Based on - https://stackoverflow.com/a/65628817
            'context_measure_simple': ContextMeasureSimple.fga,
        }
        return utilsScripts.get_stat_class(stat_class_class_object=ShotChartDetail, **kwargs)

    @cached_property
    def game_logs(self) -> PlayerGameLogs:
        return super().game_logs

    @cached_property
    def shot_dashboard(self) -> PlayerDashPtShots:
        return super().shot_dashboard

    @cached_property
    def rebound_dashboard(self) -> PlayerDashPtReb:
        return super().rebound_dashboard

    @cached_property
    def passing_dashboard(self) -> PlayerDashPtPass:
        return super().passing_dashboard

    @cached_property
    def regular_season_game_objects(self) -> List[gameScripts.NBAGamePlayer]:
        regular_season_game_objects = []
        for game_number, game_df in self.game_logs.player_game_logs.get_data_frame().iterrows():
            self.logger.info(f"Initializing game number {game_number + 1}")
            # TODO - No reason for this to work with a df - used to work with dict
            regular_season_game_objects.append(gameScripts.NBAGamePlayer(game_df, initialize_stat_classes=True))
        return regular_season_game_objects

    def is_single_team_player(self) -> bool:
        # TODO - check
        """ Whether the player played on more than one team this season """
        return len(self._players_all_stats_dicts) == 1

    def is_three_point_shooter(self, attempts_limit: int = 50, only_recent_team: bool = False) -> bool:
        """

        :param attempts_limit: attempts_limit
        :param only_recent_team: Whether to check only the player's stats on his recent team or not.
        :return: Whether or not a player SHOT more threes this season then the attempts_limit
        """
        # TODO - check
        stat_dict = utilsScripts.get_most_recent_stat_dict(
            self._players_all_stats_dicts) if only_recent_team else self.stats_df
        if stat_dict:
            try:
                return stat_dict['FG3A'] > attempts_limit
            except IndexError:
                return False
        else:
            return False

    def is_player_over_fga_limit(self, limit: int = 300, only_recent_team: bool = False) -> bool:
        """

        :param limit:
        :param only_recent_team: Whether to check only the player's stats on his recent team or not.
        :return: Whether the player shot more the 200 field goal attempts this season or not
        """
        # TODO - check
        stat_dict = utilsScripts.get_most_recent_stat_dict(
            self._players_all_stats_dicts) if only_recent_team else self.stats_df
        if stat_dict:
            return stat_dict["FGA"] > limit
        else:
            return False

    def is_player_over_fga_outside_10_feet_limit(self, limit: int = 200) -> bool:
        """ Whether the player shot more the 100 field goal attempts outside 10 feet this season or not """
        # TODO - check
        shot_dashboard_general_dict = self.shot_dashboard.general_shooting()
        if len(shot_dashboard_general_dict) == 0:
            return False
        else:
            try:
                percentage_of_inside_shots = \
                    [i for i in shot_dashboard_general_dict if i['SHOT_TYPE'] == 'Less than 10 ft'][0]['FGA_FREQUENCY']
                percentage_of_outside_shots = 1 - percentage_of_inside_shots
            except IndexError:
                # If there is no dict for 'Less than 10 ft', that means all of the player's shots were outside 10 ft
                percentage_of_outside_shots = 1
            if self.stats_df:
                number_of_total_fga = self.stats_df["FGA"]
                number_of_outside_shots = percentage_of_outside_shots * number_of_total_fga
                return number_of_outside_shots > limit
            else:
                return False

    def is_player_over_assists_limit(self, limit: int = 100, only_recent_team: bool = False) -> bool:
        """

        :param limit:
        :param only_recent_team: Whether to check only the player's stats on his recent team or not.
        :return: Whether the player passed more the 50 assists this season or not
        """
        # TODO - check
        stat_dict = utilsScripts.get_most_recent_stat_dict(
            self._players_all_stats_dicts) if only_recent_team else self.stats_df
        if stat_dict:
            return stat_dict['AST'] > limit
        else:
            return False

    def is_player_over_minutes_limit(self, limit: int, only_recent_team: bool = False) -> bool:
        """

        :param limit:
        :param only_recent_team: Whether to check only the player's stats on his recent team or not.
        :return: Whether the player passed more the 50 assists this season or not
        """
        # TODO - check
        stat_dict = utilsScripts.get_most_recent_stat_dict(
            self._players_all_stats_dicts) if only_recent_team else self.stats_df
        if stat_dict:
            return stat_dict['MIN'] > limit
        else:
            return False

    def is_player_over_projected_minutes_limit(self, minutes_limit: int = 1000) -> bool:
        """

        :param minutes_limit: minutes limit (TOT)
        :return: Whether the player is projected to pass a given minutes limit.
        """
        return self._get_player_projected_minutes_played() > minutes_limit

    def _get_player_projected_minutes_played(self) -> int:
        """
        Based on how many minutes a player already played and how many games his team has left, returns a projection of
        how many minutes the player will finish the season with.

        :return: A projection of how many minutes the player will finish the season with.
        """
        team_minutes_played = self.current_team_object.stats_df['MIN']
        team_games_played = self.current_team_object.stats_df['GP']
        team_games_remaining = 82 - team_games_played
        player_minutes_played = self.stats_df['MIN']
        return int(player_minutes_played + (player_minutes_played / team_minutes_played) * team_games_remaining)

    # BLOCKED BY NBA - No longer provide defender distance per shot
    # def _get_average_defender_distance_depending_on_shot_result(self, shot_result):
    #     total_shots_with_result = 0
    #     total_distance_of_defenders_on_shots_with_result = 0
    #     shot_dicts_list = self.shot_log.log()
    #     for i in range(len(shot_dicts_list) - 1):
    #         if shot_dicts_list[i]['SHOT_MADE_FLAG'] == shot_result:
    #             total_shots_with_result += 1
    #             total_distance_of_defenders_on_shots_with_result += shot_dicts_list[i]['CLOSE_DEF_DIST']
    #
    #     if total_shots_with_result == 0:
    #         return 0, 0
    #     else:
    #         return total_distance_of_defenders_on_shots_with_result / total_shots_with_result, total_shots_with_result
    #
    # def get_average_defender_distance_on_makes(self):
    #     return self._get_average_defender_distance_depending_on_shot_result(1)
    #
    # def get_average_defender_distance_on_misses(self):
    #     return self._get_average_defender_distance_depending_on_shot_result(0)
    #
    # def _get_average_defender_distance_depending_on_previous_shot_result(self, shot_result):
    #     total_shots_after_result = 0
    #     total_distance_of_defenders_on_shots_after_result = 0
    #     shot_dicts_list = self.shot_chart.chart()
    #     for i in range(len(shot_dicts_list) - 1):
    #         if shot_dicts_list[i]['GAME_ID'] == shot_dicts_list[i + 1]['GAME_ID']:
    #             if shot_dicts_list[i]['SHOT_MADE_FLAG'] == shot_result:
    #                 total_shots_after_result += 1
    #                 total_distance_of_defenders_on_shots_after_result += shot_dicts_list[i + 1]['CLOSE_DEF_DIST']
    #
    #     if total_shots_after_result == 0:
    #         return 0, 0
    #     else:
    #         return total_distance_of_defenders_on_shots_after_result / total_shots_after_result, \
    #                total_shots_after_result
    #
    # def get_average_defender_distance_after_makes(self):
    #     """
    #     :return: tuple of the FG% on shots after specific shot_result and the amount of those shots
    #     :rtype: tuple(float)
    #     """
    #     return self._get_average_defender_distance_depending_on_previous_shot_result(1)
    #
    # def get_average_defender_distance_after_misses(self):
    #     """
    #     :return: tuple of the FG% on shots after specific shot_result and the amount of those shots
    #     :rtype: tuple(float)
    #     """
    #     return self._get_average_defender_distance_depending_on_previous_shot_result(0)

    def _get_efg_percentage_depending_on_previous_shots_results(self, shot_result: int,
                                                                number_of_previous_shots_to_check: int = 1) \
            -> tuple[float, int]:
        """
        :param shot_result: made (1) or missed (0)
        :param number_of_previous_shots_to_check: number of previous shots to check the condition on
        :return: tuple of the EFG% on shots after specific shot_result and the amount of those shots
        """
        df = self.shot_chart.shot_chart_detail.get_data_frame()
        # We don't want shots from different games counting as a shot sequence
        grouped = df.groupby('GAME_ID')

        # Custom rolling function to calculate sum of previous x shots made
        def sum_previous_x_makes(s):
            return s.rolling(window=number_of_previous_shots_to_check).sum().shift()

        # Calculate the number of makes out of previous x shots for each group
        df['PREV_X_MAKES'] = grouped['SHOT_MADE_FLAG'].transform(sum_previous_x_makes)

        # Filter the dataframe to include only the rows where the previous x shots were all makes
        filtered_df = df[df['PREV_X_MAKES'] == (number_of_previous_shots_to_check if shot_result == 1 else 0)]

        made_shots_num = filtered_df["SHOT_MADE_FLAG"].sum()
        three_pt_made_shots_num = filtered_df[
            (filtered_df['SHOT_MADE_FLAG'] == 1) & (filtered_df['SHOT_TYPE'] == '3PT Field Goal')
            ].shape[0]
        attempted_shots_num = len(filtered_df)

        return (
            utilsScripts.calculate_efg_percent(made_shots_num, three_pt_made_shots_num, attempted_shots_num),
            attempted_shots_num
        )

    def get_efg_percentage_after_makes(self, number_of_previous_shots_to_check: int = 1) -> tuple[float, int]:
        """
        :return: tuple of the EFG% on shots after makes, and the amount of those shots
        """
        return self._get_efg_percentage_depending_on_previous_shots_results(
            shot_result=1, number_of_previous_shots_to_check=number_of_previous_shots_to_check)

    def get_efg_percentage_after_misses(self, number_of_previous_shots_to_check: int = 1) -> tuple[float, int]:
        """
        :return: tuple of the EFG% on shots after misses, and the amount of those shots
        """
        return self._get_efg_percentage_depending_on_previous_shots_results(
            shot_result=0, number_of_previous_shots_to_check=number_of_previous_shots_to_check)

    @staticmethod
    def _groupby_side_of_floor(df: DataFrame) -> DataFrameGroupBy:
        """
        Contested - defender within 4 feet
        :return: tuple of the FG% on contested shots, and the amount of those shots.
        :rtype: tuple(float, float)
        """

        # Define a function to categorize shot zone descriptions into three groups
        def side_group(shot_zone_area: str):
            if 'left' in shot_zone_area.lower():
                return 'Left'
            elif 'right' in shot_zone_area.lower():
                return 'Right'
            else:
                return 'Center'

        # Apply the function to create a new column 'DISTANCE_GROUP'
        df['SHOT_SIDE'] = df['SHOT_ZONE_AREA'].apply(side_group)
        # Group by 'DISTANCE_GROUP' and sum the desired categories
        grouped_df = df.groupby('SHOT_SIDE')[['SHOT_MADE_FLAG', 'SHOT_TYPE']]
        return grouped_df

    def _get_shooting_data_from_floor_side(self, side: SIDE_OF_FLOOR) -> tuple[int, int, int]:
        """
        Finds the logs for all the shots from a side of the floor, and returns all the necessary data
        to calculate EFG%

        :param side: Right, Left or Center
        :return: A dict with number of FG made, number of 3FG made, and number on FG attempted
        """
        if side not in typing.get_args(SIDE_OF_FLOOR):
            raise ValueError(f'Wrong param. "{side}" not in ["Right", "Left", "Center"]')
        df = self.shot_chart.shot_chart_detail.get_data_frame()
        grouped_df = self._groupby_side_of_floor(df)
        side_value_count = grouped_df.value_counts()[side]

        made_shots_num = side_value_count[1].sum()
        three_pt_made_shots_num = side_value_count[1]['3PT Field Goal']
        attempted_shots_num = side_value_count.sum()

        return made_shots_num, three_pt_made_shots_num, attempted_shots_num

    def _get_efg_percentage_from_side(self, side: SIDE_OF_FLOOR) -> tuple[float, int]:
        """

        :param side: Right, Left or Center
        :return: tuple of the EFG% on shots from a side of the floor, and the amount of those shots
        """
        if side not in ['Right', 'Left']:
            raise ValueError('Wrong param. Has to be "Right" or "Left"')
        jump_shot_data = self._get_shooting_data_from_floor_side(side)
        efg_percentage = utilsScripts.calculate_efg_percent(jump_shot_data[0],
                                                            jump_shot_data[1],
                                                            jump_shot_data[2])
        return efg_percentage, jump_shot_data[2]

    def get_efg_percentage_from_right_side(self) -> tuple[float, int]:
        """
        :return: tuple of the EFG% on shots from the right side of the floor, and the amount of those shots
        """
        return self._get_efg_percentage_from_side('Right')

    def get_efg_percentage_from_left_side(self) -> tuple[float, int]:
        """
        :return: tuple of the EFG% on shots from the left side of the floor, and the amount of those shots
        """
        return self._get_efg_percentage_from_side('Left')

    @must_have_one_team_wrapper
    def _get_teammates_relevant_shooting_stats(self) -> tuple[int, int, int]:
        """
        :return: tuple of:
            The number of field goals made by the players' teammates,
            The number of 3 point field goals made by the players' teammates,
            The number of field goals attempted by the players' teammates
        """
        if self.current_team_object is None:
            raise PlayerHasNoTeam('{player_name} has no team (and therefore no teammates) at the moment'.format(
                player_name=self.name))

        if self.stats_df is not None:
            player_fgm = self.stats_df["FGM"].item()
            player_fg3m = self.stats_df["FG3M"].item()
            player_fga = self.stats_df["FGA"].item()
        else:
            player_fgm = 0
            player_fg3m = 0
            player_fga = 0

        teammates_fgm = self.current_team_object.stats_df['FGM'].item() - player_fgm
        teammates_fg3m = self.current_team_object.stats_df['FG3M'].item() - player_fg3m
        teammates_fga = self.current_team_object.stats_df['FGA'].item() - player_fga
        if teammates_fga == 0:
            return 0, 0, 0
        else:
            return teammates_fgm, teammates_fg3m, teammates_fga

    def _get_teammates_efg_percentage(self) -> tuple[float, int]:
        """
        :return: tuple of the EFG% on shots of teammates, and the amount of those shots
        """
        teammates_fgm, teammates_fg3m, teammates_fga = self._get_teammates_relevant_shooting_stats()

        return utilsScripts.calculate_efg_percent(teammates_fgm, teammates_fg3m, teammates_fga), teammates_fga

    def get_teammates_efg_percentage_from_passes(self) -> tuple[float, int]:
        """
        :return: tuple of the EFG% on shots of teammates after a pass, and the amount of those shots
        """
        return utilsScripts.get_efg_percentage_from_multiple_shot_charts(
            self.passing_dashboard.passes_made.get_data_frame())

    def _get_teammates_efg_percentage_without_passes(self) -> tuple[float, int]:
        """
        :return: tuple of the FG% on shots of teammates that were not after a pass, and the amount of those shots.
        """
        teammates_fgm, teammates_fg3m, teammates_fga = self._get_teammates_relevant_shooting_stats()
        teammates_fgm_from_player_passes, teammates_fg3m_from_player_passes, teammates_fga_from_player_passes = \
            utilsScripts.get_efg_relevant_data_from_multiple_shot_charts(
                self.passing_dashboard.passes_made.get_data_frame())

        teammates_fgm_without_player_pass = teammates_fgm - teammates_fgm_from_player_passes
        teammates_fg3m_without_player_pass = teammates_fg3m - teammates_fg3m_from_player_passes
        teammates_fga_without_player_pass = teammates_fga - teammates_fga_from_player_passes
        if teammates_fga_without_player_pass == 0:
            return 0, 0
        else:
            efg_percent_without_a_pass = utilsScripts.calculate_efg_percent(
                teammates_fgm_without_player_pass,
                teammates_fg3m_without_player_pass,
                teammates_fga_without_player_pass)
            return efg_percent_without_a_pass, teammates_fga_without_player_pass

    def get_diff_in_teammates_efg_percentage_on_shots_from_player_passes(self) -> tuple[float, int]:
        """

        :return: tuple of:
            The diff in EFG% between shots of teammates that were after a pass by him, and ones that were not.
            The amount of the teammates shots.
        """
        teammates_efg_on_shots_after_pass_from_player, teammates_number_of_shots_after_pass_from_player = \
            self.get_teammates_efg_percentage_from_passes()
        if teammates_number_of_shots_after_pass_from_player == 0:
            return 0, 0
        else:
            teammates_efg_on_shots_not_after_pass_from_player, teammates_number_of_shots_not_after_pass_from_player = \
                self._get_teammates_efg_percentage_without_passes()
            if teammates_number_of_shots_not_after_pass_from_player == 0:
                return 0, 0
            return teammates_efg_on_shots_after_pass_from_player - teammates_efg_on_shots_not_after_pass_from_player, \
                teammates_number_of_shots_after_pass_from_player

    # noinspection PyPep8Naming
    def get_aPER(self) -> float:
        """ A calculation of the aPER, which is the PER measurement BEFORE normalization """
        # TODO - Check
        return utilsScripts.get_aPER_from_stat_dict(self.stats_df, self.current_team_object)

    def print_shooting_info(self) -> None:
        """ Printing all the main relevant info on a player's shooting """

        efg_after_makes = self.get_efg_percentage_after_makes
        efg_after_misses = self.get_efg_percentage_after_misses
        efg_on_contested = self.get_efg_percentage_on_contested_shots_outside_10_feet
        efg_on_uncontested = self.get_efg_percentage_on_uncontested_shots_outside_10_feet
        efg_right_side = self.get_efg_percentage_from_right_side
        efg_left_side = self.get_efg_percentage_from_left_side
        self.print_field_goal_percentage_in_a_given_condition(self.name,
                                                              efg_after_makes,
                                                              "%EFG after a make")
        self.print_field_goal_percentage_in_a_given_condition(self.name,
                                                              efg_after_misses,
                                                              "%EFG after a miss")
        self.print_field_goal_percentage_in_a_given_condition(self.name,
                                                              efg_on_contested,
                                                              "%EFG on contested shot outside 10 feet")
        self.print_field_goal_percentage_in_a_given_condition(self.name,
                                                              efg_on_uncontested,
                                                              "%EFG on uncontested shot outside 10 feet")
        self.print_field_goal_percentage_in_a_given_condition(self.name,
                                                              efg_right_side,
                                                              "%EFG on shots from the right side")
        self.print_field_goal_percentage_in_a_given_condition(self.name,
                                                              efg_left_side,
                                                              "%EFG on shots from the left side")

    def print_passing_info(self) -> None:
        """ Printing all the main relevant info on a player's passing """
        diff_in_efg = self.get_diff_in_teammates_efg_percentage_on_shots_from_player_passes
        self.print_field_goal_percentage_in_a_given_condition(self.name,
                                                              diff_in_efg,
                                                              "- change in teammates %EFG "
                                                              "after a pass from a player")

    def get_most_frequent_passer_to_player(self) -> Optional[dict]:
        """
        A dict that represent the passing connection between the player and the player that passes him the ball the most
        """
        # TODO - Check
        if not self.passing_dashboard.passes_received():
            self.logger.warning('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_received(), key=lambda x: x["FREQUENCY"])
        return utilsScripts.get_per_game_from_total_stats(most_frequent_assistant_dict)

    def get_most_frequent_receiver_of_player_passes(self) -> Optional[dict]:
        """
        A dict that represent the passing connection between the player and the player he passes the ball the most to
        """
        # TODO - Check
        if not self.passing_dashboard.passes_received():
            self.logger.warning('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_made(),
                                           key=lambda x: utilsScripts.get_per_game_from_total_stats(x)["AST"])
        return utilsScripts.get_per_game_from_total_stats(most_frequent_assistant_dict)

    def get_most_frequent_assister_to_player(self) -> Optional[dict]:
        """
        A dict that represent the passing connection between the player and the player that
        passes him the most assists
        """
        # TODO - Check
        if not self.passing_dashboard.passes_received():
            self.logger.warning('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_received(),
                                           key=lambda x: utilsScripts.get_per_game_from_total_stats(x)["AST"])
        return utilsScripts.get_per_game_from_total_stats(most_frequent_assistant_dict)

    def get_most_frequent_receiver_of_player_assists(self) -> Optional[dict]:
        """
        A dict that represent the passing connection between the player and the player that
        he passes the most assists to
        """
        # TODO - Check
        if not self.passing_dashboard.passes_received():
            self.logger.warning('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_made(), key=lambda x: x["FREQUENCY"])
        return utilsScripts.get_per_game_from_total_stats(most_frequent_assistant_dict)

    def _get_team_advanced_stats_with_player_on_and_off_court(self):
        # TODO - Check
        if self.current_team_object is None:
            raise PlayerHasNoTeam('{player_name} has no team (and therefore no teammates) at the moment'.format(
                player_name=self.name))
        team_advanced_stats_with_player_on_court = [
            x for x in self.current_team_object.on_off_court.players_on_court_team_player_on_off_summary()
            if x['VS_PLAYER_ID'] == self.id
        ]
        team_advanced_stats_with_player_off_court = [
            x for x in self.current_team_object.on_off_court.players_off_court_team_player_on_off_summary()
            if x['VS_PLAYER_ID'] == self.id
        ]
        return team_advanced_stats_with_player_on_court, \
            team_advanced_stats_with_player_off_court

    def get_team_net_rtg_on_off_court(self) -> tuple[float, float]:
        """ The player's current team's net rating when he's ON and OFF the court """
        # TODO - Check
        team_advanced_stats_with_player_on_court, team_advanced_stats_with_player_off_court = \
            self._get_team_advanced_stats_with_player_on_and_off_court()
        if team_advanced_stats_with_player_off_court and team_advanced_stats_with_player_on_court:
            return team_advanced_stats_with_player_on_court[0]['NET_RATING'], \
                team_advanced_stats_with_player_off_court[0]['NET_RATING']
        else:
            return 0, 0

    def get_team_off_rtg_on_off_court(self) -> tuple[float, float]:
        """ The player's current team's offensive rating when he's ON and OFF the court """
        # TODO - Check
        team_advanced_stats_with_player_on_court, team_advanced_stats_with_player_off_court = \
            self._get_team_advanced_stats_with_player_on_and_off_court()
        if team_advanced_stats_with_player_off_court and team_advanced_stats_with_player_on_court:
            return team_advanced_stats_with_player_on_court[0]['OFF_RATING'], \
                team_advanced_stats_with_player_off_court[0]['OFF_RATING']
        else:
            return 0, 0

    def get_team_def_rtg_on_off_court(self) -> tuple[float, float]:
        """ The player's current team's defensive rating when he's ON and OFF the court """
        # TODO - Check
        team_advanced_stats_with_player_on_court, team_advanced_stats_with_player_off_court = \
            self._get_team_advanced_stats_with_player_on_and_off_court()
        if team_advanced_stats_with_player_off_court and team_advanced_stats_with_player_on_court:
            return team_advanced_stats_with_player_on_court[0]['DEF_RATING'], \
                team_advanced_stats_with_player_off_court[0]['DEF_RATING']
        else:
            return 0, 0

    def get_team_net_rtg_on_off_court_diff(self) -> float:
        # TODO - Check
        on_court_net_rtg, off_court_net_rtg = self.get_team_net_rtg_on_off_court()
        return on_court_net_rtg - off_court_net_rtg

    def get_team_off_rtg_on_off_court_diff(self) -> float:
        # TODO - Check
        on_court_off_rtg, off_court_off_rtg = self.get_team_off_rtg_on_off_court()
        return on_court_off_rtg - off_court_off_rtg

    def get_team_def_rtg_on_off_court_diff(self) -> float:
        # TODO - Check
        on_court_def_rtg, off_court_def_rtg = self.get_team_def_rtg_on_off_court()
        return on_court_def_rtg - off_court_def_rtg

    def get_all_time_game_objects(self, initialize_stat_classes: bool = False) -> list[gameScripts.NBAGamePlayer]:
        """

        :param initialize_stat_classes: Whether to initialize the stat classes for the game objects
        :return:
        """
        # TODO - Check
        player_all_time_game_logs = [game_log for game_log in self.get_all_time_game_logs()]
        player_all_time_game_objects = [gameScripts.NBAGamePlayer(game_log, initialize_stat_classes) for game_log in
                                        player_all_time_game_logs]
        return player_all_time_game_objects

    def get_over_minutes_limit_games_per_36_stats_compared_to_other_games(self, minutes_limit=30) -> dict[
        str, dict[str, float]]:
        # TODO - Check
        over_limit_game_dicts = [game_log for game_log in self.game_logs.player_game_logs() if game_log['MIN'] >= 30]
        under_limit_game_dicts = [game_log for game_log in self.game_logs.player_game_logs() if game_log['MIN'] < 30]
        return {
            ('Over %s minutes' % minutes_limit): utilsScripts.join_single_game_stats(over_limit_game_dicts,
                                                                                     per_36=True),
            ('Under %s minutes' % minutes_limit): utilsScripts.join_single_game_stats(under_limit_game_dicts,
                                                                                      per_36=True)}

    def get_teammate_cooperation_stats(self, teammate_name: str) -> dict[str, dict[str, float]]:
        """
        Receives a teammate's name and returns team's advanced stat dict for minutes:
        -When player AND teammate are on the floor together
        -When player is on the floor WITHOUT the teammate
        """
        # TODO - Check
        teammate_object = self.current_team_object.get_player_object_by_name(teammate_name)
        teammate_name = teammate_object.name
        lineups_with_teammate = self.current_team_object.get_filtered_lineup_dicts(white_list=[self, teammate_object])
        lineups_without_teammate = self.current_team_object.get_filtered_lineup_dicts(white_list=[self],
                                                                                      black_list=[teammate_object])
        stats_with_teammate = utilsScripts.join_advanced_lineup_dicts(lineups_with_teammate)
        stats_without_teammate = utilsScripts.join_advanced_lineup_dicts(lineups_without_teammate)
        return {
            f'Stats With {teammate_name}': stats_with_teammate,
            f'Stats Without {teammate_name}': stats_without_teammate}

    def get_net_rtg_with_and_without_teammate(self, teammate_name: str) -> tuple[float, float]:
        # TODO - Check
        a = self.get_teammate_cooperation_stats(teammate_name)
        return a[f'Stats With {teammate_name}']['NET_RATING'], a[f'Stats Without {teammate_name}']['NET_RATING']


if __name__ == "__main__":
    players_names_list = [
        # 'rajon rondo',
        'stephen curry',
        'james harden',
        'lebron james',
        'kevin durant',
        # 'jr smith',
        # 'paul pierce',
        # 'carmelo anthony'
    ]
    selected_season = '2022-23'
    for player_name_ in players_names_list:
        nba_player = NBAPlayer(name_or_id=player_name_, season=selected_season)
        nba_player.logger.info(f"Print {nba_player.name} shooting info")
        nba_player.print_shooting_info()
        nba_player.logger.info(f"Print {nba_player.name} passing info")
        nba_player.print_passing_info()

        # national_tv_stats = nba_player.get_national_tv_all_time_per_game_stats()
        # not_national_tv_stats = nba_player.get_not_national_tv_all_time_per_game_stats()
        # csv_path = os.path.join(csvs_folder_path,
        #                         '%s_all_time_national_tv_stats_per_36_minutes' % nba_player.name + '.csv')
        # convert_dicts_into_csv([national_tv_stats, not_national_tv_stats], csv_path)
