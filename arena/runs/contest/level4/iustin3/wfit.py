"""Fit the hybrid feature weights (base frozen) by value MSE on held-out self-play data. usage: wfit.py BASE.pt glob"""
import sys, glob, numpy as np, torch
sys.path.insert(0, "."); sys.path.insert(0, "../iustin3")
import hybrid
from net import Net
torch.set_num_threads(2)
files = sorted(glob.glob(sys.argv[2]))
P = np.concatenate([np.load(f)["P"] for f in files]).astype(np.float32); Z = np.concatenate([np.load(f)["Z"] for f in files])
idx = np.random.default_rng(1).permutation(len(Z))[:40000]; X, Z = torch.from_numpy(P[idx]), torch.from_numpy(Z[idx]).float()
sd = torch.load(sys.argv[1], map_location="cpu"); ch = int(sd["stem.0.weight"].shape[0]); bl = len({k.split(".")[1] for k in sd if k.startswith("body.")})
base = Net(ch, bl); base.load_state_dict(sd); base.eval()
m = hybrid.Hybrid(base, {}).eval()
KS = ("myk", "enk", "fire", "kcent", "enk2", "myk2")
with torch.no_grad():
    h = base.body(base.stem(X)); zn = base.vfc(torch.flatten(base.vconv(h), 1)).reshape(-1)
    # recompute raw features with unit weights by probing f for each feature alone
    feats = []
    for k in KS:
        w = {kk: 0.0 for kk in KS}; w[k] = 1.0; w["vcap"] = 1.0
        m.w = {**hybrid.DEFAULT, **w}
        _, v = m(X)
        feats.append(torch.atanh(v.clamp(-0.999999, 0.999999)) - zn)
F = torch.stack(feats, 1)
print("feature mean", F.mean(0).numpy().round(3), "nonzero frac", (F != 0).float().mean(0).numpy().round(3))
wv = torch.zeros(len(KS), requires_grad=True); a = torch.ones(1, requires_grad=True); vc = torch.tensor([0.0], requires_grad=True)
tr, va = slice(0, 30000), slice(30000, None)
opt = torch.optim.Adam([wv, a, vc], lr=0.02)
for it in range(600):
    v = torch.sigmoid(vc + 3) * torch.tanh(a * zn[tr] + F[tr] @ wv)
    loss = ((v - Z[tr]) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step()
with torch.no_grad():
    for name, v in (("base", torch.tanh(zn[va])), ("fit", torch.sigmoid(vc + 3) * torch.tanh(a * zn[va] + F[va] @ wv))):
        print(name, "val mse", round(((v - Z[va]) ** 2).mean().item(), 4), "sign", round(((v > 0) == (Z[va] > 0)).float().mean().item(), 4))
print("w", KS, "(signed as in f)", wv.detach().numpy().round(3), "a", a.item(), "vcap", torch.sigmoid(vc + 3).item())
