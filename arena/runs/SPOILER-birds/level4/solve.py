import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sklearn.ensemble import ExtraTreesClassifier
from feats import HERE, features, load, temps

# Species per flock, macro-F1 > 0.90. Rows are now noisy, so the level-3 rules become per-flock features
# (palindrome score, row similarity, shared prefix/suffix, temperature, node overlap with other flocks)
# and a classifier learns them from the 288 labelled flocks. CV macro-F1: ET 0.982, LGBM 0.972, logreg 0.964.
HEAD = "Flock ID,Species"
SPECIES = set((HERE / "level_4_species.in").read_text(encoding="utf-8").split("\n")) - {""}


def main():
    T = temps()
    main_d = load((HERE / "in_level-4_1-main.txt").read_text(encoding="utf-8"))
    Fm = features(main_d, T)
    ym = main_d.groupby("flock", sort=False).species.first()
    tr = ym != "missing"
    m = ExtraTreesClassifier(n_estimators=1000, random_state=0, n_jobs=-1).fit(Fm[tr], ym[tr])

    d = load(sys.stdin.read())
    F = features(d, T)
    y = d.groupby("flock", sort=False).species.first()
    miss = y[y == "missing"].index
    print(HEAD)
    for f, p in zip(miss, m.predict(F.loc[miss])):
        print(f"{f},{p}")


def check(data, out):
    d = load(data)
    want = list(d.groupby("flock", sort=False).species.first().pipe(lambda s: s[s == "missing"]).index)
    lines = out.strip().splitlines()
    got = [int(l.split(",")[0]) for l in lines[1:]]
    ok = lines[0] == HEAD and got == want and all(l.split(",", 1)[1] in SPECIES for l in lines[1:])
    return ok, f"{len(got)} flocks"


if __name__ == "__main__":
    main()
