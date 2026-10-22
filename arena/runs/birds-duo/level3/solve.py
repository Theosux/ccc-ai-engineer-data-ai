import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import io
import numpy as np, pandas as pd
from scipy.optimize import linear_sum_assignment

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Flock ID,Species"
SPECIES = [s.strip() for s in (HERE / "level_3_species.in").read_text(encoding="utf-8").splitlines() if s.strip()]


def temps():
    d = pd.read_csv(HERE / "all_data_from_level_1.in")
    d.columns = ["id", "t", "h"]
    d["t"] = np.where(d.t > 54, (d.t - 32) * 5 / 9, d.t)
    return dict(zip(d.id, d.t))


def load(text):
    fl = {}
    for line in text.strip().splitlines()[1:]:
        f, p = line.split(",")
        fl.setdefault(int(f), []).append(tuple(map(int, p.split())))
    return fl


def prefix(rows):
    n = 0
    for col in zip(*rows):
        if len(set(col)) > 1:
            break
        n += 1
    return n


def features(fl, T):
    feat = {}
    for f, rows in fl.items():
        nodes = set(x for r in rows for x in r)
        inner = [x for r in rows for x in r[1:-1]]
        feat[f] = dict(
            pal=np.mean([r == r[::-1] for r in rows]),
            ident=float(len(set(rows)) == 1),
            pre=prefix(rows),
            nodes=nodes,
            reuse=1 - len(set(inner)) / max(len(inner), 1),
            temp=np.mean([T.get(x, np.nan) for x in inner or list(nodes)]),
        )
    ts = np.array([v["temp"] for v in feat.values()])
    for f, v in feat.items():
        v["tz"] = (v["temp"] - ts.mean()) / (ts.std() + 1e-9)
        # share of my nodes that lie on a (bigger) palindrome route
        v["sub"] = max([len(v["nodes"] & w["nodes"]) / len(v["nodes"]) for g, w in feat.items()
                        if g != f and w["pal"] > 0.5 and len(w["nodes"]) > len(v["nodes"])] or [0])
    return feat


def score(v, sp):
    multi = 1 - v["ident"]
    if sp == "Medieval Bluetit":
        return 10 * v["pal"] - 6 * v["sub"]
    if sp == "Sticky Wolfthroat":
        return 12 * v["sub"]
    if sp == "Flanking Blackfinch":
        return 10 * v["ident"] * (1 - v["pal"])
    if sp == "Rusty Goldhammer":
        return 10 * multi * (v["pre"] >= 2) + v["pre"] / 100
    hot = 2 * v["tz"] + 5 * v["reuse"]
    base = 10 * multi * (v["pre"] <= 1) * (1 - v["pal"])
    if sp == "Hurracurra Bird":
        return base + hot
    if sp == "Red Firefinch":
        return base - hot
    raise ValueError(sp)


def assign(text):
    fl = load(text)
    feat = features(fl, temps())
    ids = sorted(fl)
    S = np.array([[score(feat[f], s) for s in SPECIES] for f in ids])
    r, c = linear_sum_assignment(-S)
    for f in ids:
        v = feat[f]
        print(f"  flock {f}: pal={v['pal']:.2f} ident={v['ident']:.0f} pre={v['pre']} sub={v['sub']:.2f} "
              f"reuse={v['reuse']:.2f} temp={v['temp']:.1f}", file=sys.stderr)
    return {ids[i]: SPECIES[j] for i, j in zip(r, c)}


def main():
    a = assign(sys.stdin.read())
    print(HEAD)
    for f in sorted(a):
        print(f"{f},{a[f]}")


def check(data, out):
    fl = load(data)
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "header"
    rows = [l.split(",") for l in lines[1:]]
    if [int(r[0]) for r in rows] != sorted(fl):
        return False, "flock ids"
    sp = [r[1] for r in rows]
    if any(s not in SPECIES for s in sp) or (len(fl) == len(SPECIES) and len(set(sp)) != len(sp)):
        return False, "species"
    return True, " ".join(f"{r[0]}={r[1].split()[-1]}" for r in rows)


if __name__ == "__main__":
    main()
