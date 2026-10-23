"""Hybrid model: a trained env4/net.py Net plus fixed tactical terms inside the ONNX graph.

policy += cap * own_any[from] x enemy_value[to]          (Kernel target gets a big bonus)
value   = vcap * tanh(z_net + w . features)                features from the side to move:
  myk_exp   relu(enemy reach on my Kernel - my guards), weighted more with 1 action left
  enk_exp   relu(my reach on enemy Kernel - its guards), weighted more with 2 actions left
  fire      pieces on the next ring to lock, scaled by firewall urgency (Kernel heavy)
  kcent     Kernel centrality difference, scaled by urgency
usage (cwd env4, .venv python): ../iustin3/hybrid.py BASE.pt OUT.onnx ['{"cap":0.5,...}']"""
import sys, json, numpy as np, torch, torch.nn as nn
sys.path.insert(0, ".")
from net import Net, export

VAL = [1.5, 4.5, 2.5, 3.0, 5.0, 0.0]          # ping daemon exploit trace ice kernel (Greedy-like scale)
DEFAULT = dict(cap=0.15, kcap=4.0, vcap=0.92, myk=0.6, enk=0.4, fire=1.2, kcent=0.15, enk2=0.0, myk2=0.0)


def reach_kernel():
    """(1, 6, 7, 7): squares each enemy piece type attacks in one action, blocking ignored.
    All patterns are point-symmetric, so conv (correlation) equals the attack map."""
    k = np.zeros((6, 7, 7), np.float32)
    c = 3
    for dr in range(-3, 4):
        for dc in range(-3, 4):
            if dr == dc == 0:
                continue
            ar, ac, cheb = abs(dr), abs(dc), max(abs(dr), abs(dc))
            diag, orth = ar == ac, dr == 0 or dc == 0
            if diag and cheb <= 2: k[0, c + dr, c + dc] = 1                    # ping diag capture 1..2
            if cheb == 1 or (orth and cheb in (2, 3)): k[1, c + dr, c + dc] = 1  # daemon shoot adj, move-capture 2..3
            if {ar, ac} == {1, 2}: k[2, c + dr, c + dc] = 1                    # exploit L jump
            if diag and cheb in (2, 3): k[3, c + dr, c + dc] = 1               # trace diag shot 2..3
            if (diag or orth) and cheb <= 2: k[4, c + dr, c + dc] = 1          # ice 1..2 any line
            if cheb == 1: k[5, c + dr, c + dc] = 1                             # kernel step
    return torch.from_numpy(k[None])


MOVES = {0: lambda r, c: (r == 0 or c == 0) and max(abs(r), abs(c)) <= 2,           # ping orth 1..2
         1: lambda r, c: (r == 0 or c == 0) and max(abs(r), abs(c)) <= 3,           # daemon orth 1..3
         2: lambda r, c: {abs(r), abs(c)} == {1, 2},                                # exploit
         3: lambda r, c: abs(r) + abs(c) == 1,                                      # trace orth 1
         4: lambda r, c: (r == 0 or c == 0 or abs(r) == abs(c)) and max(abs(r), abs(c)) <= 2,  # ice
         5: lambda r, c: max(abs(r), abs(c)) == 1}                                  # kernel


def reach2_kernel():
    """(1, 6, 13, 13): squares each piece type attacks with one move then one attack (or a direct attack)."""
    a = reach_kernel()[0].numpy()
    k = np.zeros((6, 13, 13), np.float32)
    for p in range(6):
        offs = [(0, 0)] + [(r, c) for r in range(-3, 4) for c in range(-3, 4) if (r, c) != (0, 0) and MOVES[p](r, c)]
        for mr, mc in offs:
            k[p, 3 + mr:10 + mr, 3 + mc:10 + mc] = np.maximum(k[p, 3 + mr:10 + mr, 3 + mc:10 + mc], a[p])
    return torch.from_numpy(k[None])


def rings():
    r = np.array([[min(i, j, 7 - i, 7 - j) for j in range(8)] for i in range(8)])
    R = np.stack([(r == k).astype(np.float32) for k in range(4)])             # (4,8,8)
    cent = (r.astype(np.float32) / 3.0)                                        # 0 edge .. 1 centre
    return torch.from_numpy(R), torch.from_numpy(cent)


