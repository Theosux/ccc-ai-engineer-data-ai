import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from lib.ml import to_num, log
import pandas as pd
from sklearn.linear_model import LinearRegression

HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "BOP,Bird Love Score [<3]"
FEATS = ["veg", "ins", "light", "t", "h"]


def rows(text):
    return [l.split(",") for l in text.strip().splitlines()[1:]]


def level1():
    d = pd.DataFrame(rows((HERE / "all_data_from_level_1.in").read_text(encoding="utf-8")), columns=["id", "t", "h"])
    for c in d.columns:
        d[c] = to_num(d[c], False)
    d["t"] = d.t.where(d.t <= 50, (d.t - 32) * 5 / 9)  # statement: some °C values were reported in °F
    return d


def load(text, l1):
    d = pd.DataFrame(rows(text), columns=["id", "veg", "ins", "light", "y"])
    for c in ["id", "veg", "ins", "light"]:
        d[c] = to_num(d[c], False)
    d["y"] = pd.to_numeric(d.y, errors="coerce")
    return d.merge(l1, on="id", how="left")


def main():
    l1 = level1()
    d = load(sys.stdin.read(), l1)
    tr = pd.concat([load(p.read_text(encoding="utf-8"), l1) for p in sorted(HERE.glob("in_level-2_*.txt"))])
    tr = tr[tr.y.notna()].drop_duplicates("id")
    m = LinearRegression().fit(tr[FEATS], tr.y)
    log(f"train rows {len(tr)}")
    te = d[d.y.isna()]
    print(HEAD)
    for i, p in zip(te.id, m.predict(te[FEATS])):
        print(f"{int(i)},{p:.2f}")


def check(data, out):
    want = [l.split(",")[0] for l in data.strip().splitlines()[1:] if l.strip().endswith("missing")]
    lines = out.strip().splitlines()
    got = [l.split(",")[0] for l in lines[1:]]
    return lines[0] == HEAD and got == want, f"{len(got)} preds"


if __name__ == "__main__":
    main()
