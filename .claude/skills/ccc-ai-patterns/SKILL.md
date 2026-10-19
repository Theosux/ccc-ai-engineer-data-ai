---
name: ccc-ai-patterns
description: Technique cheat sheet + lib/ml.py API for CCC DATA/AI levels - which model/validation/feature trick for which level type, dirty-data trap checklist, puzzle detection, output rules. Use whenever writing or strategizing a Data/AI solve.py, when a model misses its threshold, or when the user says "solve level N" / "next level" / "contest started" (with ccc-ai-solve).
---

# CCC DATA/AI patterns

Deeper references (open only when needed): `docs/knowledge/data-ai-patterns.md` (level type → technique table,
trap checklist, lib API), `docs/knowledge/ml-playbook.md` (procedure, ladder when not passing),
`docs/knowledge/past-games.md` (how past games escalated; Birds is a spoiler).

## solve.py skeleton
```python
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import numpy as np, pandas as pd
from lib.ml import read_csv, clean_numeric, best_model, log, fmt_lines
HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Id,Prediction"                                   # copy from the example output

def main():
    d = clean_numeric(read_csv(sys.stdin.read()))
    lab = pd.concat([clean_numeric(read_csv(p.read_text(encoding="utf-8"))) for p in sorted(HERE.glob("in_level-*_*.txt"))])
    tr = lab[lab.y.notna()]                               # pooled labelled rows
    m, _ = best_model(tr[FEATS], tr.y, "reg", "rmse")     # CV table on stderr
    te = d[d.y.isna()]
    print(HEAD)
    for i, p in zip(te.id, m.predict(te[FEATS])): print(f"{i},{p:.2f}")

def check(data, out):                                    # format only: ids, order, count, labels
    ...; return ok, msg

if __name__ == "__main__":
    main()
```

## Decision rules
1. **Traps first** (every past game had them): spelled-out numbers, °F/°C or K clusters, `missing`/`?`/NaN,
   outliers outside a range given in the PDF, wrong-length rows, re-shipped data with the same bug.
   pandas 3: text dtype is `str`, so test `not is_numeric_dtype`.
2. **Exact / 100% / password / weird twist = puzzle**: look for reversal, shift, duplicates against older data,
   reshape √n×√n, scatter the PCA. Don't train.
3. **Regression:** linear first (synthetic data); flat CV across models = noise floor reached.
4. **Classification:** ExtraTrees/LightGBM on engineered features; macro-F1 → class weights, threshold tuning.
5. **Grade per group (flock/day/user):** aggregate to one row per group; story sentences become features.
6. **Forecasting / top-K:** rolling-origin validation at several cuts with the task's horizon; given future
   covariates are allowed; rank-average scorers; evaluate the exact graded quantity (daily top-K overlap).
7. **Images:** pretrained embeddings → LogReg (weights pre-downloaded). Text: TF-IDF + LogReg.
8. **Margin:** submit at CV ≥ threshold + margin. The verdict shows the real score; use it to calibrate.
9. **Big CSVs:** pivot to numpy matrices, no row loops; `read_csv(low_memory=False)`.
10. **Output:** byte-identical format to the example (header, order, decimals); stdout = answer only.
