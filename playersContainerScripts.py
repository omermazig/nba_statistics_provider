import abc

import utilsScripts
from my_exceptions import NoSuchPlayer, TooMuchPlayers, PlayerHasMoreThenOneTeam, PlayerHasNoTeam


class PlayersContainer:
    """
    An object which holds several player objects
    """
    __metaclass__ = abc.ABCMeta

    @property
    @abc.abstractmethod
    def logger(self):
        """
        The logger object for writing messages
        :return:
        """
        pass

    @property
    @abc.abstractmethod
    def current_players_objects(self):
        """
        A list of generated player objects for all of the players for the given season.

        :return:
        :rtype:list[playerScripts.NBAPlayer]
        """
        pass

    def get_player_object_by_name(self, player_name):
        """
        Doesn't create a new object - Just finds and takes it from self.current_players_objects
        Can accept part of the name - uses __contains__ to find the right player
        Has to be singular - will not return 2 players
        :param player_name: The desired player's name or part of it
        :type player_name: str
        :return: The desired player's object
        :rtype: playerScripts.NBAPlayer
        """
        filtered_player_objects_list = [player_object for player_object in self.current_players_objects if
                                        player_name in player_object.name]
        filtered_player_objects_list_length = len(filtered_player_objects_list)
        if filtered_player_objects_list_length == 0:
            raise NoSuchPlayer('There was no player matching the given name')
        elif filtered_player_objects_list_length > 1:
            raise TooMuchPlayers(
                'There were more then one player matching the given name:\n%s' % [player_object.name for
                                                                                  player_object in
                                                                                  filtered_player_objects_list])
        else:
            return filtered_player_objects_list[0]

    def get_players_sorted_by_diff_in_per_between_minutes_played(self):
        """

        :return:
        :rtype: list[(string, float)]
        """
        self.logger.info('Filtering out players with not enough minutes...')
        filtered_player_objects_list = [my_player_object for my_player_object in self.current_players_objects if
                                        my_player_object.is_player_over_minutes_limit() and
                                        my_player_object.is_single_team_player()]

        self.logger.info('Getting relevant data...')
        players_name_and_result = []
        for i, my_player_object in enumerate(filtered_player_objects_list, start=1):
            self.logger.info('Player %s/%s' % (i, len(filtered_player_objects_list)))
            try:
                my_team_object = my_player_object.current_team_object
                games_split = my_player_object.get_over_minutes_limit_games_per_36_stats_compared_to_other_games()
                over_limit_stats = games_split['Over 30 minutes']
                under_limit_stats = games_split['Under 30 minutes']
                if (over_limit_stats and under_limit_stats) and \
                        (over_limit_stats['NUM_OF_ITEMS'] > 20 and under_limit_stats['NUM_OF_ITEMS'] > 20):
                    diff = utilsScripts.get_aPER_from_stat_dict(over_limit_stats, my_team_object) - \
                           utilsScripts.get_aPER_from_stat_dict(under_limit_stats, my_team_object)
                    players_name_and_result.append((my_player_object.name,
                                                    diff))
            except PlayerHasMoreThenOneTeam:
                pass
        self.logger.info('Sorting...')
        players_name_and_result.sort(key=lambda x: x[-1], reverse=True)
        return players_name_and_result

    def get_players_sorted_by_diff_in_teammates_efg_percentage_between_shots_from_passes_by_player_to_other_shots(self):
        """
        Sort all the players WITH MORE THEN 50 ASSISTS this season, by how much better their teammates shot the ball
        with them passing to them (rather then not)
        :return:
        :rtype: list[(string, (float, int))]
        """
        self.logger.info('Filtering out players with not enough assists...')
        filtered_player_objects_list = [my_player_object for my_player_object in self.current_players_objects if
                                        my_player_object.is_player_over_assists_limit()]

        self.logger.info('Getting relevant data...')
        players_name_and_result = []
        for i, my_player_object in enumerate(filtered_player_objects_list, start=1):
            self.logger.info('Player %s/%s' % (i, len(filtered_player_objects_list)))
            try:
                diff_in_teammates_efg_percentage = \
                    my_player_object.get_diff_in_teammates_efg_percentage_on_shots_from_player_passes()
                players_name_and_result.append((my_player_object.name,
                                                diff_in_teammates_efg_percentage))
            except PlayerHasMoreThenOneTeam:
                pass
        self.logger.info('Sorting...')
        players_name_and_result.sort(key=lambda x: x[1][0], reverse=True)
        return players_name_and_result

    def get_players_sorted_by_diff_in_efg_percentage_between_uncontested_and_contested_shots_outside_10_feet(self):
        """
        Sort all the players WITH MORE THEN 200 OUTSIDE FGA this season, by how much better their EFG% was on
        uncontested shots than on contested shots.
        :return:
        :rtype: list[(string, (float, float))]
        """
        self.logger.info('Filtering out players with not enough shot attempts...')
        filtered_player_objects_list = [my_player_object for my_player_object in self.current_players_objects if
                                        my_player_object.is_player_over_fga_outside_10_feet_limit()]

        self.logger.info('Getting relevant data...')
        players_name_and_result_list = []

        for i, my_player_object in enumerate(filtered_player_objects_list, start=1):
            self.logger.info('Player %s/%s' % (i, len(filtered_player_objects_list)))
            diff_in_teammates_efg_percentage = \
                my_player_object.get_diff_in_efg_percentage_between_uncontested_and_contested_shots_outside_10_feet()
            players_name_and_result_list.append((my_player_object.name, diff_in_teammates_efg_percentage))
        self.logger.info('Sorting...')
        players_name_and_result_list.sort(key=lambda x: x[1][0], reverse=True)
        return players_name_and_result_list

    def get_players_sorted_by_percentage_of_shots_outside_10_feet_that_were_uncontested(self):
        """
        Sort all the players WITH MORE THEN 100 OUTSIDE FGA this season, by the percentage of their outside shots which
        were uncontested.
        :return:
        :rtype: list[(string, (float, float))]
        """
        self.logger.info('Filtering out players with not enough shot attempts...')
        filtered_player_objects_list = [my_player_object for my_player_object in self.current_players_objects if
                                        my_player_object.is_player_over_fga_outside_10_feet_limit(limit=100)]

        self.logger.info('Getting relevant data...')
        players_name_and_result = []

        for i, my_player_object in enumerate(filtered_player_objects_list, start=1):
            self.logger.info('Player %s/%s' % (i, len(filtered_player_objects_list)))
            diff_in_teammates_efg_percentage = \
                my_player_object.get_diff_in_efg_percentage_between_uncontested_and_contested_shots_outside_10_feet()
            players_name_and_result.append((my_player_object.name, diff_in_teammates_efg_percentage))
        self.logger.info('Sorting...')
        players_name_and_result.sort(key=lambda x: x[1][1], reverse=True)
        return players_name_and_result

    def get_players_sorted_by_team_net_rtg_on_off_court_diff(self):
        """
        Sort all the players WITH MORE THEN 800 MINUTES this season, by how much better their team's net rating was
        when they were on the court (rather then not)
        :return:
        :rtype: list[(string, (float, float))]
        """
        self.logger.info('Filtering out players with not enough minutes...')
        filtered_player_objects_list = [my_player_object for my_player_object in self.current_players_objects if
                                        my_player_object.is_player_over_minutes_limit(only_recent_team=True)]

        self.logger.info('Getting relevant data...')
        players_name_and_result = []
        for i, my_player_object in enumerate(filtered_player_objects_list, start=1):
            self.logger.info('Player %s/%s' % (i, len(filtered_player_objects_list)))
            try:
                players_name_and_result.append((my_player_object.name,
                                                my_player_object.get_team_net_rtg_on_off_court()))
            except (PlayerHasMoreThenOneTeam, PlayerHasNoTeam):
                pass
        self.logger.info('Sorting...')
        players_name_and_result.sort(key=lambda x: x[1][0] - x[1][1], reverse=True)
        return players_name_and_result

    def get_players_sorted_by_team_def_rtg_on_off_court_diff(self):
        """
        Sort all the players WITH MORE THEN 800 MINUTES this season, by how much better their team's def rating was
        when they were on the court (rather then not)
        :return:
        :rtype: list[(string, (float, float))]
        """
        self.logger.info('Filtering out players with not enough minutes...')
        filtered_player_objects_list = [my_player_object for my_player_object in self.current_players_objects if
                                        my_player_object.is_player_over_minutes_limit(only_recent_team=True)]

        self.logger.info('Getting relevant data...')
        players_name_and_result = []
        for i, my_player_object in enumerate(filtered_player_objects_list, start=1):
            self.logger.info('Player %s/%s' % (i, len(filtered_player_objects_list)))
            try:
                players_name_and_result.append((my_player_object.name,
                                                my_player_object.get_team_def_rtg_on_off_court()))
            except (PlayerHasMoreThenOneTeam, PlayerHasNoTeam):
                pass
        self.logger.info('Sorting...')
        players_name_and_result.sort(key=lambda x: x[1][0] - x[1][1], reverse=True)
        return players_name_and_result
