import pickle
import os
import goldsberry
from playerScripts import NBAPlayer
from playerScripts import NoSuchPlayer
from gameScripts import NBAGames
from utilsScripts import join_advanced_lineup_dicts, is_lineup_valid, pickles_folder_path

teams_id_dict_pickle_path = os.path.join(pickles_folder_path, "nba_teams_numbers_dict.pickle")
with open(teams_id_dict_pickle_path, 'rb') as file1:
    teams_id_dict = pickle.load(file1)
    """:type : dict"""

nba_teams_all_shooters_lineups_dicts_path_regex = os.path.join(pickles_folder_path,
                                                               'nba_teams_all_shooters_lineups_dicts_{season}.pickle')


class NBATeam(object):
    def __init__(self, team_name_or_id, season='2015', initialize_stat_classes=True):
        """

        :rtype : An NBA team object
        """
        if type(team_name_or_id) is int:
            self.team_id = team_name_or_id
        elif type(team_name_or_id) is str:
            self.team_id = teams_id_dict[team_name_or_id]
        else:
            raise Exception('Constructor only receives string ot integer')
        self.season = season
        if initialize_stat_classes:
            for stat_class in filter(lambda x: not x.startswith('_'), dir(goldsberry.team)):
                stat_class_function = getattr(goldsberry.team, stat_class)
                if 'season' in stat_class_function.__init__.func_code.co_varnames:
                    setattr(self, stat_class, stat_class_function(team_id=self.team_id, season=self.season))
                else:
                    setattr(self, stat_class, stat_class_function(team_id=self.team_id))
        self.games_summary_dicts = NBAGames(season).get_specific_team_games(self.team_id)
        self.players_objects_list = []
        """:type : list[NBAPlayer]"""

    def __repr__(self):
        teams_name_dict = {v: k for k, v in teams_id_dict.items()}
        return "{team_name} Object".format(team_id=teams_name_dict[self.team_id])

    def initialize_players_objects(self, initialize_stat_classes=True, override=False):
        """
        Fills (If empty) member 'players_objects_list' of class with a list of player objects for players on the roster
        """
        if not override and self.players_objects_list:
            raise Exception('Players_objects_list object is already set')
        else:
            self.players_objects_list = []
            for player_dict in goldsberry.team.roster(team_id=self.team_id, season=self.season).players():
                try:
                    nba_player_object = NBAPlayer(PERSON_ID=player_dict['PLAYER_ID'],
                                                  season=self.season,
                                                  initialize_stat_classes=initialize_stat_classes)
                    self.players_objects_list.append(nba_player_object)
                except NoSuchPlayer:
                    print (
                        "{player_name} was not found in leagues players, even though he's on the team roster".format(
                            player_name=player_dict['PLAYER']))
                except Exception as e:
                    self.players_objects_list = []
                    raise e

    def get_filtered_lineup_dicts(self, white_list=None, black_list=None):
        """

        :param white_list: player objects white list
        :type white_list: list[NBAPlayer]
        :param black_list: player objects black list
        :type black_list: list[NBAPlayer]
        :return: Filtered dict based on the parameters given
        :rtype: list[dict]
        """
        if not white_list:
            white_list = []
        if not black_list:
            black_list = []

        return filter(lambda lineup_dict: is_lineup_valid(lineup_dict, white_list, black_list), self.lineups.lineups())

    def get_all_shooters_lineup_dicts(self, attempts_limit=20):
        if not self.players_objects_list:
            self.initialize_players_objects()

        only_non_shooters_player_objects = [player_object for player_object in self.players_objects_list
                                            if not player_object.is_three_point_shooter(attempts_limit=attempts_limit)]
        all_shooters_lineup_dicts = self.get_filtered_lineup_dicts(black_list=only_non_shooters_player_objects)
        return all_shooters_lineup_dicts


if __name__ == "__main__":
    # suns = NBATeam('suns')
    # only_shooters_suns_lineups = suns.get_all_shooters_lineup_dicts()
    # suns_all_shooters_advanced_stats = join_advanced_lineup_dicts(only_shooters_suns_lineups)
    #
    # bobcats = NBATeam('bobcats')
    # only_shooters_bobcats_lineups = bobcats.get_all_shooters_lineup_dicts()
    # bobcats_all_shooters_advanced_stats = join_advanced_lineup_dicts(only_shooters_bobcats_lineups)
    my_season = 2015
    league_dict = {}
    for team_name, team_id in teams_id_dict.items():
        team_object = NBATeam(team_id)
        only_shooters_team_lineups = team_object.get_all_shooters_lineup_dicts()
        team_all_shooters_advanced_stats = join_advanced_lineup_dicts(only_shooters_team_lineups)
        league_dict[team_name] = (only_shooters_team_lineups, team_all_shooters_advanced_stats)
    with open(nba_teams_all_shooters_lineups_dicts_path_regex.format(season=my_season), 'wb') as file1:
        pickle.dump(league_dict, file1)
