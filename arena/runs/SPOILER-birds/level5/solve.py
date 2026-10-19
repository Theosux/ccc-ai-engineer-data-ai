import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import rankdata
from l5lib import flow_matrix, load_main, samples

# Top-50 BOPs by Arrivals for days 731..760 (mean daily overlap >= 50%).
# Findings: wind is one value per day in piecewise-constant regimes; inside a regime per-BOP arrivals are smooth
# (day ratio ~0.985) and jump when the wind changes; occupancy is GIVEN for future days. Days 731-732 continue the
# regime that started on day 728, so the last known arrivals are near-oracle there.
# Ensemble (rank average): LightGBM on forecast-origin samples + wind-kNN rate*occupancy.
FE = ["h", "occ", "occ_p", "occ_n", "docc", "occ_cut", "in", "in0", "last", "m7", "m28", "ratio", "ratio_occ",
      "wx", "wy", "ins"]
CUT = 730


def predict(A, O, wind, ins, cut=CUT, H=30):
    Wn = flow_matrix()
    Av, Ov, Wd = A.values, O.values, wind.values
    tr = pd.concat([samples(A, O, wind, ins, Wn, c) for c in range(100, cut - 29, 15)])
    m = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=63, verbose=-1, n_jobs=-1, random_state=0)
    m.fit(tr[FE], np.log1p(tr.y))
    te = samples(A, O, wind, ins, Wn, cut, H)
    pl = m.predict(te[FE]).reshape(H, -1)
    hist = np.arange(1, cut)
    same = lambda i: np.allclose(Wd[i], Wd[cut - 1])
    P = {}
    for h in range(H):
        i = cut + h
        nn = hist[np.argsort(np.linalg.norm(Wd[hist] - Wd[i], axis=1))[:10]]
        knn = np.mean(Av[nn] / np.maximum(Ov[nn], 1), 0) * Ov[i]
        s = rankdata(pl[h]) + rankdata(knn)
        if all(same(k) for k in range(cut, i + 1)):          # still in the last observed regime
            s = rankdata(Av[cut - 1] * 1.0) * 2 + s * 0.5
        P[i + 1] = s
    return P


def main():
    A, O, wind, ins = load_main(sys.stdin.read())
    P = predict(A, O, wind, ins)
    print("Day,Top 50 Arrivals BOPs")
    for day in sorted(P):
        top = np.argsort(-P[day])[:50] + 1
        print(f"{day}," + " ".join(map(str, top)))


def check(data, out):
    lines = out.strip().splitlines()
    rows = [l.split(",") for l in lines[1:]]
    ok = (lines[0] == "Day,Top 50 Arrivals BOPs" and [int(r[0]) for r in rows] == list(range(731, 761))
          and all(len(set(r[1].split())) == 50 for r in rows))
    return ok, f"{len(rows)} days"


if __name__ == "__main__":
    main()
