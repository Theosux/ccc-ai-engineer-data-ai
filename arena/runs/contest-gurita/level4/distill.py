"""Self-play the linear seat model and train a small conv net on the MCTS visit targets."""
import sys
from pathlib import Path

import numpy as np

ENV = Path(__file__).resolve().parents[2] / "contest" / "level4" / "env4"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ENV))
sys.path.insert(0, str(HERE))


def generate(n_games, sims, seed=0):
    from colony_one import constants, mcts
    from colony_one.env import ColonyOneEnv
    from colony_one.onnx_runner import OnnxEvaluator
    ev = OnnxEvaluator(HERE / "driver_linear.onnx")
    rng = np.random.default_rng(seed)
    cfg = mcts.MCTSConfig(simulations=sims, batch_size=8)
    P, PI, Z = [], [], []
    wins = 0
    for g in range(n_games):
        env = ColonyOneEnv()
        rec = []
        while not env.terminated:
            team = env.current_team
            planes = env.observation()
            root = mcts.run(env.board, team, env.actions_left, env.round_number, ev, cfg, rng=rng)
            pi = mcts.policy_target(root)
            mv = mcts.move_number(team, env.actions_left, env.round_number)
            temp = mcts.warmup_temperature(mv, cfg.warmup_temperatures, cfg.warmup_step_actions)
            idx = mcts.select_action_index(root, temp, rng=rng)
            rec.append((planes, pi, team))
            env.step(idx)
        wins += env.winner == constants.CYAN
        for planes, pi, team in rec:
            P.append(planes.astype(np.float32))
            PI.append(pi.astype(np.float32))
            Z.append(1.0 if team == env.winner else -1.0)
        print(f"game {g} winner {env.winner} len {env.action} positions {len(Z)}", flush=True)
    print(f"cyan {wins}/{n_games}")
    return np.stack(P), np.stack(PI), np.array(Z, np.float32)


def train(P, PI, Z, epochs=8, ch=32, blocks=2):
    import torch
    import torch.nn.functional as F
    sys.path.insert(0, str(ENV))
    from net import Net, augment_flip, export
    P2, PI2 = augment_flip(P, PI)
    P = np.concatenate([P, P2]); PI = np.concatenate([PI, PI2]); Z = np.concatenate([Z, Z])
    n = len(Z)
    rng = np.random.default_rng(0)
    perm = rng.permutation(n)
    nv = max(1, n // 10)
    va, tr = perm[:nv], perm[nv:]
    net = Net(ch, blocks)
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4)
    Pt, PIt, Zt = torch.from_numpy(P), torch.from_numpy(PI), torch.from_numpy(Z)
    bs = min(256, len(tr))
    steps = max(1, epochs * (len(tr) // bs))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 2e-3, total_steps=steps)
    for ep in range(epochs):
        net.train(); rng.shuffle(tr)
        for i in range(len(tr) // bs):
            b = tr[i * bs:(i + 1) * bs]
            p, v = net(Pt[b])
            legal = PIt[b] > 0
            lp = F.log_softmax(p.masked_fill(~legal, -1e9), dim=1)
            loss = -(PIt[b] * lp).sum(1).mean() + 4.0 * F.mse_loss(v, Zt[b])
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        net.eval()
        with torch.no_grad():
            p, v = net(Pt[va])
            acc = ((v > 0) == (Zt[va] > 0)).float().mean().item()
        print(f"ep {ep} sign {acc:.3f}", flush=True)
    out = HERE / "gurita_net.onnx"
    export(net, str(out))
    print("exported", out, out.stat().st_size)
    return out


if __name__ == "__main__":
    P, PI, Z = generate(int(sys.argv[1]) if len(sys.argv) > 1 else 24, int(sys.argv[2]) if len(sys.argv) > 2 else 40)
    np.savez_compressed(HERE / "distill.npz", P=P, PI=PI, Z=Z)
    train(P, PI, Z)
