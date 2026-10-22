import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import io
import numpy as np, pandas as pd

HEAD = "Day,Top 50 Arrivals BOPs"
K = 50


def load(text):
    d = pd.read_csv(io.StringIO(text), low_memory=False)
    d.columns = ["day", "bop", "arr", "occ", "wx", "wy", "ins"]
    d["arr"] = pd.to_numeric(d.arr, errors="coerce")
    return d


def main():
    d = load(sys.stdin.read())
    te = d[d.arr.isna()]
    print(HEAD)
    # rank BOPs by the given (future) occupancy of the same day: rolling CV ~0.5, rehearsal real 0.528
    for day, g in te.groupby("day", sort=True):
        g = g.sort_values(["occ", "bop"], ascending=[False, True])
        print(f"{day}," + " ".join(map(str, g.bop.head(K))))


def check(data, out):
    d = load(data)
    want = sorted(d[d.arr.isna()].day.unique())
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "header"
    rows = [l.split(",") for l in lines[1:]]
    if [int(r[0]) for r in rows] != want:
        return False, "days"
    bops = set(d.bop)
    for r in rows:
        b = r[1].split()
        if len(b) != K or len(set(b)) != K or any(int(x) not in bops for x in b):
            return False, f"bops day {r[0]}"
    return True, f"{len(rows)} days"


if __name__ == "__main__":
    main()
