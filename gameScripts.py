"""
All objects that represent an nba game. NBAGame is the basic object.
Also contains necessary imports functions and consts
"""
import goldsberry
from goldsberry import apiconvertor
from goldsberry.apiparams import default_season


class NBAGame(object):
    """
    An object that represent a single nba game.
    """
    def __init__(self, game_dict, initialize_stat_classes=False):
        """

        :param game_dict:
        :type game_dict: dict
        :param initialize_stat_classes:
        :type initialize_stat_classes: bool
        :return: an object that represent one nba game
        :rtype : An NBA game object
        """
        self.game_dict = game_dict

        if 'GAME_ID' in self.game_dict:
            self.game_dict['Game_ID'] = self.game_dict['GAME_ID']
        elif 'Game_ID' in self.game_dict:
            self.game_dict['GAME_ID'] = self.game_dict['Game_ID']
        if 'TEAM_ID' in self.game_dict:
            self.game_dict['Team_ID'] = self.game_dict['TEAM_ID']
        elif 'Team_ID' in self.game_dict:
            self.game_dict['TEAM_ID'] = self.game_dict['Team_ID']

        self.game_id = self.game_dict["GAME_ID"]
        if initialize_stat_classes:
            self.initialize_stat_classes()

    def _initialize_stat_class(self, stat_class_name):
        """

        :param stat_class_name:
        :type stat_class_name: str
        :return:
        :rtype: None
        """
        stat_class = getattr(goldsberry.game, stat_class_name)(gameid=self.game_id)
        """:type : NbaDataProvider"""
        setattr(self, stat_class_name, stat_class)

    def initialize_stat_classes(self):
        """

        :return:
        :rtype: None
        """
        for stat_class_name in [my_stat_class for my_stat_class in dir(goldsberry.game) if
                                not my_stat_class.startswith('_')]:
            self._initialize_stat_class(stat_class_name)

    def get_broadcasting_network(self):
        """

        :return:
        :rtype:str
        """
        relevant_stat_class = 'boxscore_summary'
        if not hasattr(self, relevant_stat_class):
            self._initialize_stat_class(relevant_stat_class)
        return self.boxscore_summary.game_summary()[0]['NATL_TV_BROADCASTER_ABBREVIATION']

    def is_game_on_national_tv(self, broadcasters_list=None):
        """

        :param broadcasters_list:
        :type broadcasters_list:list[str]
        :return:
        :rtype: bool
        """
        if broadcasters_list is None:
            broadcasters_list = ['ESPN',
                                 'TNT',
                                 'ABC',
                                 # 'ESPN 2',
                                 # 'NBA TV'
                                 ]
        return self.get_broadcasting_network() in broadcasters_list

    def is_team_hosting_game(self, team_id):
        """

        :param team_id:
        :type team_id:int
        :return:
        :rtype:bool
        """
        relevant_stat_class = 'boxscore_summary'
        if not hasattr(self, relevant_stat_class):
            self._initialize_stat_class(relevant_stat_class)
        return self.boxscore_summary.game_summary()[0]['HOME_TEAM_ID'] == team_id


class NBAGameTeam(NBAGame):
    """
    An object that represent a single nba game from a team's perspective.
    """
    def __init__(self, game_dict, initialize_stat_classes=False):
        NBAGame.__init__(self, game_dict, initialize_stat_classes=False)
        self.team_id = self.game_dict['TEAM_ID']
        if initialize_stat_classes:
            self.initialize_stat_classes()

    def is_home_game(self):
        """

        :return:
        :rtype:bool
        """
        return self.is_team_hosting_game(self.team_id)

    def _initialize_stat_class(self, stat_class_name):
        """

        :param stat_class_name:
        :type stat_class_name: str
        :return:
        :rtype: None
        """
        stat_class = getattr(goldsberry.game, stat_class_name)(gameid=self.game_id)
        """:type : NbaDataProvider"""
        if hasattr(stat_class, 'team_stats'):
            try:
                stat_dict = [team_stat_dict for team_stat_dict in stat_class.team_stats() if
                             team_stat_dict['TEAM_ID'] == self.team_id][0]
            except IndexError:
                stat_dict = None
            setattr(self, stat_class_name, stat_dict)
        else:
            setattr(self, stat_class_name, stat_class)


class NBAGamePlayer(NBAGame):
    """
    An object that represent a single nba game from a player's perspective.
    """
    def __init__(self, game_dict, initialize_stat_classes=False):
        NBAGame.__init__(self, game_dict, initialize_stat_classes=False)
        self.player_id = self.game_dict['Player_ID']
        if initialize_stat_classes:
            self.initialize_stat_classes()

    def _initialize_stat_class(self, stat_class_name):
        """

        :param stat_class_name:
        :type stat_class_name: str
        :return:
        :rtype: None
        """
        stat_class = getattr(goldsberry.game, stat_class_name)(gameid=self.game_id)
        """:type : NbaDataProvider"""
        if hasattr(stat_class, 'player_stats'):
            try:
                stat_dict = [player_stat_dict for player_stat_dict in stat_class.player_stats() if
                             player_stat_dict['PLAYER_ID'] == self.player_id][0]
            except IndexError:
                stat_dict = None
            setattr(self, stat_class_name, stat_dict)
        else:
            setattr(self, stat_class_name, stat_class)


class NBASingleSeasonGames(object):
    """
    An object that represent a season of nba games
    """
    def __init__(self, season=default_season, include_playoffs=False, include_preseason=False):
        """
        returns a list of short dict summaries for every nba game played in history
        :return:
        :rtype:NBASingleSeasonGames object
        """
        games_objects = goldsberry.GameIDs()
        with games_objects.object_manager.reinitialize_data_with_new_parameters(Season=season):
            all_games_dicts = games_objects.game_list()

        if include_playoffs:
            with games_objects.object_manager.reinitialize_data_with_new_parameters(
                    Season=apiconvertor.nba_season(season),
                    SeasonType=apiconvertor.season_type(2)):
                playoff_games_objects = games_objects.game_list()
            all_games_dicts += playoff_games_objects
        if include_preseason:
            with games_objects.object_manager.reinitialize_data_with_new_parameters(
                    Season=apiconvertor.nba_season(season),
                    SeasonType=apiconvertor.season_type(4)):
                preseason_games_objects = games_objects.game_list()
            all_games_dicts = preseason_games_objects + all_games_dicts
        self.games_objects = [NBAGame(game_dict) for game_dict in all_games_dicts]
        """:type : list[NBAGame]"""

    def get_specific_team_home_games(self, team_id):
        """

        :param team_id:
        :type team_id: int
        :return:
        :rtype: list[NBAGame]
        """
        return [game for game in self.games_objects if game.game_dict['HOME_TEAM_ID'] == team_id]

    def get_specific_team_away_games(self, team_id):
        """

        :param team_id:
        :type team_id: int
        :return:
        :rtype: list[NBAGame]
        """
        return [game for game in self.games_objects if game.game_dict['VISITOR_TEAM_ID'] == team_id]

    def get_specific_team_games(self, team_id):
        """

        :param team_id:
        :type team_id: int
        :return:
        :rtype: list[NBAGame]
        """
        all_team_games = self.get_specific_team_home_games(team_id) + self.get_specific_team_away_games(team_id)
        all_team_games.sort(key=lambda game: game.game_dict['GAME_ID'])
        return all_team_games


if __name__ == "__main__":
    games_2015 = NBASingleSeasonGames(include_playoffs=True, include_preseason=False)
    broadcasting_networks = set([game_object.get_broadcasting_network() for game_object in games_2015.games_objects])
    games_2015.get_specific_team_games(1610612761)
