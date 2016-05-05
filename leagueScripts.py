from __future__ import print_function
from __future__ import division
import os
import pickle
import time

import playerScripts
import utilsScripts
import teamScripts
from my_exceptions import NoSuchPlayer, TooMuchPlayers, NoSuchTeam, TooMuchTeams, PlayerHasMoreThenOneTeam
import goldsberry

league_object_pickle_path_regex = os.path.join(utilsScripts.pickles_folder_path, 'league_object_{season}.pickle')


class PlayTypeLeagueAverage(object):
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


class NBALeague(object):
    def __init__(self, season=goldsberry.apiparams.default_season, initialize_stat_classes=True,
                 initialize_team_objects=False, initialize_player_objects=False):
        self.season = season
        self.team_objects_list = []
        if initialize_stat_classes:
            self.initialize_stat_classes()
            self.playtype = PlayTypeLeagueAverage()
        # Warning - Takes a LONG time - A few hours
        if initialize_team_objects:
            for team_name, team_id in teamScripts.teams_id_dict.items():
                time.sleep(0.1)
                print('Fetching %s team object...' % team_name)
                team_object = teamScripts.NBATeam(team_id, season=self.season)
                print("Initializing team game's objects ...")
                # We want to initialize 'team_regular_season_game_objects' cached property
                a = team_object.team_regular_season_game_objects
                if initialize_player_objects:
                    for player_object in team_object.current_players_objects:
                        time.sleep(0.1)
                        print('    Initializing stat classes for %s object..' % player_object.player_name)
                        player_object.initialize_stat_classes()
                        # We want to initialize 'player_stats_dict' cached property
                        a = player_object.player_stats_dict
                self.team_objects_list.append(team_object)
            print('Initializing players with no current team...')
            players_not_on_team_dicts_list = [player_dict for player_dict in
                                              goldsberry.PlayerList(season=season).players() if
                                              not player_dict['TEAM_ID']]
            self._players_not_on_team_objects_list = [
                playerScripts.NBAPlayer(player_name_or_id=player_dict['PERSON_ID'], season=self.season) for player_dict
                in
                players_not_on_team_dicts_list]
            for player_object in self._players_not_on_team_objects_list:
                # We want to initialize 'player_stats_dict' and 'current_team_object' cached properties
                a = player_object.player_stats_dict
                b = player_object.current_team_object

    @property
    def player_objects_list(self):
        """
        A list of generated player objects for all of the players for the given season.
        This property is compiled by adding all of the players that are on teams (Initialized under self.team_objects
        int __init__) and the players that are not on teams (Initialized under self._players_not_on_team_objects_list
        in __init__)
        :return:
        :rtype:list[playerScripts.NBAPlayer]
        """
        players_on_teams_objects_list = []
        for team_object in self.team_objects_list:
            players_on_teams_objects_list += team_object.current_players_objects
        players_on_teams_objects_list += self._players_not_on_team_objects_list
        return players_on_teams_objects_list

    def initialize_stat_classes(self):
        """
        Initializing all of the classes in goldsberry.league, and setting them under self
        :return:
        :rtype: None
        """
        public_stat_classes_names = [stat_class1 for stat_class1 in dir(goldsberry.league) if
                                     not stat_class1.startswith('_')]

        for stat_class_name in public_stat_classes_names:
            stat_class = getattr(goldsberry.league, stat_class_name)(season=self.season)
            """:type : NbaDataProvider"""
            setattr(self, stat_class_name, stat_class)

    def get_player_object_by_name(self, player_name):
        """
        Doesn't create a new object - Just finds and takes it from self.player_objects_list
        Can accept part of the name - uses __contains__ to find the right player
        Has to be singular - will not return 2 players
        :param player_name: The desired player's name or part of it
        :type player_name: str
        :return: The desired player's object
        :rtype: playerScripts.NBAPlayer
        """
        filtered_player_objects_list = [player_object for player_object in self.player_objects_list if
                                        player_name in player_object.player_name]
        filtered_player_objects_list_length = len(filtered_player_objects_list)
        if filtered_player_objects_list_length == 0:
            raise NoSuchPlayer('There was no player matching the given name')
        elif filtered_player_objects_list_length > 1:
            raise TooMuchPlayers(
                'There were more then one player matching the given name:\n%s' % [player_object.player_name for
                                                                                  player_object in
                                                                                  filtered_player_objects_list])
        else:
            return filtered_player_objects_list[0]

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
                                      team_name in team_object.team_name]
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
        for all_shooters_lineups_dict_for_a_team in [
            team_object.get_all_shooters_lineup_dicts(attempts_limit=attempts_limit) for team_object in
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
        for team_id, team_all_shooters_lineups_dicts in [(team_object.team_id, team_object.get_all_shooters_lineup_dicts
            (attempts_limit=attempts_limit)) for team_object in self.team_objects_list]:
            team_name = teamScripts.teams_name_dict[team_id]
            league_all_shooters_lineups_dicts[team_name] = utilsScripts.join_advanced_lineup_dicts(
                team_all_shooters_lineups_dicts)
        return league_all_shooters_lineups_dicts

    def get_players_sorted_by_diff_in_teammates_efg_percentage_between_shots_from_passes_by_player_to_other_shots(self):
        """
        Sort all the players WITH MORE THEN 50 ASSISTS this season, by how much better their teammates shot the ball
        with them passing to them (rather then not)
        :return:
        :rtype: list[playerScripts.NBAPlayer]
        """
        print('Filtering out players with not enough shots...')
        filtered_player_objects_list = [my_player_object for my_player_object in self.player_objects_list if
                                        my_player_object.is_player_over_50_assists()]

        print('Getting relevant data...')
        players_name_and_result = []
        i = 1
        for my_player_object in filtered_player_objects_list:
            time.sleep(1)
            print('Player %s/%s' % (i, len(filtered_player_objects_list)))
            try:
                players_name_and_result.append((my_player_object.player_name,
                                                my_player_object.get_diff_in_teammates_efg_percentage_between_shots_from_passes_by_player_to_other_shots()))
            except PlayerHasMoreThenOneTeam:
                pass
            i += 1
        print('Sorting...')
        players_name_and_result.sort(key=lambda x: x[1][0], reverse=True)
        return players_name_and_result

    def get_players_sorted_by_team_net_rtg_on_off_court_diff(self):
        """
        Sort all the players WITH MORE THEN 700 MINUTES this season, by how much better their team's net rating was
        when they were on the court (rather then not)
        :return:
        :rtype: list[playerScripts.NBAPlayer]
        """
        print('Filtering out players with not enough shots...')
        filtered_player_objects_list = [my_player_object for my_player_object in self.player_objects_list if
                                        my_player_object.is_player_over_700_minutes()]

        print('Getting relevant data...')
        players_name_and_result = []
        i = 1
        for my_player_object in filtered_player_objects_list:
            print('Player %s/%s' % (i, len(filtered_player_objects_list)))
            try:
                players_name_and_result.append((my_player_object.player_name,
                                                my_player_object.get_team_net_rtg_on_off_court()))
            except PlayerHasMoreThenOneTeam:
                pass
            i += 1
        print('Sorting...')
        players_name_and_result.sort(key=lambda x: x[1][0] - x[1][1], reverse=True)
        return players_name_and_result

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
        league_object_pickle_path = league_object_pickle_path_regex.format(season=self.season[:4])
        with open(league_object_pickle_path, 'wb') as file1:
            'Updating pickle...'
            pickle.dump(self, file1)

    @staticmethod
    def get_cached_league_object(season='2015'):
        """

        :param season:
        :type season: str
        :return:
        :rtype: NBALeague
        """
        with open(league_object_pickle_path_regex.format(season=season), "rb") as file1:
            player_objects_2015 = pickle.load(file1)
        return player_objects_2015


if __name__ == "__main__":
    for year in range(2015, 2012, -1):
        league_year = NBALeague(initialize_stat_classes=True, initialize_player_objects=True,
                                initialize_team_objects=True, season=goldsberry.apiconvertor.nba_season(year))
        my_league_object_pickle_path = league_object_pickle_path_regex.format(season=league_year.season[:4] + 'kuku')
        with open(my_league_object_pickle_path, 'wb') as file1:
            'Updating pickle...'
            pickle.dump(league_year, file1)

        league_year.pickle_league_object()
