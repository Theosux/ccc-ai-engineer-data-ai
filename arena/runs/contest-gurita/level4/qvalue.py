"""Distill linear-search Q into a value head. Policy stays the seat prior.

Terminal outcomes were a strong classifier and still lost under MCTS: they
pull search off the prior. Search Q is the value the prior already agrees with,
plus the lookahead the static eval does not have.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ENV = HERE.parents[1] / "contest" / "level4" / "env4"
sys.path.insert(0, str(ENV))


def generate_fixed(n_games=40, sims=100, seed=7):
    from colony_one import constants, mcts
    from colony_one.env import ColonyOneEnv
    from colony_one.onnx_runner import OnnxEvaluator
    ev = OnnxEvaluator(HERE / "driver_linear.onnx")
    rng = np.random.default_rng(seed)
    cfg = mcts.MCTSConfig(simulations=sims, batch_size=8)
    P, Q, Z = [], [], []
    cyan = 0
    for g in range(n_games):
        env = ColonyOneEnv()
        rec = []
        while not env.terminated:
            team = env.current_team
            planes = env.observation()
            root = mcts.run(env.board, team, env.actions_left, env.round_number, ev, cfg, rng=rng)
            visits = sum(root.N.values()) or 1
            q = float(sum(root.W.values()) / visits)
            mv = mcts.move_number(team, env.actions_left, env.round_number)
            temp = mcts.warmup_temperature(mv, cfg.warmup_temperatures, cfg.warmup_step_actions)
            idx = mcts.select_action_index(root, temp, rng=rng)
            rec.append((planes.astype(np.float32), np.float32(q), team))
            env.step(idx)
        cyan += env.winner == constants.CYAN
        for planes, q, team in rec:
            P.append(planes)
            Q.append(q)
            Z.append(np.float32(1.0 if team == env.winner else -1.0))
        print(f"game {g} {env.winner} len {env.action} n {len(Q)}", flush=True)
    print(f"cyan {cyan}/{n_games} q mean {np.mean(Q):.3f} |q| {np.mean(np.abs(Q)):.3f}")
    return np.stack(P), np.array(Q, np.float32), np.array(Z, np.float32)


def train(P, Q, epochs=12, ch=32, blocks=2):
    import torch
    import torch.nn.functional as F
    from net import Net, export
    # left-right flip keeps the value
    P2 = P[:, :, :, ::-1].copy()
    P = np.concatenate([P, P2])
    Q = np.concatenate([Q, Q])
    n = len(Q)
    rng = np.random.default_rng(0)
    perm = rng.permutation(n)
    nv = max(1, n // 8)
    va, tr = perm[:nv], perm[nv:]
    net = Net(ch, blocks)
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4)
    Pt = torch.from_numpy(P)
    Qt = torch.from_numpy(Q)
    bs = min(256, len(tr))
    steps = max(1, epochs * (len(tr) // bs))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 2e-3, total_steps=steps)
    for ep in range(epochs):
        net.train()
        rng.shuffle(tr)
        for i in range(len(tr) // bs):
            b = tr[i * bs:(i + 1) * bs]
            _, v = net(Pt[b])
            loss = F.mse_loss(v, Qt[b])
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        net.eval()
        with torch.no_grad():
            _, v = net(Pt[va])
            mse = F.mse_loss(v, Qt[va]).item()
            corr = np.corrcoef(v.numpy(), Qt[va].numpy())[0, 1]
        print(f"ep {ep} val mse {mse:.4f} corr {corr:.3f}", flush=True)
    out = HERE / "gurita_q.onnx"
    export(net, str(out))
    print("exported", out, out.stat().st_size)
    return out


if __name__ == "__main__":
    P, Q, Z = generate_fixed(int(sys.argv[1]) if len(sys.argv) > 1 else 36, 100)
    np.savez_compressed(HERE / "qdistill.npz", P=P, Q=Q, Z=Z)
    print("q vs z corr", float(np.corrcoef(Q, Z)[0, 1]))
    train(P, Q)
