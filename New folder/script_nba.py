import sys
import os
import pickle
import IPython

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(path)
from playerScripts import NBAPlayer
from teamScripts import NBATeam
from leagueScripts import NBALeague, league_object_pickle_path_regex
from gameScripts import NBAGame, NBASingleSeasonGames

sys.path.remove(path)
import goldsberry

if __name__ == "__main__":
    with open(league_object_pickle_path_regex.format(season='2015'),
              "rb") as file1:
        player_objects_2015 = pickle.load(file1)
    sys.path.append(r'C:\Users\Administrator\Documents\NBA\pythonProjects')
    IPython.embed()
