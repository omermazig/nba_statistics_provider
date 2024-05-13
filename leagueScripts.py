"""
All objects that represent a single season of the nba. NBALeague is the basic object.
Also contains necessary imports functions and consts.
"""
import datetime
import os
import pickle
import time
import functools
import glob
import collections
import inspect

import playerScripts
import utilsScripts
import teamScripts
from playersContainerScripts import PlayersContainer
from my_exceptions import NoSuchPlayer, TooMuchPlayers, NoSuchTeam, TooMuchTeams, PlayerHasMoreThenOneTeam, \
    PlayerHasNoTeam
import goldsberry

league_object_pickle_path_regex = os.path.join(utilsScripts.pickles_folder_path, 'league_object_{season}.pickle')


class PlayTypeLeagueAverage(object):
    """
    An object that represent the league average points per possession for every play type
    """

    def __init__(self):
        playtype_classes_names = [stat_class1 for stat_class1 in dir(goldsberry.playtype) if
                                  not stat_class1.startswith('_')]
        for playtype_class_name in playtype_classes_names:
            value = self._get_ppp_league_average_for_specific_play_type(playtype_class_name,
                                                                        'offensive')
            setattr(self, playtype_class_name, value)

    @staticmethod
    def _get_ppp_league_average_for_specific_play_type(playtype_to_search, offensive_or_defensive):
        """

        :param playtype_to_search: play type description
        :type playtype_to_search: str
        :param offensive_or_defensive: 'offensive' ot 'defensive'
        :type offensive_or_defensive: str
        :return: PPP for play type
        :rtype: float
        """
        points_scored = 0
        possessions = 0
        playtype_object = goldsberry.playtype
        specific_playtype_object = getattr(playtype_object, playtype_to_search)(team=True)
        for player_playtype_offensive_dict in getattr(specific_playtype_object, offensive_or_defensive)():
            points_scored += player_playtype_offensive_dict["Points"]
            possessions += player_playtype_offensive_dict["Poss"]

        return points_scored / possessions


