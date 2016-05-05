import sys
import os
import pickle
import IPython

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(path)
from playerScripts import NBAPlayer
from teamScripts import NBATeam
from leagueScripts import NBALeague
from gameScripts import NBAGame, NBASingleSeasonGames

import goldsberry

if __name__ == "__main__":
    IPython.embed()
    sys.path.remove(path)
