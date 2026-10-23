"""Ensemble of env4/net.py nets in one ONNX, with optional opening sharpening.
policy = mean(log_softmax(p_i)) * (1 + sharp * opening), value = mean(v_i)
opening = no locked squares and firewall urgency <= 0.25 (rounds 1-2: the referee's sampled warmup)
usage (cwd env4, .venv python): [MB=0.3] ../iustin3/ens.py OUT.onnx SHARP a.pt [b.pt ...]"""
import os, sys, torch, torch.nn as nn
sys.path.insert(0, ".")
from net import Net, export


def load(pt):
    sd = torch.load(pt, map_location="cpu")
    ch = int(sd["stem.0.weight"].shape[0]); bl = len({k.split(".")[1] for k in sd if k.startswith("body.")})
    n = Net(ch, bl); n.load_state_dict(sd); return n.eval()


class Ens(nn.Module):
    def __init__(s, nets, sharp, mb=0.0):
        super().__init__()
        s.nets, s.sharp, s.mb = nn.ModuleList(nets), sharp, mb

    def forward(s, x):
        x = torch.clamp(x, 0, 1)                      # the validator feeds extreme inputs; planes are 0..1
        ps, vs = zip(*[n(x) for n in s.nets])
        p = sum(torch.log_softmax(q, 1) for q in ps) / len(ps)
        v = torch.clamp(sum(vs) / len(vs), -1, 1)
        if s.sharp:
            lock = x[:, 12].sum((1, 2))
            u = x[:, 14].mean((1, 2))
            op = torch.relu(1 - lock) * (u < 0.3).float()
            p = p * (1 + s.sharp * op).unsqueeze(1)
        if s.mb:
            # Magenta wins the tiebreak: shift value toward Magenta as the final locks approach (zero-sum: Cyan gets -)
            side = x[:, 15].mean((1, 2)); u = x[:, 14].mean((1, 2))
            v = torch.clamp(v + s.mb * u * (2 * side - 1), -1, 1)
        return p, v


if __name__ == "__main__":
    out, sharp = sys.argv[1], float(sys.argv[2])
    mb = float(os.environ.get("MB", "0"))             # Magenta tiebreak value bias
    export(Ens([load(p) for p in sys.argv[3:]], sharp, mb).eval(), out)
    print("built", out, sharp, sys.argv[3:])