class NBALeagues(object):
    """
    Represents multiple accumulated season in the nba.
    """

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
        for cached_season in [league_object_path.strip('.pickle')[-4:] for league_object_path in
                              glob.glob(utilsScripts.pickles_folder_path + '\*league_object_*')]:
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

    def __init__(self, season=goldsberry.apiparams.default_season, initialize_stat_classes=True,
                 initialize_team_objects=False, initialize_player_objects=False, initialize_game_objects=False):
        super().__init__()
        self.season = season
        self.league_object_pickle_path = league_object_pickle_path_regex.format(season=self.season[:4])
        self.team_objects_list = []
        """:type : list[teamScripts.NBATeam]"""
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
            for i, team_id in enumerate(teamScripts.teams_id_dict.values(), start=1):
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
                self.logger.info(f'---------------'
                                 f'Finished {i}/{len(teamScripts.teams_id_dict.values())} of the teams... '
                                 f'---------------')
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
        A list of generated player objects for all of the players for the given season.
        This property is compiled by adding all of the players that are on teams (Initialized under self.team_objects
        int __init__) and the players that are not on teams (Initialized under self._players_not_on_team_objects_list
        in __init__)
        :return:
        :rtype:list[playerScripts.NBAPlayer]
        """
        return self.players_on_teams_objects_list + self._players_not_on_team_objects_list

    def initialize_stat_classes(self):
        """
        Initializing all of the classes in goldsberry.league, and setting them under self
        :return:
        :rtype: None
        """
        self.logger.info('Initializing league stat classes...')
        public_stat_classes_names = [stat_class1 for stat_class1 in dir(goldsberry.league) if
                                     not stat_class1.startswith('_')]

        for stat_class_name in public_stat_classes_names:
            stat_class = getattr(goldsberry.league, stat_class_name)(season=self.season)
            """:type : NbaDataProvider"""
            setattr(self, stat_class_name, stat_class)

    def _initialize_players_not_on_team_objects(self, initialize_game_objects=False):
        """

        :return:
        :rtype: None
        """
        self.logger.info('Initializing players with no current team...')
        players_not_on_team_dicts_list = [player_dict for player_dict in
                                          goldsberry.PlayerList(season=self.season).players() if
                                          not player_dict['TEAM_ID']]
        # noinspection PyTypeChecker
        self._players_not_on_team_objects_list = [
            playerScripts.NBAPlayer(name_or_id=player_dict['PERSON_ID'], season=self.season,
                                    initialize_game_objects=initialize_game_objects) for player_dict in
            players_not_on_team_dicts_list]
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

    def get_league_all_shooters_lineups_dicts(self, attempts_limit=50):
        """
        :param attempts_limit: The number of attempted three's a player has to shot to count as a shooter
        :type attempts_limit: int
        :return: a list of dicts, where every dict represent a lineup where all of it's participants shot more three's
        this season then the attempts_limit
        :rtype: list[dict]
        """
        league_all_shooters_lineups_dicts = []
        for all_shooters_lineups_dict_for_a_team in \
                [team_object.get_all_shooters_lineup_dicts(attempts_limit=attempts_limit) for team_object in
                 self.team_objects_list]:
            league_all_shooters_lineups_dicts += all_shooters_lineups_dict_for_a_team
        return league_all_shooters_lineups_dicts

    def get_league_all_shooters_lineups_stats_per_team(self, attempts_limit=50):
        """

        :param attempts_limit: The number of attempted three's a player has to shot to count as a shooter
        :type attempts_limit: int
        :return:
        :rtype:dict[dict]
        """
        league_all_shooters_lineups_dicts = {}
        teams_all_shooters_lineup_dicts = [
            (team_object.id, team_object.get_all_shooters_lineup_dicts(attempts_limit=attempts_limit)) for
            team_object in self.team_objects_list]
        for team_id, team_all_shooters_lineups_dicts in teams_all_shooters_lineup_dicts:
            team_name = teamScripts.teams_name_dict[team_id]
            league_all_shooters_lineups_dicts[team_name] = utilsScripts.join_advanced_lineup_dicts(
                team_all_shooters_lineups_dicts)
        return league_all_shooters_lineups_dicts

    # noinspection PyPep8Naming
    def get_players_sorted_by_per(self):
        """

        :return:
        :rtype: list[(string, float)]
        """
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

    def get_league_classic_stat_sum(self, stat_key):
        """

        :param stat_key: The stat to check
        :type stat_key: str
        :return: The sum of all 30 teams value for the given stat key
        :rtype: float
        """
        return utilsScripts.get_stat_summation_from_list(self.team_stats_classic.stats(), stat_key)

    def get_league_classic_stat_average(self, stat_key):
        """

        :param stat_key: The stat to check
        :type stat_key: str
        :return: The average value of all 30 teams for the given stat key
        :rtype: float
        """
        return utilsScripts.get_stat_average_from_list(self.team_stats_classic.stats(), stat_key)

    def get_league_ppp(self):
        """

        :return: The league average points per possession. The amount of points an average offensive possession rewards
        the offensive team.
        :rtype: float
        """
        return self.get_league_classic_stat_sum('PTS') / self.get_league_num_of_possessions()

    def get_league_defensive_reb_percentage(self):
        """

        :return: The league's percentage of defensive rebounds out of all rebounds
        :rtype: float
        """
        d_reb = self.get_league_classic_stat_sum('DREB')
        reb = self.get_league_classic_stat_sum('REB')
        return d_reb / reb

    def get_league_assist_factor(self):
        """

        :return:
        :rtype: float
        """
        assists = self.get_league_classic_stat_sum('AST')
        field_goals_made = self.get_league_classic_stat_sum('FGM')
        free_throws_made = self.get_league_classic_stat_sum('FTM')
        return (2 / 3) - (0.5 * (assists / field_goals_made)) / (2 * (field_goals_made / free_throws_made))

    def get_league_foul_factor(self):
        """

        :return:
        :rtype: float
        """
        free_throws_made = self.get_league_classic_stat_sum('FTM')
        free_throws_attempted = self.get_league_classic_stat_sum('FTA')
        personal_fouls = self.get_league_classic_stat_sum('PF')
        ppp = self.get_league_ppp()
        return (free_throws_made / personal_fouls) - (0.44 * (free_throws_attempted / personal_fouls) * ppp)

    def get_league_num_of_possessions(self):
        """

        :return:
        :rtype: float
        """
        offensive_possessions = 0
        for team_stat_dict in self.team_stats_classic.stats():
            offensive_possessions += utilsScripts.get_num_of_possessions_from_stat_dict(team_stat_dict)
        return offensive_possessions

    def get_league_average_pace(self):
        """

        :return:
        :rtype: float
        """
        offensive_possessions = 0
        for team_stat_dict in self.team_stats_classic.stats():
            offensive_possessions += utilsScripts.get_num_of_possessions_from_stat_dict(team_stat_dict)
        minutes_played = self.get_league_classic_stat_sum('MIN')
        return (offensive_possessions / minutes_played) * 48

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
    def get_cached_league_object(season=None):
        """

        :param season:
        :type season: str
        :return:
        :rtype: NBALeague
        """
        if not season:
            season = goldsberry.apiparams.default_season[:4]
        with open(league_object_pickle_path_regex.format(season=season), "rb") as file_to_read:
            player_objects_2015 = pickle.load(file_to_read)
        return player_objects_2015


def main():
    for year in range(2021, 2012, -1):
        try:
            current_league_year = NBALeague.get_cached_league_object(season=str(year))
        except FileNotFoundError:
            current_league_year = None
        # Check if there's a need to update the league's object
        already_in_playoffs_date = datetime.datetime(year + 1, 4, 26)
        if not current_league_year or current_league_year.date < already_in_playoffs_date:
            league_year = NBALeague(initialize_stat_classes=True,
                                    initialize_player_objects=True,
                                    initialize_team_objects=True,
                                    season=goldsberry.apiconvertor.nba_season(year))
            league_year.pickle_league_object()


if __name__ == "__main__":
    main()
