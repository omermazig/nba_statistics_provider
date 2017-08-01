"""
NBAPlayer object and necessary imports functions and consts
"""
from __future__ import print_function
from __future__ import division
from cached_property import cached_property
from retrying import retry

from my_exceptions import NoSuchPlayer, TooMuchPlayers, PlayerHasNoTeam, PlayerHasMoreThenOneTeam
import teamScripts
import gameScripts
import utilsScripts
import goldsberry
import generalStatsScripts

# import used only for type-hinting
# noinspection PyUnresolvedReferences
from goldsberry.masterclass import NbaDataProvider


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
        :type args: list
        :return:
        :rtype:
        """
        if not args[0].is_single_team_player():
            raise PlayerHasMoreThenOneTeam
        else:
            return func1(*args)

    return wrapper


class NBAPlayer(generalStatsScripts.NBAStatObject):
    """
    An object that represent a single nba player in a single season.
    """

    @retry(stop_max_attempt_number=3, wait_fixed=5000,
           retry_on_exception=lambda exception: isinstance(exception, ConnectionError))
    def __init__(self, player_name_or_id, season=goldsberry.apiparams.default_season, initialize_stat_classes=True,
                 initialize_game_objects=False):
        """
        NBA player object
        :param player_name_or_id: can be a player id or full name with an underline ('steph_curry').
        :type player_name_or_id: int or str
        :param season: Season to initialize player's data by
        :type season: str
        :param initialize_stat_classes: Whether to initialize player's stat classes or not (take a little time)
        :type initialize_stat_classes: bool
        """
        self.player_dict = self._get_player_dict(player_name_or_id, season)
        super(NBAPlayer, self).__init__(season=season, initialize_stat_classes=initialize_stat_classes)
        self.season = season
        """:type : str"""

        if initialize_game_objects:
            # Cache game objects. a is unused
            # noinspection PyUnusedLocal
            a = self.player_regular_season_game_objects

    @staticmethod
    def _get_player_dict(player_name_or_id, season):
        """
        Get player's id or name + season, and returns it's game id for that season
        :param player_name_or_id:
        :type player_name_or_id: str or int
        :param season:
        :type season: str
        :return:
        :rtype: dict
        """
        if type(player_name_or_id) is int:
            identifying_key = 'PERSON_ID'
            filter_function = lambda dict1: dict1[identifying_key] and player_name_or_id == dict1[identifying_key]
        elif type(player_name_or_id) is str:
            identifying_key = 'PLAYERCODE'
            filter_function = lambda dict1: dict1[identifying_key] and player_name_or_id.lower() in dict1[
                identifying_key]
        else:
            raise Exception('Constructor only receives string or integer')

        filtered_player_dicts_list = [dict1 for dict1 in goldsberry.PlayerList(is_only_current_season=0).players()
                                      if
                                      int(dict1['FROM_YEAR']) <= int(season[:4]) <= int(dict1['TO_YEAR'])]
        filtered_player_dicts_list = [dict1 for dict1 in filtered_player_dicts_list if filter_function(dict1)]
        number_of_matching_player_dicts = len(filtered_player_dicts_list)
        if number_of_matching_player_dicts == 0:
            raise NoSuchPlayer('There was no player matching the given parameters')
        elif number_of_matching_player_dicts > 1:
            raise TooMuchPlayers('There were %s dicts for %s...' % (number_of_matching_player_dicts, player_name_or_id))
        else:
            return filtered_player_dicts_list[0]

    @property
    def _object_indicator(self):
        return "player"

    @property
    def name(self):
        """

        :return:
        :rtype: str
        """
        return self.player_dict["PLAYERCODE"]

    @property
    def id(self):
        """

        :return:
        :rtype: str
        """
        return self.player_dict["PERSON_ID"]

    @cached_property
    def current_team_object(self):
        """

        :return: A generated object for the team that the player is currently playing for
        :rtype: teamScripts.NBATeam
        """
        if self.team_id:
            return teamScripts.NBATeam(self.team_id, season=self.season)
        else:
            return None

    @property
    def team_id(self):
        """

        :return: Last team player played for in the given season
        :rtype: int
        """
        num_of_matching_dicts = len(self._players_all_stats_dicts)
        if num_of_matching_dicts == 0:
            return None
        elif num_of_matching_dicts == 1:
            return self._players_all_stats_dicts[0]['TEAM_ID']
        else:
            return [career_stats_dict for career_stats_dict in self._players_all_stats_dicts if
                    career_stats_dict['TEAM_ID']][-1]['TEAM_ID']

    @staticmethod
    def _get_relevant_stat_dict_for_list_of_stat_dicts(list_of_stat_dicts):
        """
        NOTE: If a player had more then 1 team in season, the stats dict will be for his combined stats from all teams.
        :return: A dict that represent the player's basic total stats for the given season
        :rtype: dict
        """
        num_of_matching_dicts = len(list_of_stat_dicts)
        if num_of_matching_dicts == 0:
            return None
        elif num_of_matching_dicts == 1:
            return list_of_stat_dicts[0]
        else:
            return [stats_dict for stats_dict in list_of_stat_dicts if
                    stats_dict['TEAM_ABBREVIATION'] == 'TOT'][0]

    @cached_property
    def _players_all_stats_dicts(self):
        """
        NOTE: goldsberry originated object of 'career_stats' is essential for this property, so we initialize it if
        it's not already initialized.
        :return: A list of dicts that represents the player's basic total stats for the given season. Every dict
        represents a team (or TOTAL, if the player had more then one)
        :rtype: list[dict]
        """
        print("Initializes all of %s stats dicts" % self.name)
        self._initialize_stat_class_if_not_initialized('career_stats')
        filtered_list_of_player_stats_dicts = [stats_dict for stats_dict in
                                               self.career_stats.seasons_regular() if
                                               stats_dict['SEASON_ID'] == self.season]
        return filtered_list_of_player_stats_dicts

    @property
    def stats_dict(self):
        """
        NOTE: If a player had more then 1 team in season, the stats dict will be for his combined stats from all teams
        :return: A dict that represent the player's basic total stats for the given season
        :rtype: dict
        """
        return self._get_relevant_stat_dict_for_list_of_stat_dicts(self._players_all_stats_dicts)

    @property
    def _players_all_stats_dicts_per_game(self):
        """
        :return: A list of dicts that represents the player's basic per game stats for the given season. Every dict
        represents a team (or TOTAL, if the player had more then one)
        :rtype: list[dict]
        """
        return [utilsScripts.get_per_game_from_total_stats(stat_dict) for stat_dict in self._players_all_stats_dicts]

    @property
    def player_stats_dict_per_game(self):
        """
        NOTE: If a player had more then 1 team in season, the stats dict will be for his combined stats from all teams
        :return: A dict that represent the player's basic total stats for the given season
        :rtype: dict
        """
        return self._get_relevant_stat_dict_for_list_of_stat_dicts(self._players_all_stats_dicts_per_game)

    @property
    def first_year(self):
        """

        :return: The first year that the object existed
        :rtype: int
        """
        return int(self.player_dict['FROM_YEAR'])

    @property
    def last_year(self):
        """

        :return: The first year that the object existed
        :rtype: int
        """
        return int(self.player_dict['TO_YEAR'])

    @cached_property
    def player_regular_season_game_objects(self):
        """

        :return:
        :rtype: list[gameScripts.NBAGamePlayer]
        """
        regular_season_game_objects = []
        for game_number, game_log in enumerate(reversed(self.game_logs.logs())):
            print('Initializing game number %s' % (game_number + 1))
            regular_season_game_objects.append(gameScripts.NBAGamePlayer(game_log, initialize_stat_classes=True))
        return regular_season_game_objects

    def is_single_team_player(self):
        """

        :return: Whether or not the player played on more then one team this season
        :rtype: bool
        """
        return len(self._players_all_stats_dicts) == 1

    def is_three_point_shooter(self, attempts_limit=50, only_recent_team=False):
        """

        :param attempts_limit: attempts_limit
        :type attempts_limit: int
        :param only_recent_team: Whether to check only the player's stats on his recent team or not.
        :type only_recent_team: bool
        :return: Whether or not a player SHOT more threes this season then the attempts_limit
        :rtype : bool
        """
        stat_dict = utilsScripts.get_most_recent_stat_dict(
            self._players_all_stats_dicts) if only_recent_team else self.stats_dict
        if stat_dict:
            try:
                return stat_dict['FG3A'] > attempts_limit
            except IndexError:
                return False
        else:
            return False

    def is_player_over_fga_limit(self, limit=300, only_recent_team=False):
        """

        :param limit:
        :type limit: int
        :param only_recent_team: Whether to check only the player's stats on his recent team or not.
        :type only_recent_team: bool
        :return: Whether the player shot more the 200 field goal attempts this season or not
        :rtype: bool
        """
        stat_dict = utilsScripts.get_most_recent_stat_dict(
            self._players_all_stats_dicts) if only_recent_team else self.stats_dict
        if stat_dict:
            return stat_dict["FGA"] > limit
        else:
            return False

    def is_player_over_fga_outside_10_feet_limit(self, limit=200):
        """

        :param limit:
        :type limit: int
        :return: Whether the player shot more the 100 field goal attempts outside of 10 feet this season or not
        :rtype: bool
        """
        shot_dashboard_general_dict = self.shot_dashboard.general()
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
            if self.stats_dict:
                number_of_total_fga = self.stats_dict["FGA"]
                number_of_outside_shots = percentage_of_outside_shots * number_of_total_fga
                return number_of_outside_shots > limit
            else:
                return False

    def is_player_over_assists_limit(self, limit=100, only_recent_team=False):
        """

        :param limit:
        :type limit: int
        :param only_recent_team: Whether to check only the player's stats on his recent team or not.
        :type only_recent_team: bool
        :return: Whether the player passed more the 50 assists this season or not
        :rtype: bool
        """
        stat_dict = utilsScripts.get_most_recent_stat_dict(
            self._players_all_stats_dicts) if only_recent_team else self.stats_dict
        if stat_dict:
            return stat_dict['AST'] > limit
        else:
            return False

    def is_player_over_minutes_limit(self, limit=800, only_recent_team=False):
        """

        :param limit:
        :type limit: int
        :param only_recent_team: Whether to check only the player's stats on his recent team or not.
        :type only_recent_team: bool
        :return: Whether the player passed more the 50 assists this season or not
        :rtype: bool
        """
        stat_dict = utilsScripts.get_most_recent_stat_dict(
            self._players_all_stats_dicts) if only_recent_team else self.stats_dict
        if stat_dict:
            return stat_dict['MIN'] > limit
        else:
            return False

    def _is_player_over_projected_minutes_limit(self, minutes_limit=1000):
        """
        Returns whether or not the player is projected to pass a given minutes limit.

        :param minutes_limit: minutes limit (TOT)
        :type minutes_limit: int
        :return:
        :rtype: bool
        """
        return self._get_player_projected_minutes_played() > minutes_limit

    def _get_player_projected_minutes_played(self):
        """
        Based on how many minutes a player already played and how many games his team has left, returns a projection of
        how many minutes the player will finish the season with.

        :return: A projection of how many minutes the player will finish the season with.
        :rtype: float
        """
        team_minutes_played = self.current_team_object.stats_dict['MIN']
        team_games_played = self.current_team_object.stats_dict['GP']
        team_games_remaining = 82 - team_games_played
        player_minutes_played = self.stats_dict['MIN']
        return player_minutes_played + (player_minutes_played / team_minutes_played) * team_games_remaining

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

    def _get_effective_field_goal_percentage_depending_on_previous_shots_results(self, shot_result,
                                                                                 number_of_previous_shots_to_check=1):
        """
        :param shot_result: made (1) or missed (2)
        :type shot_result: int
        :param number_of_previous_shots_to_check: number of previous shots to check the condition on
        :type number_of_previous_shots_to_check: int
        :return: tuple of the EFG% on shots after specific shot_result and the amount of those shots
        :rtype: tuple(float, int)
        """
        player_fgm = 0
        player_fg3m = 0
        player_fga = 0
        shots_dicts_list = self.shot_chart.chart()
        for i in range(number_of_previous_shots_to_check, len(shots_dicts_list)):
            shots_to_check_condition_on = shots_dicts_list[i - number_of_previous_shots_to_check:i]
            shots_to_check_condition_on_results_set = list(set([shot_dict['SHOT_MADE_FLAG'] for shot_dict in
                                                                shots_to_check_condition_on]))
            shots_to_check_condition_on_game_id = list(set([shot_dict['GAME_ID'] for shot_dict in
                                                            shots_to_check_condition_on]))
            # Checking whether all the previous shots that we check are from the same game or not
            if len(shots_to_check_condition_on_game_id) == 1:
                # Checking whether all the previous shots that we check had the same result ot not,
                # AND whether it was the right result or not
                if len(shots_to_check_condition_on_results_set) == 1 and \
                                shots_to_check_condition_on_results_set[0] == shot_result:
                    # Verifying the shot was in the same game as the last one
                    if shots_dicts_list[i]['GAME_ID'] == shots_dicts_list[i - 1]['GAME_ID']:
                        if shots_dicts_list[i]['SHOT_MADE_FLAG']:
                            player_fgm += 1
                            if shots_dicts_list[i]['SHOT_TYPE'] == '3PT Field Goal':
                                player_fg3m += 1
                        player_fga += 1

        if player_fga == 0:
            return 0, 0
        else:
            return utilsScripts.calculate_effective_field_goal_percent(player_fgm, player_fg3m, player_fga), player_fga

    def get_effective_field_goal_percentage_after_makes(self, number_of_previous_shots_to_check=1):
        """
        :return: tuple of the EFG% on shots after makes, and the amount of those shots
        :rtype: tuple(float, int)
        """
        return self._get_effective_field_goal_percentage_depending_on_previous_shots_results(
            shot_result=1, number_of_previous_shots_to_check=number_of_previous_shots_to_check)

    def get_effective_field_goal_percentage_after_misses(self, number_of_previous_shots_to_check=1):
        """
        :return: tuple of the EFG% on shots after misses, and the amount of those shots
        :rtype: tuple(float, int)
        """
        return self._get_effective_field_goal_percentage_depending_on_previous_shots_results(
            shot_result=0, number_of_previous_shots_to_check=number_of_previous_shots_to_check)

    @must_have_one_team_wrapper
    def _get_teammates_relevant_shooting_stats(self):
        """
        :return: tuple of:
        The number of field goals made by the players' teammates,
        The number of 3 point field goals made by the players' teammates,
        The number of field goals attempted by the players' teammates
        :rtype: tuple(int, int, int)
        """
        if self.current_team_object is None:
            raise PlayerHasNoTeam('{player_name} has no team (and therefore no teammates) at the moment'.format(
                player_name=self.name))

        if self.stats_dict:
            player_fgm = self.stats_dict["FGM"]
            player_fg3m = self.stats_dict["FG3M"]
            player_fga = self.stats_dict["FGA"]
        else:
            player_fgm = 0
            player_fg3m = 0
            player_fga = 0

        teammates_fgm = self.current_team_object.stats_dict['FGM'] - player_fgm
        teammates_fg3m = self.current_team_object.stats_dict['FG3M'] - player_fg3m
        teammates_fga = self.current_team_object.stats_dict['FGA'] - player_fga
        if teammates_fga == 0:
            return 0, 0, 0
        else:
            return teammates_fgm, teammates_fg3m, teammates_fga

    def _get_teammates_effective_field_goal_percentage(self):
        """
        :return: tuple of the EFG% on shots of teammates, and the amount of those shots
        :rtype: tuple(float, int)
        """
        teammates_fgm, teammates_fg3m, teammates_fga = self._get_teammates_relevant_shooting_stats()

        if teammates_fga == 0:
            return 0, 0
        else:
            return utilsScripts.calculate_effective_field_goal_percent(teammates_fgm, teammates_fg3m,
                                                                       teammates_fga), teammates_fga

    def get_teammates_effective_field_goal_percentage_from_passes(self):
        """
        :return: tuple of the EFG% on shots of teammates after a pass, and the amount of those shots
        :rtype: tuple(float, int)
        """
        return utilsScripts.get_effective_field_goal_percentage_from_multiple_shot_charts(
            self.passing_dashboard.passes_made())

    def _get_teammates_effective_field_goal_percentage_without_passes(self):
        """
        :return: tuple of the FG% on shots of teammates that were not after a pass, and the amount of those shots.
        :rtype: tuple(float, int)
        """
        teammates_fgm, teammates_fg3m, teammates_fga = self._get_teammates_relevant_shooting_stats()
        teammates_fgm_from_player_passes, teammates_fg3m_from_player_passes, teammates_fga_from_player_passes = \
            utilsScripts.get_effective_field_goal_relevant_data_from_multiple_shot_charts(
                self.passing_dashboard.passes_made())

        teammates_fgm_without_player_pass = teammates_fgm - teammates_fgm_from_player_passes
        teammates_fg3m_without_player_pass = teammates_fg3m - teammates_fg3m_from_player_passes
        teammates_fga_without_player_pass = teammates_fga - teammates_fga_from_player_passes
        if teammates_fga_without_player_pass == 0:
            return 0, 0
        else:
            effective_field_goal_percent_without_a_pass = utilsScripts.calculate_effective_field_goal_percent(
                teammates_fgm_without_player_pass,
                teammates_fg3m_without_player_pass,
                teammates_fga_without_player_pass)
            return effective_field_goal_percent_without_a_pass, teammates_fga_without_player_pass

    def get_diff_in_teammates_efg_percentage_on_shots_from_player_passes(self):
        """

        :return: tuple of:
        The diff in EFG% between shots of teammates that were after a pass by him, and ones that were not.
        The amount of the teammates shots.
        :rtype: tuple(float, int)
        """
        teammates_efg_on_shots_after_pass_from_player, teammates_number_of_shots_after_pass_from_player = \
            self.get_teammates_effective_field_goal_percentage_from_passes()
        if teammates_number_of_shots_after_pass_from_player == 0:
            return 0, 0
        else:
            teammates_efg_on_shots_not_after_pass_from_player, teammates_number_of_shots_not_after_pass_from_player = \
                self._get_teammates_effective_field_goal_percentage_without_passes()
            if teammates_number_of_shots_not_after_pass_from_player == 0:
                return 0, 0
            return teammates_efg_on_shots_after_pass_from_player - teammates_efg_on_shots_not_after_pass_from_player, \
                   teammates_number_of_shots_after_pass_from_player

    # noinspection PyPep8Naming
    def get_aPER(self):
        """
        A calculation of the aPER, which is the PER measurement BEFORE normalization.

        :return:
        :rtype: float
        """
        return utilsScripts.get_aPER_from_stat_dict(self.stats_dict, self.current_team_object)

    def print_shooting_info(self):
        """
        Printing all the main relevant info on a player's shooting
        :return:
        :rtype: None
        """

        efg_after_makes = self.get_effective_field_goal_percentage_after_makes
        efg_after_misses = self.get_effective_field_goal_percentage_after_misses
        efg_on_contested = self.get_effective_field_goal_percentage_on_contested_shots_outside_10_feet
        efg_on_uncontested = self.get_effective_field_goal_percentage_on_uncontested_shots_outside_10_feet
        utilsScripts.print_field_goal_percentage_in_a_given_condition(self.name,
                                                                      efg_after_makes,
                                                                      "%EFG after a make")
        utilsScripts.print_field_goal_percentage_in_a_given_condition(self.name,
                                                                      efg_after_misses,
                                                                      "%EFG after a miss")
        utilsScripts.print_field_goal_percentage_in_a_given_condition(self.name,
                                                                      efg_on_contested,
                                                                      "%EFG on contested shot outside 10 feet")
        utilsScripts.print_field_goal_percentage_in_a_given_condition(self.name,
                                                                      efg_on_uncontested,
                                                                      "%EFG on uncontested shot outside 10 feet")
        print('')

    def print_passing_info(self):
        """
        Printing all the main relevant info on a player's passing
        :return:
        :rtype: None
        """
        diff_in_efg = self.get_diff_in_teammates_efg_percentage_on_shots_from_player_passes
        utilsScripts.print_field_goal_percentage_in_a_given_condition(self.name,
                                                                      diff_in_efg,
                                                                      "- change in teammates %EFG "
                                                                      "after a pass from a player")

    def get_most_frequent_passer_to_player(self):
        """
        A dict that represent the passing connection between the player and the player that passes him the ball the most
        :return:
        :rtype: dict
        """
        if not self.passing_dashboard.passes_received():
            print('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_received(), key=lambda x: x["FREQUENCY"])
        return utilsScripts.get_per_game_from_total_stats(most_frequent_assistant_dict)

    def get_most_frequent_receiver_of_player_passes(self):
        """
        A dict that represent the passing connection between the player and the player he passes the ball the most to
        :return:
        :rtype: dict
        """
        if not self.passing_dashboard.passes_received():
            print('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_made(),
                                           key=lambda x: utilsScripts.get_per_game_from_total_stats(x)["AST"])
        return utilsScripts.get_per_game_from_total_stats(most_frequent_assistant_dict)

    def get_most_frequent_assister_to_player(self):
        """
        A dict that represent the passing connection between the player and the player that
        passes him the most assists
        :return:
        :rtype: dict
        """
        if not self.passing_dashboard.passes_received():
            print('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_received(),
                                           key=lambda x: utilsScripts.get_per_game_from_total_stats(x)["AST"])
        return utilsScripts.get_per_game_from_total_stats(most_frequent_assistant_dict)

    def get_most_frequent_receiver_of_player_assists(self):
        """
        A dict that represent the passing connection between the player and the player that
        he passes the most assists to
        :return:
        :rtype: dict
        """
        if not self.passing_dashboard.passes_received():
            print('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_made(), key=lambda x: x["FREQUENCY"])
        return utilsScripts.get_per_game_from_total_stats(most_frequent_assistant_dict)

    def get_team_net_rtg_on_off_court(self):
        """

        :return: The player's current team's net rating when he's ON and OFF the court
        :rtype: tuple(float, float)
        """
        if self.current_team_object is None:
            raise PlayerHasNoTeam('{player_name} has no team (and therefore no teammates) at the moment'.format(
                player_name=self.name))
        team_advanced_stats_with_player_on_court = [x for x in self.current_team_object.on_off_court.on_court() if
                                                    x['VS_PLAYER_ID'] == self.id]
        team_advanced_stats_with_player_off_court = [x for x in self.current_team_object.on_off_court.off_court() if
                                                     x['VS_PLAYER_ID'] == self.id]
        if team_advanced_stats_with_player_off_court and team_advanced_stats_with_player_on_court:
            return team_advanced_stats_with_player_on_court[0]['NET_RATING'], \
                   team_advanced_stats_with_player_off_court[0]['NET_RATING']
        else:
            return 0, 0

    def get_team_net_rtg_on_off_court_diff(self):
        """

        :return:
        :rtype: float
        """
        try:
            on_court_net_rtg, off_court_net_rtg = self.get_team_net_rtg_on_off_court()
        except PlayerHasNoTeam:
            return 0
        return on_court_net_rtg - off_court_net_rtg

    def get_all_time_game_objects(self, initialize_stat_classes=False):
        """

        :param initialize_stat_classes: Whether or not to initialize the stat classes for the game objects
        :type initialize_stat_classes: bool
        :return:
        :rtype: list[NBAGamePlayer]
        """
        player_all_time_game_logs = [game_log for game_log in self.get_all_time_game_logs()]
        player_all_time_game_objects = [gameScripts.NBAGamePlayer(game_log, initialize_stat_classes) for game_log in
                                        player_all_time_game_logs]
        return player_all_time_game_objects

    def get_over_minutes_limit_games_per_36_stats_compared_to_other_games(self, minutes_limit=30):
        """

        :return:
        :rtype: dict[str, dict[str, float]]
        """
        over_limit_game_dicts = [game_log for game_log in self.game_logs.logs() if game_log['MIN'] >= 30]
        under_limit_game_dicts = [game_log for game_log in self.game_logs.logs() if game_log['MIN'] < 30]
        return {
            ('Over %s minutes' % minutes_limit): utilsScripts.join_single_game_stats(over_limit_game_dicts,
                                                                                     per_36=True),
            ('Under %s minutes' % minutes_limit): utilsScripts.join_single_game_stats(under_limit_game_dicts,
                                                                                      per_36=True)}


if __name__ == "__main__":
    players_names_list = [
        # 'rajon_rondo',
        'stephen_curry',
        # 'james_harden',
        # 'lebron_james',
        # 'jr_smith',
        # 'paul_pierce',
        # 'carmelo_anthony'
    ]
    selected_season = '2015-16'
    for player_name in players_names_list:
        nba_player = NBAPlayer(player_name_or_id=player_name, season=selected_season)
        nba_player.get_effective_field_goal_percentage_after_makes(number_of_previous_shots_to_check=7)
        # nba_player.print_passing_info()

        # national_tv_stats = nba_player.get_national_tv_all_time_per_game_stats()
        # not_national_tv_stats = nba_player.get_not_national_tv_all_time_per_game_stats()
        # csv_path = os.path.join(csvs_folder_path,
        #                         '%s_all_time_national_tv_stats_per_36_minutes' % nba_player.name + '.csv')
        # convert_dicts_into_csv([national_tv_stats, not_national_tv_stats], csv_path)
