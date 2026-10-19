# Workflow: how we solve a Data/AI game

## The loop per level (driver's Claude, skills `ccc-ai-solve` + `ccc-ai-patterns`)
1. `fetch N` (or the tail of `go N-1`) prints the statement, sizes, extra files, example.
2. **One exploration script:** traps (non-numeric values, unit clusters, NaN/outliers, labelled vs unlabelled per
   file) + a CV table with the PDF metric, or the exact-relation checks for puzzle levels.
3. **Write `solve.py`** (Write tool) with `check()` for the output format.
4. `go N`: runs, checks, submits sequentially, prints **the achieved score** and on PASS the next level.
5. WRONG → ladder in `docs/knowledge/ml-playbook.md` §5. Stuck > 15 min → second opinion (below).
6. After each pass: commit `arena/runs` in the background.

Measured on Migratory Birds (2026-10-19): 6/6 in 16 min with this loop; the 2025 winner needed 85 min.

## Roles on contest day (2 people)
| Role | Who | Does |
|---|---|---|
| **Driver** | `roles.md` | runs Claude with the loop above on the main laptop; the only one who runs `go`/`submit` |
| **Trap hunter + second opinion** | the other | reads each new PDF in parallel (story rules, traps, metric, output format) and tells the driver anything the Claude summary missed; when a level is stuck, solves it on their own laptop with a different method using `run`/`probe` only, and hands over via a branch |
A third member (if registered) reads ahead and checks outputs/visualisations.

## Second-opinion handover (no concurrent submits)
1. Driver: `git add arena/runs/contest/levelN && git commit -m "[<sig>] wip levelN" && git push`.
2. Helper: `git pull`, then in Claude: *"signature: <me>. Level N of run contest is stuck: our approach was X,
   score Y vs threshold Z. Solve it with a DIFFERENT method. Use only `CCC_RUN=contest python arena/ccc.py run N`
   and `probe N`, never `go` or `submit`."*
3. Helper puts the solver in `arena/runs/contest/levelN/solve_alt.py`, pushes branch `alt-N`.
4. Driver: `git fetch && git checkout origin/alt-N -- arena/runs/contest/levelN/solve_alt.py`, then
   `python arena/ccc.py go N --solver "python solve_alt.py"`.

## Between sessions (preparation days)
Each person works in their own run folder and pushes; the next Claude reads `docs/team/handoff.md`. See
[team protocol](../team/protocol.md).
