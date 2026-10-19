import sys, pathlib, io
import numpy as np
import pandas as pd

# "Think, don't train": the WeatherChanger plays the level-5 world BACKWARDS. Day 761+k is exactly day 760-k
# (occupancy and arrivals identical), so day 791 = day 730 of the level-5 data -> lookup, 100% accuracy.
HERE = pathlib.Path(__file__).resolve().parent / "files"


def piv(src):
    d = pd.read_csv(src, low_memory=False)
    d.columns = ["day", "bop", "arr", "occ", "wx", "wy", "ins"]
    d["arr"] = pd.to_numeric(d.arr, errors="coerce")
    return d.pivot(index="day", columns="bop", values="arr"), d.pivot(index="day", columns="bop", values="occ")


def main():
    A6, O6 = piv(io.StringIO(sys.stdin.read()))
    A5, O5 = piv(HERE / "all_data_from_level_5.in")
    first, last = A6.index.min(), A6.index.max()
    for d in A6.index:                                   # verify the mirror on every given day
        m = 2 * first - 1 - d
        assert (O6.loc[d].values == O5.loc[m].values).all() and (A6.loc[d].values == A5.loc[m].values).all(), d
    target, src = last + 1, 2 * first - 1 - (last + 1)
    a = A5.loc[src].sort_values(ascending=False, kind="stable")
    print(f"  day {target} = day {src}; rank50={a.iloc[49]} rank51={a.iloc[50]}", file=sys.stderr)
    print("Day,Top 50 Arrivals BOPs")
    print(f"{target}," + " ".join(map(str, a.index[:50])))


def check(data, out):
    lines = out.strip().splitlines()
    return lines[0] == "Day,Top 50 Arrivals BOPs" and len(set(lines[1].split(",")[1].split())) == 50, lines[1][:20]


if __name__ == "__main__":
    main()