class Hybrid(nn.Module):
    def __init__(s, base, w):
        super().__init__()
        s.base, s.w = base, {**DEFAULT, **w}
        s.register_buffer("reach", reach_kernel())
        s.register_buffer("reach2", reach2_kernel())
        s.register_buffer("adj", torch.ones(1, 5, 3, 3))                      # guards: ping daemon exploit trace ice
        R, cent = rings()
        s.register_buffer("R", R[None])                                        # (1,4,8,8)
        s.register_buffer("Rn", R.sum((1, 2))[None])                           # (1,4) squares per ring
        s.register_buffer("cent", cent[None, None])
        s.register_buffer("shift", torch.diag(torch.ones(3), 1))
        s.register_buffer("e0", torch.tensor([[1.0, 0, 0, 0]]))
        s.register_buffer("val", torch.tensor(VAL).reshape(1, 6, 1, 1))

    def side_feats(s, att, dfn):
        """att: attacker planes (B,6,8,8); dfn: defender planes. -> relu(reach on defender Kernel - guards)."""
        reach = nn.functional.conv2d(att, s.reach, padding=3)                  # (B,1,8,8)
        guards = nn.functional.conv2d(dfn[:, 0:5], s.adj, padding=1)
        k = dfn[:, 5:6]
        return torch.relu(((reach - guards) * k).sum((1, 2, 3)))

    def side_feats2(s, att, dfn):
        """2-action threat on the defender Kernel: up to 2 direct attacks, or 1 attack after a move, minus guards."""
        r1 = nn.functional.conv2d(att, s.reach, padding=3)
        r2 = torch.clamp(nn.functional.conv2d(att, s.reach2, padding=6), 0, 1)
        guards = nn.functional.conv2d(dfn[:, 0:5], s.adj, padding=1)
        t = torch.clamp(torch.clamp(r1, 0, 2) + r2, 0, 2)
        return (torch.relu(t - guards) * dfn[:, 5:6]).sum((1, 2, 3))

    def forward(s, x):
        w = s.w
        h = s.base.body(s.base.stem(x))
        p = s.base.pol(h)
        p = torch.flatten(p.permute(0, 2, 3, 1), 1)
        z = s.base.vfc(torch.flatten(s.base.vconv(h), 1)).reshape(-1)

        own, en = x[:, 0:6], x[:, 6:12]
        own_any = torch.flatten(own.sum(1), 1).unsqueeze(2)
        en_val = (en * s.val).sum(1) + en[:, 5] * w["kcap"]
        bonus = own_any * torch.flatten(en_val, 1).unsqueeze(1)                            # (B,64from,64to)
        p = p + w["cap"] * torch.flatten(bonus, 1)

        a = x[:, 13].mean((1, 2))                                              # 1.0 = 2 actions left, 0.5 = 1
        u = x[:, 14].mean((1, 2))
        myk = s.side_feats(en, own) * (1.5 - a)
        enk = s.side_feats(own, en) * (a + 0.0)
        lockr = (x[:, 12:13] * s.R).sum((2, 3)) / s.Rn                         # (B,4) ring k locked fraction
        prev = lockr @ s.shift + s.e0                                       # [1, l0, l1, l2]
        doom = (prev * (1 - lockr)).unsqueeze(2).unsqueeze(3)
        D = (doom * s.R).sum(1)                                                # (B,8,8) next ring to lock
        g = torch.relu(u - 0.6) / 0.4
        own_n, en_n = own[:, 0:5].sum(1), en[:, 0:5].sum(1)
        fire = ((own[:, 5] * 3 + own_n * 0.3 - en[:, 5] * 3 - en_n * 0.3) * D).sum((1, 2)) * g
        kc = ((own[:, 5] - en[:, 5]) * s.cent[:, 0]).sum((1, 2)) * (0.3 + u)
        enk2 = s.side_feats2(own, en) * (2 * a - 1)                            # we move next with 2 actions
        myk2 = s.side_feats2(en, own) * (2 - 2 * a)                            # 1 action left, then they get 2
        f = -w["myk"] * myk + w["enk"] * enk - w["fire"] * fire + w["kcent"] * kc + w["enk2"] * enk2 - w["myk2"] * myk2
        v = w["vcap"] * torch.tanh(z + f)
        return p, v


def build(base_pt, out, w):
    sd = torch.load(base_pt, map_location="cpu")
    ch = int(sd["stem.0.weight"].shape[0]); blocks = len({k.split(".")[1] for k in sd if k.startswith("body.")})
    base = Net(ch, blocks); base.load_state_dict(sd); base.eval()
    m = Hybrid(base, w).eval()
    export(m, out)
    return m


if __name__ == "__main__":
    w = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    build(sys.argv[1], sys.argv[2], w)
    print("built", sys.argv[2], {**DEFAULT, **w})
