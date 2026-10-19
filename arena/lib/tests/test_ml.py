"""Tests for lib.ml. Run: python arena/lib/tests/test_ml.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np  # noqa: E402

from lib.ml import best_model, clean_col, cv_score, fmt_lines, fmt_space, quick_models, read_csv  # noqa: E402


def t_read_csv():
    df = read_csv("BOP,Temperature [°C], Humidity [%]\n1, 20, 15\n2, 24, 15\n")
    assert list(df.columns) == ["bop", "temperature", "humidity"], df.columns
    assert df.humidity.tolist() == [15, 15]
    assert clean_col("BOP id") == "bop_id"


def t_models():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, 4))
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    m, rows = best_model(X, y, "clf", "acc", folds=3, models={k: v for k, v in quick_models("clf").items() if k in ("lgbm", "logreg")})
    assert rows[0][1] > 0.9, rows
    yr = X[:, 0] * 3 + 1
    mean, _ = cv_score(quick_models("reg")["ridge"], X, yr, "rmse", folds=3)
    assert mean < 0.1, mean


def t_fmt():
    assert fmt_space([2, 3.0, np.int64(4)]) == "2 3 4"
    assert fmt_lines(["a", 1.5]) == "a\n1.5"


if __name__ == "__main__":
    t0 = time.time()
    for name, fn in list(globals().items()):
        if name.startswith("t_") and callable(fn):
            fn()
            print("ok", name)
    print(f"ALL OK ({time.time() - t0:.1f}s)")
