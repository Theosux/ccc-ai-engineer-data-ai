---
name: ccc-ai-solve
description: Fast loop for solving a CCC DATA/AI level with the arena CLI (fetch → read statement + traps → solve.py with CV + check() → go → read score). Use when training on Migratory Birds or another game, or during the contest, whenever the user says "solve level N", "next level", "start training", or "contest started". Use together with ccc-ai-patterns.
---

# CCC DATA/AI solve loop

CLI: `python arena/ccc.py` from the repo root (`arena/README.md`). Procedure details: `docs/knowledge/ml-playbook.md`.
**Target: few tool calls per level**: an exploration run (traps + CV table), Write solve.py, `go N`.

## 0. Setup
- **Contest:** follow `docs/strategy/contest-day-runbook.md`. Only the **contest driver** (`docs/team/roles.md`)
  runs `golive`, `go` and `submit`. From T-15 run `python arena/golive.py --browser` in the background; it exits with
  the level 1 statement printed.
- **Training:** `python arena/ccc.py train ccc-2025.11-ai-birds --mode challenge --name birds-<signature>`, then `fetch 1`.
  Never open `arena/runs/SPOILER-birds/` during a cold rehearsal.

## 1. Read (statement + example are printed by `fetch N` / the tail of `go N-1`; don't re-read them)
Write down: output format (copy the example: header, separators, decimals, id order) · metric and threshold
**per file** (PDF text only) · story sentences that are rules · train vs test rows · extra files
(`all_data_from_level_K.in`, label lists). Image-only or garbled pages → `fetch N --png` and Read the PNGs.

## 2. Explore in ONE script (traps + baseline)
One Bash python run that: loads every input (`lib.ml.read_csv`), prints non-numeric values per numeric column,
histograms for unit clusters, NaN/outlier counts, labelled/unlabelled counts per file, and a `best_model(...)` CV
table with the PDF metric. For time series use rolling-origin cuts, not random CV. Look for an exact relation to old
data when the metric is exact/100%.

## 3. Write `arena/runs/<run>/levelN/solve.py` (Write tool only, never heredoc patches)
- It starts as a copy of level N-1's solver. stdin → stdout; diagnostics on stderr.
- Header: `import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))`, then
  `from lib.ml import read_csv, clean_numeric, best_model, fmt_space, fmt_lines`.
- Read sibling data with `pathlib.Path(__file__).resolve().parent / "files" / "<name>"` (cwd is levelN).
- Files with no labels: train on labelled rows pooled from every `files/in_level-N_*.txt`.
- **Add `check(data, out)`** (header, ids/order, count, valid labels): `go` then accepts predictions that differ from
  the example.

## 4. `python arena/ccc.py go N` (tool timeout 600000; heavy training: `go N --timeout 900`)
- Runs every input, applies `check()`, submits sequentially (smallest first), stops at the first WRONG.
- **The verdict prints the achieved score** (`RMSE = 2.56 (limit 6.00)`, also on WRONG). On WRONG: read the gap,
  climb the ladder in `ml-playbook.md` §5 (re-read story → noise floor → features → blend), then `go N` again.
- PASSED prints the next level. After each pass (contest): commit `arena/runs` in the background.

## Rules
- Never submit in parallel or from two laptops. Never pipe `go` into `tail`/`grep` before chaining a submit.
- Submit when CV clears the threshold with margin. One calibration submit is fine when validation is doubtful.
- No side work while a level is unsolved. Big inputs (> 50 MB) must not be committed (add them to `.gitignore`).
