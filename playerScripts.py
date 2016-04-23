from __future__ import print_function
from __future__ import print_function
from __future__ import division
from cached_property import cached_property
import webbrowser

import teamScripts
import gameScripts
import utilsScripts
from my_exceptions import NoSuchPlayer, TooMuchPlayers, PlayerHasNoTeam
import goldsberry

from goldsberry.masterclass import NbaDataProvider

player_stat_page_regex = "http://stats.nba.com/player/#!/{player_id}/stats/"


class NBAPlayer(object):
    # @retry(stop_max_attempt_number=3, wait_fixed=5000,
    #        retry_on_exception=lambda exception: isinstance(exception, ConnectionError))
    def __init__(self, player_name_or_id, season=goldsberry.apiparams.default_season, initialize_stat_classes=True):
        """
        NBA player object
        :param player_name_or_id: can be a player id or full name with an underline ('steph_curry').
        :type player_name_or_id: int or str
        :param season: Season to initialize player's data by
        :type season: str
        :param initialize_stat_classes: Whether to initialize player's stat classes or not (take a little time)
        :type initialize_stat_classes: bool
        """
        self.season = season

        if type(player_name_or_id) is int:
            identifying_key = 'PERSON_ID'
            filter_function = lambda dict1: player_name_or_id == dict1[identifying_key]
        elif type(player_name_or_id) is str:
            identifying_key = 'PLAYERCODE'
            filter_function = lambda dict1: player_name_or_id in dict1[identifying_key]
        else:
            raise Exception('Constructor only receives string or integer')

        filtered_player_dicts_list = goldsberry.PlayerList().players()
        filtered_player_dicts_list = [dict1 for dict1 in filtered_player_dicts_list if filter_function(dict1)]
        number_of_matching_player_dicts = len(filtered_player_dicts_list)
        if number_of_matching_player_dicts == 0:
            raise NoSuchPlayer('There was no player matching the given parameters')
        elif number_of_matching_player_dicts > 1:
            raise TooMuchPlayers('There were more then one player matching the given parameters')
        else:
            self.player_dict = filtered_player_dicts_list[0]
        self.player_id = self.player_dict["PERSON_ID"]
        self.team_id = self.player_dict["TEAM_ID"] if self.player_dict["TEAM_ID"] else None
        self.player_name = self.player_dict["PLAYERCODE"]

        if initialize_stat_classes:
            self.initialize_stat_classes()

    def __repr__(self):
        return "<{player_name} Object>".format(player_name=self.player_name)

    @cached_property
    def current_team_object(self):
        """

        :return:A generated object for the team that the player is currently playing for
        :rtype:teamScripts.NBATeam
        """
        if self.team_id:
            return teamScripts.NBATeam(self.team_id)
        else:
            return None

    @cached_property
    def player_stats_dict(self):
        """
        NOTE: We use the goldsberry originated object of 'career_stats' and not the class's one because we want this
        property to be available even when the player's stat classes are not initialized.
        :return: A dict that represent the player's basic total stats for the given season
        :rtype: dict
        """
        if not hasattr(self, 'career_stats'):
            self._initialize_stat_class('career_stats')
        with self.career_stats.object_manager.reinitialize_data_with_new_parameters(PerMode="Totals"):
            return [stats_dict for stats_dict in self.career_stats.season_totals_regular() if
                    stats_dict['SEASON_ID'] == self.season][0]

    def _initialize_stat_class(self, stat_class_name):
        stat_class = getattr(goldsberry.player, stat_class_name)(self.player_id, self.season)
        """:type : NbaDataProvider"""
        setattr(self, stat_class_name, stat_class)

    def initialize_stat_classes(self):
        """
        Initializing all of the classes in goldsberry.player with the player's id, and setting them under self
        :return:
        :rtype: None
        """
        public_stat_classes_names = [stat_class1 for stat_class1 in dir(goldsberry.player) if
                                     not stat_class1.startswith('_')]

        for stat_class_name in public_stat_classes_names:
            self._initialize_stat_class(stat_class_name)

    def open_player_web_stat_page(self):
        """

        :return:
        :rtype: None
        """
        webbrowser.open(player_stat_page_regex.format(player_id=self.player_id))

    def is_three_point_shooter(self, attempts_limit=50):
        """

        :param attempts_limit: attempts_limit
        :type attempts_limit: int
        :return: Whether or not a player SHOT more threes this season then the attempts_limit
        :rtype : bool
        """
        try:
            return self.player_stats_dict['FG3A'] > attempts_limit
        except IndexError:
            return False

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

    def _get_effective_field_goal_percentage_depending_on_previous_shot_result(self, shot_result):
        """
        :param shot_result: made (1) or missed (2)
        :type shot_result: int
        :return: tuple of the EFG% on shots after specific shot_result and the amount of those shots
        :rtype: tuple(float, int)
        """
        player_fgm = 0
        player_fg3m = 0
        player_fga = 0
        shots_dicts_list = self.shot_chart.chart()
        for i in range(len(shots_dicts_list) - 1):
            if shots_dicts_list[i]['SHOT_MADE_FLAG'] == shot_result:
                # Verifying the shot was in the same game as the last one
                if shots_dicts_list[i]['GAME_ID'] == shots_dicts_list[i + 1]['GAME_ID']:
                    if shots_dicts_list[i + 1]['SHOT_MADE_FLAG']:
                        player_fgm += 1
                        if shots_dicts_list[i + 1]['SHOT_TYPE'] == '3PT Field Goal':
                            player_fg3m += 1
                    player_fga += 1

        if player_fga == 0:
            return 0, 0
        else:
            return utilsScripts.calculate_effective_field_goal_percent(player_fgm, player_fg3m, player_fga), player_fga

    def get_effective_field_goal_percentage_after_makes(self):
        """
        :return: tuple of the EFG% on shots after makes, and the amount of those shots
        :rtype: tuple(float, int)
        """
        return self._get_effective_field_goal_percentage_depending_on_previous_shot_result(1)

    def get_effective_field_goal_percentage_after_misses(self):
        """
        :return: tuple of the EFG% on shots after misses, and the amount of those shots
        :rtype: tuple(float, int)
        """
        return self._get_effective_field_goal_percentage_depending_on_previous_shot_result(0)

    def _get_teammates_relevant_shooting_stats(self):
        """
        :return: tuple of:
        The number of field goals made by the players' teammates,
        The number of 3 point field goals made by the players' teammates,
        The number of field goals attempted by the players' teammates
        :rtype: tuple(int, int, int)
        """
        if self.team_id is None:
            raise PlayerHasNoTeam('{player_name} has no team (and therefore no teammates) at the moment'.format(
                player_name=self.player_name))
        else:
            with self.current_team_object.year_by_year.object_manager.reinitialize_data_with_new_parameters(
                    PerMode="Totals"):
                team_stats_dict = [stats_dict for stats_dict in self.current_team_object.year_by_year.team_stats() if
                                   stats_dict['YEAR'] == self.season]
        if self.player_stats_dict:
            player_fgm = self.player_stats_dict["FGM"]
            player_fg3m = self.player_stats_dict["FG3M"]
            player_fga = self.player_stats_dict["FGA"]
        else:
            player_fgm = 0
            player_fg3m = 0
            player_fga = 0

        teammates_fgm = team_stats_dict[0]['FGM'] - player_fgm
        teammates_fg3m = team_stats_dict[0]['FG3M'] - player_fg3m
        teammates_fga = team_stats_dict[0]['FGA'] - player_fga
        if teammates_fga == 0:
            return 0, 0, 0
        else:
            return teammates_fgm, teammates_fg3m, teammates_fga

    def get_teammates_effective_field_goal_percentage(self):
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
        with self.passing_dashboard.object_manager.reinitialize_data_with_new_parameters(PerMode='Totals'):
            return utilsScripts.get_effective_field_goal_percentage_from_multiple_shot_charts(
                self.passing_dashboard.passes_made())

    def get_teammates_effective_field_goal_percentage_without_passes(self):
        """
        :return: tuple of the FG% on shots of teammates that were not after a pass, and the amount of those shots.
        :rtype: tuple(float, int)
        """
        teammates_fgm, teammates_fg3m, teammates_fga = self._get_teammates_relevant_shooting_stats()
        with self.passing_dashboard.object_manager.reinitialize_data_with_new_parameters(PerMode='Totals'):
            teammates_fgm_from_player_passes, teammates_fg3m_from_player_passes, teammates_fga_from_player_passes = \
                utilsScripts.get_effective_field_goal_relevant_data_from_multiple_shot_charts(
                    self.passing_dashboard.passes_made())

        teammates_fgm_without_player_pass = teammates_fgm - teammates_fgm_from_player_passes
        teammates_fg3m_without_player_pass = teammates_fg3m - teammates_fg3m_from_player_passes
        teammates_fga_without_player_pass = teammates_fga - teammates_fga_from_player_passes
        if teammates_fga_without_player_pass == 0:
            return 0, 0
        else:
            return utilsScripts.calculate_effective_field_goal_percent(teammates_fgm_without_player_pass,
                                                                       teammates_fg3m_without_player_pass,
                                                                       teammates_fga_without_player_pass), \
                   teammates_fga_without_player_pass

    def get_diff_in_teammates_efg_percentage_between_shots_from_passes_by_player_to_other_shots(self):
        """

        :return: tuple of:
        the diff in EFG% between shots of teammates that were after a pass, and ones that were not after a pass,
        and the amount of the teammates shots.
        :rtype: tuple(float, int)
        """
        teammates_efg_on_shots_after_a_pass_from_player, teammates_number_of_shots_after_a_pass_from_player = \
            self.get_teammates_effective_field_goal_percentage_from_passes()
        teammates_efg_on_shots_not_after_a_pass_from_player, teammates_number_of_shots_not_after_a_pass_from_player = \
            self.get_teammates_effective_field_goal_percentage_without_passes()
        if teammates_number_of_shots_after_a_pass_from_player == 0 or teammates_number_of_shots_not_after_a_pass_from_player == 0:
            return 0, 0
        return teammates_efg_on_shots_after_a_pass_from_player - teammates_efg_on_shots_not_after_a_pass_from_player, \
               teammates_number_of_shots_after_a_pass_from_player

    def print_field_goal_percentage_in_a_given_condition(self, condition_func, condition_string,
                                                         is_percentage_diff=False):
        function_result, number_of_shots = condition_func()
        if type(function_result) is float and -1 <= function_result <= 1:
            if is_percentage_diff:
                function_result = "{0:+.2f}%".format(function_result * 100)
            else:
                function_result = "{0:.2f}%".format(function_result * 100)
        print("{player_name} {condition} - {function_result} - on {number_of_shots} shots".format(
            player_name=self.player_name,
            condition=condition_string,
            function_result=function_result,
            number_of_shots=number_of_shots))

    def print_shooting_info(self):
        """
        Printing all the main relevant info on a player's shooting
        :return:
        :rtype: None
        """

        self.print_field_goal_percentage_in_a_given_condition(self.get_effective_field_goal_percentage_after_makes,
                                                              "%FG after a make")
        self.print_field_goal_percentage_in_a_given_condition(self.get_effective_field_goal_percentage_after_misses,
                                                              "%FG after a miss")
        # self.print_field_goal_percentage_in_a_given_condition(self.get_average_defender_distance_on_makes,
        #                                                       "closest defender's average distance (in feets) on makes")
        # self.print_field_goal_percentage_in_a_given_condition(self.get_average_defender_distance_on_misses,
        #                                                       "closest defender's average distance (in feets) on misses")
        # self.print_field_goal_percentage_in_a_given_condition(self.get_average_defender_distance_after_makes,
        #                                                       "closest defender's average distance (in feets) after a make")
        # self.print_field_goal_percentage_in_a_given_condition(self.get_average_defender_distance_after_misses,
        #                                                       "closest defender's average distance (in feets) after a miss")
        self.print_field_goal_percentage_in_a_given_condition(
            self.get_effective_field_goal_percentage_on_contested_shots_outside_10_feet,
            "%EFG on contested shot outside 10 feet")
        self.print_field_goal_percentage_in_a_given_condition(
            self.get_effective_field_goal_percentage_on_uncontested_shots_outside_10_feet,
            "%EFG on uncontested shot outside 10 feet")
        print('')

    def print_passing_info(self):
        """
        Printing all the main relevant info on a player's passing
        :return:
        :rtype: None
        """
        self.print_field_goal_percentage_in_a_given_condition(
            self.get_diff_in_teammates_efg_percentage_between_shots_from_passes_by_player_to_other_shots,
            "- change in teammates %EFG after a pass from a player")

    def get_most_frequent_passer_to_player(self):
        """
        A dict that represent the passing connection between the player and the player that passes him the ball the most
        :return:
        :rtype: dict
        """
        if not self.passing_dashboard.passes_received():
            print('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.player_name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_received(), key=lambda x: x["FREQUENCY"])
        return most_frequent_assistant_dict

    def get_most_frequent_receiver_from_player_passes(self):
        """
        A dict that represent the passing connection between the player and the player he passes the ball the most to
        :return:
        :rtype: dict
        """
        if not self.passing_dashboard.passes_received():
            print('{player_name} does not have any FG from passes. returning None...'.format(
                player_name=self.player_name))
            return None
        most_frequent_assistant_dict = max(self.passing_dashboard.passes_made(), key=lambda x: x["FREQUENCY"])
        return most_frequent_assistant_dict

    def get_team_net_rtg_on_off_court(self):
        """

        :return: The player's current team's net rating when he's ON and OFF the court
        :rtype: tuple(float, float)
        """
        if self.team_id is None:
            return 0, 0
        team_advanced_stats_with_player_on_court = [x for x in self.current_team_object.on_off_court.on_court() if
                                                    x['VS_PLAYER_ID'] == self.player_id]
        team_advanced_stats_with_player_off_court = [x for x in self.current_team_object.on_off_court.off_court() if
                                                     x['VS_PLAYER_ID'] == self.player_id]
        if [] in [team_advanced_stats_with_player_off_court, team_advanced_stats_with_player_on_court]:
            return 0, 0
        return team_advanced_stats_with_player_on_court[0]['NET_RATING'], team_advanced_stats_with_player_off_court[0][
            'NET_RATING']

    def get_team_net_rtg_on_off_court_diff(self):
        """

        :return:
        :rtype: float
        """
        on_court_net_rtg, off_court_net_rtg = self.get_team_net_rtg_on_off_court()
        return on_court_net_rtg - off_court_net_rtg

    def get_all_time_game_logs(self):
        """
        Returns all time game log dict objects for a player (Regardless of player's defined season)
        :return:
        :rtype:list[dict]
        """
        all_time_game_logs = []
        for year in range(int(self.player_dict['FROM_YEAR']), int(self.player_dict['TO_YEAR']) + 1):
            for season_type in [1, 2]:
                with self.game_logs.object_manager.reinitialize_data_with_new_parameters(
                        Season=goldsberry.apiconvertor.nba_season(year),
                        SeasonType=goldsberry.apiconvertor.season_type(
                            season_type)):
                    logs_by_year_and_season_type = self.game_logs.logs()
                    logs_by_year_and_season_type.reverse()
                    all_time_game_logs += logs_by_year_and_season_type
        return all_time_game_logs

    def get_all_time_per_game_stats(self, per_36=False):
        """

        :param per_36: Get per 36 stats oppose to per game stats
        :type per_36: bool
        :return:
        :rtype: dict
        """
        return utilsScripts.join_player_single_game_stats(self.get_all_time_game_logs(), per_36=per_36)

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

    def get_national_tv_all_time_game_objects_and_remaining_game_objects(self):
        """

        :return:
        :rtype:tuple(list[dict], list[dict])
        """
        all_time_game_objects = self.get_all_time_game_objects()
        all_time_national_tv_game_objects = []
        all_time_not_national_tv_game_objects = []
        for game_object in all_time_game_objects:
            if game_object.is_game_on_national_tv():
                all_time_national_tv_game_objects.append(game_object)
            else:
                all_time_not_national_tv_game_objects.append(game_object)
        return all_time_national_tv_game_objects, all_time_not_national_tv_game_objects

    def get_national_tv_all_time_per_36_stats_compared_to_other_games(self):
        """

        :return:
        :rtype:dict[str, dict]
        """
        all_time_national_tv_game_objects, all_time_not_national_tv_game_objects = \
            self.get_national_tv_all_time_game_objects_and_remaining_game_objects()
        all_time_national_tv_game_dicts = [game_object.game_dict for game_object in all_time_national_tv_game_objects]
        all_time_not_national_tv_game_dicts = [game_object.game_dict for game_object in
                                               all_time_not_national_tv_game_objects]
        return {'National TV': utilsScripts.join_player_single_game_stats(all_time_national_tv_game_dicts, per_36=True),
                'Not National TV': utilsScripts.join_player_single_game_stats(all_time_not_national_tv_game_dicts,
                                                                              per_36=True)}

    def get_effective_field_goal_percentage_on_contested_shots_outside_10_feet(self):
        """
        Contested - defender within 4 feet
        :return: tuple of the FG% on contested shots, and the amount of those shots.
        :rtype: tuple(float, float)
        """
        very_tight_shots_dict = {"FGM": 0, "FGA": 0, "FG3M": 0}
        tight_shots_dict = {"FGM": 0, "FGA": 0, "FG3M": 0}
        with self.shot_dashboard.object_manager.reinitialize_data_with_new_parameters(PerMode='Totals'):
            for dict_to_match in self.shot_dashboard.closest_defender_10ft():
                if dict_to_match['CLOSE_DEF_DIST_RANGE'] == '0-2 Feet - Very Tight':
                    very_tight_shots_dict = dict_to_match
                elif dict_to_match['CLOSE_DEF_DIST_RANGE'] == '2-4 Feet - Tight':
                    tight_shots_dict = dict_to_match

        contested_field_goal_makes = very_tight_shots_dict["FGM"] + tight_shots_dict["FGM"]
        contested_field_goal_attempts = very_tight_shots_dict["FGA"] + tight_shots_dict["FGA"]
        contested_3_pointer_makes = very_tight_shots_dict["FG3M"] + tight_shots_dict["FG3M"]
        if contested_field_goal_attempts == 0:
            return 0, 0
        else:
            effective_field_goal_percentage = utilsScripts.calculate_effective_field_goal_percent(
                contested_field_goal_makes,
                contested_3_pointer_makes,
                contested_field_goal_attempts)
            return effective_field_goal_percentage, contested_field_goal_attempts

    def get_effective_field_goal_percentage_on_uncontested_shots_outside_10_feet(self):
        """
        Contested - defender within more then 4 feet
        :return: tuple of the FG% on uncontested shots, and the amount of those shots.
        :rtype: tuple(float, float)
        """
        open_shots_dict = {"FGM": 0, "FGA": 0, "FG3M": 0}
        wide_open_shots_dict = {"FGM": 0, "FGA": 0, "FG3M": 0}
        for dict_to_match in self.shot_dashboard.closest_defender_10ft():
            if dict_to_match['CLOSE_DEF_DIST_RANGE'] == '4-6 Feet - Open':
                open_shots_dict = dict_to_match
            elif dict_to_match['CLOSE_DEF_DIST_RANGE'] == '6+ Feet - Wide Open':
                wide_open_shots_dict = dict_to_match

        uncontested_field_goal_makes = open_shots_dict["FGM"] + wide_open_shots_dict["FGM"]
        uncontested_field_goal_attempts = open_shots_dict["FGA"] + wide_open_shots_dict["FGA"]
        uncontested_3_pointer_makes = open_shots_dict["FG3M"] + wide_open_shots_dict["FG3M"]
        if uncontested_field_goal_attempts == 0:
            return 0, 0
        else:
            effective_field_goal_percentage = utilsScripts.calculate_effective_field_goal_percent(
                uncontested_field_goal_makes,
                uncontested_3_pointer_makes,
                uncontested_field_goal_attempts)
            return effective_field_goal_percentage, uncontested_field_goal_attempts


if __name__ == "__main__":
    players_names_list = [
        'rajon_rondo',
        'stephen_curry',
        'james_harden',
        'lebron_james',
        'jr_smith',
        'paul_pierce',
        'carmelo_anthony',
    ]
    selected_season = 2015
    for player_name in players_names_list:
        nba_player = NBAPlayer(player_name_or_id=player_name)
        b = nba_player.shot_dashboard.overall()
        a = nba_player.get_all_time_per_game_stats()
        nba_player.print_passing_info()

        # national_tv_stats = nba_player.get_national_tv_all_time_per_game_stats()
        # not_national_tv_stats = nba_player.get_not_national_tv_all_time_per_game_stats()
        # csv_path = os.path.join(csvs_folder_path,
        #                         '%s_all_time_national_tv_stats_per_36_minutes' % nba_player.player_name + '.csv')
        # convert_dicts_into_csv([national_tv_stats, not_national_tv_stats], csv_path)
