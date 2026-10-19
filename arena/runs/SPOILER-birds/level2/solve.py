import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from lib.ml import read_csv, clean_numeric

# Bird Love Score (BLS) regression, RMSE < 6 / 3 / 3.
# Traps: (1) 3-c has NO labelled rows -> train on labelled rows pooled from every input file;
# (2) temperature from level 1 is partly in °F (values > 50; clean gap 50..70 in the histogram);
# (3) "seventeen" in level-1 data. BLS ~ 1.7*T°C + 14.3 + noise (sd 2.58); other features ~0 -> plain linear fit.
HERE = pathlib.Path(__file__).resolve().parent / "files"
FEATS = ["vegetation", "insects", "urban_light", "tc", "humidity"]
HEAD = "BOP,Bird Love Score [<3]"


def l1():
    d = clean_numeric(read_csv((HERE / "all_data_from_level_1.in").read_text(encoding="utf-8")), report=False)
    d["tc"] = np.where(d.temperature > 50, (d.temperature - 32) * 5 / 9, d.temperature)
    return d[["bop", "tc", "humidity"]]


def prep(d, base):
    d = d.merge(base, on="bop", how="left")
    d["y"] = pd.to_numeric(d.bird_love_score, errors="coerce")
    return d


def model(base):
    train = pd.concat([prep(read_csv(p.read_text(encoding="utf-8")), base) for p in sorted(HERE.glob("in_level-2_*.txt"))])
    train = train[train.y.notna()].drop_duplicates("bop")
    return LinearRegression().fit(train[FEATS], train.y)


def main():
    base = l1()
    d = prep(read_csv(sys.stdin.read()), base)
    m = model(base)
    miss = d[d.y.isna()]
    print(HEAD)
    for b, p in zip(miss.bop, m.predict(miss[FEATS])):
        print(f"{b},{p:.2f}")


def check(data, out):
    """Format check: exactly the missing BOPs, in order, numeric scores."""
    d = read_csv(data)
    want = d.bop[d.bird_love_score.astype(str) == "missing"].tolist()
    lines = out.strip().splitlines()
    if lines[0] != HEAD:
        return False, "bad header"
    got = [int(l.split(",")[0]) for l in lines[1:]]
    ok = got == want and all(np.isfinite(float(l.split(",")[1])) for l in lines[1:])
    return ok, f"{len(got)} rows"


if __name__ == "__main__":
    main()
