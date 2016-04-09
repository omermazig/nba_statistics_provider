class NoSuchPlayer(Exception):
    def __init__(self, message=''):
        self.message = message


class TooMuchPlayers(Exception):
    def __init__(self, message=''):
        self.message = message


class PlayerHasNoTeam(Exception):
    def __init__(self, message=''):
        self.message = message


class PlayerDidNotPlayAGame(Exception):
    def __init__(self, message=''):
        self.message = message


class CouldNotInitializePlayerObject(Exception):
    def __init__(self, message=''):
        self.message = message
