"""
NBATeam object and necessary imports functions and consts
"""
import pickle
import os
from cached_property import cached_property

import goldsberry
import playerScripts
import leagueScripts
import gameScripts
import utilsScripts
from goldsberry.apiparams import default_season
import generalStatsScripts

teams_id_dict_pickle_path = os.path.join(utilsScripts.pickles_folder_path, "nba_teams_numbers_dict.pickle")
with open(teams_id_dict_pickle_path, 'rb') as file1:
    teams_id_dict = pickle.load(file1)
    """:type : dict"""
teams_name_dict = {v: k for k, v in teams_id_dict.items()}

nba_teams_all_shooters_lineups_dicts_path_regex = os.path.join(utilsScripts.pickles_folder_path,
                                                               'nba_teams_all_shooters_lineups_dicts_{season}.pickle')


class NBATeam(generalStatsScripts.NBAStatObject):
    """
    An object that represent a single nba team in a single season.
    """

    def __init__(self, team_name_or_id, season=default_season, initialize_stat_classes=True,
                 initialize_game_objects=False):
        """
        :param team_name_or_id:
        :type team_name_or_id: int or string
        :return: An NBA team object
        :rtype : NBATeam
        """
        self.team_name_or_id = team_name_or_id
        super(NBATeam, self).__init__(season=season, initialize_stat_classes=initialize_stat_classes,
                                      goldsberry_object_name=self.object_indicator)
        print('Initialize %s team object...' % self.name)
        self.season = season
        if initialize_game_objects:
            # Cache game objects. a is unused
            # noinspection PyUnusedLocal
            a = self.team_regular_season_game_objects

    def __del__(self):
        for player_object in self.current_players_objects:
            del player_object

    @property
    def object_indicator(self):
        return "team"

    @property
    def name(self):
        """

        :return:
        :rtype: str
        """
        if type(self.team_name_or_id) is str:
            return self.team_name_or_id.lower()
        elif type(self.team_name_or_id) is int:
            return teams_name_dict[self.id]
        else:
            raise Exception('Constructor only receives string or integer')

    @property
    def id(self):
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
    def stats_dict(self):
        """

        :return:
        :rtype:
        """
        self._initialize_stat_class_if_not_initialized('season_stats')
        with self.season_stats.object_manager.reinitialize_data_with_new_parameters(MeasureType='Base'):
            return self.season_stats.overall()[0]

    @property
    def first_year(self):
        """

        :return: The first year that the object existed
        :rtype: int
        """
        self._initialize_stat_class_if_not_initialized('year_by_year')
        return int(self.team_info.info()[0]['MIN_YEAR'])

    @property
    def last_year(self):
        """

        :return: The first year that the object existed
        :rtype: int
        """
        self._initialize_stat_class_if_not_initialized('year_by_year')
        return int(self.team_info.info()[0]['MAX_YEAR'])

    @cached_property
    def team_regular_season_game_objects(self):
        """

        :return:
        :rtype: list[gameScripts.NBAGameTeam]
        """
        regular_season_game_objects = []
        for game_number, game_log in enumerate(reversed(self.game_logs.logs())):
            print('Initializing game number %s' % (game_number + 1))
            regular_season_game_objects.append(gameScripts.NBAGameTeam(game_log, initialize_stat_classes=True))
        return regular_season_game_objects

    @cached_property
    def current_league_object(self):
        """

        :return:A generated object for the team that the player is currently playing for
        :rtype: leagueScripts.NBALeague
        """
        return leagueScripts.NBALeague(season=self.season)

    @cached_property
    def current_players_objects(self):
        """

        :return:
        :rtype: list[playerScripts.NBAPlayer]
        """
        return self._generate_current_players_objects(initialize_stat_classes=False)

    def _generate_current_players_objects(self, initialize_stat_classes):
        """
        Returns a list of player objects for players on the team's roster
        :param initialize_stat_classes:
        :type initialize_stat_classes: bool
        :return:
        :rtype: list[playerScripts.NBAPlayer]
        """
        players_objects_list = []
        for player_dict_on_roster in goldsberry.team.roster(team_id=self.id, season=self.season).players():
            player_name = player_dict_on_roster['PLAYER']
            player_id = player_dict_on_roster['PLAYER_ID']
            try:
                nba_player_object = playerScripts.NBAPlayer(player_name_or_id=player_id,
                                                            season=self.season,
                                                            initialize_stat_classes=initialize_stat_classes)
                nba_player_object.current_team_object = self
                players_objects_list.append(nba_player_object)
            except playerScripts.NoSuchPlayer:
                print(
                    "{player_name} was not found in leagues players, even though he's on the team roster".format(
                        player_name=player_name))
            except Exception as e:
                raise e
        return players_objects_list

    def get_filtered_lineup_dicts(self, lineups_list=None, white_list=None, black_list=None):
        """

        :param lineups_list: lineups list to filter valid lineups from. If None, uses all team's lineups from reg season
        :type lineups_list: list[dict]
        :param white_list: player objects white list
        :type white_list: list[playerScripts.NBAPlayer]
        :param black_list: player objects black list
        :type black_list: list[playerScripts.NBAPlayer]
        :return: Filtered dict based on the parameters given
        :rtype: list[dict]
        """
        if not white_list:
            white_list = []
        if not black_list:
            black_list = []

        if not lineups_list:
            lineups_list = self.lineups.lineups()
        return [lineup_dict for lineup_dict in lineups_list if
                utilsScripts.is_lineup_valid(lineup_dict, white_list, black_list)]

    def get_all_shooters_lineup_dicts(self, attempts_limit=50):
        """

        :param attempts_limit:
        :type attempts_limit: int
        :return:
        :rtype: list[dict]
        """
        non_shooter_player_objects = [player_object for player_object in self.current_players_objects
                                      if not player_object.is_three_point_shooter(attempts_limit=attempts_limit)]
        all_shooters_lineup_dicts = self.get_filtered_lineup_dicts(black_list=non_shooter_player_objects)
        return all_shooters_lineup_dicts

    def get_all_time_game_objects(self, initialize_stat_classes=False):
        """

        :param initialize_stat_classes: Whether or not to initialize the stat classes for the game objects
        :type initialize_stat_classes: bool
        :return:
        :rtype: list[NBAGamePlayer]
        """
        player_all_time_game_logs = [game_log for game_log in self.get_all_time_game_logs()]
        player_all_time_game_objects = [gameScripts.NBAGameTeam(game_log, initialize_stat_classes) for game_log in
                                        player_all_time_game_logs]
        return player_all_time_game_objects

    def get_pace(self):
        return self.season_stats.overall()[0]['PACE']

    def get_pace_adjustment(self):
        """

        :return: League's pace divided by team's pace. Used for PER calculation
        :rtype: float
        """
        return self.current_league_object.get_league_average_pace()/self.get_pace()

    def get_assist_percentage(self):
        """

        :return: The portion of the team's field goals wich was assisted
        :rtype: float
        """
        return self.season_stats.overall()[0]['AST_PCT']


if __name__ == "__main__":
    # suns = NBATeam('suns')
    # only_shooters_suns_lineups = suns.get_all_shooters_lineup_dicts()
    # suns_all_shooters_advanced_stats = join_advanced_lineup_dicts(only_shooters_suns_lineups)
    #
    # bobcats = NBATeam('bobcats')
    # only_shooters_bobcats_lineups = bobcats.get_all_shooters_lineup_dicts()
    # bobcats_all_shooters_advanced_stats = join_advanced_lineup_dicts(only_shooters_bobcats_lineups)
    my_season = '2015-16'
    warriors = NBATeam('warriors', season='2015-16')
    all_time_per_game_stats = warriors.get_all_time_per_game_stats()
    print(all_time_per_game_stats)
