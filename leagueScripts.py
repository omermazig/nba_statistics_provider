from __future__ import print_function
from __future__ import division
from playerScripts import NBAPlayer
from utilsScripts import pickles_folder_path
from teamScripts import nba_teams_all_shooters_lineups_dicts_path_regex
from my_exceptions import NoSuchPlayer, TooMuchPlayers
from goldsberry.apiparams import default_season
import goldsberry
import os
import pickle


class NBALeague(object):
    player_objects_list_pickle_path_regex = os.path.join(pickles_folder_path, 'nba_players_objects_{season}.pickle')

    def __init__(self, season=default_season, reinitialize_player_objects=False):
        self.season = season
        self.player_dicts_list = goldsberry.PlayerList().players()
        player_objects_list_pickle_path = self.player_objects_list_pickle_path_regex.format(season=self.season[:4])
        self.player_objects_list = []
        if reinitialize_player_objects:
            # Warning - Takes a LONG time - A few hours
            dicts_to_fetch = len(self.player_dicts_list)
            for player_dict in self.player_dicts_list:
                print('Fetching %s dict (%s / %s)...' % (player_dict["PLAYERCODE"],
                                                         (len(self.player_objects_list) + 1),
                                                         dicts_to_fetch
                                                         ))
                player_object = NBAPlayer(season=self.season, PLAYERCODE=player_dict["PLAYERCODE"])
                # current_team_object is a cached property, so we force the class to initialize it
                a = player_object.current_team_object
                self.player_objects_list.append(player_object)

            with open(player_objects_list_pickle_path, 'wb') as file1:
                'Updating pickle...'
                pickle.dump(self.player_objects_list, file1)
        else:
            with open(player_objects_list_pickle_path, 'rb') as file1:
                self.player_objects_list = pickle.load(file1)
                """:type : list[NBAPlayer]"""

    def initialize_stat_classes(self):
        public_stat_classes_names = [stat_class1 for stat_class1 in dir(goldsberry.league) if
                                     not stat_class1.startswith('_')]

        for stat_class_name in public_stat_classes_names:
            stat_class = getattr(goldsberry.player, stat_class_name)(self.season)
            """:type : NbaDataProvider"""
            setattr(self, stat_class_name, stat_class)

    def get_player_object_by_name(self, player_name):
        filtered_player_objects_list = [player_object for player_object in self.player_objects_list if
                                        player_name in player_object.player_name]
        filtered_player_objects_list_length = len(filtered_player_objects_list)
        if filtered_player_objects_list_length == 0:
            raise NoSuchPlayer('There was no player matching the given name')
        elif filtered_player_objects_list_length > 1:
            raise TooMuchPlayers('There were more then one player matching the given name')
        else:
            return filtered_player_objects_list[0]

    @staticmethod
    def get_point_per_possession_league_average_for_specific_play_type(play_type_to_search):
        """
        Name
        :param play_type_to_search: play type description
        :type play_type_to_search: str
        :return: PPP for play type
        :rtype: float
        """
        points_scored = 0
        possessions = 0
        for player_play_type_offensive_dict in getattr(goldsberry.playtype, play_type_to_search)().offensive():
            points_scored += player_play_type_offensive_dict["Points"]
            possessions += player_play_type_offensive_dict["Poss"]

        return points_scored / possessions

    def get_point_per_possession_league_average_for_post_ups(self):
        return self.get_point_per_possession_league_average_for_specific_play_type('postup')

    def get_league_all_shooters_lineups_dicts(self):
        with open(nba_teams_all_shooters_lineups_dicts_path_regex.format(season=self.season), 'rb') as file1:
            nba_teams_all_shooters_lineups_dicts = pickle.load(file1)
        return nba_teams_all_shooters_lineups_dicts


if __name__ == "__main__":
    nba_league_2015 = NBALeague(2015, reinitialize_player_objects=False)

    # def print_league_playtypes():
    #     for play_type in filter(lambda game_object: not game_object.startswith('_'), dir(goldsberry.league.playtype)):
    #         print '{play_type_to_print} - {ppp_to_print}'.format(play_type_to_print=play_type,
    #                                                              ppp_to_print=nba_league_2015.get_point_per_possession_league_average_for_specific_play_type(play_type))
    #
    # print_league_playtypes()

    player_objects_list = nba_league_2015.player_objects_list


    def is_over_200_fga(player_object):
        try:
            return player_object.player_stats_dict[0]["FGA"] > 200
        except IndexError:
            return False


    def is_over_50_assists(player_object):
        try:
            return player_object.player_stats_dict[0]['AST'] > 50
        except IndexError:
            return False


    player_objects_list = [my_player_object for my_player_object in player_objects_list if
                           is_over_50_assists(my_player_object)]

    list1 = [(my_player_object.player_name,
              my_player_object.get_diff_in_teammates_efg_percentage_between_shots_from_passes_by_player_to_other_shots())
             for my_player_object in player_objects_list]
    list1.sort(key=lambda x: x[1][0], reverse=True)
    print(list1)
