import numpy as np, pandas as pd
from collections import Counter, defaultdict
from itertools import combinations

def temps(path):
    d = pd.read_csv(path); d.columns = ["id", "t", "h"]
    d["t"] = np.where(d.t > 54, (d.t - 32) * 5 / 9, d.t)
    return dict(zip(d.id, d.t))

def sym(r):
    n = len(r); return np.mean([r[i] == r[n - 1 - i] for i in range(n // 2)]) if n > 1 else 1

def posagree(rows, lo, hi):
    L = min(len(r) for r in rows); a = []
    for i in range(int(lo * L), max(int(hi * L), int(lo * L) + 1)):
        c = Counter(r[i] for r in rows); a.append(c.most_common(1)[0][1] / len(rows))
    return np.mean(a)

def flock_feats(fl, T):
    edges = {f: set(frozenset(e) for r in rows for e in zip(r, r[1:])) for f, rows in fl.items()}
    nodes = {f: set(x for r in rows for x in r) for f, rows in fl.items()}
    node_owner = defaultdict(set)
    for f, ns in nodes.items():
        for x in ns: node_owner[x].add(f)
    edge_owner = defaultdict(set)
    for f, es in edges.items():
        for e in es: edge_owner[e].add(f)
    out = {}
    for f, rows in fl.items():
        n = len(rows); lens = [len(r) for r in rows]
        inner = [x for r in rows for x in r[1:-1]]
        tt = [T.get(x, np.nan) for x in inner] or [np.nan]
        pref = 0
        for col in zip(*rows):
            if len(set(col)) > 1: break
            pref += 1
        jac = [len(set(a) & set(b)) / len(set(a) | set(b)) for a, b in combinations(rows, 2)] or [1]
        # containment in other flocks
        other_nodes = Counter(g for x in nodes[f] for g in node_owner[x] if g != f)
        other_edges = Counter(g for e in edges[f] for g in edge_owner[e] if g != f)
        cn = max(other_nodes.values(), default=0) / len(nodes[f])
        ce = max(other_edges.values(), default=0) / max(len(edges[f]), 1)
        shared_nodes = np.mean([len(node_owner[x]) > 1 for x in nodes[f]])
        rep_in_row = np.mean([1 - len(set(r[1:-1])) / max(len(r) - 2, 1) for r in rows])
        cnt = Counter(inner)
        out[f] = dict(
            n=n, len_mean=np.mean(lens), len_std=np.std(lens), len_min=min(lens), len_max=max(lens),
            pal=np.mean([r == r[::-1] for r in rows]), sym=np.mean([sym(r) for r in rows]),
            ident=len(set(rows)) == 1, uniq_rows=len(set(rows)) / n,
            closed=np.mean([r[0] == r[-1] for r in rows]), same_start=len(set(r[0] for r in rows)) == 1,
            pref=pref, pref_rel=pref / np.mean(lens),
            a_q1=posagree(rows, 0, .25), a_q2=posagree(rows, .25, .5), a_q3=posagree(rows, .5, .75), a_q4=posagree(rows, .75, 1),
            jac=np.mean(jac), jac_min=min(jac),
            nodes_per_row=len(nodes[f]) / n, node_reuse=1 - len(set(inner)) / max(len(inner), 1),
            max_cnt=max(cnt.values(), default=0) / n, rep_in_row=rep_in_row,
            t_mean=np.nanmean(tt), t_min=np.nanmin(tt), t_max=np.nanmax(tt), t_std=np.nanstd(tt),
            cont_nodes=cn, cont_edges=ce, shared_nodes=shared_nodes,
        )
    return pd.DataFrame(out).T.astype(float)
