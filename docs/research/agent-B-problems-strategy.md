# Agent B: Data/AI CCC problems, and techniques that win them

Researched 2026-10-19 for the **42nd DATA/AI CCC** (`42nd-data-ai-ccc-5873`, Fri 23 Oct 2026, 240 min, teams of up to 3).
Tags: **[OFFICIAL]** means a Cloudflight statement, platform JSON or official doc. **[COMMUNITY]** means a participant repo or write-up. **[INFERRED]** means my own analysis.

> **SPOILER WARNING.** Section 1.1 gives the full level-by-level solution of **Migratory Birds** (`ccc-2025.11-ai-birds`). If you are solving Birds hands-on, read only the TL;DR and sections 2–5.

## TL;DR
1. **We found three past Data/AI games with full statements:** Dancing Bees (Nov 2022, 8 levels), a "spy/USB" game (2023, 11 levels) and Migratory Birds (Nov 2025, 6 levels). All three are **synthetic tabular or sequence data**. None uses images, free text or GPUs. [COMMUNITY]
2. **The levels follow a fixed pattern.** L1–L2 are parsing, counting, sorting or cleaning, with an exact answer. Next comes a first model with a soft threshold (accuracy ≥60%, RMSE < 6). Then the threshold rises or the metric changes (macro-F1 ≥ 0.90/0.98, per-class precision/recall, RMSE ≤ 0.45). The last level or two are a twist: a forecast/ranking task, or a **puzzle with an exact answer that is hidden in the data**. [COMMUNITY]
3. **Every game had planted dirty-data traps:** °F mixed into °C, Kelvin with an unknown unit "?", numbers spelled out as words ("seventeen"), NaNs, out-of-range outliers, and samples of the wrong length. Assume each input has at least one trap and check for it on purpose. [COMMUNITY]
4. **The data is generated, so look for the generator before training a model.** In Birds L2 the target was about 0.99-correlated with one feature, so linear regression won. Birds L6 was a time-reversed replay of the L5 data. In 2023 the predictions reshaped to 50×50 formed a picture of the password. **EDA and invariant checks beat model tuning.** [COMMUNITY]
5. **Metrics seen so far:** exact match, accuracy, precision and recall for one class, macro-F1 on an imbalanced test set, RMSE, and daily top-50 overlap. **No level in Birds' public `game-info` has `optimization: true`.** Every level is pass/fail, and the threshold appears only in the PDF. [OFFICIAL]
6. **Default model:** `HistGradientBoosting*` (sklearn) or LightGBM on engineered features, with 5-fold CV (or a time-based split) from the first minute. Add a linear baseline (Ridge or LogReg) as a sanity check. Most levels pass with this. [INFERRED]
7. **Time series and ranking:** validate on the **most recent** windows only. In Birds L5 an all-history backtest scored 0.88 but recent windows scored 0.42. When the grader scores top-K membership, model top-K membership directly. [COMMUNITY]
8. **Team workflow:** one "pipeline/IO" person, one "EDA/trap hunter + rules" person, one "modeler". All three share one local `score.py` that replicates the PDF metric, and every candidate output is checked with it before upload. Wrong uploads may cost penalty minutes, so submit only after local CV clears the threshold with margin. [INFERRED]
9. **Environment:** every package we need has a Py3.14 Windows wheel. sklearn, catboost, torch, torchvision, pyarrow, statsmodels, numba and hdbscan ship `cp314-win_amd64` wheels. lightgbm, xgboost and prophet ship `py3-none-win_amd64`. opencv and safetensors ship abi3. timm, optuna, polars, sentence-transformers and imbalanced-learn are pure Python. Teo's local torch is **CPU-only** (`2.12.0+cpu`) even though the laptop has an RTX 4060. The CUDA cp314 builds exist at `download.pytorch.org/whl/cu126` and `cu130`. [OFFICIAL]
10. **Pre-download "just in case" weights:** resnet18/50 and efficientnet_b0 (torchvision), `all-MiniLM-L6-v2` (sentence-transformers) and optionally CLIP ViT-B/32. Past games never needed them, so this is insurance only. [INFERRED]

---

## 1. Past Data/AI CCC problems

