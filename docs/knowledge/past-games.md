# Past Data/AI games: level by level

Sources: hands-on solve of Migratory Birds (2026-10-19, `arena/runs/SPOILER-birds/`) and research reports
[agent-A](../research/agent-A-contest-facts.md) / [agent-B](../research/agent-B-problems-strategy.md) (check
[verification-report](../research/verification-report.md) for what was confirmed).

> **SPOILER:** section 1 solves Migratory Birds, the only Data/AI practice game on the platform. If you want an
> honest timed rehearsal, do the cold Challenge run first (`docs/strategy/training-plan.md`) and come back here after.

## 1. Migratory Birds (41st Data/AI CCC, Nov 2025), `ccc-2025.11-ai-birds`, 6 levels ⚠ SPOILER
Our run (Opus 5.5, inline, exploration mode): **6/6 in 16.1 min** fetch→pass (L1 79 s, L2 113 s, L3 66 s, L4 115 s,
L5 8.0 min, L6 47 s). Not fully cold: a research summary had mentioned the L6 trick. 2025 winners: 85 min.

| L | Task | Input → output | Metric (from the PDF) | What worked | Trap / lesson |
|---|---|---|---|---|---|
| 1 | Sort observation points (BOPs) by popularity | CSV `BOP,Temperature [°C],Humidity [%]` → ids space-separated | exact order | sort: temp desc, humidity asc, id asc | **"seventeen" in a numeric column** → `lib.ml.clean_numeric`. Second bug: pandas 3 reads text as dtype `str`, not `object` |
| 2 | Predict missing "Bird Love Score" | CSV with `missing` rows + level-1 table → `BOP,Bird Love Score [<3]` (2 decimals) | RMSE < 6 / 3 / 3 per file | **plain LinearRegression**, score ≈ 1.7·T°C + 14.3 (noise σ 2.58, other features ≈ 0) | **°F mixed into °C** (values > 50, clean gap 50–70); file `3-c` has **no labels** → train on rows pooled from all files |
| 3 | Match 6 flocks to 6 species | `Flock ID,BOP Path` → `Flock ID,Species` | exact | **hand rules from the story prose**: palindrome = Bluetit (bigger one); palindrome ⊂ Bluetit nodes = Wolfthroat; identical loop = Blackfinch; long shared prefix then split = Goldhammer; of the rest, hotter BOPs (level-1 temps) = Hurracurra, other = Firefinch | the rules are ONLY in the story pages; every sentence is a feature |
| 4 | Same at scale: 360 flocks, 72 missing, noisy rows | `Flock ID,BOP Path,Species\|missing` | macro-F1 > 0.90 | per-flock features (palindrome score, pairwise Jaccard / positional match, prefix/suffix share, temps, node overlap with other flocks) → ExtraTrees. CV 0.982, **real 0.9885** | aggregate rows → one row per graded entity |
| 5 | Top-50 BOPs by arrivals for each of days 731–760 | 1.9 M rows (60 MB): Day, BOP, Arrivals, Occupancy, Wind X/Y, Insects Δ; future occupancy + wind given | mean daily top-50 overlap ≥ 0.50 | rank-average of LightGBM (forecast-origin samples, horizon feature) + wind-kNN rate×occupancy; last-known arrivals while the last wind regime continues. Holdout 0.56–0.60, **real 0.5687** | **random CV lies; validate with rolling origins** (cut 640/670/700 differed by 0.15). Wind is one value per day in constant regimes; per-BOP arrivals are smooth inside a regime |
| 6 | Top-50 for day 791 after a "WeatherChanger" | 30 new days + the L5 panel | 100% | **lookup**: day 761+k is bit-identical to day 760−k, so day 791 = day 730 | "think, don't train": check reversals/shifts/duplicates against old data first |

Community solution for L5 (goncalogalante): HistGradientBoostingClassifier on "is in today's top 50" rank-averaged
60/40 with the occupancy rank, backtest 0.638. 37 of the 2025 teams got stuck at L5: it is the hard level.

