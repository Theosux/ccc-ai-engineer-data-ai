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
def quick_models(task, seed=SEED):
    """Fast, strong baselines. task: 'clf' or 'reg'. Returns {name: unfitted estimator}."""
    from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    import lightgbm as lgb
    q = dict(random_state=seed, n_jobs=-1)
    if task == "clf":
        return {
            "lgbm": lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, verbose=-1, **q),
            "rf": RandomForestClassifier(n_estimators=400, **q),
            "et": ExtraTreesClassifier(n_estimators=400, **q),
            "logreg": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
            "knn": make_pipeline(StandardScaler(), KNeighborsClassifier(7)),
        }
    return {
        "lgbm": lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, verbose=-1, **q),
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
    models = models or quick_models(task, seed)
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
