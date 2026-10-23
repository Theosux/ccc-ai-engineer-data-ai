import sys, numpy as np
sys.path.insert(0, 'play'); sys.path.insert(0, '.')
from pathlib import Path
from model_vs_model import SearchAgent, play_game
from colony_one.baselines import GreedyAgent
model, n = sys.argv[1], int(sys.argv[2])
w = 0
for g in range(n):
    a = SearchAgent(Path(model), 60, seed=1000 + g)
    winner, acts = play_game(a, GreedyAgent(seed=g))
    w += winner == "CYAN"
print(model, f"{w}/{n}")
