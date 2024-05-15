import IPython
import os
import sys

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(path)

if __name__ == "__main__":
    IPython.embed()
    sys.path.remove(path)
