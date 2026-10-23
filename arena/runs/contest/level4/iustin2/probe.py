"""Candidate model vs GreedyAgent (no search) by colour, under the referee MCTS (100 sims).
usage (cwd env4, .venv python): ../iustin2/probe.py model.onnx games_per_colour [procs]"""
import sys, os
os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, "play"); sys.path.insert(0, ".")
from pathlib import Path
from multiprocessing import Pool


def one(args):
    model, g, cyan = args
    from model_vs_model import SearchAgent, play_game
    from colony_one.baselines import GreedyAgent
    me = SearchAgent(Path(model), 100, seed=7919 * g + 3)
    opp = GreedyAgent(seed=1000 + g)
    w, _ = play_game(me, opp) if cyan else play_game(opp, me)
    mine = "CYAN" if cyan else "MAGENTA"
    return cyan, w == mine


if __name__ == "__main__":
    model, n = sys.argv[1], int(sys.argv[2])
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    with Pool(procs) as p:
        res = p.map(one, [(model, g, c) for g in range(n) for c in (True, False)])
    for c, lab in ((True, "CYAN"), (False, "MAGENTA")):
        r = [w for cc, w in res if cc == c]
        print(f"{model} vs Greedy as {lab}: {sum(r)}/{len(r)}")
