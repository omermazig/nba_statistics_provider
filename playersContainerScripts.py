import abc

from my_exceptions import NoSuchPlayer, TooMuchPlayers


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
