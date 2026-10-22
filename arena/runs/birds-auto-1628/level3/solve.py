import sys, pathlib
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Flock ID,Species"
SPECIES = ["Hurracurra Bird", "Medieval Bluetit", "Flanking Blackfinch", "Rusty Goldhammer", "Red Firefinch",
           "Sticky Wolfthroat"]


def temps():
    a = pd.read_csv(HERE / "all_data_from_level_1.in")
    a.columns = ["BOP", "T", "H"]
    t = pd.to_numeric(a["T"], errors="coerce")
    t = np.where(t >= 55, (t - 32) * 5 / 9, t)
    return dict(zip(a.BOP, t))


def parse(data):
    flocks = {}
    for l in data.strip().splitlines()[1:]:
        f, p = l.split(",")
        flocks.setdefault(f.strip(), []).append(tuple(int(x) for x in p.split()))
    return flocks


def prefix(paths):
    n = 0
    while all(len(p) > n for p in paths) and len({p[n] for p in paths}) == 1:
        n += 1
    return n


def classify(flocks, T):
    ids = list(flocks)
    same = {f: len(set(flocks[f])) == 1 for f in ids}
    pal = {f: all(p == p[::-1] for p in flocks[f]) for f in ids}
    nodes = {f: set(x for p in flocks[f] for x in p) for f in ids}
    heat = {f: np.nanmean([T.get(x, np.nan) for x in nodes[f]]) for f in ids}
    pre = {f: prefix(flocks[f]) for f in ids}
    res = {}
    pals = [f for f in ids if same[f] and pal[f]]
    if len(pals) >= 2:
        pals.sort(key=lambda f: len(nodes[f]))
        small, big = pals[0], pals[-1]
        if not nodes[small] <= nodes[big]:
            print(f"warn: {small} not subset of {big}", file=sys.stderr)
        res[small], res[big] = "Sticky Wolfthroat", "Medieval Bluetit"
    elif len(pals) == 1:
        res[pals[0]] = "Medieval Bluetit"
    rest = [f for f in ids if f not in res]
    bf = [f for f in rest if same[f]]
    for f in bf[:1]:
        res[f] = "Flanking Blackfinch"
    rest = [f for f in ids if f not in res]
    if rest:
        g = max(rest, key=lambda f: pre[f])
        if pre[g] >= 2:
            res[g] = "Rusty Goldhammer"
    rest = sorted([f for f in ids if f not in res], key=lambda f: -heat[f])
    left = [s for s in ["Hurracurra Bird", "Red Firefinch", "Rusty Goldhammer", "Flanking Blackfinch",
                        "Sticky Wolfthroat", "Medieval Bluetit"] if s not in res.values()]
    for f, s in zip(rest, left):
        res[f] = s
    for f in ids:
        print(f"flock {f}: n={len(flocks[f])} same={same[f]} pal={pal[f]} pre={pre[f]} heat={heat[f]:.1f} "
              f"nodes={len(nodes[f])} -> {res[f]}", file=sys.stderr)
    return res


def main():
    flocks = parse(sys.stdin.read())
    res = classify(flocks, temps())
    print(HEAD)
    for f in flocks:
        print(f"{f},{res[f]}")


def check(data, out):
    flocks = parse(data)
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "header"
    rows = [l.split(",") for l in lines[1:]]
    ok = [r[0] for r in rows] == list(flocks) and all(r[1] in SPECIES for r in rows)
    if len(flocks) == 6:
        ok = ok and len({r[1] for r in rows}) == 6
    return ok, "ok" if ok else "bad ids/species"


if __name__ == "__main__":
    main()
