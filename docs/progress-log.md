# Progress log

Newest entry at the bottom. Heading format: `## YYYY-MM-DD: <signature>: <title>`, then Done / Findings / Next.

## 2026-10-19: teo-bootstrap: repo created (bootstrap it-1)
**Done**
- Private repo `Theosux/ccc-ai-engineer-data-ai` with CLAUDE.md, the signature ritual (`ccc-ai-context`),
  the team protocol (`docs/team/`), index and progress log.
- Background research agents on Data/AI contest facts and on problem types and strategy (reports in `docs/research/`).

**Next:** port the arena tooling to the DATA/AI contest, then verification of the research, then a hands-on
Migratory Birds solve (bootstrap it-2), then strategy, skills and runbook (it-3).

## 2026-10-19: teo-bootstrap: tooling, Birds 6/6, knowledge, strategy, handover (bootstrap it-1..it-3)
**Done**
- Tooling ported from Teo's Classic repo and re-pointed to `42nd-data-ai-ccc-5873`. All tests pass.
  `golive.py --preflight` passes against DATA/AI: team The Posers 3/3, CREIC Cluj.
- New `lib/ml.py`:
  - `read_csv` (clean headers), `clean_numeric` (spelled-out numbers, decimal commas, units);
  - `best_model` / `cv_score` / `quick_models`, metrics, output formatters;
  - tests in `lib/tests/test_ml.py`.
- **Migratory Birds 6/6 in 16.1 min** (fetch→pass), run `arena/runs/SPOILER-birds/`. Per level:
  - L1: 79 s, 2 WRONG (a spelled-out "seventeen"; a pandas-3 dtype bug).
  - L2: 113 s, linear regression, RMSE 2.55–2.70.
  - L3: 66 s, story rules.
  - L4: 115 s, ExtraTrees on flock features, F1 0.9885.
  - L5: 8 min, LightGBM + wind-kNN rank ensemble, top-50 accuracy 0.5687 against the 0.50 bar.
  - L6: 47 s, time-reversal lookup, 1.0.
- Research:
  - A: contest facts and 5 past editions with leaderboards.
  - B: past problems and a fast-baseline playbook.
  - Verification: 34 claims, 22 ✅ / 7 ⚠️ / 5 ❌; corrections applied in `docs/contest/` and `docs/knowledge/`.
- Docs:
  - `contest/` overview, format-and-scoring, rules;
  - `knowledge/` patterns, ml-playbook, past-games, datasets, resources;
  - `strategy/` workflow, runbook, training plan;
  - skills `ccc-ai-solve`, `ccc-ai-patterns`;
  - the session prompt `docs/team/session-prompt.txt` (a copy is on Teo's desktop).

**Findings**
- **The verdict shows the achieved score on CORRECT and on WRONG** (`Top-50 accuracy = 0.0193 (threshold 0.50)`),
  so each submit is an exact readout of the hidden metric.
- Thresholds exist only in the PDF and can differ per file. Birds game-info has no `passScore`.
- Inputs above 50 MB must not be committed (Birds L5/L6 are gitignored; re-fetch them).

**Next (Dobrin + Iustin):** `docs/strategy/training-plan.md`.
1. Decide the contest driver (`roles.md`).
2. Each runs a cold timed Birds Challenge run on their own account.
3. Practise the second-opinion handover.
4. Thursday: `--preflight`.
