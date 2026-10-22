import sys, io
import numpy as np, pandas as pd

HEAD = "Day,Top 50 Arrivals BOPs"
K = 50


def load(text):
    d = pd.read_csv(io.StringIO(text), low_memory=False)
    d.columns = ["day", "bop", "arr", "occ", "wx", "wy", "ins"]
    d["arr"] = pd.to_numeric(d.arr, errors="coerce")
    return d


def rk(M):
    return M.argsort(1).argsort(1) / M.shape[1]


def main():
    d = load(sys.stdin.read())
    A = d.pivot(index="day", columns="bop", values="arr")
    O = d.pivot(index="day", columns="bop", values="occ").values.astype(float)
    W = d.groupby("day")[["wx", "wy"]].first().values
    days, bops = A.index.values, A.columns.values
    A = A.values
    known = ~np.isnan(A).any(1)
    past = np.where(known)[0]
    fut = np.where(~known)[0]
    Z = A[past]
    Z = (Z - Z.mean(1, keepdims=True)) / Z.std(1, keepdims=True)
    print(HEAD)
    for t in fut:
        # mirrored wind kNN (best real score in rehearsal) blended with same-day occupancy ranking
        dist = np.linalg.norm(W[past] + W[t], axis=1)
        mir = Z[np.argsort(dist)[:10]].mean(0)
        s = rk(O[t:t + 1])[0] + rk(mir[None])[0]
        top = bops[np.argsort(-s, kind="stable")[:K]]
        print(f"{days[t]}," + " ".join(str(b) for b in top))


def check(data, out):
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "header"
    rows = [l.split(",") for l in lines[1:]]
    days = [int(r[0]) for r in rows]
    ok = days == list(range(731, 761)) and all(len(set(r[1].split())) == K for r in rows)
    return ok, f"{len(rows)} days"


if __name__ == "__main__":
    main()
