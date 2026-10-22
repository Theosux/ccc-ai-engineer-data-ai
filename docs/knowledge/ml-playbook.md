# ML playbook: one Data/AI level under time pressure

Ranking = **levels completed, then time**. A level counts only when every scored file passes its threshold. Extra
accuracy above the threshold is worth nothing (unless the level is an optimization level, see §7).
So optimize **time-to-pass**: the simplest thing that clears the bar, verified, submitted.

## 0. Fetch + read (≤ 2 min)
`python arena/ccc.py fetch N` prints the statement, the input `sizes:`, the other files in the zip
(`all_data_from_level_K.in`, label lists) and the example. Extract four things before writing code:
1. **Output format**: copy the example output exactly (header row, separators, decimals, order of ids).
2. **Metric + threshold per file**: they are only in the PDF text, and can differ per file (Birds L2: a < 6, b/c < 3).
3. **Story sentences that are rules** ("flies back along the same route" = palindrome; "some °C were °F").
4. **Which rows are train vs test** (`missing` markers, separate files, files with no labels).
If the statement is only bullets or looks garbled: `fetch N --png` and Read the page images.

## 1. Trap hunt (≤ 3 min, ALWAYS)
Run the trap checklist in [data-ai-patterns.md](data-ai-patterns.md): non-numeric values, unit clusters, NaN,
outliers, wrong-length rows, duplicates. Every past game planted at least one trap per dataset, and the same trap
returns in later levels that re-ship the data. Birds L1 cost 2 wrong submits on a spelled-out "seventeen".

## 2. Is it a puzzle? (≤ 2 min)
Exact metric (100%, "exact", a password) or a weird story twist → look for structure before modelling:
- an exact relation to earlier data (reversal, shift, duplicate, permutation; Birds L6 was the L5 data backwards);
- a formula (one feature with r ≈ 0.99; Birds L2 was linear in temperature);
- a hidden picture (reshape to √n × √n, scatter the PCA).
"Not all problems need to be solved with machine learning" (organizers, 2023).

## 3. Baseline + local score (≤ 10 min)
- Build `X, y` and run `best_model(X, y, "clf"|"reg", metric)` from `lib.ml`, a 5-fold CV table in seconds.
  Always include a linear model: on generated data it often wins (Birds L2 Ridge 2.58 vs LightGBM 2.92).
- Re-implement the PDF metric exactly (macro vs weighted F1, per-day average, RMSE not MSE).
- **Time series / forecasting:** never random CV. Use rolling origins: cut at several days (e.g. T−90, T−60,
  T−30) and forecast the same horizon the task asks for. Birds L5 scores at different cuts ranged 0.42–0.70.
- **Margin:** submit when CV clears the threshold with room (RMSE ≤ 0.9× limit, F1 ≥ limit + 0.02). If not, go to §5.

## 4. Submit and read the score
- `solve.py` gets a `check(data, out)` (right ids, count, labels, header) so `go N` accepts predictions that
  differ from the example. Then `python arena/ccc.py go N`.
- **The verdict shows the achieved score, on CORRECT and on WRONG alike** (tested 2026-10-19):
  `RMSE = 2.5604 (limit 6.00)`, `Top-50 accuracy = 0.0193 (threshold 0.50)`. Each submit is an exact readout of
  the hidden test metric. Per-file cooldown ~5 s.
- Wrong submits: no time penalty was measured in Classic Challenge mode (`passedAt` unchanged), but the 2026 contest
  rule is unconfirmed. So: **don't spam, but do use one real submit to calibrate** when the local CV is
  borderline or the validation scheme is doubtful (forecasting), instead of tuning blind for 20 min.

## 5. Not passing yet: the ladder (stop after the first rung that works)
1. **Re-read the story** for a missed rule or trap (most common blocker).
2. Check the **noise floor**: if every model lands at the same CV and the residuals look like pure noise, you are at
   the floor. If the threshold is below it, there is a hidden formula/feature, so don't tune.
3. Better **features** from the story and the structure (group aggregates, relations between entities, the
   previous level's data). Birds L4 went from rules to 0.98 with ~15 hand features.
4. **Model sweep and blend**: ExtraTrees / LightGBM / linear; rank-average or mean of the top 2–3; seed-average.
5. Classification constraints: class weights for imbalance; tune probability thresholds on out-of-fold predictions.
6. Time-box 15 min, then the second-opinion teammate attacks it with a different formulation (runbook).

## 6. Heavy data and images
- **Large CSVs** (Birds L5: 60 MB, 1.9 M rows): pandas `read_csv(low_memory=False)` loads in ~2 s; pivot to
  day × entity matrices and use numpy. No Python loops over rows. Cache with `df.to_pickle` for experiments.
- Training sets of millions of rows: LightGBM `n_jobs=-1` is fine (3 M rows × 16 features ≈ 30–60 s).
- **Images** (2021, autumn 2023): pretrained torchvision ResNet/EfficientNet embeddings → LogisticRegression;
  fine-tune only if needed. Pre-download weights before the contest (venue Wi-Fi). CPU embedding of 10k small
  images takes minutes. A CUDA torch build needs testing beforehand, never install it mid-contest.
- `go`'s default timeout is 180 s. Use `go N --timeout 900` for heavy training runs.

## 7. Optimization levels (possible in 2026)
`game-info` (cached in `arena/runs/<run>/game-info.json`) shows `optimization`, `passScore` and `scoreDirection`.
If a level is an optimization level: ranking is level, then score, then time. Passing still matters most,
because the next level outranks any score. Bank the pass first, improve only if nothing else is open.

## 8. Process rules carried over from the Classic training (they cost us minutes when broken)
- Write solvers with **Write/Edit only**, never heredoc or `python -c` patches (broke 6× in Classic training).
- **No side work while a level is unsolved.**
- Never pipe `go` into `tail`/`grep` and then chain a submit (the exit code is lost).
- Submit from **one laptop** only (concurrent submits lose updates on the server).
- Probe slow runs before full runs (`python arena/ccc.py probe N`), and read `sizes:` before choosing a method.

## Checklist before every submit
- [ ] trap checklist done            - [ ] output format = example (header, order, decimals)
- [ ] CV ≥ threshold with margin      - [ ] stdout = answer only (diagnostics on stderr)
- [ ] `check()` passes on every file

## 9. Lessons from Iustin's cold Birds rehearsal (2026-10-22, 6/6 in 14:04) *(iustin)*
- **Clean only what the statement asks for.** L1 shipped a 70..113 cluster that looks like °F; the grader wanted the
  raw values (the °F fix is requested only from L2 on). Cost: 1 WRONG.
- **A WRONG verdict is an oracle.** It reports the score (`1062/2171 positions correct`). Score each alternative
  interpretation against your own output: the one that reproduces the reported number is what the grader wants.
- **Forecast levels can hide a regime change.** L5: a ratio model scored 0.747 on 11 rolling-origin cuts and 0.32 on
  the real window. The hidden days 731-760 were already the "WeatherChanger" period that L6's story reveals.
  When the real score is far below CV, stop tuning and probe 2-3 structurally different models against the grader.
  Real L5 scores (truth revealed in L6's data): future occupancy 0.528, persistence 0.562, wind-kNN 0.550,
  wind-kNN with the wind sign flipped 0.605, ratio14 0.322.
- **macOS:** `ortools` 9.15 deadlocks with >1 CP-SAT worker (pinned 9.14 in requirements); Edge is missing, so the
  browser tools fall back to Chrome (`ccc.launch_browser`).
