"""
All objects that represent a single season of the nba. NBALeague is the basic object.
Also contains necessary imports functions and consts.
"""
import collections
import datetime
import functools
import glob
import inspect
import os
import pickle
import pandas as pd
import tqdm

from contextlib import contextmanager
from functools import cached_property
from nba_api.stats.endpoints import CommonAllPlayers, LeagueDashTeamStats, SynergyPlayTypes
from nba_api.stats.library.parameters import PlayType, Season, SeasonYear, TypeGroupingNullable, \
    MeasureTypeDetailedDefense
from typing import Literal

from pandas import DataFrame

import playerScripts
import teamScripts
import utilsScripts
from my_exceptions import NoSuchTeam, TooMuchTeams, NoStatDashboard
from playersContainerScripts import PlayersContainer

league_object_pickle_path_regex = os.path.join(utilsScripts.pickles_folder_path, 'league_object_{season}.pickle')


class CustomUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        caller_module = inspect.currentframe().f_back.f_globals['__name__']
        if module == "__main__":
            module = caller_module.split('.')[0]
        return super().find_class(module, name)


class PlayTypeLeagueAverage:
    """
    An object that represent the league average points per possession for every play type
    """

    def __init__(self, season: str = Season.current_season):
        playtype_classes_names = [
            stat_class1 for stat_class1 in dir(PlayType)
            if not (stat_class1.startswith('_') or stat_class1 == "default")
        ]
        for playtype_class_name in playtype_classes_names:
            value = self._get_ppp_league_average_for_specific_play_type(playtype_class_name, 'offensive', season)
            setattr(self, playtype_class_name, value)

    @staticmethod
    def _get_ppp_league_average_for_specific_play_type(
            playtype_to_search: str, offensive_or_defensive: Literal['offensive', 'defensive'], season: str
    ) -> float:
        """

        :param playtype_to_search: play type description
        :param offensive_or_defensive: 'offensive' ot 'defensive'
        :param season: The season to calculate
        :return: PPP for play type
        """
        specific_playtype_df = SynergyPlayTypes(
            type_grouping_nullable=getattr(TypeGroupingNullable, offensive_or_defensive),
            play_type_nullable=getattr(PlayType, playtype_to_search),
            season=season
        ).synergy_play_type.get_data_frame()
        sums = specific_playtype_df[["PTS", "POSS"]].sum(axis=0)
        return sums["PTS"] / sums["POSS"]


class NBALeagues(object):
    """
    Represents multiple accumulated season in the nba.
    """
    # TODO - Fix

    def __init__(self, league_objects=None):
        """
        An object that represent multiple league objects from different years
        :param league_objects:
        :type league_objects: list[NBALeague]
        """
        self.league_objects_list = league_objects if isinstance(league_objects, list) else []
        for func_name, func in [i for i in inspect.getmembers(NBALeague, predicate=inspect.isfunction) if
                                not i[0].startswith('get')]:
            setattr(self, 'get_%s_results_for_all_league_objects' % func_name,
                    functools.partial(self.get_function_result_for_all_league_objects, func=func))

    def append_all_cached_league_objects(self):
        """

        :return:
        :rtype: None
        """
        for cached_season in utilsScripts.get_all_seasons_of_pickle_files():
            self.league_objects_list.append(NBALeague.get_cached_league_object(cached_season))

    def get_function_result_for_all_league_objects(self, func, **kwargs):
        """
        Receives a function and it's params, runs it with every league's object in the class as 'self',
        and returns all the results as an ordered dict
        :param func: function to run on all league objects that the class possesses.
        :type func: lambda
        :param kwargs: The parameters of the function.
        BE CAREFUL - THE FUNCTION WILL NOT THROW IF WRONG PARAMETERS ARE PASSED
        :type kwargs: dict
        :return:
        :rtype: None
        """
        passed_function_results_by_seasons_ordered_dict = collections.OrderedDict()
        for league_object in self.league_objects_list:
            passed_function_results_by_seasons_ordered_dict[league_object.season] = func(self=league_object, **kwargs)
        return passed_function_results_by_seasons_ordered_dict


