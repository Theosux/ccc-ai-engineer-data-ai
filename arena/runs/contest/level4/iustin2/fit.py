"""Fit value = tanh(features . w + b) on self-play outcomes; compare with v1/n1 values on held-out games.
usage (env4/.venv python, cwd iustin2): fit.py"""
import glob, json, sys
import numpy as np, torch, onnxruntime as ort
from feat import features, NAMES

D = "../env4/data"
files = sorted(glob.glob(f"{D}/g1.part*.npz"), key=lambda s: int(s.split("part")[1].split(".")[0]))
tr_f, te_f = files[:-2], files[-2:]                                  # held-out = whole worker files (other games)


def load(fs):
    P, Z = [], []
    for f in fs:
        d = np.load(f); P.append(d["P"]); Z.append(d["Z"])
    return np.concatenate(P).astype(np.float32), np.concatenate(Z).astype(np.float32)


Ptr, Ztr = load(tr_f); Pte, Zte = load(te_f)
Xtr, Xte = features(Ptr), features(Pte)
mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
xt, yt = torch.tensor((Xtr - mu) / sd), torch.tensor(Ztr)
w = torch.zeros(xt.shape[1], requires_grad=True); b = torch.zeros(1, requires_grad=True)
opt = torch.optim.LBFGS([w, b], max_iter=500, line_search_fn="strong_wolfe")


def closure():
    opt.zero_grad()
    v = torch.tanh(xt @ w + b)
    loss = ((v - yt) ** 2).mean() + 1e-4 * (w ** 2).sum()
    loss.backward(); return loss


opt.step(closure)
W = w.detach().numpy() / sd; B = float(b.detach()) - float((w.detach().numpy() * mu / sd).sum())


def metrics(v, z):
    return dict(mse=float(((v - z) ** 2).mean()), acc=float(((v > 0) == (z > 0)).mean()))


mine = np.tanh(Xte @ W + B)
out = {"mine": metrics(mine, Zte)}
for name in ("v1", "n1", "t0"):
    try:
        s = ort.InferenceSession(f"../env4/{name}.onnx", providers=["CPUExecutionProvider"])
        vals = np.concatenate([s.run(["value"], {"observation": Pte[i:i + 4096]})[0] for i in range(0, len(Pte), 4096)])
        out[name] = metrics(vals, Zte)
    except Exception as e:
        out[name] = str(e)[:100]
print(f"train {len(Ztr)}  test {len(Zte)}  (held-out games)")
for k, v in out.items():
    print(k, v)
print("weights:", ", ".join(f"{n}={x:+.3f}" for n, x in sorted(zip(NAMES, W), key=lambda t: -abs(t[1]))))
json.dump({"W": W.tolist(), "B": B, "names": NAMES}, open("value_w.json", "w"))
