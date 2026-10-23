"""Small AlphaZero-style policy/value net + training + ONNX export.
usage: net.py train OUT.onnx data_glob [--init prev.pt] [--epochs N] [--ch C] [--blocks K]"""
import sys, glob, argparse, time, numpy as np, torch, torch.nn as nn, torch.nn.functional as F

torch.set_num_threads(12)


class Block(nn.Module):
    def __init__(s, c):
        super().__init__()
        s.c1 = nn.Conv2d(c, c, 3, padding=1); s.b1 = nn.BatchNorm2d(c)
        s.c2 = nn.Conv2d(c, c, 3, padding=1); s.b2 = nn.BatchNorm2d(c)

    def forward(s, x):
        y = F.relu(s.b1(s.c1(x)))
        return F.relu(x + s.b2(s.c2(y)))


class Net(nn.Module):
    def __init__(s, ch=32, blocks=3):
        super().__init__()
        s.stem = nn.Sequential(nn.Conv2d(16, ch, 3, padding=1), nn.BatchNorm2d(ch), nn.ReLU())
        s.body = nn.Sequential(*[Block(ch) for _ in range(blocks)])
        s.pol = nn.Conv2d(ch, 64, 1)                 # channel = to-square, spatial = from-square
        s.vconv = nn.Sequential(nn.Conv2d(ch, 2, 1), nn.BatchNorm2d(2), nn.ReLU())
        s.vfc = nn.Sequential(nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(s, x):
        h = s.body(s.stem(x))
        p = s.pol(h)                                 # (B,64to,8,8from)
        p = torch.flatten(p.permute(0, 2, 3, 1), 1)   # (B, from*64+to)
        v = torch.tanh(s.vfc(torch.flatten(s.vconv(h), 1))).reshape(-1)
        return p, v


def load(globs):
    P, PI, Z = [], [], []
    for g in globs:
        for f in sorted(glob.glob(g)):
            d = np.load(f)
            P.append(d["P"]); PI.append(d["PI"]); Z.append(d["Z"])
    return np.concatenate(P).astype(np.float16), np.concatenate(PI).astype(np.float16), np.concatenate(Z)


def augment_flip(P, PI):
    """left-right mirror: col -> 7-col (rules are symmetric under it)."""
    P2 = P[:, :, :, ::-1].copy()
    a = np.arange(4096); f, t = a // 64, a % 64
    fm = (f // 8) * 8 + (7 - f % 8); tm = (t // 8) * 8 + (7 - t % 8)
    PI2 = np.zeros_like(PI); PI2[:, fm * 64 + tm] = PI[:, a]
    return P2, PI2


def export(net, path):
    net.eval()
    x = torch.zeros(2, 16, 8, 8)
    torch.onnx.export(net, x, path, input_names=["observation"], output_names=["policy", "value"],
                      dynamic_axes={"observation": {0: "batch"}, "policy": {0: "batch"}, "value": {0: "batch"}},
                      opset_version=17, external_data=False, dynamo=False)
    import onnx
    from onnx import numpy_helper
    m = onnx.load(path)
    keep = []
    for nd in m.graph.node:
        if nd.op_type == "Constant":
            t = onnx.helper.get_attribute_value(nd.attribute[0])
            arr = numpy_helper.to_array(t)
            m.graph.initializer.append(numpy_helper.from_array(arr, nd.output[0]))
        else:
            keep.append(nd)
    del m.graph.node[:]
    m.graph.node.extend(keep)
    print("ops", sorted({n.op_type for n in m.graph.node}))
    onnx.save(m, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("data", nargs="+")
    ap.add_argument("--init"); ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--ch", type=int, default=32); ap.add_argument("--blocks", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-3); ap.add_argument("--flip", type=int, default=1)
    a = ap.parse_args()
    P, PI, Z = load(a.data)
    if a.flip:
        P2, PI2 = augment_flip(P, PI)
        P, PI, Z = np.concatenate([P, P2]), np.concatenate([PI, PI2]), np.concatenate([Z, Z])
    n = len(Z); print("positions", n, "z mean", Z.mean(), flush=True)
    b = None
    rng = np.random.default_rng(0); perm = rng.permutation(n); nv = min(5000, n // 10)
    va, tr = perm[:nv], perm[nv:]
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    net = Net(a.ch, a.blocks)
    if a.init:
        net.load_state_dict(torch.load(a.init))
    net = net.to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=1e-4)
    Pt, PIt, Zt = torch.from_numpy(P), torch.from_numpy(PI), torch.from_numpy(Z)
    bs = 512; steps = a.epochs * (len(tr) // bs)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, a.lr, total_steps=steps)
    t0 = time.time()
    for ep in range(a.epochs):
        net.train(); rng.shuffle(tr)
        for i in range(len(tr) // bs):
            b = tr[i * bs:(i + 1) * bs]
            xb, pib, zb = Pt[b].to(dev).float(), PIt[b].to(dev).float(), Zt[b].to(dev)
            p, v = net(xb)
            lp = F.log_softmax(p, dim=1)
            lpol = -(pib * lp).sum(1).mean()
            lval = F.mse_loss(v, zb)
            loss = lpol + lval
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        net.eval()
        with torch.no_grad():
            xv, piv, zv = Pt[va].to(dev).float(), PIt[va].to(dev).float(), Zt[va].to(dev)
            p, v = net(xv)
            lpol = -(piv * F.log_softmax(p, 1)).sum(1).mean().item()
            lval = F.mse_loss(v, zv).item()
            acc = ((v > 0) == (zv > 0)).float().mean().item()
        print(f"ep {ep} val pol {lpol:.3f} val mse {lval:.3f} sign acc {acc:.3f} ({time.time()-t0:.0f}s)", flush=True)
    net = net.cpu()
    torch.save(net.state_dict(), a.out.replace(".onnx", ".pt"))
    export(net, a.out)
    print("exported", a.out)


if __name__ == "__main__":
    main()
