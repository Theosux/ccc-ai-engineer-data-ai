import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from lib.ml import to_num, log, best_model
import itertools
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Flock ID,Species"


def temps():
    rows = [l.split(",") for l in (HERE / "all_data_from_level_1.in").read_text(encoding="utf-8").strip().splitlines()[1:]]
    d = pd.DataFrame(rows, columns=["id", "t", "h"])
    for c in d.columns:
        d[c] = to_num(d[c], False)
    d["t"] = d.t.where(d.t <= 50, (d.t - 32) * 5 / 9)
    return dict(zip(d.id.astype(int), d.t))


def flocks(text):
    f, lab = {}, {}
    for l in text.strip().splitlines()[1:]:
        k, p, s = l.split(",")
        f.setdefault(int(k), []).append([int(x) for x in p.split()])
        lab[int(k)] = s.strip()
    return f, lab


def agree(paths, sl):
    """Mean position-wise agreement between bird pairs over the slice sl (fraction of the path)."""
    if len(paths) < 2:
        return 1.0
    v = []
    for a, b in itertools.combinations(paths, 2):
        n = min(len(a), len(b))
        lo, hi = int(n * sl[0]), max(int(n * sl[0]) + 1, int(n * sl[1]))
        v.append(np.mean([a[i] == b[i] for i in range(lo, hi)]))
    return float(np.mean(v))


def feats(paths, T, bluenodes):
    L = [len(p) for p in paths]
    pal = np.mean([np.mean([p[i] == p[-1 - i] for i in range(len(p) // 2)]) for p in paths])
    nodes = [x for p in paths for x in p]
    t = [T.get(x, np.nan) for x in nodes]
    sets = [set(p) for p in paths]
    jac = np.mean([len(a & b) / len(a | b) for a, b in itertools.combinations(sets, 2)]) if len(sets) > 1 else 1
    return {
        "n": len(paths), "len": np.mean(L), "len_sd": np.std(L), "pal": pal,
        "a_all": agree(paths, (0, 1)), "a_h1": agree(paths, (0, .5)), "a_h2": agree(paths, (.5, 1)),
        "a_q1": agree(paths, (0, .25)), "a_q4": agree(paths, (.75, 1)),
        "t_mean": np.nanmean(t), "t_min": np.nanmin(t), "t_max": np.nanmax(t),
        "revisit": np.mean([1 - len(set(p)) / len(p) for p in paths]),
        "uniq": len(set(nodes)) / len(nodes), "jac": jac,
        "cyc": np.mean([p[0] == p[-1] for p in paths]),
        "blue_ov": len(set(nodes) & bluenodes) / len(set(nodes)),
    }


def table(f, T, lab):
    blue = set(x for k in f if lab.get(k) == "Medieval Bluetit" for p in f[k] for x in p)
    rows = []
    for k in sorted(f):
        b = blue - set(x for p in f[k] for x in p) if lab.get(k) == "Medieval Bluetit" else blue
        rows.append({"id": k, "y": lab[k], **feats(f[k], T, b)})
    return pd.DataFrame(rows)


def main():
    T = temps()
    f, lab = flocks(sys.stdin.read())
    if len(f) < 20:  # the tiny example: train on the main file
        f2, lab2 = flocks((HERE / "in_level-4_1-main.txt").read_text(encoding="utf-8"))
        tr = table(f2, T, lab2)
    else:
        tr = None
    d = table(f, T, lab)
    tr = d if tr is None else tr
    tr = tr[tr.y != "missing"]
    X = [c for c in d.columns if c not in ("id", "y")]
    m, _ = best_model(tr[X], tr.y, "clf", "f1")
    te = d[d.y == "missing"]
    print(HEAD)
    for i, p in zip(te.id, m.predict(te[X])):
        print(f"{i},{p}")


def check(data, out):
    f, lab = flocks(data)
    want = sorted(k for k in f if lab[k] == "missing")
    lines = out.strip().splitlines()
    sp = {s.strip() for s in (HERE / "level_4_species.in").read_text(encoding="utf-8").splitlines() if s.strip()}
    got = [l.split(",") for l in lines[1:]]
    return lines[0] == HEAD and [int(a) for a, _ in got] == want and all(b in sp for _, b in got), f"{len(got)} preds"


if __name__ == "__main__":
    main()
