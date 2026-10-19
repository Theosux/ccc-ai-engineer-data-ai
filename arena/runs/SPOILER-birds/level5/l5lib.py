"""Level 5 feature builder: forecast-origin samples (cutoff c, target day t = c+h, h=1..30)."""
import io
import pathlib
from collections import Counter
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent / "files"
N = 2500


def load_main(text=None):
    d = pd.read_csv(io.StringIO(text) if text is not None else HERE / "in_level-5_1-main.txt", low_memory=False)
    d.columns = ["day", "bop", "arr", "occ", "wx", "wy", "ins"]
    d["arr"] = pd.to_numeric(d.arr, errors="coerce")
    A = d.pivot(index="day", columns="bop", values="arr").astype(float)
    O = d.pivot(index="day", columns="bop", values="occ").astype(float)
    wind = d.groupby("day")[["wx", "wy"]].first()
    ins = d.groupby("bop").ins.first().reindex(A.columns).values
    return A, O, wind, ins


def flow_matrix():
    p = pd.read_csv(HERE / "all_data_from_level_4.in")
    p.columns = ["flock", "path", "sp"]
    W = np.zeros((N, N))
    for s in p.path:
        r = list(map(int, s.split()))
        for a, b in zip(r, r[1:]):
            if a != b:
                W[a - 1, b - 1] += 1
    return W / np.maximum(W.sum(1, keepdims=True), 1)


def samples(A, O, wind, ins, Wn, cut, H=30):
    """Feature rows for every bop and t = cut+1..cut+H, using arrivals only up to `cut`."""
    Av, Ov = A.values, O.values          # row i = day i+1
    c = cut - 1
    inflow = Ov @ Wn                     # inflow[i] from occupancy of predecessors on day i+1
    last = Av[c]
    m7 = np.nanmean(Av[c - 6:c + 1], 0)
    m28 = np.nanmean(Av[c - 27:c + 1], 0)
    ratio = np.nanmean(Av[c - 27:c + 1] / np.maximum(Ov[c - 27:c + 1], 1), 0)
    rows = []
    for h in range(1, H + 1):
        i = c + h
        if i >= len(Av):
            break
        f = pd.DataFrame({
            "bop": np.arange(1, N + 1), "day": i + 1, "h": h,
            "occ": Ov[i], "occ_p": Ov[i - 1], "occ_n": Ov[min(i + 1, len(Ov) - 1)], "docc": Ov[i] - Ov[i - 1],
            "occ_cut": Ov[c], "in": inflow[i - 1], "in0": inflow[i],
            "last": last, "m7": m7, "m28": m28, "ratio": ratio, "ratio_occ": ratio * Ov[i],
            "wx": wind.wx.values[i], "wy": wind.wy.values[i], "ins": ins,
            "y": Av[i],
        })
        rows.append(f)
    return pd.concat(rows, ignore_index=True)


def topk_score(df, pred, k=50):
    s = []
    for _, g in df.assign(p=pred).groupby("day"):
        s.append(len(set(g.nlargest(k, "p").bop) & set(g.nlargest(k, "y").bop)) / k)
    return float(np.mean(s))
