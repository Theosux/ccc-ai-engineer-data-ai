"""gurita_stitch.onnx (linear policy, conv value) vs driver_linear.onnx."""
import sys
from pathlib import Path

import numpy as np

ENV = Path(__file__).resolve().parents[2] / "contest" / "level4" / "env4"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ENV))

from colony_one import constants, mcts
from colony_one.env import ColonyOneEnv
from colony_one.onnx_runner import OnnxEvaluator


def main():
    sims = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    games = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    me_path = sys.argv[3] if len(sys.argv) > 3 else str(HERE / "gurita_stitch.onnx")
    a = OnnxEvaluator(me_path)
    b = OnnxEvaluator(HERE / "driver_linear.onnx")
    cfg = mcts.MCTSConfig(simulations=sims, batch_size=8)
    w = 0
    for g in range(games):
        me_cyan = g % 2 == 0
        ra, rb = np.random.default_rng(20000 + g), np.random.default_rng(30000 + g)
        env = ColonyOneEnv()
        while not env.terminated:
            use = (env.current_team == constants.CYAN) == me_cyan
            ev, rng = (a, ra) if use else (b, rb)
            env.step(mcts.search_action(
                env.board, env.current_team, env.actions_left, env.round_number, ev, cfg, rng=rng))
        me = (env.winner == "CYAN") == me_cyan
        w += me
        print(g, "ME" if me else "them", env.winner, "len", env.action, flush=True)
    print(f"stitch {w}/{games} sims {sims}")


if __name__ == "__main__":
    main()
