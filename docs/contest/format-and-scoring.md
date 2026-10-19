# Format and scoring (Data/AI)

## Structure
- **A story over levels** (3–11 in past editions; Birds had 6). Level N+1 unlocks only when every scored file of
  level N passes. Later levels reuse earlier data and code. Source: game client + past PDFs (research reports).
- **Per level:** a zip with the PDF statement, input files `in_level-N_<fileId>.txt`, sometimes an unscored
  `0-example` with its expected output, and extra data (`all_data_from_level_K.in`, label lists). Verified hands-on
  on Birds 2026-10-19. Birds file ids: L1 `0-example, 1-a … 5-e`; L2–L3 `0-example, 1-a, 2-b, 3-c`;
  L4 `0-example, 1-main`; L5–L6 `1-main` only (no example). Source: Birds `game/game-info` (needs
  `Referer: https://birds.codingcontest.org/` + `Sec-Fetch-Site: same-origin`).
- **You upload output files only**, one per input. The CLI names them so the platform's rule ("last number picks
  the case") matches.

## Metrics and thresholds
- Each level states a **metric and a threshold in the PDF** (exact order, RMSE < 3, macro-F1 > 0.90, daily
  top-50 overlap ≥ 0.50, 100%…). Thresholds can differ **per file** (Birds L2: a < 6, b and c < 3). They are not in
  `game-info` (no `passScore`, all `optimization: false` on Birds).
- **The verdict shows the achieved score** for CORRECT and WRONG submissions alike, e.g.
  `RMSE = 2.5604 (limit 6.00)`, `Top-50 accuracy = 0.0193 (threshold 0.50)`. Tested hands-on 2026-10-19.
- **Cooldown:** after every submit, per level and file (~5 s measured in Classic). Upload size cap exists
  (HTTP 413), value unknown. Source: game client bundle (verification report).

## Ranking
- **Levels completed (descending), then time (ascending).** Every past AI leaderboard has `score: null`.
  Source: `https://codingcontest.org/api/hall-of-fame/contests/38/leaderboard`.
- The 2026 client also supports optimization levels ("Ranking goes by level, then score, then time: the next level
  outranks any extra points here"). None has been used in an AI contest so far; check `game-info` at the start.
- **Wrong submissions:** no current public text mentions a penalty (the pre-2026 rule was +1 min per wrong).
  A wrong submit did not change `passedAt` in a Classic Challenge test. Treat wrong submits as possibly costly.

## Open questions
- Does a wrong submit add penalty time in the real 2026 contest? (Spring 2023 finishing times up to 311 min
  suggest penalties existed then.)
- Upload size cap value and exact cooldown.
- Optimization levels in 2026?