class NBALeague(utilsScripts.Loggable, PlayersContainer):
    """
    An object that represent a single nba season.
    """

    def __init__(self, season=Season.current_season, initialize_stat_classes=True,
                 initialize_team_objects=False, initialize_player_objects=False, initialize_game_objects=False):
        super().__init__()
        self.season = season
        self._additional_parameters = {}
        self.league_object_pickle_path = league_object_pickle_path_regex.format(season=self.season[:4])
        self.team_objects_list: list[teamScripts.NBATeam] = []
        self._players_not_on_team_objects_list = []
        if initialize_stat_classes:
            self.initialize_stat_classes()
            self.logger.info('Initializing league playtypes...')
            try:
                self.playtype = PlayTypeLeagueAverage()
            except Exception as e:
                self.logger.warning("Couldn't initialize playtype data - %s" % e)
        # Warning - Takes a LONG time - A few hours
        if initialize_team_objects:
            for team_id in tqdm.tqdm(teamScripts.teams_id_dict.values(), desc="Teams Completed"):
                team_object = teamScripts.NBATeam(team_id, season=self.season,
                                                  initialize_game_objects=initialize_game_objects)
                team_object.current_league_object = self
                # Cache player_stats_dict objects. a is unused
                # noinspection PyUnusedLocal
                a = team_object.stats_df
                if initialize_player_objects:
                    for player_object in team_object.current_players_objects:
                        player_object.initialize_stat_classes()
                        # Cache player_stats_dict objects. a is unused
                        # noinspection PyUnusedLocal
                        a = player_object.stats_df
                        if initialize_game_objects:
                            self.logger.info('Initializing players game objects for %s object..' % player_object.name)
                            # Cache game objects. a is unused
                            # noinspection PyUnusedLocal
                            a = player_object.regular_season_game_objects
                self.team_objects_list.append(team_object)
        if initialize_player_objects:
            self._initialize_players_not_on_team_objects(initialize_game_objects=initialize_game_objects)

        self.date = datetime.datetime.now()

    @property
    def players_on_teams_objects_list(self):
        """

        :return: A list if player objects for all the players which are on teams
        :rtype: list[playerScripts.NBAPlayer]
        """
        players_on_teams_objects_list = []
        for team_object in self.team_objects_list:
            players_on_teams_objects_list += team_object.current_players_objects
        return players_on_teams_objects_list

    @property
    def current_players_objects(self):
        """
        A list of generated player objects for all the players for the given season.
        This property is compiled by adding all the players that are on teams (Initialized under self.team_objects
        int __init__) and the players that are not on teams (Initialized under self._players_not_on_team_objects_list
        in __init__)
        :return:
        :rtype:list[playerScripts.NBAPlayer]
        """
        return self.players_on_teams_objects_list + self._players_not_on_team_objects_list

    @staticmethod
    def get_stat_classes_names() -> list[str]:
        """ The stat classes available for the object """
        return [
            'team_stats_classic',
        ]

    def get_stat_class(self, stat_class_class_object: type[utilsScripts.T], **kwargs) -> utilsScripts.T:
        return utilsScripts.get_stat_class(stat_class_class_object, **(kwargs | self._additional_parameters))

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
                self.__dict__.pop(stat_class_name, None)

    @cached_property
    def team_stats_classic(self) -> LeagueDashTeamStats:
        if int(self.season[:4]) < 1996:
            raise NoStatDashboard(f'No team classic stats in {self.season[:4]} - Only since 1996')
        kwargs = {
            'season': self.season,
        }
        return self.get_stat_class(stat_class_class_object=LeagueDashTeamStats, **kwargs)

    def initialize_stat_classes(self) -> None:
        """ Initializing all the classes, and setting them under self """
        self.logger.info(f'Initializing stat classes for league {self.season} object..')

        for stat_class_name in self.get_stat_classes_names():
            try:
                # This is to force the lru property to actually cache the value.
                getattr(self, stat_class_name)
            except ValueError as e:
                self.logger.warning(f"Couldn't initialize {stat_class_name} - Maybe it didn't exist in {self.season}")
                self.logger.error(e, exc_info=True)

    def _initialize_players_not_on_team_objects(self, initialize_game_objects: bool = False) -> None:
        self.logger.info('Initializing players with no current team...')
        players = CommonAllPlayers(season=self.season, is_only_current_season=1).common_all_players.get_data_frame()
        players_not_on_team = players[players['ROSTERSTATUS'] == 0]
        self._players_not_on_team_objects_list = [
            playerScripts.NBAPlayer(player_id, self.season, initialize_game_objects)
            for player_id in players_not_on_team['PERSON_ID']
        ]
        for player_object in self._players_not_on_team_objects_list:
            # Cache player_stats_dict objects. a is unused
            # noinspection PyUnusedLocal
            a = player_object.stats_df

    def get_team_object_by_name(self, team_name):
        """
        Doesn't create a new object - Just finds and takes it from self.team_objects_list
        Can accept part of the name - uses __contains__ to find the right team
        Has to be singular - will not return 2 teams
        :param team_name: The desired team's name or part of it
        :type team_name: str
        :return: The desired team's object
        :rtype: NBATeam
        """
        filtered_team_objects_list = [team_object for team_object in self.team_objects_list if
                                      team_name in team_object.name]
        filtered_team_objects_list_length = len(filtered_team_objects_list)
        if filtered_team_objects_list_length == 0:
            raise NoSuchTeam('There was no team matching the given name')
        elif filtered_team_objects_list_length > 1:
            raise TooMuchTeams('There were more then one team matching the given name')
        else:
            return filtered_team_objects_list[0]

    def get_league_all_shooters_lineups(self, attempts_limit: int = 50) -> DataFrame:
        """
        :param attempts_limit: The number of attempted three's a player has to shot to count as a shooter
        :return: a list of dicts, where every dict represent a lineup where all of its participants shot more three's
        this season than the attempts_limit
        """
        league_all_shooters_lineups_dfs = []
        for team_object in self.team_objects_list:
            team_all_shooters_lineups_dfs = team_object.get_all_shooters_lineups_df(attempts_limit=attempts_limit)
            league_all_shooters_lineups_dfs.append(team_all_shooters_lineups_dfs)
        league_all_shooters_lineups_df = pd.concat(league_all_shooters_lineups_dfs, ignore_index=True)
        return league_all_shooters_lineups_df.sort_values(by=['MIN'], ascending=False)

    def get_league_all_shooters_lineups_stats_per_team(self, attempts_limit: int = 50) -> DataFrame:
        """

        :param attempts_limit: The number of attempted three's a player has to shot to count as a shooter
        :return: The cumulative advanced stats for the all shooters lineup, for each team
        """
        teams_all_shooters_lineup_dicts = {
            team_object.name:
                utilsScripts.join_advanced_lineup_df(team_object.get_all_shooters_lineups_df(attempts_limit))
            for team_object in self.team_objects_list
        }
        df = pd.concat(teams_all_shooters_lineup_dicts, names=['Team'])
        df = df.reset_index(level=0)
        return df

    # noinspection PyPep8Naming
    def get_players_sorted_by_per(self):
        """

        :return:
        :rtype: list[(string, float)]
        """
        # TODO - Fix
        self.logger.info('Getting aPER data...')
        players_name_and_result = []
        aPer_sum = 0
        # Getting qualifying players for stat - players with a team that are on pace to play at least 500 minutes
        qualifying_players = [p for p in self.players_on_teams_objects_list if p.stats_df and
                              p.is_player_over_projected_minutes_limit(minutes_limit=500)]
        num_of_players_on_teams = len(qualifying_players)

        for i, my_player_object in enumerate(qualifying_players, start=1):
            self.logger.info('Player %s/%s' % (i, num_of_players_on_teams))
            aPER = my_player_object.get_aPER()
            aPer_sum += aPER
            players_name_and_result.append((my_player_object.name, aPER))

        self.logger.info('Normalizing aPER to PER on list...')
        aPer_average = aPer_sum / num_of_players_on_teams
        for i in range(len(players_name_and_result)):
            per = players_name_and_result[i][1] * (15 / aPer_average)
            players_name_and_result[i] = (players_name_and_result[i][0], per)

        self.logger.info('Sorting...')
        players_name_and_result.sort(key=lambda x: x[1], reverse=True)
        return players_name_and_result

    def get_league_classic_stat_sum(self, stat_key: str) -> float:
        """

        :param stat_key: The stat to check
        :return: The sum of all 30 teams value for the given stat key
        """
        return self.team_stats_classic.league_dash_team_stats.get_data_frame()[stat_key].sum().item()

    def get_league_classic_stat_average(self, stat_key):
        """

        :param stat_key: The stat to check
        :type stat_key: str
        :return: The average value of all 30 teams for the given stat key
        :rtype: float
        """
        return utilsScripts.get_stat_average_from_list(self.team_stats_classic.league_dash_team_stats(), stat_key)

    def get_league_ppp(self):
        """

        :return: The league average points per possession. The amount of points an average offensive possession rewards
        the offensive team.
        :rtype: float
        """
        return self.get_league_classic_stat_sum('PTS') / self.get_league_num_of_possessions()

    def get_league_defensive_reb_percentage(self) -> float:
        """ Gets the league's percentage of defensive rebounds out of all rebounds """
        d_reb = self.get_league_classic_stat_sum('DREB')
        reb = self.get_league_classic_stat_sum('REB')
        return d_reb / reb

    def get_league_assist_factor(self) -> float:
        assists = self.get_league_classic_stat_sum('AST')
        field_goals_made = self.get_league_classic_stat_sum('FGM')
        free_throws_made = self.get_league_classic_stat_sum('FTM')
        return (2 / 3) - (0.5 * (assists / field_goals_made)) / (2 * (field_goals_made / free_throws_made))

    def get_league_foul_factor(self) -> float:
        free_throws_made = self.get_league_classic_stat_sum('FTM')
        free_throws_attempted = self.get_league_classic_stat_sum('FTA')
        personal_fouls = self.get_league_classic_stat_sum('PF')
        ppp = self.get_league_ppp()
        return (free_throws_made / personal_fouls) - (0.44 * (free_throws_attempted / personal_fouls) * ppp)

    def get_league_num_of_possessions(self) -> int:
        pace_df = self.get_league_pace_info()
        return int(pace_df["POSS"].sum())

    def get_league_pace_info(self) -> DataFrame:
        with self.reinitialize_class_with_new_parameters(
                'team_stats_classic', measure_type_detailed_defense=MeasureTypeDetailedDefense.advanced
        ):
            df = self.team_stats_classic.league_dash_team_stats.get_data_frame()
        pace_df = df[['TEAM_ID', 'POSS', 'MIN']].copy()
        pace_df['PACE'] = (pace_df["POSS"]/pace_df["MIN"]) * 48
        return pace_df

    def print_league_playtype_point_per_possession(self):
        """

        :return:
        :rtype: None
        """
        for k, v in self.playtype.__dict__.items():
            print('{play_type_to_print} - {ppp_to_print:.2f}'.format(play_type_to_print=k, ppp_to_print=v))

    def pickle_league_object(self):
        """
        Caching self object using pickle, so we don't have to create it every time (Take a LONG time)
        :return:
        :rtype: None
        """
        os.makedirs(utilsScripts.pickles_folder_path, exist_ok=True)
        with open(self.league_object_pickle_path, 'wb') as file_to_write_to:
            self.logger.info('Updating pickle...')
            pickle.dump(self, file_to_write_to)

    @staticmethod
    def get_cached_league_object(season: str = Season.default) -> 'NBALeague':
        """ Retrieve a cached NBALeague object for a specific season """
        pickle_path = league_object_pickle_path_regex.format(season=season)
        if not os.path.exists(pickle_path):
            raise FileNotFoundError(f"Pickle file not found: {pickle_path}")
        with open(pickle_path, "rb") as file_to_read:
            return CustomUnpickler(file_to_read).load()


def main():
    for year in range(SeasonYear.current_season_year, 2012, -1):
        try:
            current_league_year = NBALeague.get_cached_league_object(season=utilsScripts.get_season_from_year(year))
        except FileNotFoundError:
            current_league_year = None
        # Check if there's a need to update the league's object
        already_in_playoffs_date = datetime.datetime(year + 1, 4, 26)
        if not current_league_year or current_league_year.date < already_in_playoffs_date:
            league_year = NBALeague(initialize_stat_classes=True,
                                    initialize_player_objects=True,
                                    initialize_team_objects=True,
                                    season=utilsScripts.get_season_from_year(year))
            league_year.pickle_league_object()


if __name__ == "__main__":
    main()
