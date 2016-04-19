from __future__ import print_function
from __future__ import division
from playerScripts import NBAPlayer
from utilsScripts import pickles_folder_path
from my_exceptions import NoSuchPlayer, TooMuchPlayers
from goldsberry.apiparams import default_season
import goldsberry
import os
import pickle


class PlayTypeLeagueAverage(object):
    def __init__(self, offensive_or_defensive):
        playtype_classes_names = [stat_class1 for stat_class1 in dir(goldsberry.playtype) if
                                  not stat_class1.startswith('_')]
        for playtype_class_name in playtype_classes_names:
            value = self._get_ppp_league_average_for_specific_play_type(playtype_class_name,
                                                                        offensive_or_defensive)
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


class PlayTypeOffensiveLeagueAverage(PlayTypeLeagueAverage):
    def __init__(self):
        PlayTypeLeagueAverage.__init__(self, 'offensive')


class PlayTypeDefensiveLeagueAverage(PlayTypeLeagueAverage):
    def __init__(self):
        PlayTypeLeagueAverage.__init__(self, 'defensive')


class NBALeague(object):
    league_object_pickle_path_regex = os.path.join(pickles_folder_path, 'league_object_{season}.pickle')

    def __init__(self, season=default_season, initialize_stat_classes=True, initialize_player_objects=False):
        self.season = season
        self.player_dicts_list = goldsberry.PlayerList().players()
        self.player_objects_list = []
        if initialize_stat_classes:
            self.initialize_stat_classes()
            self.playtype_offense = PlayTypeOffensiveLeagueAverage()
            self.playtype_defense = PlayTypeDefensiveLeagueAverage()
        league_object_pickle_path = self.league_object_pickle_path_regex.format(season=self.season[:4])
        # Warning - Takes a LONG time - A few hours
        number_of_dicts_to_fetch = len(self.player_dicts_list)
        if initialize_player_objects:
            for i in range(len(self.player_dicts_list)):
                player_dict = self.player_dicts_list[i]
                print('Fetching %s dict (%s / %s)...' % (player_dict["PLAYERCODE"],
                                                         (i + 1),
                                                         number_of_dicts_to_fetch
                                                         ))
                player_object = NBAPlayer(player_name_or_id=player_dict["PLAYERCODE"], season=self.season)
                print('Initializing %s team object (%s / %s)...' % (player_dict["PLAYERCODE"],
                                                                    (i + 1),
                                                                    number_of_dicts_to_fetch
                                                                    ))
                a = player_object.current_team_object
                self.player_objects_list.append(player_object)

            with open(league_object_pickle_path, 'wb') as file1:
                'Updating pickle...'
                pickle.dump(self, file1)

    def initialize_stat_classes(self):
        public_stat_classes_names = [stat_class1 for stat_class1 in dir(goldsberry.league) if
                                     not stat_class1.startswith('_')]

        for stat_class_name in public_stat_classes_names:
            stat_class = getattr(goldsberry.league, stat_class_name)(season=self.season)
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

    def get_league_all_shooters_lineups_dicts(self):
        raise NotImplemented


if __name__ == "__main__":
    nba_league_2015 = NBALeague(initialize_player_objects=False)

    # def print_league_playtypes():
    #     for play_type in filter(lambda game_object: not game_object.startswith('_'), dir(goldsberry.league.playtype)):
    #         print '{play_type_to_print} - {ppp_to_print}'.format(play_type_to_print=play_type,
    #                                                              ppp_to_print=nba_league_2015.get_offensive_ppp_league_average_for_specific_play_type(play_type))
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
