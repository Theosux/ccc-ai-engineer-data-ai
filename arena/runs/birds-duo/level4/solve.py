import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import io
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from feats import flock_feats, temps   # one feature row per flock (palindrome, prefix agreement, containment, temps...)

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Flock ID,Species"
SPECIES = [s.strip() for s in (HERE / "level_4_species.in").read_text(encoding="utf-8").splitlines() if s.strip()]


def load(text):
    d = pd.read_csv(io.StringIO(text))
    d.columns = ["f", "p", "s"]
    fl = {}
    for f, p in zip(d.f, d.p):
        fl.setdefault(int(f), []).append(tuple(map(int, p.split())))
    y = d.groupby("f").s.first()
    return fl, y


def main():
    fl, y = load(sys.stdin.read())
    main_fl, main_y = load((HERE / "in_level-4_1-main.txt").read_text(encoding="utf-8"))
    T = temps(HERE / "all_data_from_level_1.in")
    Xm = flock_feats(main_fl, T)
    ym = main_y.reindex(Xm.index)
    tr = ym != "missing"
    m = ExtraTreesClassifier(1000, random_state=0, n_jobs=-1).fit(Xm[tr], ym[tr])
    X = flock_feats(fl, T)
    te = [f for f in X.index if y[f] == "missing"]
    print(HEAD)
    for f, p in zip(te, m.predict(X.loc[te])):
        print(f"{f},{p}")


def check(data, out):
    fl, y = load(data)
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "header"
    rows = [l.split(",") for l in lines[1:]]
    want = [f for f in fl if y[f] == "missing"]
    if [int(r[0]) for r in rows] != want:
        return False, "flock ids/order"
    if any(r[1] not in SPECIES for r in rows):
        return False, "species"
    return True, f"{len(rows)} flocks"


if __name__ == "__main__":
    main()
