"""Per-flock features encoding the species riddles of level 3 (shared by level 4 solve.py and experiments)."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import io
from collections import Counter
from itertools import combinations
import numpy as np
import pandas as pd
from lib.ml import read_csv, clean_numeric

HERE = pathlib.Path(__file__).resolve().parent / "files"


def temps():
    d = clean_numeric(read_csv((HERE / "all_data_from_level_1.in").read_text(encoding="utf-8")), report=False)
    tc = np.where(d.temperature > 50, (d.temperature - 32) * 5 / 9, d.temperature)
    return {str(b): t for b, t in zip(d.bop, tc)}


def load(text):
    d = pd.read_csv(io.StringIO(text))
    d.columns = ["flock", "path", "species"][:len(d.columns)]
    d["p"] = d.path.str.split()
    return d


def pal(r):
    n = len(r)
    return sum(r[i] == r[n - 1 - i] for i in range(n // 2)) / max(1, n // 2)


def prefix(rows):
    k = 0
    while all(len(r) > k and r[k] == rows[0][k] for r in rows):
        k += 1
    return k


def suffix(rows):
    return prefix([r[::-1] for r in rows])


def jacc(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b)


def posq(a, b):
    n = min(len(a), len(b))
    return sum(x == y for x, y in zip(a, b)) / max(len(a), len(b)) if n else 0


def features(d, T):
    groups = {f: list(g.p) for f, g in d.groupby("flock", sort=False)}
    node_flocks = Counter(b for rows in groups.values() for b in {x for r in rows for x in r})
    out = []
    for f, rows in groups.items():
        L = [len(r) for r in rows]
        nodes = [b for r in rows for b in r]
        uniq = set(nodes)
        pairs = list(combinations(rows, 2))[:200]
        inner = [b for r in rows for b in r[1:-1]] or nodes
        t = [T.get(b, np.nan) for b in inner]
        out.append(dict(
            flock=f, n=len(rows), len_mean=np.mean(L), len_std=np.std(L),
            pal=np.mean([pal(r) for r in rows]), closed=np.mean([r[0] == r[-1] for r in rows]),
            same_start=float(len({r[0] for r in rows}) == 1),
            jac=np.mean([jacc(a, b) for a, b in pairs]) if pairs else 1.0,
            pos=np.mean([posq(a, b) for a, b in pairs]) if pairs else 1.0,
            pre=prefix(rows) / np.mean(L), suf=suffix(rows) / np.mean(L),
            uniq_ratio=len(uniq) / len(nodes),
            rep_in_row=np.mean([1 - len(set(r[1:-1])) / max(1, len(r) - 2) for r in rows]),
            t_mean=np.nanmean(t), t_min=np.nanmin(t), t_max=np.nanmax(t),
            shared=np.mean([node_flocks[b] - 1 for b in uniq]),
            shared_frac=np.mean([node_flocks[b] > 1 for b in uniq]),
        ))
    return pd.DataFrame(out).set_index("flock")
