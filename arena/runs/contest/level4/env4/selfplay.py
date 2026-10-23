"""Self-play data under referee MCTS. usage: selfplay.py out.npz games modelA.onnx [modelB.onnx ...]
Each game picks CYAN/MAGENTA models at random from the list (first model weighted x2). Records every action:
planes (16,8,8) uint8-ish, visit policy (4096), side-to-move team, then outcome z for side to move."""
import sys, os, numpy as np
sys.path.insert(0, '.')
from pathlib import Path
from multiprocessing import Pool
os.environ.setdefault("OMP_NUM_THREADS", "1")


def worker(args):
    out, seed, ngames, models, sims = args
    from colony_one import mcts, constants
    from colony_one.env import ColonyOneEnv
    from colony_one.onnx_runner import OnnxEvaluator
    evs = [OnnxEvaluator(Path(m)) for m in models]
    rng = np.random.default_rng(seed)
    cfg = mcts.MCTSConfig(simulations=sims, batch_size=8)
    P, PI, Z, R = [], [], [], []
    wins = 0
    for g in range(ngames):
        pool = [0] + list(range(len(evs)))
        ec, em = evs[pool[rng.integers(len(pool))]], evs[pool[rng.integers(len(pool))]]
        env = ColonyOneEnv()
        rec = []
        while not env.terminated:
            team = env.current_team
            ev = ec if team == constants.CYAN else em
            planes = env.observation()
            root = mcts.run(env.board, team, env.actions_left, env.round_number, ev, cfg, rng=rng)
            pi = mcts.policy_target(root)
            mv = mcts.move_number(team, env.actions_left, env.round_number)
            temp = mcts.warmup_temperature(mv, cfg.warmup_temperatures, cfg.warmup_step_actions)
            if temp <= 1e-3 and rng.random() < 0.1:
                temp = 1.0       # extra exploration
            idx = mcts.select_action_index(root, temp, rng=rng)
            rec.append((planes, pi, team, env.round_number))
            env.step(idx)
        wins += env.winner == constants.CYAN
        for planes, pi, team, rnd in rec:
            P.append(planes.astype(np.float16)); PI.append(pi.astype(np.float16))
            Z.append(1.0 if team == env.winner else -1.0); R.append(rnd)
    np.savez_compressed(out, P=np.array(P), PI=np.array(PI), Z=np.array(Z, np.float32), R=np.array(R, np.int16))
    return wins, ngames, len(Z)


if __name__ == "__main__":
    out, games, models = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    sims = int(os.environ.get("SIMS", "100"))
    nproc = 12
    per = (games + nproc - 1) // nproc
    seed0 = abs(hash(out)) % 100000
    with Pool(nproc) as p:
        res = p.map(worker, [(f"{out}.part{i}.npz", seed0 + i, per, models, sims) for i in range(nproc)])
    print("cyan wins", sum(r[0] for r in res), "/", sum(r[1] for r in res), "positions", sum(r[2] for r in res))