The AI track started in 2021 as the "AI Challenge" ("solve a complex machine learning task"). It was later renamed #Data/AI: "Let your model find the perfect algorithms" and is described as 4 hours "for machine learning aficionados". Topics stay secret until the start. [OFFICIAL: cloudflight.io blog 2021/2023, event page 42, CCC page]

### 1.1 Migratory Birds (41st CCC, Nov 2025): `ccc-2025.11-ai-birds` ⚠ SPOILERS

**Public game-info [OFFICIAL]** (fetched with `Referer: https://birds.codingcontest.org/` and `Sec-Fetch-Site: same-origin`; without these headers it returns 403):

| L | inputFiles | unscored | optimization |
|---|---|---|---|
| 1 | 0-example, 1-a … 5-e | 0-example | false |
| 2 | 0-example, 1-a, 2-b, 3-c | 0-example | false |
| 3 | 0-example, 1-a, 2-b, 3-c | 0-example | false |
| 4 | 0-example, 1-main | 0-example | false |
| 5 | 1-main (no example) | — | false |
| 6 | 1-main (no example) | — | false |

Every level reports `scoreDirection: LOWER_IS_BETTER`, but that is a meaningless default because no level is an optimization level. Level thresholds therefore exist only in the PDF.

**Statements and a full solution** come from goncalogalante/CCContest-2025-AI-solution, which includes the original PDFs and inputs, "every level passed" [COMMUNITY]:

| L | Task (story) | Input | Output | Metric / threshold | What actually worked |
|---|---|---|---|---|---|
| 1 | Sort BOPs (observation points) by popularity: higher temp first, then lower humidity, then lower id | CSV `BOP,Temperature [°C],Humidity [%]`, with a header | ids separated by spaces | exact | A plain sort. **Trap:** two temperatures are spelled out as words ("seventeen"). |
| 2 | Predict the missing "Bird Love Score" | CSV with vegetation, insects, urban light and score (`missing`); L1 table bundled | CSV `BOP,Bird Love Score [<3]` | RMSE < 6 (a), < 3 (b, c) | **Trap:** some °C values are actually °F. They form two clean clusters (≤45 vs ≥70) and are converted with (F−32)·5/9. The target is about 0.99-correlated with temperature, so **linear regression beat boosting**. File c has no labels, so train on a+b pooled. |
| 3 | Match 6 flocks to 6 species from prose descriptions | `Flock ID,BOP Path` (space-separated BOP sequence), species list | `Flock ID,Species` | exact (one of each species) | **Hand rules, no ML.** Palindromic route = Bluetit. Palindrome that is a *subset* of a Bluetit route = Wolfthroat. Identical closed loop = Blackfinch. Shared outbound leg then split = Goldhammer. Shared nest only = Firefinch. Hottest mean path temperature = Hurracurra. |
| 4 | Same task at scale: 360 flocks, 72 unlabelled, noisy | `Flock ID,BOP Path,Species\|missing` | `Flock ID,Species` | **macro-F1 > 0.90** | One feature row per flock: palindrome fraction, closed-loop fraction, pairwise Jaccard, longest common substring, common-prefix fraction, path temperature, and **overlap with Bluetit routes**. Then a RandomForest. CV 0.978. |
| 5 | Panel of 730 days × 2500 BOPs (Day, BOP, Arrivals, Occupancy, Wind X/Y, Insects Δ, 1.9 M rows, 58 MB). Predict the top 50 BOPs by arrivals for each of days 731–760 | Arrivals are `missing` for future days, other columns are given | `Day,Top 50 Arrivals BOPs` (30 lines) | mean daily overlap **> 0.50** | Future occupancy is given and correlates about 0.86 with arrivals. HistGradientBoosting**Classifier** on "is this BOP in today's top 50", rank-averaged 60/40 with the occupancy rank. **Validate on recent windows only.** Backtest 0.638. |
| 6 | "WeatherChanger": wind reversed. Top 50 for day 791, **100% required** | 30 more days plus the L5 panel again | 1 line | exact | **Puzzle, not ML.** Occupancy on new day t is bit-identical to old day 1521−t, so the answer is looked up in the L5 data. The solver asserts the mirror holds before relying on it. |

Runtimes: L1–3 and L6 take seconds, L4 about 1 minute, L5 a few minutes on CPU. The pip set used was `pandas pyarrow scikit-learn scipy`. Nothing heavier was needed.

