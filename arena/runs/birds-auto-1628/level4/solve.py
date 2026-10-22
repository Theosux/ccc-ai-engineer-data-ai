import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from feats import HERE, temps, load, edges, feats

HEAD = "Flock ID,Species"
SPECIES = [l.strip() for l in (HERE / "level_4_species.in").read_text(encoding="utf-8").splitlines() if l.strip()]


def dedup(p):
    return tuple(x for i, x in enumerate(p) if i == 0 or x != p[i - 1])


def build(d, T):
    F = feats(d, T, None)
    E = {f: set().union(*[edges(dedup(p)) for p in g.p]) for f, g in d.groupby("f", sort=False)}
    palf = set(F.f[F.palq > 0.8])
    F["blue"] = [len(E[f] & set().union(*[E[h] for h in palf if h != f])) / max(1, len(E[f])) for f in F.f]
    return F


def main():
    T = temps()
    d = load(sys.stdin.read())
    main_d = load((HERE / "in_level-4_1-main.txt").read_text(encoding="utf-8"))
    Fm = build(main_d, T)
    tr = Fm[Fm.s != "missing"]
    Fd = build(d, T) if len(d) != len(main_d) else Fm
    te = Fd[Fd.s == "missing"]
    cols = [c for c in tr.columns if c not in ("f", "s")]
    m = ExtraTreesClassifier(1000, random_state=0, n_jobs=-1).fit(tr[cols].values.astype(float), np.array(tr.s.tolist()))
    pred = m.predict(te[cols].values.astype(float)) if len(te) else []
    print(HEAD)
    for f, p in zip(te.f, pred):
        print(f"{f},{p}")
    from collections import Counter
    print(Counter(pred), file=sys.stderr)


def check(data, out):
    d = load(data)
    want = [str(f) for f in d[d.s == "missing"].f.drop_duplicates()]
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "header"
    rows = [l.split(",") for l in lines[1:]]
    ok = [r[0] for r in rows] == want and all(r[1] in SPECIES for r in rows)
    return ok, f"{len(rows)} rows vs {len(want)}"


if __name__ == "__main__":
    main()
