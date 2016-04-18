import dateutil.parser
import goldsberry
from goldsberry import apiconvertor
from goldsberry.apiparams import default_season


class NBAGame(object):
    def __init__(self, game_dict, initialize_stat_classes=False):
        """

        :param game_dict:
        :type game_dict:dict
        :param initialize_stat_classes:
        :type initialize_stat_classes:bool
        :return: an object that represent one nba game
        :rtype : An NBA team object
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
            public_stat_classes_names = [stat_class1 for stat_class1 in dir(goldsberry.game) if
                                         not stat_class1.startswith('_')]
            for stat_class_name in public_stat_classes_names:
                stat_class = getattr(goldsberry.game, stat_class_name)(self.game_id)
                """:type : NbaDataProvider"""
                setattr(self, stat_class_name, stat_class)

    def get_broadcasting_network(self):
        return goldsberry.game.boxscore_summary(self.game_id).game_summary()[0]['NATL_TV_BROADCASTER_ABBREVIATION']

    def is_game_on_national_tv(self, broadcasters_list=None):
        if broadcasters_list is None:
            broadcasters_list = ['ESPN',
                                 'TNT',
                                 'ABC',
                                 # 'ESPN 2',
                                 # 'NBA TV'
                                 ]
        return self.get_broadcasting_network() in broadcasters_list

    def is_team_hosting_game(self, team_id):
        return goldsberry.game.boxscore_summary(self.game_id).game_summary()[0]['HOME_TEAM_ID'] == team_id


class NBAGameTeam(NBAGame):
    def __init__(self, game_dict, initialize_stat_classes=False):
        NBAGame.__init__(self, game_dict, initialize_stat_classes)
        self.team_id = self.game_dict['TEAM_ID']

    def is_home_game(self):
        self.is_team_hosting_game(self.team_id)


class NBAGamePlayer(NBAGame):
    def __init__(self, game_dict, initialize_stat_classes=False):
        NBAGame.__init__(self, game_dict, initialize_stat_classes)
        self.player_id = self.game_dict['Player_ID']


class NBASingleSeasonGames(object):
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
        return [game for game in self.games_objects if game.game_dict['HOME_TEAM_ID'] == team_id]

    def get_specific_team_away_games(self, team_id):
        return [game for game in self.games_objects if game.game_dict['VISITOR_TEAM_ID'] == team_id]

    def get_specific_team_games(self, team_id):
        all_team_games = self.get_specific_team_home_games(team_id) + self.get_specific_team_away_games(team_id)
        all_team_games.sort(key=lambda game: game.game_dict['GAME_ID'])
        return all_team_games


if __name__ == "__main__":
    games_2015 = NBASingleSeasonGames(include_playoffs=True, include_preseason=False)
    broadcasting_networks = set([game_object.get_broadcasting_network() for game_object in games_2015.games_objects])
    games_2015.get_specific_team_games(1610612761)
