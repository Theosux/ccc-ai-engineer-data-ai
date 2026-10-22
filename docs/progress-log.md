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
  - L2: 113 s, linear regression, RMSE 2.55-2.70.
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

## 2026-10-22: iustin: autopilot train run birds-auto-1628, 6/6 in about 6 min (NOT graded)
**Done**
- Autonomous Claude drove run `birds-auto-1628` from the go-live output to `ALL LEVELS DONE`, no human input.
  Fetch L1 16:28:29, fetch L6 16:33:59, L6 done 16:34:23 (local), about 6 min in total. Per level (fetch to fetch):
  - L1: 24 s. Sort by temperature desc, humidity asc, id asc; raw values (no °F fix); "seventeen" mapped to 17.
  - L2: 47 s. Join L1 temps (°F cluster >= 55 converted), LinearRegression, CV RMSE 2.58 (bars 6/3/3).
  - L3: 38 s. Story rules: identical palindrome = Bluetit, its node subset = Wolfthroat, identical cycle =
    Blackfinch, shared prefix = Goldhammer, hottest loop flock (about 43 °C) = Hurracurra, other loop flock = Firefinch.
  - L4: 88 s. One feature row per flock (palindrome score, path similarity, temps, edge overlap with other
    palindromic flocks), ExtraTrees, CV macro-F1 0.9965 (bar 0.90).
  - L5: 134 s. Rank blend of same-day occupancy and mirrored wind-kNN (k=10). Rolling-origin CV is noisy
    (0.30 to 0.63 depending on the cut); chosen from the rehearsal grader readouts, not from CV.
  - L6: 24 s. Exact lookup: day t == day 1521 - t, found programmatically; day 791 = day 730.

**Findings**
- **Nothing was actually graded.** Training contest 12063 (started 13:09 UTC) already had every file passed from
  the earlier `birds-iustin` run, so `go` printed `already passed (skipped)` and submitted nothing on every level.
  The "PASSED" lines only reflect the old server state. The L5 blend in particular is unverified.
- For an honest autopilot rehearsal, start a fresh `train` contest first so the grader sees new submissions.

**Next:** rerun the autopilot on a fresh training contest to get real verdicts (especially L5), then the
`--preflight` check before Friday.

## 2026-10-22: iustin: cold Birds rehearsal 6/6 in 14:04, contest autopilot built and dress-rehearsed
**Done**
- Setup on the driver's Mac: requirements, tests ALL OK, `login --http`, `golive.py --preflight` ALL OK
  (The Posers 3/3, CREIC). Fixes: ortools 9.14 pin on macOS (9.15 CP-SAT deadlock), Edge->Chrome browser fallback.
- Roles: driver = iustin; Dobrin left, Gurita replaces him (second opinion).
- **Cold Challenge rehearsal, run `birds-iustin`: 6/6 in 14:04** (16:09:53 to 16:23:57). The 2025 winner took
  85 min; Teo's spoiler run took 16.1 min. Per level: L1 ~1.5 min (1 WRONG: converted °F the grader wanted raw),
  L2 ~1 min (linear, RMSE 2.55-2.70), L3 ~1 min (story rules, first try), L4 ~1 min (ExtraTrees, F1 0.9755),
  L5 ~7.5 min (ratio14 0.32 WRONG despite 0.747 CV; future occupancy 0.528 PASS), L6 ~1.5 min (mirror, 1.0).
- **Autopilot** (`arena/autopilot.sh`, prompt `docs/strategy/autopilot-prompt.md`): caffeinate, login, golive until
  level 1, then an autonomous Opus session. `--schedule HH:MM` (launchd opens Terminal by itself; tested).
- **Hands-off dress rehearsal `birds-auto-1628`: launch to ALL LEVELS DONE in 6.5 min, zero human input.** The
  platform reused the finished Challenge, so nothing was submitted; graded offline instead: L1, L2, L3, L6 outputs
  byte-identical to accepted ones, L4 agrees on 70/72 flocks with the accepted 0.9755 answer, L5 scores 0.513 against
  the true arrivals revealed in L6's data (bar 0.50). Caveat: its prompt carried the Birds lessons, so 6.5 min is
  optimistic for an unseen game.

**Findings**
- One Challenge per game per account: `train --mode challenge` returns the same contest once it is done.
- L5 post-mortem against the truth: wind-kNN with the wind sign flipped 0.605 > persistence 0.562 > wind-kNN 0.550 >
  occupancy 0.528 > ratio14 0.322. Lessons in `docs/knowledge/ml-playbook.md` section 9.

**Next:** Fri: `bash arena/autopilot.sh --schedule 15:30` at the venue after Wi-Fi + `--preflight`.

## 2026-10-22 23:05: iustin: duo mode, both laptops solve in parallel
**Done**
- `arena/duo.py` + `docs/strategy/shadow-prompt.md`: the second laptop (gurita) runs `autopilot.sh --shadow` or
  `duo.py shadow`, waits for the driver's level 1 via git, and an autonomous Claude solves the same open level with a
  deliberately different approach, publishing `arena/runs/<run>-gurita/levelN/solve.py` + NOTE.md. It never talks
  to the platform. The driver shares after every `go`, posts WRONG verdicts as notes, and after a WRONG or 10 min on a
  level runs `duo.py take` + `go N --solver solve_gurita.py` (rules 6 and 7 in `autopilot-prompt.md`).