### 1.2 The 2023 "spy / encrypted USB" game (AI category, 11 levels)
Source: sheilateozy/cloudflight-ai-coding-contest (PDFs and notebooks) [COMMUNITY]. The edition is probably the 38th CCC (20 Oct 2023), whose AI winner was "Random Forest Rangers" (JKU Linz) [OFFICIAL blog]. The repo does not confirm the edition.

| L | Task | Answer type | Threshold |
|---|---|---|---|
| 1 | PCA of a CSV to 2D; report the std of both components (2 decimals) | 2 numbers | exact |
| 2 | **Scatter-plot the PCA output; the points spell the ZIP password** | string | exact |
| 3 | train.csv cleaning: drop NaN rows and AMPS outliers outside [0,1]; report the row count | int | exact |
| 4 | Convert TEMP Kelvin→°C and report mean/std. Unit "?" is ambiguous; the hint says to use the °C min/max to infer it | numbers | exact |
| 5 / 6 | Regress OUTPUT (MODE, POWER categorical; AMPS, VOLTS, TEMP, DELTA, GAMMA) | one prediction per line | RMSE ≤ 2.0 / ≤ 1.5 |
| 7 | **Reshape the 2500 test predictions to 50×50 and imshow; it shows the password** | string | exact |
| 8–11 | "Improve as much as possible" | predictions | RMSE ≤ 1.0 / 0.75 / 0.5 / 0.45 |

The author placed in the top 10% using Optuna-tuned XGBoost and LightGBM plus an H2O deep-learning stacked ensemble of 40 models in about 1 h of training. The **tail levels (8–11) separated the leaderboard**. They reward squeezing the metric (tuning plus ensembling), and on synthetic data probably also discovering the true formula [INFERRED].

### 1.3 Dancing Bees (CCC of 11 Nov 2022, edition number unverified; AI category, 8 levels)
Source: MattiaSangermano/Cloudflight-Coding-Contest-AI-2022 (slide PDFs, code, report) [COMMUNITY].
Data: each sample is a 30-letter string over `a–i` (dance moves) with a label 0–4 (danger, food N/E/S/W). There are three unlabeled test files: simple (classes 0/1 only), full, and imbalanced.

| L | Task | Threshold |
|---|---|---|
| 1 | Class histogram of train (one count per line) | exact |
| 2 | Drop samples whose length is not 30, recount; "use filtered data for all following levels" | exact |
| 3 | Binary 0 vs 1 on simple test | accuracy ≥ 60% |
| 4 | 5-class on full test | accuracy ≥ 60% |
| 5 | Class 0 (Danger) on full test | precision ≥ 80% **and** recall ≥ 80%, plus accuracy ≥ 50% |
| 6 / 7 / 8 | Imbalanced test | **macro-F1 ≥ 65% / 90% / 98%** |

The solution used a Keras 2×LSTM with RandomOverSampler and class weights, reaching 0.99 macro-F1 on validation. [INFERRED] For 30-length sequences over 9 symbols, try first: **per-position one-hot (270 features) plus n-gram counts into LightGBM or LogReg**, or a small 1D-CNN/GRU in torch. That should be minutes, not hours.

### 1.4 What we could NOT find
- **2021 (first AI Challenge) and 2024 (39th/40th) Data/AI statements.** I searched GitHub (`cloudflight ai`, `ccc data ai`, `ccc 2024 ai`, the topic `cloudflight-coding-contest`) and the web and found nothing. Only Birds is listed as a platform practice game for the AI track (our `datasets.md`).
- **Official thresholds in machine-readable form.** game-info has none for Birds.
- **Whether the new platform shows the achieved metric value on a failed submit.** Unknown; see Open questions.
- **Winning teams' code or write-ups.** None found for "Mara & Cata" (2025) or "Random Forest Rangers" (2023).

## 2. Typical level progression, and what to expect on Friday

**Observed skeleton across the three games [COMMUNITY → INFERRED]:**

