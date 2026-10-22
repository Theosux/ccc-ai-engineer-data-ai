import sys, io, pathlib
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Day,Top 50 Arrivals BOPs"
K = 50


def piv(text):
    d = pd.read_csv(io.StringIO(text), low_memory=False)
    d.columns = ["day", "bop", "arr", "occ", "wx", "wy", "ins"]
    d["arr"] = pd.to_numeric(d.arr, errors="coerce")
    return d.pivot(index="day", columns="bop", values="arr")


def main():
    A6 = piv(sys.stdin.read())
    A5 = piv((HERE / "all_data_from_level_5.in").read_text(encoding="utf-8"))
    A = pd.concat([A5, A6])
    A = A[~A.index.duplicated(keep="last")]
    # the WeatherChanger mirrors time: day t == day S - t; find S from the given days
    rows = {int(i): r for i, r in zip(A.index, A.values)}
    sums = set()
    for t in A6.index:
        m = [s for s, r in rows.items() if s != t and np.array_equal(r, A6.loc[t].values)]
        sums.update(int(t) + s for s in m)
    print(f"mirror sums {sums}", file=sys.stderr)
    S = sums.pop()
    target = int(A6.index.max()) + 1
    src = rows[S - target]
    top = A.columns.values[np.lexsort((A.columns.values, -src))[:K]]
    print(HEAD)
    print(f"{target}," + " ".join(str(b) for b in top))


def check(data, out):
    lines = out.strip().splitlines()
    ok = lines[0] == HEAD and len(lines) == 2 and len(set(lines[1].split(",")[1].split())) == K
    return ok, "ok" if ok else "format"


if __name__ == "__main__":
    main()
