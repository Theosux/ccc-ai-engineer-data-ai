import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from lib.ml import log
import io
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Day,Top 50 Arrivals BOPs"


def load(src):
    d = pd.read_csv(src, low_memory=False)
    d.columns = ["day", "bop", "arr", "occ", "wx", "wy", "ins"]
    d["arr"] = pd.to_numeric(d.arr, errors="coerce")
    return d


def main():
    new = load(io.StringIO(sys.stdin.read()))
    old = load(HERE / "all_data_from_level_5.in")
    A = pd.concat([old, new]).drop_duplicates(["day", "bop"], keep="last").pivot(index="day", columns="bop", values="arr")
    # the WeatherChanger plays time backwards: every new day t equals old day m - t (found m = 1521 exactly)
    first, last = new.day.min(), new.day.max()
    m = next(s for s in A.index if s < first and np.array_equal(A.loc[s].values, A.loc[first].values)) + first
    assert all(np.array_equal(A.loc[t].values, A.loc[m - t].values) for t in range(first, last + 1))
    target = last + 1
    src = A.loc[m - target]
    log(f"mirror m={m}: day {target} = day {m - target}")
    top = sorted(src.index, key=lambda b: (-src[b], b))[:50]
    print(HEAD)
    print(f"{target}," + " ".join(str(b) for b in top))


def check(data, out):
    lines = out.strip().splitlines()
    day, top = lines[1].split(",")
    return lines[0] == HEAD and len(set(top.split())) == 50, f"day {day}"


if __name__ == "__main__":
    main()
