"""A vs B under referee MCTS (100 sims), sides alternated, parallel. usage: match.py a.onnx b.onnx games [sims]"""
import sys, numpy as np
sys.path.insert(0, 'play'); sys.path.insert(0, '.')
from pathlib import Path
from multiprocessing import Pool


def one(args):
    a, b, g, sims = args
    from model_vs_model import SearchAgent, play_game
    A = SearchAgent(Path(a), sims, seed=7919 * g + 1)
    B = SearchAgent(Path(b), sims, seed=7919 * g + 2)
    if g % 2 == 0:
        w, n = play_game(A, B)
        return w == "CYAN", "C", n
    w, n = play_game(B, A)
    return w == "MAGENTA", "M", n


if __name__ == "__main__":
    a, b, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    sims = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    with Pool(10) as p:
        res = p.map(one, [(a, b, g, sims) for g in range(n)])
    wc = sum(r[0] for r in res if r[1] == "C"); nc = sum(1 for r in res if r[1] == "C")
    wm = sum(r[0] for r in res if r[1] == "M"); nm = n - nc
    print(f"{a} vs {b}: {wc + wm}/{n}  (as CYAN {wc}/{nc}, as MAGENTA {wm}/{nm}), avg len {np.mean([r[2] for r in res]):.0f}")
