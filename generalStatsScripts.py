"""
NBAStatObject object and necessary imports functions and consts
"""
import webbrowser
import abc
from cached_property import cached_property

import goldsberry
# import used only for type-hinting
# noinspection PyUnresolvedReferences
from goldsberry.masterclass import NbaDataProvider

import gameScripts
import utilsScripts


class NBAStatObject(utilsScripts.Loggable):
    """
    An abstract class that gathers functions that uses elements that are common for a number of object,
    like player or team
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, season, initialize_stat_classes, initialize_game_objects):
        super().__init__()
        self.season = season
        """:type : str"""
        if initialize_stat_classes:
            self.initialize_stat_classes()
        if initialize_game_objects:
            # Cache game objects. a is unused
            # noinspection PyUnusedLocal
            a = self.regular_season_game_objects

    @property
    @abc.abstractmethod
    def _object_indicator(self):
        """

        :return:
        :rtype: str
        """
        pass

    @property
    @abc.abstractmethod
    def name(self):
        """

        :return:
        :rtype: str
        """
        pass

    @property
    @abc.abstractmethod
    def id(self):
        """

        :return:
        :rtype: str
        """
        pass

    @property
    @abc.abstractmethod
    def first_year(self):
        """

        :return: The first year that the object existed
        :rtype: int
        """
        pass

    @property
    @abc.abstractmethod
    def last_year(self):
        """

        :return: The last year that the object existed
        :rtype: int
        """
        pass

    @cached_property
    @abc.abstractmethod
    def stats_dict(self):
        """

        :return: The last year that the object existed
        :rtype: dict[str, any]
        """
        pass

    @property
    def _stats_page_url(self):
        """
        Om NBA.COM
        :return:
        :rtype: str
        """
        player_stat_page_regex = "http://stats.nba.com/%s/#!/{id}/stats/" % self._object_indicator
        return player_stat_page_regex.format(id=self.id)

    @cached_property
    def regular_season_game_objects(self):
        """

        :return:
        :rtype: list[gameScripts.NBAGameTeam]
        """
        regular_season_game_objects = []
        for game_number, game_log in enumerate(reversed(self.game_logs.logs())):
            self.logger.info('Initializing game number %s' % (game_number + 1))
            # TODO - Make NBAGame specefically NBATeam/NBAPlayer
            regular_season_game_objects.append(gameScripts.NBAGame(game_log, initialize_stat_classes=True))
        return regular_season_game_objects

    def __cmp__(self, other):
        """
        The compare between two NBATeam objects is to check whether they have the same team id And the same season
        :param other:
        :type other: self
        :return:
        :rtype: bool
        """
        return self.id == other.id and self.season == other.season

    def __repr__(self):
        """

        :return:
        :rtype: str
        """
        return "{name} Object".format(name=self.name)

    def _initialize_stat_class(self, stat_class_name):
        goldsberry_object = getattr(goldsberry, self._object_indicator)
        stat_class = getattr(goldsberry_object, stat_class_name)(self.id, self.season)
        """:type : NbaDataProvider"""
        setattr(self, stat_class_name, stat_class)

    def _initialize_stat_class_if_not_initialized(self, stat_class_name):
        """
        Checks whether a stat class is already initialized, and initializes it if not
        :param stat_class_name: stat_class name to potentially initialize
        :type stat_class_name: str
        :return:
        :rtype: None
        """
        if not hasattr(self, stat_class_name):
            self._initialize_stat_class(stat_class_name)

    def initialize_stat_classes(self):
        """
        Initializing all of the classes in goldsberry_object with the id, and setting them under self
        :return:
        :rtype: None
        """
        self.logger.info('Initializing stat classes for %s object..' % self.name)
        goldsberry_object = getattr(goldsberry, self._object_indicator)
        public_stat_classes_names = [stat_class1 for stat_class1 in dir(goldsberry_object) if
                                     not stat_class1.startswith('_')]

        for stat_class_name in public_stat_classes_names:
            try:
                self._initialize_stat_class(stat_class_name)
            except ValueError:
                self.logger.warning("Could not initialize %s - Maybe it wasn't instituted in %s" % (stat_class_name,
                                                                                                    self.season))

    def open_web_stat_page(self):
        """

        :return:
        :rtype: None
        """
        webbrowser.open(self._stats_page_url)

    def get_efg_percentage_on_contested_shots_outside_10_feet(self):
        """
        Contested - defender within 4 feet
        :return: tuple of the FG% on contested shots, and the amount of those shots.
        :rtype: tuple(float, float)
        """
        very_tight_shots_dict = {"FGM": 0, "FGA": 0, "FG3M": 0}
        tight_shots_dict = {"FGM": 0, "FGA": 0, "FG3M": 0}
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
            efg_percentage = utilsScripts.calculate_efg_percent(
                contested_field_goal_makes,
                contested_3_pointer_makes,
                contested_field_goal_attempts)
            return efg_percentage, contested_field_goal_attempts

    def get_efg_percentage_on_uncontested_shots_outside_10_feet(self):
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
            efg_percentage = utilsScripts.calculate_efg_percent(
                uncontested_field_goal_makes,
                uncontested_3_pointer_makes,
                uncontested_field_goal_attempts)
            return efg_percentage, uncontested_field_goal_attempts

    def get_diff_in_efg_percentage_between_uncontested_and_contested_shots_outside_10_feet(self):
        """

        :return: tuple of:
         - The diff in EFG% between uncontested shots and contested shots
         - The % of all shots outside 10 feet that were uncontested.
        :rtype: tuple(float, float)
        """
        efg_on_uncontested_shots_outside_10_feet, number_of_uncontested_shots_outside_10_feet = \
            self.get_efg_percentage_on_uncontested_shots_outside_10_feet()
        if number_of_uncontested_shots_outside_10_feet == 0:
            return 0, 0
        else:
            efg_on_contested_shots_outside_10_feet, number_of_contested_shots_outside_10_feet = \
                self.get_efg_percentage_on_contested_shots_outside_10_feet()
            if number_of_contested_shots_outside_10_feet == 0:
                return 0, 100
            diff_in_efg = efg_on_uncontested_shots_outside_10_feet - efg_on_contested_shots_outside_10_feet
            percentage_of_contested_shots = number_of_uncontested_shots_outside_10_feet / (
                    number_of_uncontested_shots_outside_10_feet + number_of_contested_shots_outside_10_feet)
            return diff_in_efg, percentage_of_contested_shots

    def get_all_time_game_logs(self):
        """
        Returns all time game log dict objects (Regardless of defined 'season' param)
        :return:
        :rtype:list[dict]
        """
        all_time_game_logs = []
        for year in range(self.first_year, self.last_year + 1):
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
        return utilsScripts.join_single_game_stats(self.get_all_time_game_logs(), per_36=per_36)

    def get_all_time_game_objects(self, initialize_stat_classes=False):
        """

        :param initialize_stat_classes: Whether or not to initialize the stat classes for the game objects
        :type initialize_stat_classes: bool
        :return:
        :rtype: list[NBAGame]
        """
        pass

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

    # TODO - Generalize the comparision code to a separate function
    def get_national_tv_all_time_per_36_stats_compared_to_other_games(self):
        """

        :return:
        :rtype:dict[str, dict]
        """
        all_time_national_tv_game_objects, all_time_not_national_tv_game_objects = \
            self.get_national_tv_all_time_game_objects_and_remaining_game_objects()
        all_time_national_tv_game_dicts = [game_object.game_dict for game_object in
                                           all_time_national_tv_game_objects]
        all_time_not_national_tv_game_dicts = [game_object.game_dict for game_object in
                                               all_time_not_national_tv_game_objects]
        return {
            'National TV': utilsScripts.join_single_game_stats(all_time_national_tv_game_dicts, per_36=True),
            'Not National TV': utilsScripts.join_single_game_stats(all_time_not_national_tv_game_dicts,
                                                                   per_36=True)}

    def get_num_of_offensive_possessions(self):
        """

        :return:
        :rtype: float
        """
        return utilsScripts.get_num_of_possessions_from_stat_dict(self.stats_dict)

    def print_field_goal_percentage_in_a_given_condition(self, name, condition_func, condition_string,
                                                         is_percentage_diff=False):
        """

        :param name: Name of the player/team
        :type name: str
        :param condition_func: The function that returns the printed results.
        Have to return a tuple of two floats - The resulted percentage and the number of shots
        :type condition_func: lambda
        :param condition_string: The string that will declare what the numbers meaning is
        :type condition_string: str
        :param is_percentage_diff: Whether the result is an actual percentage or a diff between two percentage values
        :type is_percentage_diff: bool
        :return:
        :rtype: None
        """
        function_result, number_of_shots = condition_func()
        if type(function_result) is float and -1 <= function_result <= 1:
            if is_percentage_diff:
                function_result = "{0:+.2f}%".format(function_result * 100)
            else:
                function_result = "{0:.2f}%".format(function_result * 100)
        self.logger.info("{player_name} {condition} - {function_result} : on {number_of_shots} shots".format(
            player_name=name,
            condition=condition_string,
            function_result=function_result,
            number_of_shots=number_of_shots))
