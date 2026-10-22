"""ML helpers for CCC Data/AI levels (pandas + scikit-learn + LightGBM). Import explicitly (heavy imports):

    from lib.ml import read_csv, best_model, cv_score, fmt_space, seed_all

Typical level:  df = read_csv()                       # stdin CSV -> DataFrame, clean column names
                train, test = df[df.y.notna()], df[df.y.isna()]
                m, table = best_model(train[feats], train.y, "clf", metric="acc")   # prints a CV table to stderr
                print(fmt_lines(m.predict(test[feats])))
Local validation = cross-validation on the labelled rows (the platform only says CORRECT/WRONG per file).
All diagnostics go to stderr so stdout stays the answer.
"""
import io
import random
import re
import sys
import time

import numpy as np
import pandas as pd

SEED = 0


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def seed_all(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except ImportError:
        pass


def clean_col(c):
    """'Temperature [°C]' -> 'temperature', ' Humidity [%]' -> 'humidity', 'BOP id' -> 'bop_id'."""
    c = re.sub(r"[\[(].*?[\])]", "", str(c)).strip().lower()
    return re.sub(r"\W+", "_", c).strip("_") or "col"


def read_csv(data=None, clean=True, **kw):
    """CSV text (default: stdin) -> DataFrame. Strips spaces after commas; cleans header names unless clean=False."""
    if data is None:
        data = sys.stdin.read()
    df = pd.read_csv(io.StringIO(data), skipinitialspace=True, **kw)
    if clean:
        df.columns = [clean_col(c) for c in df.columns]
    return df


# ---------------------------------------------------------------- dirty values (Birds L1: "seventeen" in a numeric column)
_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if i > 1}


def word_num(s):
    """'seventeen' -> 17, 'minus twenty-one' -> -21, 'one hundred and five' -> 105, 'two thousand' -> 2000; else None."""
    w = re.sub(r"[-,]", " ", str(s).lower()).split()
    sign, total, cur = 1, 0, 0
    if w and w[0] in ("minus", "negative"):
        sign, w = -1, w[1:]
    if not w:
        return None
    for t in w:
        if t in _UNITS:
            cur += _UNITS[t]
        elif t in _TENS:
            cur += _TENS[t]
        elif t == "hundred":
            cur = (cur or 1) * 100
        elif t in ("thousand", "million"):
            total += (cur or 1) * (1000 if t == "thousand" else 10 ** 6)
            cur = 0
        elif t != "and":
            return None
    return sign * (total + cur)


def to_num(col, report=True):
    """Numeric Series from a messy column: number words, '12,5' decimal commas, stray units/spaces ('20°C').
    Values that still fail become NaN; they are printed to stderr so you can decide (drop/impute/fix)."""
    s = pd.Series(col)
    out = pd.to_numeric(s, errors="coerce")
    bad = out.isna() & s.notna()
    for i in s.index[bad]:
        v = str(s[i]).strip()
        n = word_num(v)
        if n is None:
            m = re.fullmatch(r"\s*([-+]?\d+(?:[.,]\d+)?)\s*\D{0,4}\s*", v)
            n = float(m.group(1).replace(",", ".")) if m else None
        if n is not None:
            out[i] = n
    still = out.isna() & s.notna()
    if report and bad.any():
        log(f"  to_num({s.name}): fixed {int(bad.sum() - still.sum())}, unparsed {sorted(set(s[still].astype(str)))[:10]}")
    return out


def clean_numeric(df, cols=None, report=True):
    """Apply to_num to every object column that is mostly numeric (or to `cols`). Returns df (modified copy)."""
    df = df.copy()
    for c in cols or df.columns:
        # pandas 3 reads text as dtype "str", not object: test "not numeric" instead of "== object"
        if not pd.api.types.is_numeric_dtype(df[c]) and (cols or pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.5):
            df[c] = to_num(df[c], report)
    return df


# ---------------------------------------------------------------- metrics (higher is better unless noted)
def _metric(name):
    from sklearn import metrics as M
    table = {
        "acc": (M.accuracy_score, True), "f1": (lambda y, p: M.f1_score(y, p, average="macro"), True),
        "rmse": (lambda y, p: float(np.sqrt(M.mean_squared_error(y, p))), False),
        "mae": (M.mean_absolute_error, False), "r2": (M.r2_score, True),
        "mape": (M.mean_absolute_percentage_error, False),
    }
    if callable(name):
        return name, True
    return table[name]


