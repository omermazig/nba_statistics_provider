import sys
import os

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(path)
from playerScripts import NBAPlayer
from teamScripts import NBATeam
from leagueScripts import NBALeague
from gameScripts import NBAGame, NBASingleSeasonGames

sys.path.remove(path)
import goldsberry
import pickle
import IPython
import sys

if __name__ == "__main__":
    # with open(r"C:\Users\Administrator\Documents\NBA\pythonProjects\pythonPickles\nba_players_objects_2015.pickle",
    #           "rb") as file1:
    #     player_objects_2015 = pickle.load(file1)
    # sys.path.append(r'C:\Users\Administrator\Documents\NBA\pythonProjects')
    IPython.embed()
