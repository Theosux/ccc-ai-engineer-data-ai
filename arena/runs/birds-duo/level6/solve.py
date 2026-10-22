import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import io
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Day,Top 50 Arrivals BOPs"
K = 50
DAY = 791
MIRROR = 1521   # WeatherChanger replays history backwards: day t == day 1521 - t (exact on all 30 days 761..790)


def load(text):
    d = pd.read_csv(io.StringIO(text), low_memory=False)
    d.columns = ["day", "bop", "arr", "occ", "wx", "wy", "ins"]
    d["arr"] = pd.to_numeric(d.arr, errors="coerce")
    return d


def main():
    d = load(sys.stdin.read())
    old = load((HERE / "all_data_from_level_5.in").read_text(encoding="utf-8"))
    al = pd.concat([old, d]).drop_duplicates(["day", "bop"], keep="last")
    A = al.pivot(index="day", columns="bop", values="arr")
    ok = np.mean([(A.loc[t].values == A.loc[MIRROR - t].values).mean() for t in sorted(d.day.unique())])
    print(f"mirror match on given days: {ok:.4f}", file=sys.stderr)
    src = al[al.day == MIRROR - DAY].sort_values(["arr", "bop"], ascending=[False, True])
    print(HEAD)
    print(f"{DAY}," + " ".join(map(str, src.bop.head(K).astype(int))))


def check(data, out):
    lines = out.strip().splitlines()
    if lines[0] != HEAD or len(lines) != 2:
        return False, "header/lines"
    day, b = lines[1].split(",")
    b = b.split()
    if int(day) != DAY or len(b) != K or len(set(b)) != K:
        return False, "row"
    return True, "1 day"


if __name__ == "__main__":
    main()