def score(y, p, metric="acc"):
    return _metric(metric)[0](y, p)


# ---------------------------------------------------------------- models
def lgbm_params(n=None):
    """LightGBM speed settings. n_jobs=-1 is the slowest choice on the M4 Pro at every size (5-fold CV, 600 trees:
    2k rows 15.1 s vs 0.2 s single-threaded; 50k 17.5 s vs 5.3 s; 200k 20.5 s vs 9.5 s with 4 threads), identical
    scores. Under 10k rows 200 trees at lr 0.1 match or beat 600 at 0.05 (Birds L2 RMSE 2.877 vs 2.916)."""
    small = n is not None and n < 10_000
    return dict(n_estimators=200 if small else None, learning_rate=0.1 if small else None,
                n_jobs=1 if n is not None and n < 100_000 else 4)


def quick_models(task, seed=SEED, n=None):
    """Fast, strong baselines. task: 'clf' or 'reg'; n = training rows (tunes LightGBM speed). {name: estimator}."""
    from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    import lightgbm as lgb
    q = dict(random_state=seed, n_jobs=-1)  # sklearn forests: all cores is fastest (RF 0.9 s vs 1.3 s with 4)
    lp = lgbm_params(n)
    lq = dict(random_state=seed, n_jobs=lp["n_jobs"], verbose=-1)
    if task == "clf":
        return {
            "lgbm": lgb.LGBMClassifier(n_estimators=lp["n_estimators"] or 400, learning_rate=lp["learning_rate"] or 0.05, **lq),
            "rf": RandomForestClassifier(n_estimators=400, **q),
            "et": ExtraTreesClassifier(n_estimators=400, **q),
            "logreg": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
            "knn": make_pipeline(StandardScaler(), KNeighborsClassifier(7)),
        }
    return {
        "lgbm": lgb.LGBMRegressor(n_estimators=lp["n_estimators"] or 600, learning_rate=lp["learning_rate"] or 0.05, **lq),
        "rf": RandomForestRegressor(n_estimators=400, **q),
        "et": ExtraTreesRegressor(n_estimators=400, **q),
        "ridge": make_pipeline(StandardScaler(), Ridge(1.0)),
        "knn": make_pipeline(StandardScaler(), KNeighborsRegressor(7)),
    }


def cv_score(model, X, y, metric="acc", folds=5, seed=SEED, task=None):
    """Mean K-fold CV score (stratified for classification). Returns (mean, std)."""
    from sklearn.base import clone
    from sklearn.model_selection import KFold, StratifiedKFold
    fn, _ = _metric(metric)
    X, y = np.asarray(X), np.asarray(y)
    task = task or ("clf" if metric in ("acc", "f1") else "reg")
    kf = (StratifiedKFold if task == "clf" else KFold)(folds, shuffle=True, random_state=seed)
    s = []
    for tr, va in kf.split(X, y):
        m = clone(model).fit(X[tr], y[tr])
        s.append(fn(y[va], m.predict(X[va])))
    return float(np.mean(s)), float(np.std(s))


def best_model(X, y, task="clf", metric=None, folds=5, models=None, seed=SEED):
    """CV every quick model, print a table to stderr, refit the best on all rows. Returns (fitted, rows)."""
    metric = metric or ("acc" if task == "clf" else "rmse")
    _, higher = _metric(metric)
    models = models or quick_models(task, seed, n=len(X))
    rows = []
    for name, m in models.items():
        t = time.time()
        mean, sd = cv_score(m, X, y, metric, folds, seed, task)
        rows.append((name, mean, sd, time.time() - t))
        log(f"  {name:8s} {metric}={mean:.4f} +-{sd:.4f}  ({rows[-1][3]:.1f}s)")
    rows.sort(key=lambda r: r[1], reverse=higher)
    best = rows[0][0]
    log(f"  best: {best}")
    return models[best].fit(np.asarray(X), np.asarray(y)), rows


# ---------------------------------------------------------------- output
def _s(v):
    if isinstance(v, (float, np.floating)) and float(v).is_integer():
        return str(int(v))
    return str(v.item() if hasattr(v, "item") else v)


def fmt_space(seq):
    return " ".join(_s(v) for v in seq)


def fmt_lines(seq):
    return "\n".join(_s(v) for v in seq)
