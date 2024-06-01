"""
NBAStatObject object and necessary imports functions and consts
"""
import abc
import webbrowser
from contextlib import contextmanager
from functools import cached_property
from nba_api.stats.endpoints import PlayerDashPtShots, TeamDashPtShots, PlayerGameLogs, TeamGameLogs, TeamDashPtReb, \
    PlayerDashPtReb, TeamDashPtPass, PlayerDashPtPass, ShotChartDetail
from nba_api.stats.library.parameters import SeasonTypePlayoffs, ContextMeasureSimple
from pandas import DataFrame
from typing import Union

import gameScripts
import utilsScripts
from utilsScripts import T
from my_exceptions import NoStatDashboard


class NBAStatObject(abc.ABC, utilsScripts.Loggable):
    """
    An abstract class that gathers functions that uses elements that are common for a number of object,
    like player or team
    """
    def __init__(self, season: str, initialize_stat_classes, initialize_game_objects):
        super().__init__()
        self.season = season
        self._additional_parameters = {}
        self._initialize_stat_classes = initialize_stat_classes
        self._initialize_game_objects = initialize_game_objects
        if self._initialize_stat_classes:
            self.initialize_stat_classes()
        if self._initialize_game_objects:
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

    @contextmanager
    def reinitialize_class_with_new_parameters(self, stat_class_name: str, **kwargs):
        original_stat_class_dict = self.__dict__.pop(stat_class_name, None)
        try:
            self._additional_parameters |= kwargs
            # This assignment is just for re-cacheing
            # noinspection PyUnusedLocal
            new_stat_class = getattr(self, stat_class_name)
            yield
        finally:
            self._additional_parameters = {}
            if original_stat_class_dict:
                self.__dict__[stat_class_name] = original_stat_class_dict
            else:
                self.__dict__.pop(stat_class_name)

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

    def get_stat_classes_names(self) -> list[str]:
        """ The stat classes available for the object """
        return [
            'game_logs',
            'shot_dashboard',
            'rebound_dashboard',
            'passing_dashboard',
            'year_by_year_stats',
            'shot_chart',
        ]

    def get_stat_class(
            self, stat_class_class_object: type[T], custom_filters: list[tuple[str, str, str]] = None, **kwargs
    ) -> T:
        return utilsScripts.get_stat_class(
            stat_class_class_object, custom_filters, **(kwargs | self._additional_parameters)
        )

    @cached_property
    def shot_dashboard(self) -> Union[PlayerDashPtShots, TeamDashPtShots]:
        if int(self.season[:4]) < 2013:
            raise NoStatDashboard(f'No shot dashboard in {self.season[:4]} - Only since 2013')
        kwargs = {
            'team_id': self.id if self._object_indicator == 'team' else 0,
            'season': self.season,
        }
        if self._object_indicator == 'player':
            kwargs['player_id'] = self.id

        stat_class_class_object = PlayerDashPtShots if self._object_indicator == 'player' else TeamDashPtShots
        return self.get_stat_class(stat_class_class_object=stat_class_class_object, **kwargs)

    @cached_property
    def rebound_dashboard(self) -> Union[PlayerDashPtReb, TeamDashPtReb]:
        if int(self.season[:4]) < 2013:
            raise NoStatDashboard(f'No rebound dashboard in {self.season[:4]} - Only since 2013')
        kwargs = {
            'team_id': self.id if self._object_indicator == 'team' else 0,
            'season': self.season,
        }
        if self._object_indicator == 'player':
            kwargs['player_id'] = self.id

        stat_class_class_object = PlayerDashPtReb if self._object_indicator == 'player' else TeamDashPtReb
        return self.get_stat_class(stat_class_class_object=stat_class_class_object, **kwargs)

    @cached_property
    def passing_dashboard(self) -> Union[PlayerDashPtPass, TeamDashPtPass]:
        if int(self.season[:4]) < 2013:
            raise NoStatDashboard(f'No passing dashboard in {self.season[:4]} - Only since 2013')
        kwargs = {
            'team_id': self.id if self._object_indicator == 'team' else 0,
            'season': self.season,
        }
        if self._object_indicator == 'player':
            kwargs['player_id'] = self.id

        stat_class_class_object = PlayerDashPtPass if self._object_indicator == 'player' else TeamDashPtPass
        return self.get_stat_class(stat_class_class_object=stat_class_class_object, **kwargs)

    @cached_property
    def shot_chart(self) -> ShotChartDetail:
        if int(self.season[:4]) < 1996:
            raise NoStatDashboard(f'No shot dashboard in {self.season[:4]} - Only since 2013')
        kwargs = {
            'team_id': self.id if self._object_indicator == "team" else 0,
            'player_id': self.id if self._object_indicator == "player" else 0,
            'season_nullable': self.season,
            # Default value makes it only return FGM, so changed to FGA. Based on - https://stackoverflow.com/a/65628817
            'context_measure_simple': ContextMeasureSimple.fga,
        }
        return self.get_stat_class(stat_class_class_object=ShotChartDetail, **kwargs)

    @cached_property
    def game_logs(self) -> Union[PlayerGameLogs, TeamGameLogs]:
        kwargs = {
            f'{self._object_indicator}_id_nullable': self.id,
            'season_nullable': self.season,
        }
        stat_class_class_object = PlayerGameLogs if self._object_indicator == 'player' else TeamGameLogs
        return self.get_stat_class(stat_class_class_object, **kwargs)

    @cached_property
    @abc.abstractmethod
    def year_by_year_stats(self):
        pass

    @cached_property
    @abc.abstractmethod
    def stats_df(self) -> DataFrame:
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
        player_stat_page_regex = f"https://www.nba.com/stats/{self._object_indicator}/{self.id}"
        return player_stat_page_regex

    @cached_property
    def regular_season_game_objects(self):
        """

        :return:
        :rtype: list[gameScripts.NBAGameTeam]
        """
        regular_season_game_objects = []
        for game_number, game_log in enumerate(reversed(self.game_logs.player_game_logs.get_data_frame())):
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

    def initialize_stat_classes(self) -> None:
        """ Initializing all the classes, and setting them under self """
        self.logger.info('Initializing stat classes for %s object..' % self.name)

        for stat_class_name in self.get_stat_classes_names():
            try:
                # This is to force the lru property to actually cache the value.
                getattr(self, stat_class_name)
            except ValueError as e:
                self.logger.warning(f"Couldn't initialize {stat_class_name} - Maybe it didn't exist in {self.season}")
                self.logger.error(e, exc_info=True)

    def open_web_stat_page(self):
        """

        :return:
        :rtype: None
        """
        webbrowser.open(self._stats_page_url)

    @staticmethod
    def groupby_defender_distance(df):
        """
        Contested - defender within 4 feet
        :return: tuple of the FG% on contested shots, and the amount of those shots.
        :rtype: tuple(float, float)
        """
        # Define a function to categorize close defense distances into two groups
        def distance_group(distance):
            if distance in ['0-2 Feet - Very Tight', '2-4 Feet - Tight']:
                return 'Tight'
            else:
                return 'Open'

        # Apply the function to create a new column 'DISTANCE_GROUP'
        df['DISTANCE_GROUP'] = df['CLOSE_DEF_DIST_RANGE'].apply(distance_group)
        # Group by 'DISTANCE_GROUP' and sum the desired categories
        grouped_df = df.groupby('DISTANCE_GROUP')[['FGM', 'FGA', 'FG3M']].sum()
        return grouped_df

    def get_efg_percentage_on_contested_shots_outside_10_feet(self):
        """
        Contested - defender within 4 feet
        :return: tuple of the FG% on contested shots, and the amount of those shots.
        :rtype: tuple(float, float)
        """
        df = self.shot_dashboard.closest_defender10ft_plus_shooting.get_data_frame()
        return self._get_efg_percentage_of_custom_df(df, self.groupby_defender_distance, "Tight")

    def get_efg_percentage_on_uncontested_shots_outside_10_feet(self):
        """
        Contested - defender within more then 4 feet
        :return: tuple of the FG% on uncontested shots, and the amount of those shots.
        :rtype: tuple(float, float)
        """
        df = self.shot_dashboard.closest_defender10ft_plus_shooting.get_data_frame()
        return self._get_efg_percentage_of_custom_df(df, self.groupby_defender_distance, "Open")

    @staticmethod
    def _get_efg_percentage_of_custom_df(df, groupby_func, key):
        grouped_df = groupby_func(df)
        stats = grouped_df.loc[key]
        field_goal_makes = stats["FGM"]
        field_goal_attempts = stats["FGA"]
        three_pointer_makes = stats["FG3M"]
        efg_percentage = utilsScripts.calculate_efg_percent(
            field_goal_makes,
            three_pointer_makes,
            field_goal_attempts)
        return efg_percentage, field_goal_attempts

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

    def get_all_time_game_logs(self) -> DataFrame:
        """ Returns all time game log df objects (Regardless of defined 'season' param) """
        all_time_game_logs = []
        for year in range(self.first_year, self.last_year + 1):
            for season_type in [SeasonTypePlayoffs.regular, SeasonTypePlayoffs.playoffs]:
                with self.game_logs.object_manager.reinitialize_data_with_new_parameters(
                        Season=utilsScripts.get_season_from_year(year),
                        SeasonType=season_type):
                    logs_by_year_and_season_type = self.game_logs.player_game_logs.get_data_frame()
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
        return utilsScripts.get_num_of_possessions_from_stat_dict(self.stats_df)

    @staticmethod
    def print_field_goal_percentage_in_a_given_condition(name, condition_func, condition_string,
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
        print("{player_name} {condition} - {function_result} : on {number_of_shots} shots".format(
            player_name=name,
            condition=condition_string,
            function_result=function_result,
            number_of_shots=number_of_shots))
