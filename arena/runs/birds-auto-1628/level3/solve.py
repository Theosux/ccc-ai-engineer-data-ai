import sys, pathlib, io
import numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "BOP,Bird Love Score [<3]"
F = ["V", "I", "U", "Tc", "H"]


def load(text):
    d = pd.read_csv(io.StringIO(text))
    d.columns = ["BOP", "V", "I", "U", "y"]
    d["y"] = pd.to_numeric(d.y, errors="coerce")
    return d


def level1():
    a = pd.read_csv(HERE / "all_data_from_level_1.in")
    a.columns = ["BOP", "T", "H"]
    a["T"] = pd.to_numeric(a["T"], errors="coerce")
    a["Tc"] = np.where(a["T"] >= 55, (a["T"] - 32) * 5 / 9, a["T"])  # °F cluster 65..113
    return a


def main():
    a = level1()
    d = load(sys.stdin.read()).merge(a, on="BOP", how="left")
    lab = pd.concat([load(p.read_text(encoding="utf-8")) for p in sorted(HERE.glob("in_level-2_*.txt"))])
    lab = lab[lab.y.notna()].drop_duplicates("BOP").merge(a, on="BOP")
    m = LinearRegression().fit(lab[F], lab.y)
    print(f"trained on {len(lab)}", file=sys.stderr)
    te = d[d.y.isna()]
    print(HEAD)
    for i, p in zip(te.BOP, m.predict(te[F])):
        print(f"{i},{p:.2f}")


def check(data, out):
    d = load(data)
    want = d[d.y.isna()].BOP.astype(str).tolist()
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "header"
    got = [l.split(",")[0] for l in lines[1:]]
    return got == want, f"{len(got)} rows vs {len(want)}"


if __name__ == "__main__":
    main()
