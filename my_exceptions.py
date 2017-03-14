"""
All project exceptions
"""


class NoSuchPlayer(Exception):
    """
    NoSuchPlayer
    """

    def __init__(self, message=''):
        self.message = message


class TooMuchPlayers(Exception):
    """
    TooMuchPlayers
    """

    def __init__(self, message=''):
        self.message = message


class NoSuchTeam(Exception):
    """
    NoSuchTeam
    """
    def __init__(self, message=''):
        self.message = message


class TooMuchTeams(Exception):
    """
    TooMuchTeams
    """
    def __init__(self, message=''):
        self.message = message


class PlayerHasNoTeam(Exception):
    """
    PlayerHasNoTeam
    """
    def __init__(self, message=''):
        self.message = message


class PlayerHasMoreThenOneTeam(Exception):
    """
    PlayerHasMoreThenOneTeam
    """
    def __init__(self, message=''):
        self.message = message


class PlayerDidNotPlayAGame(Exception):
    """
    PlayerDidNotPlayAGame
    """
    def __init__(self, message=''):
        self.message = message


class CouldNotInitializePlayerObject(Exception):
    """
    CouldNotInitializePlayerObject
    """
    def __init__(self, message=''):
        self.message = message


class TeamObjectIsNotSet(Exception):
    """
    TeamObjectIsNotSet
    """
    def __init__(self, message=''):
        self.message = message


class PlayersObjectsAreNotSet(Exception):
    """
    PlayersObjectsAreNotSet
    """
    def __init__(self, message=''):
        self.message = message
