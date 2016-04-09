import dateutil.parser
import goldsberry
from goldsberry import apiconvertor


class NBAGame(object):
    def __init__(self, game_dict):
        """
        :return: an object that represent one nba game
        :rtype : An NBA team object
        """
        self.game_dict = game_dict
        self.game_id = self.game_dict['GAME_ID']
        self.team_id = self.game_dict['TEAM_ID']
        # for stat_class in filter(lambda x: not x.startswith('_'), dir(goldsberry.game)):
        #     setattr(self, stat_class, getattr(goldsberry.game, stat_class)(self.game_id))

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

    def is_team_hosting_game(self):
        return goldsberry.game.boxscore_summary(self.game_dict['GAME_ID']).game_summary()[0][
                   'HOME_TEAM_ID'] == self.team_id


class NBAGames(object):
    def __init__(self, season='2015', include_playoffs=False, include_preseason=False):
        """
        returns a list of short dict summaries for every nba game played in history
        :return:
        :rtype:NBAGames object
        """
        games_objects = goldsberry.GameIDs()
        games_objects.reinitialize_data_with_new_parameters(Season=apiconvertor.nba_season(season))
        all_games_after_parse = games_objects.game_list()

        if include_playoffs:
            games_objects.reinitialize_data_with_new_parameters(Season=apiconvertor.nba_season(season),
                                                                SeasonType=apiconvertor.season_type(2))
            playoff_games_objects = games_objects.game_list()
            playoff_games_objects.sort(key=lambda game_dict: game_dict['GAME_ID'])
            all_games_after_parse += playoff_games_objects
        if include_preseason:
            games_objects.reinitialize_data_with_new_parameters(Season=apiconvertor.nba_season(season),
                                                                SeasonType=apiconvertor.season_type(4))
            preseason_games_objects = games_objects.game_list()
            preseason_games_objects.sort(key=lambda game_dict: game_dict['GAME_ID'])
            all_games_after_parse = games_objects.game_list() + all_games_after_parse
        all_games_after_parse.sort(key=lambda game_dict: game_dict['GAME_ID'])
        self.games_objects = [NBAGame(game_after_parse) for game_after_parse in all_games_after_parse]
        """:type : list[NBAGame]"""

    def get_specific_team_home_games(self, team_id):
        return filter(lambda game: game.game_dict['HOME_TEAM_ID'] == team_id, self.games_objects)

    def get_specific_team_away_games(self, team_id):
        return filter(lambda game: game.game_dict['VISITOR_TEAM_ID'] == team_id, self.games_objects)

    def get_specific_team_games(self, team_id):
        all_team_games = self.get_specific_team_home_games(team_id) + self.get_specific_team_away_games(team_id)
        all_team_games.sort(key=lambda game: game.game_dict['GAME_ID'])
        return all_team_games


if __name__ == "__main__":
    games_2015 = NBAGames(include_playoffs=True, include_preseason=False)
    broadcasting_networks = set(map(lambda x: x.get_broadcasting_network(), games_2015.games_objects))
    games_2015.get_specific_team_games(1610612761)
