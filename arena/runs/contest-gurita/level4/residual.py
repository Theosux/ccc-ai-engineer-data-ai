"""Linear seat model plus a zero-init conv residual, trained on MCTS visit targets.

The residual starts at 0, so an untrained export ties the linear model. Training
only has to learn a correction.
"""
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ENV = Path(__file__).resolve().parents[2] / "contest" / "level4" / "env4"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ENV))


class Residual(nn.Module):
    def __init__(self, ch=32):
        super().__init__()
        import importlib.util
        spec = importlib.util.spec_from_file_location("build4", ENV / "build4.py")
        b4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(b4)
        P = b4.default_params()
        self.register_buffer("W", torch.tensor(P["W"].reshape(16, 64)))
        self.register_buffer("A", torch.tensor(P["A"]))
        self.register_buffer("Bt", torch.tensor(P["Bt"]).view(16))
        self.stem = nn.Sequential(nn.Conv2d(16, ch, 3, padding=1), nn.ReLU())
        self.body = nn.Sequential(nn.Conv2d(ch, ch, 3, padding=1), nn.ReLU(), nn.Conv2d(ch, ch, 3, padding=1), nn.ReLU())
        self.pol = nn.Conv2d(ch, 64, 1)
        self.vh = nn.Linear(ch, 1)
        nn.init.zeros_(self.pol.weight); nn.init.zeros_(self.pol.bias)
        nn.init.zeros_(self.vh.weight); nn.init.zeros_(self.vh.bias)

    def linear(self, x):
        # x (B,16,8,8)
        flat = x.flatten(2)                       # (B,16,64)
        value = torch.tanh((flat * self.W).sum((1, 2)))
        pol = torch.einsum("bpf,pt->bft", flat, self.A) + torch.einsum("q,bqt->bt", self.Bt, flat).unsqueeze(1)
        return pol.reshape(x.shape[0], -1), value

    def forward(self, x):
        lp, lv = self.linear(x)
        h = self.body(self.stem(x))
        rp = self.pol(h).permute(0, 2, 3, 1).flatten(1)
        rv = self.vh(h.mean((2, 3))).reshape(-1)
        return lp + rp, torch.tanh(lv + 0.5 * rv)


def main():
    d = np.load(HERE / "distill.npz")
    P = d["P"].astype(np.float32); PI = d["PI"].astype(np.float32); Z = d["Z"].astype(np.float32)
    sys.path.insert(0, str(ENV))
    from net import augment_flip, export
    P2, PI2 = augment_flip(P, PI)
    P = np.concatenate([P, P2]); PI = np.concatenate([PI, PI2]); Z = np.concatenate([Z, Z])
    net = Residual()
    opt = torch.optim.AdamW([p for n, p in net.named_parameters() if not n.startswith(("W", "A", "Bt"))], lr=1e-3, weight_decay=1e-4)
    Pt, PIt, Zt = torch.from_numpy(P), torch.from_numpy(PI), torch.from_numpy(Z)
    bs = 256
    for ep in range(12):
        net.train()
        idx = torch.randperm(len(Z))
        pols, vals = [], []
        for i in range(0, len(Z) - bs, bs):
            b = idx[i:i + bs]
            p, v = net(Pt[b])
            legal = PIt[b] > 0
            lp = F.log_softmax(p.masked_fill(~legal, -1e9), 1)
            lpol = -(PIt[b] * lp).sum(1).mean()
            lval = F.mse_loss(v, Zt[b])
            loss = lpol + lval
            opt.zero_grad(); loss.backward(); opt.step()
            pols.append(lpol.item()); vals.append(lval.item())
        print(f"ep {ep} pol {np.mean(pols):.3f} val {np.mean(vals):.3f}", flush=True)
    net.eval()
    out = HERE / "gurita_res.onnx"
    export(net, str(out))
    print("exported", out, out.stat().st_size)


if __name__ == "__main__":
    main()
