import numpy as np, pandas as pd, pathlib, io
from collections import Counter
HERE = pathlib.Path(__file__).resolve().parent / "files"

def temps():
    a = pd.read_csv(HERE / "all_data_from_level_1.in"); a.columns = ["BOP", "T", "H"]
    t = pd.to_numeric(a["T"], errors="coerce"); t = np.where(t >= 55, (t - 32) * 5 / 9, t)
    return dict(zip(a.BOP, t))

def load(text):
    d = pd.read_csv(io.StringIO(text)); d.columns = ["f", "p", "s"]
    d["p"] = d.p.map(lambda s: tuple(int(x) for x in str(s).split()))
    return d

def edges(p): return {frozenset(e) for e in zip(p, p[1:]) if e[0] != e[1]}

def feats(d, T, blue_edges=None):
    rows = []
    for f, g in d.groupby("f", sort=False):
        P = list(g.p)
        L = np.array([len(p) for p in P])
        pal = np.mean([np.mean([a == b for a, b in zip(p, p[::-1])]) for p in P])
        # strip padding repeats
        Q = [tuple(x for i, x in enumerate(p) if i == 0 or x != p[i - 1]) for p in P]
        palq = np.mean([np.mean([a == b for a, b in zip(p, p[::-1])]) for p in Q])
        pad = np.mean([len(p) - len(q) for p, q in zip(P, Q)])
        nodes = [set(p) for p in Q]
        jac = [len(a & b) / len(a | b) for i, a in enumerate(nodes) for b in nodes[i + 1:]] or [1]
        pos = [np.mean([x == y for x, y in zip(a, b)]) for i, a in enumerate(Q) for b in Q[i + 1:]] or [1]
        allnodes = set().union(*nodes)
        t = np.array([T.get(x, np.nan) for p in Q for x in p[1:-1]], float)
        cnt = Counter(x for p in Q for x in p)
        start_same = len({p[0] for p in Q}) == 1
        mid = [np.mean([x == y for x, y in zip(a[:len(a)//2], b[:len(b)//2])]) for i, a in enumerate(Q) for b in Q[i + 1:]] or [1]
        sec = [np.mean([x == y for x, y in zip(a[len(a)//2:], b[len(b)//2:])]) for i, a in enumerate(Q) for b in Q[i + 1:]] or [1]
        inner_rep = np.mean([1 - len(set(p[1:-1])) / max(1, len(p) - 2) for p in Q])
        E = set().union(*[edges(p) for p in Q])
        be = len(E & blue_edges) / max(1, len(E)) if blue_edges is not None else 0
        rows.append(dict(f=f, s=g.s.iloc[0], n=len(P), Lm=L.mean(), Ls=L.std(), Lq=np.mean([len(q) for q in Q]),
                         pal=pal, palq=palq, pad=pad, jac=np.mean(jac), pos=np.mean(pos), firsthalf=np.mean(mid),
                         secondhalf=np.mean(sec), uniq=len(allnodes) / sum(len(q) for q in Q), tm=np.nanmean(t),
                         tmed=np.nanmedian(t), tmin=np.nanmin(t), tmax=np.nanmax(t), hot=np.nanmean(t > 35),
                         closed=np.mean([p[0] == p[-1] for p in Q]), inner_rep=inner_rep, blue=be))
    return pd.DataFrame(rows)
