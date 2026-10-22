import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from lib.ml import to_num, log
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
    f = {}
    for l in text.strip().splitlines()[1:]:
        k, p = l.split(",")
        f.setdefault(int(k), []).append([int(x) for x in p.split()])
    return f


def common_prefix(paths):
    n = 0
    while all(len(p) > n and p[n] == paths[0][n] for p in paths):
        n += 1
    return n


def classify(f, T):
    left, out = set(f), {}
    same = {k for k in f if all(p == f[k][0] for p in f[k])}
    pal = {k for k in same if f[k][0] == f[k][0][::-1]}
    nodes = {k: set(x for p in f[k] for x in p) for k in f}
    # Bluetit: palindrome (back along the same route); Wolfthroat: lies on segments of the Bluetit route
    blue = max(pal, key=lambda k: len(nodes[k])) if pal else None
    if blue is not None:
        out[blue] = "Medieval Bluetit"
        wolf = [k for k in left - {blue} if nodes[k] <= nodes[blue]]
        if wolf:
            out[min(wolf, key=lambda k: len(nodes[k]))] = "Sticky Wolfthroat"
    left -= set(out)
    # Blackfinch: the whole flock orbits together (identical cyclic path, not a palindrome)
    bf = [k for k in left & same]
    if bf:
        out[max(bf, key=lambda k: len(f[k]))] = "Flanking Blackfinch"
    left -= set(out)
    # Goldhammer: together on the way out, split on the way back (long common prefix, then different)
    if left:
        g = max(left, key=lambda k: common_prefix(f[k]) / max(len(p) for p in f[k]))
        if common_prefix(f[g]) > 2:
            out[g] = "Rusty Goldhammer"
    left -= set(out)
    # Hurracurra: hot regions; Firefinch: shared nest, solo adventures
    mean_t = {k: sum(T[x] for p in f[k] for x in p) / sum(len(p) for p in f[k]) for k in left}
    for k in sorted(left, key=lambda k: -mean_t[k]):
        out[k] = "Hurracurra Bird" if "Hurracurra Bird" not in out.values() else "Red Firefinch"
    log({k: (out[k], round(mean_t.get(k, 0), 1)) for k in sorted(out)})
    return out


def main():
    out = classify(flocks(sys.stdin.read()), temps())
    print(HEAD)
    for k in sorted(out):
        print(f"{k},{out[k]}")


def check(data, out):
    f = flocks(data)
    sp = (HERE / "level_3_species.in").read_text(encoding="utf-8").split("\n")
    sp = {s.strip() for s in sp if s.strip()}
    lines = out.strip().splitlines()
    got = dict(l.split(",") for l in lines[1:])
    ok = lines[0] == HEAD and sorted(int(k) for k in got) == sorted(f) and set(got.values()) <= sp \
        and len(set(got.values())) == len(got)
    return ok, str(got)


if __name__ == "__main__":
    main()
