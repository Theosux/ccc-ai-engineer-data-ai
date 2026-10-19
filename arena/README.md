# Arena: training + contest working folder

Ported from Teo's CLASSIC repo on 2026-10-19 and re-pointed at **`42nd-data-ai-ccc-5873`** (DATA/AI). Everything
below works unchanged for Data/AI games (tested on Migratory Birds). Setup per laptop:
`pip install -r requirements.txt`, then `python arena/ccc.py login` (browser login; needs `playwright` + Edge).
Train: `python arena/ccc.py train ccc-2025.11-ai-birds --name birds-<signature>`.
ML helpers: `arena/lib/ml.py` (tests: `python arena/lib/tests/test_ml.py`).

**Data/AI caveat:** `go` compares your example output with the expected one. For ML levels your predictions will
rarely match the example byte for byte, so give `solve.py` a `check(data, out)` (format checks + a CV score on
the labelled rows) or use `go N --force` once the CV score is safely above the level's threshold.

Run everything from the repo root: `python arena/ccc.py <cmd>`. Run selection: the active run, or `CCC_RUN=<name>` per command.

## The loop (2 tool calls per level)
1. `fetch N`: downloads the level and **prints the cleaned statement + example input/expected output**. `levelN/solve.py` starts as a copy of level N-1's solver (or a stub).
2. Edit `levelN/solve.py`: stdin → stdout. Optionally add `check(data, out) -> bool | (bool, msg)` for levels with many valid answers.
3. `go N`:
   - runs all inputs in parallel and verifies the example (or `check()` on every file);
   - submits smallest file first, **sequentially**, skips files already passed, and stops at the first WRONG;
   - if the level passed, **fetches N+1 and prints its statement**. So `go N` → write solver → `go N+1` → ...

Diagrams: `fetch N --png` renders the statement pages to `levelN/pages/p*.png` (local zip, ~1 s). Read them.

## Commands
| Command | What it does |
|---|---|
| **`python arena/golive.py [--browser] [--preflight] [--observe school]`** | **Contest day (preferred).** Preflight, then multi-detector watch (API poll, SSE, registrations, level-1 probe, optional Edge witness), auto-register, print level 1. See `docs/strategy/contest-day-runbook.md`. |
| `wait [contest] [--name contest]` | Contest day. Polls until the game is live (keeps the session warm), registers the run, prints level 1. Run it in the background from T-15 min. |
| `contest [contest] [--name contest]` | Registers the contest run now (fails clearly if not started). Default contest is `42nd-data-ai-ccc-5873`. |
| `train <gameSlug> [--mode exploration\|challenge] [--name X]` | Starts a practice run. Becomes active unless `CCC_RUN` is set. |
| `fetch N [--png] [--scale 0.75] [--zip FILE]` | Downloads, unzips, writes `map.json` and `statement.txt`, and prints the statement + example. `--png` renders all pages; image-only pages are auto-rendered. `--zip` ingests a manually downloaded zip (emergency). |
| `go N [--force] [--no-next] [--solver CMD] [--timeout S]` | Run + verify + submit + auto-fetch next. `--force` submits despite an example/check mismatch. |
| `run N [--only ID] [--solver CMD]` | Outputs only (into `levelN/out/`). |
| `submit N [--only ID ...] [--include-example]` | Submits (sequentially). With `--only` it does not stop on WRONG. |
| `info [--raw]` | Unlocked level, per-level todo files, cooldowns. |
| `login` / `login --http` | Browser login (Edge), or HTTP login using `.auth/credentials.env` (`CCC_USER=`, `CCC_PASS=`). |
| `games`, `use NAME`, `api GET\|POST <path> [--game]` | Utilities. `api` survives Git Bash path mangling. |

`--solver "pypy3 solve.py"` or `--solver "node solve.js"` runs any command (cwd = levelN). **PyPy:** `arena/.tools/pypy/pypy3.exe` (gitignored). Activate it with a first line `# ccc: pypy` in solve.py or `CCC_PY=pypy`. To reinstall: unzip the PyPy 3.11 win64 release from pypy.org into `arena/.tools/pypy/`.

## Layout
```
arena/.auth/        GITIGNORED: cookies.json, state.json (runs + game tokens), edge-profile/, credentials.env (optional)
arena/runs/<run>/   contest.json, game-info.json (level metadata), contestant-info.json
  level<N>/         files/ (unzipped: level-N.pdf, in_level-N_<id>.txt, out_level-N_0-example.txt)
                    statement.txt, map.json, solve.py, out/, submissions.jsonl, sandbox.html?, pages/?
```

## Rules learned the hard way
- **Never submit in parallel.** The game engine loses concurrent updates: 5 parallel CORRECT verdicts, only 2 recorded. `submit`/`go` are sequential and re-submit any file that was CORRECT but not recorded. Teammates: do not submit the same level at the same moment.
- Large outputs are slow to grade (~16 s/MB server side). The 1.2 MB file took 20 s. Give `go` a long tool timeout.
- An expired session (HTTP 401) prints `SESSION EXPIRED`. With `credentials.env` present, the CLI re-logs in automatically.