- `autopilot.sh`: signature from `.claude/signature.local` (prompt no longer hard-wired to iustin), `--run NAME`,
  `--shadow`, `--schedule` keeps the other flags. Friday's installed job is unchanged (contest mode).
- Tested on two local clones with a bare remote (no test commits on GitHub): share level 1 (0.2 s), shadow mirror +
  `run` ALL OK, publish, driver note, `take` + `run --solver` ALL OK, a 58 MB input as a 14 MB .duo.gz (2 s, identical
  after unpacking), launcher waiting for level 1 and starting Claude with no unfilled placeholders.

**Next:** gurita setup + joint graded rehearsal (handoff message); Friday: driver `--schedule` (installed), gurita `--shadow`.

## 2026-10-22: gurita: shadow laptop setup, login and preflight
**Done**
- First session on this Mac (macOS 27.0.1, arm64). Signature `gurita`. Python is `python3` 3.13.7.
- `pip install -r requirements.txt` (ortools 9.14.6206). Playwright Chromium installed. `brew install libomp` so LightGBM loads.
- Tests ALL OK: `test_ml.py` 1.9s, `test_lib.py` 6.9s (CP-SAT did not hang), `test_golive.py` 6.0s.
- `python3 arena/ccc.py login --http` OK as **gura**. `python3 arena/golive.py --preflight` ALL OK: The Posers 3/3, CREIC Cluj-Napoca, contest OPEN_REGISTRATION, T-16:20, clock +0.05s. Team members: iusty64, teosux, gura.
- `python3 arena/duo.py status contest`: driver has not shared level 1 yet.

**Findings**
- This account is on the team. Platform username is `gura`.
- No active training. Birds `bestScore` is null and `currentLevel` is 1, so the graded Challenge still looks unused. Not started: it needs Iustin on `bash arena/autopilot.sh --shadow --run birds-duo` at the same time.

**Next:** joint Birds rehearsal (`birds-duo`) once Iustin's shadow is waiting. Friday: `bash arena/autopilot.sh --shadow` (or `--schedule "2026-10-23 15:30" --shadow`).

## 2026-10-22 23:55: iustin: duo mode works with Cursor (gurita uses Cursor + Grok)
**Done**
- `duo.py shadow --agent auto|claude|cursor|paste [--model SLUG]`; `autopilot.sh --agent/--model` (driver too, so
  a Cursor laptop can drive the rehearsal). Cursor CLI: `agent --force [-p --output-format text]`. Paste mode prints a
  one-line prompt for Cursor's chat and announces each new level. The full prompt goes via
  `arena/runs/<run>-<sig>/PROMPT.txt` (Windows .cmd wrappers break multi-line arguments).
- The shadow sets its active run in `arena/.auth/state.json` (`duo.py activate RUN` by hand), so plain
  `python arena/ccc.py run N` works in any terminal, including PowerShell where `CCC_RUN=... cmd` does not.
- `.cursor/rules/ccc.mdc` (always on): Cursor follows CLAUDE.md and reads `.claude/skills/*/SKILL.md` as playbooks.
- Tested with a fake `agent` binary: auto-pick without claude, `--model` passthrough, active run, paste mode
  announcing level 2 and ALL LEVELS DONE. Not tested: the real Cursor CLI (not installed on the driver Mac).

## 2026-10-23: gurita: Cursor CLI signed in, Friday command set, Birds clock already running
**Done**
- Signature `gurita`. macOS 27.0.1 arm64. Python is `python3` 3.13.7 (`python` is not on PATH).
- `pip install -r requirements.txt` already satisfied (ortools 9.14.6206). Playwright Chromium present.
  Tests ALL OK: `test_ml.py` 1.9s, `test_lib.py` 6.4s, `test_golive.py` 6.0s.
- `arena/.auth/credentials.env` was already mode 600 with both values set. `python3 arena/ccc.py login --http` OK as **gura**.
  `python3 arena/golive.py --preflight` ALL OK: The Posers 3/3, CREIC Cluj-Napoca, OPEN_REGISTRATION, T-16:01, clock +0.05s.
  Team members from `GET /api/teams/53622`: **iusty64**, **teosux**, **gura**.
- Cursor CLI installed: `agent` 2026.10.22-27dcf5f, signed in. Friday model slug: `grok-4.7-high`.
- `python3 arena/duo.py status contest`: driver has not shared level 1 of `contest`.

**Findings**
- `claude` is on PATH (`~/.local/bin/claude`), so `duo.py shadow` with `--agent auto` starts Claude. Friday must pass `--agent cursor`.
- The graded Birds Challenge is already RUNNING: `training-ccc-2025.11-ai-birds-66585-8e34538f`, start 2026-10-22 20:45:06Z,
  240 min, about 224 min left at 21:01 UTC (ends ~03:45 Romania). Level 1 is in `arena/runs/birds-duo` (commit ecb877b);
  passed files are all null and `bestScore` is null. The 23:41 handoff line "Not started" is stale.

**Next:** Friday 15:30, `bash arena/autopilot.sh --schedule "2026-10-23 15:30" --shadow --agent cursor --model grok-4.7-high`.
Birds duo only if Iustin's shadow is up during this window.
