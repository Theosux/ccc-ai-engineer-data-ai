# Data/AI patterns: "level says X → do Y → use Z"

Cheat sheet for writing `solve.py` fast. Library: `arena/lib/ml.py` (import explicitly: `from lib.ml import ...`).
Evidence for each row: [past-games.md](past-games.md).

## Level type → technique
| The statement says / the data looks like | Do | Tools |
|---|---|---|
| "sort / count / histogram / filter / report mean, std" | exact pandas; verify on `0-example` first | `read_csv`, `clean_numeric`, `fmt_space` / `fmt_lines` |
| CSV with `missing` target rows | train on labelled rows, predict missing, keep **input order** | pandas mask `y.isna()` |
| a file with **no labelled rows** | train on labelled rows **pooled from all input files** of the level | glob `files/in_level-N_*.txt` (Birds L2) |
| regression, RMSE < X | **LinearRegression/Ridge first** (synthetic targets are often linear), then `best_model(..., "reg", "rmse")`; check the noise floor (residual std ≈ CV RMSE across all models = done) | `best_model`, `cv_score` |
| classification, accuracy / macro-F1 ≥ X | `best_model(X, y, "clf", "f1")`; ExtraTrees/LightGBM usually win; `class_weight="balanced"` for imbalance | `best_model` |
| precision AND recall for one class | tune the probability threshold on out-of-fold predictions | `cross_val_predict(..., method="predict_proba")` |
| rows belong to groups and the grade is per group (flock, user, day) | **one feature row per group**; GroupKFold if rows are the unit | Birds L4 `feats.py` |
| sequences / paths / strings | shape features: length, palindrome score, closed loop, unique ratio, shared prefix/suffix, pairwise Jaccard, n-grams, per-position one-hot | Birds L3/L4, Bees |
| story prose with character descriptions | **each sentence is a rule/feature** ("flies back the same way" = palindrome) | ask Claude to list sentence → rule |
| panel time series (day × entity), forecast H days | rolling-origin backtest at several cutoffs with the same horizon; features cut at the origin; future covariates given in the file are fair game | Birds L5 `l5lib.py` |
| graded by top-K per day | evaluate top-K overlap directly; rank-average several scorers | `scipy.stats.rankdata` |
| "100% required" / weird change in the data / "backwards" | **look for an exact relation to old data**: reversal (t → C−t), shift, duplicate rows, sign flip, id permutation | `(A6.loc[d] == A5.loc[m]).all()` (Birds L6) |
| numbers that may be a picture | reshape to √n × √n, scatter the 2D/PCA projection, look | matplotlib `imshow` (Spy L2/L7) |
| PCA / clustering with k from the story | StandardScaler → PCA → KMeans(k); map clusters to names with Hungarian | `scipy.optimize.linear_sum_assignment` |
| outliers with a range given in the PDF | the range IS the rule: drop/clip outside it | pandas masks |
| images | pretrained CNN embeddings → LogReg; fine-tune only if needed | `ml-playbook.md` §6 |

## Trap checklist (run BEFORE modelling, every level)
1. **Non-numeric values in numeric columns:** `df[c][pd.to_numeric(df[c], errors="coerce").isna()].unique()`
   → spelled-out numbers, `missing`, `?`, `NaN`, decimal commas, units. Fix with `clean_numeric`.
2. **Mixed units:** histogram each numeric column; two clusters = two units (°F/°C: (F−32)·5/9; K: −273.15).
   The story usually hints ("some values were reported in °F").
3. **Re-shipped data:** `all_data_from_level_N.in` carries the same traps; fix them again.
4. **Rows to drop:** wrong length, out-of-range, duplicates (the PDF says "use filtered data from now on").
5. **Labels:** exact spelling from the provided label file; same order as input; header row exactly as the example.
6. **pandas 3:** text columns have dtype `str`, not `object`. Use `pd.api.types.is_numeric_dtype`.

## Output rules
- Copy the example output **byte for byte**: header row (`BOP,Bird Love Score [<3]`), separators, decimals, order.
- Diagnostics go to **stderr**; stdout is only the answer (`lib.ml.log`).
- Write a `check(data, out)` in solve.py (format: right ids, right count, valid labels) so `go` accepts ML outputs
  that differ from the example.

## lib/ml.py API
| Function | Does |
|---|---|
| `read_csv(text=None, clean=True)` | stdin/text → DataFrame, strips spaces after commas, cleans headers (`Temperature [°C]` → `temperature`) |
| `word_num(s)`, `to_num(series)`, `clean_numeric(df, cols=None)` | spelled-out numbers, decimal commas, stray units → numbers; prints what it fixed to stderr |
| `quick_models("clf"\|"reg")` | LightGBM, RF, ExtraTrees, LogReg/Ridge, kNN with sane defaults |
| `cv_score(model, X, y, metric, folds=5)` | mean ± std K-fold (stratified for classification) |
| `best_model(X, y, task, metric)` | CV every quick model, print a table, refit the best on all rows |
| `score(y, p, metric)` | metrics: `acc`, `f1` (macro), `rmse`, `mae`, `r2`, `mape` |
| `fmt_space`, `fmt_lines`, `seed_all`, `log` | output helpers, seeding, stderr logging |
