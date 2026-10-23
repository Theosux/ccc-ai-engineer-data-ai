"""Value MSE/sign-acc vs game result Z on self-play data: base net vs hybrid variants. usage: vcheck.py BASE.pt glob [w json ...]"""
import sys, glob, json, numpy as np, torch
sys.path.insert(0, "."); sys.path.insert(0, "../iustin3")
import hybrid
from net import Net
torch.set_num_threads(2)
files = sorted(glob.glob(sys.argv[2]))[-3:]
P = np.concatenate([np.load(f)["P"] for f in files]).astype(np.float32); Z = np.concatenate([np.load(f)["Z"] for f in files])
idx = np.random.default_rng(0).permutation(len(Z))[:20000]; X, Z = torch.from_numpy(P[idx]), torch.from_numpy(Z[idx]).float()
sd = torch.load(sys.argv[1], map_location="cpu"); ch = int(sd["stem.0.weight"].shape[0]); bl = len({k.split(".")[1] for k in sd if k.startswith("body.")})
base = Net(ch, bl); base.load_state_dict(sd); base.eval()
def rep(name, m):
    with torch.no_grad(): _, v = m(X)
    print(f"{name:50s} mse {((v - Z) ** 2).mean():.4f} sign {((v > 0) == (Z > 0)).float().mean():.4f}")
rep("base", base)
for wj in ["{}"] + sys.argv[3:]:
    rep("hybrid " + wj, hybrid.Hybrid(base, json.loads(wj)).eval())