## 2. Spy Mission (37th AI CCC, spring 2023), 11 levels
PDFs: github.com/GabrielNedianu/AI-CONTEST-SPRING-2023, github.com/sheilateozy/cloudflight-ai-coding-contest.
| L | Task | Answer | Threshold |
|---|---|---|---|
| 1 | PCA of a CSV to 2D, report std of both components (2 decimals) | 2 numbers | exact |
| 2 | **Scatter-plot the PCA output: the points spell the ZIP password** | string | exact |
| 3 | Clean train.csv: drop NaN rows and AMPS outliers outside [0,1], report row count | int | exact |
| 4 | TEMP Kelvin → °C, mean/std; unit "?" ambiguous (infer from °C min/max) | numbers | exact |
| 5–6 | Regress OUTPUT (categoricals MODE, POWER + numerics) | predictions | RMSE ≤ 2.0 / 1.5 |
| 7 | **Reshape the 2500 test predictions to 50×50 and imshow: it shows the password** | string | exact |
| 8–11 | "Improve as much as possible" | predictions | RMSE ≤ 1.0 / 0.75 / 0.5 / 0.45 |
The RMSE ladder (8–11) separated the field. Winner "Random Forest Rangers" (JKU Linz) took 51 min.

## 3. Dancing Bees (36th AI CCC, Nov 2022), 8 levels
PDFs: github.com/MattiaSangermano/Cloudflight-Coding-Contest-AI-2022, github.com/dslavulj/CCC-2022-AI.
Each sample is a 30-letter string over `a–i` (dance moves) → label 0–4. Test files: simple, full, imbalanced.
| L | Task | Threshold |
|---|---|---|
| 1 | class histogram | exact |
| 2 | drop samples whose length ≠ 30, recount (use filtered data from now on) | exact |
| 3 / 4 | binary on simple test / 5-class on full test | accuracy ≥ 60% |
| 5 | class 0 on full test | precision ≥ 80% and recall ≥ 80% (+ acc ≥ 50%) |
| 6 / 7 / 8 | imbalanced test | macro-F1 ≥ 65% / 90% / 98% |
Fast route: per-position one-hot (270 cols) + char n-grams → LightGBM/LogReg; a small LSTM/1D-CNN reached 0.99.
Winner took 32 min.

## 4. Smart Farming (38th AI CCC, autumn 2023), 8 levels: computer vision
PDFs: github.com/eduardhogea/CCC_AI_2023. 200×200 RGB drone images. L1 detect animals (acc 80%, 100 train / 1000
test), L2 count (RMSE ≤ 0.75), L3 count under clouds (image pairs), L4 locate one animal (MSE distance ≤ 150),
L5 locate 5 ("Not all problems need to be solved with machine learning"), L6 count outside the fence. **Only 3 teams
finished**, winner 176 min. If 2026 has images: pretrained CNN features first (see `ml-playbook.md` §6).

## 5. Production Line (35th AI CCC, 2021), 3 levels: images
PDFs: github.com/dslavulj/CCC-2021-AI. L1 filter 28×84 label images by brightness, L2 binary classifier
(acc ≥ 93%), L3 regress an oven parameter from 28×196 images (RMSE < 0.075). Winner 92 min.

## Cross-game patterns
- **Exact-answer data literacy first** (sort, histogram, clean+count, PCA std), then a **first model with a soft
  threshold**, then a **harder metric or scale**, then a **twist** (hidden image/password, time reversal, 100%).
- **Every game plants dirty data** and keeps it in later levels: spelled-out numbers, °F/°C, K/"?", NaN, outliers,
  wrong-length samples. Earlier levels' data is re-shipped (`all_data_from_level_N.in`).
- **The data is generated.** Look for the formula/structure before tuning: correlation with one feature, noise floor,
  reversals, reshapes. Simple models pass most levels; deep nets were needed only for images.
