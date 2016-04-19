import pickle
import os
import goldsberry
import playerScripts
from gameScripts import NBAGameTeam
from utilsScripts import join_advanced_lineup_dicts, is_lineup_valid, pickles_folder_path
from goldsberry.apiparams import default_season
from cached_property import cached_property

teams_id_dict_pickle_path = os.path.join(pickles_folder_path, "nba_teams_numbers_dict.pickle")
with open(teams_id_dict_pickle_path, 'rb') as file1:
    teams_id_dict = pickle.load(file1)
    """:type : dict"""

nba_teams_all_shooters_lineups_dicts_path_regex = os.path.join(pickles_folder_path,
                                                               'nba_teams_all_shooters_lineups_dicts_{season}.pickle')


class NBATeam(object):
    def __init__(self, team_name_or_id, season=default_season, initialize_stat_classes=True):
        """

        :return: An NBA team object
        :rtype : NBATeam
        """
        if type(team_name_or_id) is int:
            self.team_id = team_name_or_id
        elif type(team_name_or_id) is str:
            self.team_id = teams_id_dict[team_name_or_id]
        else:
            raise Exception('Constructor only receives string or integer')
        self.season = season
        if initialize_stat_classes:
            self.initialize_stat_classes()
        self.games_summary_dicts = []
        """:type : list[NBAGameTeam]"""

    def __repr__(self):
        teams_name_dict = {v: k for k, v in teams_id_dict.items()}
        return "{team_name} Object".format(team_name=teams_name_dict[self.team_id])

    def __cmp__(self, other):
        return self.team_id == other.team_id and self.season == other.season

    @cached_property
    def current_players_objects(self):
        """

        :return:
        :rtype:list[playerScripts.NBAPlayer]
        """
        return self._generate_current_players_objects()

    def _generate_current_players_objects(self, initialize_stat_classes=True):
        """
        Returns a list of player objects for players on the team's roster
        """
        players_objects_list = []
        for player_dict in goldsberry.team.roster(team_id=self.team_id, season=self.season).players():
            try:
                nba_player_object = playerScripts.NBAPlayer(player_name_or_id=player_dict['PLAYER_ID'],
                                                            season=self.season,
                                                            initialize_stat_classes=initialize_stat_classes)
                players_objects_list.append(nba_player_object)
            except playerScripts.NoSuchPlayer:
                print(
                    "{player_name} was not found in leagues players, even though he's on the team roster".format(
                        player_name=player_dict['PLAYER']))
            except Exception as e:
                raise e
        return players_objects_list

    def initialize_stat_classes(self):
        for stat_class in [my_stat_class for my_stat_class in dir(goldsberry.team) if
                           not my_stat_class.startswith('_')]:
            stat_class_function = getattr(goldsberry.team, stat_class)
            setattr(self, stat_class, stat_class_function(team_id=self.team_id, season=self.season))
        self.games_summary_dicts = [NBAGameTeam(game_log) for game_log in self.game_logs.logs()]

    def get_filtered_lineup_dicts(self, white_list=None, black_list=None):
        """

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

        return [lineup_dict for lineup_dict in self.lineups.lineups() if
                is_lineup_valid(lineup_dict, white_list, black_list)]

    def get_all_shooters_lineup_dicts(self, attempts_limit=20):
        only_non_shooters_player_objects = [player_object for player_object in self.current_players_objects
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
