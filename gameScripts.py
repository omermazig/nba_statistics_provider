"""
All objects that represent an nba game. NBAGame is the basic object.
Also contains necessary imports functions and consts
"""
from functools import cached_property
from nba_api.stats.endpoints import BoxScoreSummaryV2, LeagueGameLog
from nba_api.stats.library.parameters import Season, SeasonTypeAllStar
from pandas import DataFrame
from typing import Optional

import utilsScripts


class NBAGame(utilsScripts.Loggable):
    """
    An object that represent a single nba game.
    """

    def __init__(self, game_df: DataFrame, initialize_stat_classes: bool = False):
        """

        :param game_df:
        :param initialize_stat_classes:
        :return: an object that represent one nba game
        """
        super().__init__()
        self.game_dict = game_df

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

    @staticmethod
    def get_stat_classes_names() -> list[str]:
        """ The stat classes available for the object """
        return [
            'boxscore_summary',
        ]

    @cached_property
    def boxscore_summary(self) -> BoxScoreSummaryV2:
        kwargs = {
            'game_id': self.game_id,
        }
        return utilsScripts.get_stat_class(stat_class_class_object=BoxScoreSummaryV2, **kwargs)

    def initialize_stat_classes(self) -> None:
        """ Initializing all the classes, and setting them under self """
        self.logger.info(f'Initializing stat classes for game {self.game_id} object..')

        for stat_class_name in self.get_stat_classes_names():
            try:
                # This is to force the lru property to actually cache the value.
                getattr(self, stat_class_name)
            except ValueError as e:
                self.logger.warning(f"Couldn't initialize {stat_class_name} - Maybe it didn't exist")
                self.logger.error(e, exc_info=True)

    def get_broadcasting_network(self) -> str:
        return self.boxscore_summary.game_summary()[0]['NATL_TV_BROADCASTER_ABBREVIATION']

    def is_game_on_national_tv(self, broadcasters_list: Optional[list[str]] = None) -> bool:
        if broadcasters_list is None:
            broadcasters_list = ['ESPN',
                                 'TNT',
                                 'ABC',
                                 # 'ESPN 2',
                                 # 'NBA TV'
                                 ]
        return self.get_broadcasting_network() in broadcasters_list

    def is_team_hosting_game(self, team_id: int) -> bool:
        return self.boxscore_summary.game_summary()[0]['HOME_TEAM_ID'] == team_id


class NBAGameTeam(NBAGame):
    """
    An object that represent a single nba game from a team's perspective.
    """

    def __init__(self, game_df, initialize_stat_classes=False):
        super().__init__(game_df, initialize_stat_classes)
        self.team_id = self.game_dict['TEAM_ID']

    def is_home_game(self) -> bool:
        return self.is_team_hosting_game(self.team_id)


class NBAGamePlayer(NBAGame):
    """
    An object that represent a single nba game from a player's perspective.
    """

    def __init__(self, game_df, initialize_stat_classes=False):
        super().__init__(game_df, initialize_stat_classes)
        self.player_id = self.game_dict['Player_ID']


class NBASingleSeasonGames:
    """
    An object that represent a season of nba games
    """

    def __init__(self, season=Season.default, include_playoffs=False, include_preseason=False):
        """
        returns a list of short dict summaries for every nba game played in history
        :return:
        :rtype:NBASingleSeasonGames object
        """
        games_objects = LeagueGameLog(season=season)
        all_games_df = games_objects.league_game_log.get_data_frame()
        if include_playoffs:
            playoff_games_objects = LeagueGameLog(season=season, season_type_all_star=SeasonTypeAllStar.playoffs)
            all_games_df += playoff_games_objects.league_game_log.get_data_frame()
        if include_preseason:
            preseason_games_objects = LeagueGameLog(season=season, season_type_all_star=SeasonTypeAllStar.preseason)
            all_games_df += preseason_games_objects.league_game_log.get_data_frame()

        self.games_objects: list[NBAGame] = [NBAGame(game_dict) for game_dict in all_games_df]

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
