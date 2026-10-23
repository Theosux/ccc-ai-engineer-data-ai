"""Score gurita.onnx against the driver's linear seat model under referee MCTS."""
import sys
from multiprocessing import Pool
from pathlib import Path

ENV = Path(__file__).resolve().parents[2] / "contest" / "level4" / "env4"
sys.path.insert(0, str(ENV))
HERE = Path(__file__).resolve().parent


def one(g):
    import numpy as np
    from colony_one import constants, mcts
    from colony_one.env import ColonyOneEnv
    from colony_one.onnx_runner import OnnxEvaluator
    sims = 100
    a = OnnxEvaluator(HERE / "gurita.onnx")
    b = OnnxEvaluator(HERE / "driver_linear.onnx")
    cfg = mcts.MCTSConfig(simulations=sims, batch_size=8)
    me_cyan = g % 2 == 0
    ra, rb = np.random.default_rng(4000 + g), np.random.default_rng(5000 + g)
    env = ColonyOneEnv()
    while not env.terminated:
        use = (env.current_team == constants.CYAN) == me_cyan
        ev, rng = (a, ra) if use else (b, rb)
        act = mcts.search_action(env.board, env.current_team, env.actions_left, env.round_number, ev, cfg, rng=rng)
        env.step(act)
    return (env.winner == "CYAN") == me_cyan, env.action


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    with Pool(6) as pool:
        res = pool.map(one, range(n))
    w = sum(r[0] for r in res)
    print(f"gurita vs linear: {w}/{n} avg len {sum(r[1] for r in res)/n:.0f}")
