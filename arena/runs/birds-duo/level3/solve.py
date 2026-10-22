import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import io
import numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "BOP,Bird Love Score [<3]"
F = ["t", "h", "v", "i", "u"]


def level1():
    d = pd.read_csv(HERE / "all_data_from_level_1.in")
    d.columns = ["id", "t", "h"]
    d["t"] = np.where(d.t > 54, (d.t - 32) * 5 / 9, d.t)   # °F rows (70..113 cluster) -> °C
    return d


def load(text):
    d = pd.read_csv(io.StringIO(text), na_values=["missing"])
    d.columns = ["id", "v", "i", "u", "y"]
    return d


def main():
    L1 = level1()
    d = load(sys.stdin.read()).merge(L1, on="id", how="left")
    lab = pd.concat([load(p.read_text(encoding="utf-8")) for p in sorted(HERE.glob("in_level-2_*.txt"))
                     if "example" not in p.name])
    tr = lab[lab.y.notna()].drop_duplicates("id").merge(L1, on="id")
    m = LinearRegression().fit(tr[F], tr.y)
    te = d[d.y.isna()]
    print(HEAD)
    for i, p in zip(te.id, m.predict(te[F])):
        print(f"{i},{p:.2f}")


def check(data, out):
    d = load(data)
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "header"
    ids = [int(l.split(",")[0]) for l in lines[1:]]
    if ids != list(d.id[d.y.isna()]):
        return False, "ids/order"
    return True, f"{len(ids)} rows"


if __name__ == "__main__":
    main()