| Phase | Levels | Examples | Time budget target |
|---|---|---|---|
| A. Data literacy, exact answers | 1–2 (up to 4) | histogram, sort, filter invalid rows, PCA std, unit conversion, mean/std | ≤ 10 min each |
| B. First model, soft threshold | 3–5 | binary/multiclass accuracy 60%, RMSE < 6 / ≤ 2 | 15–25 min |
| C. Harder metric or scale | 4–8 | macro-F1 0.9+, per-class P/R, imbalanced test, 360 groups → aggregate features | 20–40 min |
| D. Twist | last 1–2 | forecast/rank (top-K per day), hidden image/password in data or predictions, time-reversed data, "100% required" | variable; think first |
| E. "Improve as much as possible" ladder | some games | RMSE 1.0→0.45, F1 0.65→0.98 | decides ranking |

**Recurring motifs to expect:**
- Data from earlier levels is reused and bundled again (`all_data_from_level_1.in`), and **traps persist** across levels (Birds' °F bug reappears in L2–L4).
- Story text encodes the rules, e.g. "flies back along the same route" means palindrome. Feed the PDF prose to Claude and have it turn each sentence into a candidate feature or rule.
- Hidden visual messages: plot 2D projections, reshape vectors to √n×√n, and look.
- Sample outputs are CSV with headers in Birds but bare lines in 2022/2023. **Copy the example format exactly**, including the header row and the id order of the input.
- Test sets are separate unlabeled files, or rows marked `missing` in the same file. Some files have no labels at all, so pool the labeled files.

**Likely task types, weighted by evidence:** [INFERRED]
1. Tabular regression/classification with dirty data: near-certain.
2. Sequence/trajectory/graph features (paths over node ids, strings): likely, given the 2022 and 2025 precedent.
3. Panel time series / ranking forecast: likely, given 2025.
4. Clustering/unsupervised (PCA appeared in 2023; "find K groups" fits the format): possible.
5. Anomaly detection (outliers are already a cleaning step): possible.
6. Images or real text: low. Never seen, and the 4-hour, any-language, CPU-laptop audience argues against it. A "hidden image" made of numbers is far more likely.
7. Simulation/RL: low, but the Classic track's simulation style could leak in. Reverse-engineering a generator (Birds L5/L6) is the Data/AI flavor of it.

Comparison with other short-format ML contests (Kaggle Days 4–8 h hackathons, IEEEXtreme data tasks, Codeforces/AtCoder ML-flavoured heuristics): they are dominated by **GBDT on tabular data, careful CV and feature engineering**, and deep models win only on images/text [INFERRED, general knowledge]. CCC differs in being **threshold/pass-fail**. Once you pass, extra accuracy is worthless except on the "improve" ladders. So optimize **time-to-pass**, not the leaderboard metric.

## 3. Fast-baseline playbook (4 h, threshold-based)

### 3.0 Universal scaffold (put it in `lib/ml.py` before Friday)
```python
import pandas as pd, numpy as np
from sklearn.model_selection import StratifiedKFold, KFold, GroupKFold, cross_val_predict
from sklearn.ensemble import HistGradientBoostingClassifier as HGBC, HistGradientBoostingRegressor as HGBR
from sklearn.metrics import f1_score, accuracy_score, mean_squared_error, precision_score, recall_score

def read(path):  # robust CSV: strip, 'missing'->NaN, words->numbers, keep header
    df = pd.read_csv(path, skipinitialspace=True, na_values=["missing", "?", "", "NaN", "nan"])
    return df
def coerce_num(s):  # 'seventeen' -> 17 ; '20,5' -> 20.5
    W = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
    return pd.to_numeric(s.astype(str).str.strip().str.lower().map(lambda x: W.get(x, x)).str.replace(",", "."), errors="coerce")
def cv(model, X, y, metric, groups=None, k=5, strat=True):
    split = GroupKFold(k) if groups is not None else (StratifiedKFold(k, shuffle=True, random_state=0) if strat else KFold(k, shuffle=True, random_state=0))
    p = cross_val_predict(model, X, y, cv=split, groups=groups); return metric(y, p), p
rmse = lambda y, p: mean_squared_error(y, p) ** 0.5
macro_f1 = lambda y, p: f1_score(y, p, average="macro")
```
`HistGradientBoosting*` handles NaN and `categorical_features="from_dtype"` natively and needs no install. Use LightGBM only when HGB is too slow or you need its knobs.

### 3.1 Per task type

| Task | Fastest strong baseline | Local validation | Pitfalls | Pretrained vs hand features |
|---|---|---|---|---|
| **Tabular classification** | `HGBC(max_iter=500, learning_rate=0.05, early_stopping=True)`; then `LGBMClassifier(n_estimators=2000, learning_rate=0.03, num_leaves=31)`; sanity `LogisticRegression` | StratifiedKFold 5; **GroupKFold** if rows belong to groups (flocks, users) | class-label spelling and order in the output, imbalance (use `class_weight="balanced"`), predicting groups vs rows | hand features |
| **Tabular regression** | Try **`LinearRegression`/`Ridge` first** (synthetic targets are often near-linear: Birds r = 0.99), then HGBR/LGBM; for the RMSE ladder, average LGBM+XGB+CatBoost+MLP | KFold 5, report RMSE vs threshold | unit mix-ups (°F/K), outliers in train (clip/drop), target outliers, predict for *all* test rows in input order | hand; try `PolynomialFeatures(2)` + Ridge to find the formula |
| **Formula discovery** (synthetic) | residual plots, `np.corrcoef`, fit Ridge on poly features, check if residual ≈ pure noise | CV RMSE flat across models means you are at the noise floor | Chasing RMSE below the noise floor wastes time; if the threshold is below the noise floor there **is** a hidden formula or a data trick | — |
| **Time series / panel forecast** | Seasonal-naive / last-value / rolling mean baseline, then a GBDT on lags (t−1, t−7, rolling means, day-of-week, given future covariates). Predict the graded object directly (e.g. top-K membership classifier) | **Rolling-origin backtest on the last N windows** with the same horizon as the task (`TimeSeriesSplit` or manual cuts) | leakage from future columns, recursive error over long horizons, drift (old windows lie), rank ties | hand features; statsforecast (AutoETS/ARIMA) only for single univariate series |
| **Sequence / string classification** (2022 bees) | one-hot per position + n-gram `CountVectorizer(analyzer="char", ngram_range=(1,3))` → LogReg/LGBM; then torch 1D-CNN/GRU (embedding 16, 2 layers, 10 epochs) | Stratified 5-fold | wrong-length samples, alphabet mapping fixed across train/test | hand; deep only if GBDT stalls |
| **Trajectory / path / graph** (2025 birds) | Aggregate per entity (path or group) to one feature row (see 3.2) → RandomForest/HGBC | GroupKFold by entity | Predicting per row when grading is per group (vote), node ids treated as numbers | hand features; networkx for graph stats |
| **Text classification** (if real text appears) | `TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)` + `LogisticRegression(C=4)`; then `SentenceTransformer("all-MiniLM-L6-v2").encode()` + LogReg | Stratified 5-fold | leakage of duplicate texts across folds | TF-IDF first; embeddings if < 1k samples or semantic |
| **Image classification, small data** | Frozen `torchvision.models.resnet50(weights="DEFAULT")` or `timm` `convnext_tiny` features (penultimate layer) → LogReg; fine-tune only if needed | Stratified 5-fold on embeddings (seconds) | resize/normalize to ImageNet stats, grayscale→3 channels, test order | **pretrained** always; CPU embedding of 10k images ≈ minutes |
| **"Numbers that are an image"** | `plt.imshow(v.reshape(int(len(v)**.5), -1))`, scatter of 2D/PCA, try transposes | eyeball | try both row/col orders, threshold the colormap | — |
| **Clustering** | Standardize → PCA → `KMeans(k)` (k given by story), else `HDBSCAN`/`DBSCAN`; Hungarian (`scipy.optimize.linear_sum_assignment`) to map clusters to named labels | silhouette; known labeled subset | label permutation, scale, k from story text | hand; UMAP only for looking |
| **Anomaly detection** | z-score/IQR per feature, `IsolationForest(contamination=story_rate)`, rule from story ranges | labeled anomalies if any; the expected count from the story | range given in PDF is the rule (2023: AMPS ∉ [0,1]) | rules first |
| **Geospatial** | haversine distances, bearings, grid/geohash bins, KNN on lat/lon, `BallTree(metric="haversine")` | spatial GroupKFold (by region/bin) | lat/lon order swap, degrees vs radians, wraparound at ±180° | hand |

### 3.2 Feature tricks: trajectory, geospatial and time ("migratory birds"-type data)
- **Path shape:** length, unique-node ratio (revisits), `p == p[::-1]` (palindrome or out-and-back), `p[0]==p[-1]` (closed loop), longest common prefix/suffix across a group's paths, pairwise Jaccard (mean/min/max), longest common substring ratio, positions where all paths align, number of distinct paths in the group.
- **Cross-entity relations:** overlap with paths of *another* class (Birds' predator/prey feature carried L4), shared-node counts, graph degree/PageRank of visited nodes (networkx), edge-transition counts.
- **Node attributes joined in:** mean/max/min of per-node features along the path (temperature, humidity), after fixing their units.
- **Geo:** step distance (haversine), total/net displacement, straightness = net/total, turning angles, heading histogram, speed stats if timestamps exist, bbox and centroid, radius of gyration, latitude change sign (seasonal migration direction), distance to a known "home" point.
- **Time:** lags, rolling mean/std (7/30), diff, day-of-week/season from the day index (`day % 7`, `day % 365`), ratio to own history (`arrivals/occupancy`), cross-sectional rank per day (`groupby(day).rank(pct=True)`), **conservation identities** (in − out = Δstock; Birds: departures(t) ≈ arrivals(t−1)).
- **Invariant checks for "twist" levels:** compare a new file with older files (exact row equality after shift, reversal `t→C−t`, sign flip, permutation of ids), `df.duplicated()`, `np.array_equal` across days.

### 3.3 Pitfalls checklist (paste into the solve prompt)
1. Units and encodings: °F/°C, K, spelled-out numbers, decimal commas, `missing`, `?`, whitespace after commas.
2. Ranges stated in the PDF are rules for outlier removal.
3. Output: exact header, id column, the same order as the input/test file, all rows present, label spelling identical to the species/label list file, no index column, trailing newline.
4. Metric: re-implement the PDF metric locally (macro vs weighted F1; per-day accuracy averaged; RMSE vs MSE).
5. Imbalance: the test may be imbalanced while train is not (2022 L6–8). Use class weights or threshold tuning per class for macro-F1.
6. Group vs row: the grade is per flock/day but the data is per bird/BOP. Aggregate before training, or vote.
7. Leakage: never compute features with the test labels or the future. For time series, cut features at the forecast origin.
8. Files without labels (Birds L2 c): train on the pooled labeled files.

## 4. How an LLM/agent-assisted team should work

### 4.1 Roles for 2–3 people, each running Claude Code [INFERRED]

| Role | Owns | First 10 min of each level |
|---|---|---|
| **Driver / IO** | fetch, `parse.py`, `score.py` (metric from the PDF), `write_out()` in the exact format, submit | read the PDF together with Claude; produce the parsed DataFrame and the scorer; submit the trivial baseline on the example |
| **EDA / trap hunter** | `describe()`, value counts, unit clusters, plots, story-rule→feature mapping, invariant checks, "is this a puzzle?" | find all dirty-data traps and any exact structure; hand rule-based features to the modeler |
| **Modeler** | `lib/ml.py` CV loop, HGB/LGBM/linear sweep, ensembling, seeds | have a CV score vs threshold within 15 min |

With only 2 people, merge EDA into the Driver role. Everyone works in **separate folders** (`levelN/a_*.py`, `levelN/b_*.py`) to avoid edit conflicts, and the shared `lib/` changes only via the Driver.

### 4.2 Operating rules
- **Score locally, then submit.** The local scorer must reproduce the exact PDF metric. Submit when CV ≥ threshold + margin (e.g. RMSE ≤ 0.85×threshold, F1 ≥ threshold + 0.02), because the test split can be harder (Birds L5: recent windows).
- **Exact-answer levels:** verify on `0-example` (unscored, so free) before uploading scored files.
- **Wrong submissions:** the legacy rule was +1 penalty minute. For 2026 it is unknown, so treat them as costly (our `docs/contest/scoring-and-ranking.md`). Do not "probe" the hidden test by repeated submits unless the penalty is confirmed to be zero.
- **Threshold hunting when CV is borderline:** (a) add a linear-model sanity check, (b) seed-average 5 models, (c) blend GBDT and linear, (d) tune the class-probability thresholds per class on OOF predictions for F1/precision/recall constraints, (e) re-read the story for a missed rule. Do not grid-search for an hour. In this contest a missing insight is the usual blocker.
- **Determinism:** set `random_state=0` everywhere, `torch.manual_seed(0)`, and save `oof.npy`, `test_pred.npy` and the model (`joblib.dump`) per experiment. Write the experiment ID into the output filename, so a passing file can always be regenerated or resubmitted.
- **Reuse across levels:** keep cleaned data as Parquet (`df.to_parquet`). Later levels re-ship the earlier data (Birds shipped the 58 MB L5 panel again in L6), and Parquet loads in about 1.5 s.
- **Claude prompts that work:** "Here is the PDF text and `head` of every input. List (1) the exact output format, (2) the metric and threshold, (3) every data trap you can find by running checks, (4) story sentences that imply rules." Then: "Write `solve.py` that prints CV metric vs threshold and writes the output. Do not submit."
- **Use the instant verdict for exact levels** (phase A): submit as soon as the example matches. For model levels, the verdict is a pass/fail oracle. Bank the pass and move on. Return to the "improve" ladder only if time remains.
- **Parallelism:** while the modeler trains (minutes), the trap hunter reads the *next* level's story once it unlocks, since levels build on the same data.

## 5. Environment checklist

### 5.1 Packages: Windows wheel availability for Python 3.14 (PyPI JSON, 2026-10-19) [OFFICIAL]

| Package | Latest | Py3.14 Windows wheel | Note |
|---|---|---|---|
| numpy / pandas / scipy | 2.5.4 / 3.0.6 / 1.18.1 | ✅ cp314 | installed |
| scikit-learn | 1.9.1 | ✅ cp314 | installed (1.9.1) |
| lightgbm | 4.7.0 | ✅ `py3-none-win_amd64` | installed |
| xgboost | 3.4.1 | ✅ `py3-none-win_amd64` | installed |
| catboost | 1.2.10 | ✅ cp314 | **not installed**, optional |
| torch / torchvision | 2.14.1 / 0.29.1 | ✅ cp314 (PyPI = **CPU-only** on Windows) | local is `2.12.0+cpu`; torchvision excludes 3.14.1 exactly |
| torch CUDA | 2.14.1+cu126 / +cu130 | ✅ cp314 on download.pytorch.org | `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126` |
| pyarrow | 26.0.0 | ✅ cp314 | needed for Parquet; **not installed** |
| polars | 2.0.0 | ✅ pure | optional |
| statsmodels / statsforecast | 0.15.0 / 2.1.1 | ✅ cp314 | optional (TS) |
| optuna | 5.0.0 | ✅ pure | optional (tuning ladders) |
| imbalanced-learn | 0.14.2 | ✅ pure | optional |
| timm / transformers / sentence-transformers | 1.0.30 / 5.20.1 / 6.1.0 | ✅ pure (+ tokenizers cp314, safetensors abi3) | insurance only |
| opencv-python | 5.0.0.93 | ✅ abi3 win_amd64 | insurance only |
| hdbscan / umap-learn / networkx / shapely / scikit-image / numba | — | ✅ all | optional |
| prophet | 1.5.0 | ✅ `py3-none-win_amd64` | skip (slow, rarely beats GBDT) |

None was flagged missing. The earlier risks for catboost/lightgbm on 3.14 are resolved. Recommended additions to `requirements.txt`: `pyarrow joblib matplotlib optuna imbalanced-learn statsmodels catboost`. Optional insurance: `timm sentence-transformers`.

### 5.2 Offline weights to pre-download (venue Wi-Fi insurance) [INFERRED]
```bash
set TORCH_HOME=%USERPROFILE%\.cache\torch & set HF_HOME=%USERPROFILE%\.cache\huggingface
python -c "import torchvision.models as m; m.resnet18(weights='DEFAULT'); m.resnet50(weights='DEFAULT'); m.efficientnet_b0(weights='DEFAULT')"
python -c "from sentence_transformers import SentenceTransformer as S; S('sentence-transformers/all-MiniLM-L6-v2')"
python -c "import timm; timm.create_model('convnext_tiny', pretrained=True)"
```
The total is about 0.4 GB. CLIP ViT-B/32 (`open_clip` or `transformers`, about 0.6 GB) is useful only for zero-shot image labels, so it is optional. Also run `pip download -r requirements.txt -d wheels\` so a reinstall works offline.

### 5.3 GPU vs CPU
- Every past solution ran on CPU in seconds to minutes (Birds L5, the heaviest at 1.9 M rows, took "a few minutes" with HGB). 16 cores are plenty: use `n_jobs=-1`, and LightGBM `num_threads=16`.
- Teo's laptop has an **RTX 4060 Laptop (8 GB)**, but torch is the CPU build. Install a CUDA build only if an image or sequence-deep task appears. Test it beforehand (`torch.cuda.is_available()`), because installing 2.5 GB of CUDA wheels during the contest is risky. The teammates' (Dobrin, Iustin) machines are unverified.
- XGBoost `device="cuda"` and CatBoost `task_type="GPU"` exist but are unnecessary at these data sizes.

## Open questions
1. Does the 2026 platform show the **achieved metric value** on a failed ML submission, or only Wrong? This decides whether submit-probing is useful. Check in the Birds hands-on run.
2. Is there still a **wrong-submission penalty** in 2026? (Shared with the rules agent.)
3. Are thresholds per file (Birds L2: a < 6, b/c < 3) shown anywhere besides the PDF? game-info has none.
4. Did 2024's Data/AI game exist on the platform under another slug (e.g. `ccc-2024.10-ai-*`)? It was not found. Ask on Discord or check `ccc.py games` for hidden AI slugs.
5. Which edition was the sheilateozy "2023 AI category" game (37th spring or 38th Oct 2023)?
6. Can Birds L5 pass with a pure occupancy-rank baseline? (Correlation 0.86 suggests it might come close to 0.5.) This is useful for calibrating "how good is good enough".

## Sources
- Birds game-info (public JSON): https://birds.codingcontest.org/game/game-info [OFFICIAL]
- Birds full solution + original PDFs/inputs: https://github.com/goncalogalante/CCContest-2025-AI-solution [COMMUNITY]
- 2023 AI category PDFs + notebooks: https://github.com/sheilateozy/cloudflight-ai-coding-contest [COMMUNITY]; author's article: https://towardsdatascience.com/stacked-ensembles-for-advanced-predictive-modeling-with-h2o-ai-and-optuna-8c339f8fb602 [COMMUNITY]
- Dancing Bees 2022 PDFs + code: https://github.com/MattiaSangermano/Cloudflight-Coding-Contest-AI-2022 [COMMUNITY]
- 41st CCC recap (Migratory Birds, 6 levels, winners Mara & Cata): https://www.cloudflight.io/en/blog/41st-cloudflight-coding-contest-brings-together-developers-worldwide/ [OFFICIAL]
- 2021 AI Challenge introduction: https://www.cloudflight.io/en/blog/europes-biggest-coding-contest-will-take-place-on-november-5th-as-hybrid-event/ [OFFICIAL]
- 2023 recap (AI winner Random Forest Rangers): https://www.cloudflight.io/en/blog/cloudflight-coding-contest-2023-new-partners-and-locations-continue-event-success/ [OFFICIAL]
- 42nd CCC event page ("Data/AI: Let your model find the perfect algorithms"): https://www.cloudflight.io/en/event/42-cloudflight-coding-contest/ [OFFICIAL]
- CCC overview (Data/AI 4 h, all languages): https://www.cloudflight.io/en/the-cloudflight-coding-contest/ [OFFICIAL]
- PyPI JSON per package, e.g. https://pypi.org/pypi/lightgbm/json, https://pypi.org/pypi/catboost/json, https://pypi.org/pypi/torch/json [OFFICIAL]
- PyTorch CUDA wheel index: https://download.pytorch.org/whl/cu126/torch/ [OFFICIAL]
- sklearn HistGradientBoosting: https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting [OFFICIAL]
- sklearn TimeSeriesSplit / GroupKFold: https://scikit-learn.org/stable/modules/cross_validation.html [OFFICIAL]
- Our own notes: `C:\Personal\Business\mvp\AiEngineer - ccc\docs\contest\scoring-and-ranking.md` (penalty rules), `docs\knowledge\datasets.md` (platform practice games)
