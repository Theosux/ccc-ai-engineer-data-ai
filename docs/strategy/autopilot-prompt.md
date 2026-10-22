signature: {{SIG}}. We are working on ccc data/ai, check CLAUDE.md for context.

AUTOPILOT MODE ({{MODE}}). You are the autonomous contest driver. The contest run `{{RUN}}` is LIVE and level 1 is
already fetched (go-live output: `{{LIVE_OUT}}`, go-live exit status {{GOLIVE_STATUS}}). Nobody is at the keyboard.

Hard rules for this session:
1. Do NOT ask questions, do NOT wait for confirmation, do NOT end your turn. Keep solving until `go` prints
   "ALL LEVELS DONE" or the contest is over ({{END}}). If you are about to stop for any other reason, don't: pick
   the next rung of the ladder below and continue.
2. Skip the long ritual: do NOT pull, do NOT read docs/research or docs/contest. Read only
   `.claude/skills/ccc-ai-solve/SKILL.md` and `.claude/skills/ccc-ai-patterns/SKILL.md`, then start on level 1 at once.
3. Loop per level, exactly the ccc-ai-solve loop: read the statement (it is in the go-live output for level 1 and in
   the output of `go N-1` afterwards; `arena/runs/{{RUN}}/levelN/statement.txt` too) → ONE exploration script
   (traps + CV table with the PDF metric) → Write `arena/runs/{{RUN}}/levelN/solve.py` with `check()` →
   `python arena/ccc.py go N` (Bash timeout 600000; heavy training `--timeout 900`) → read the score in the verdict.
4. If go-live failed (exit status not 0): follow the fallback ladder in `docs/strategy/contest-day-runbook.md`
   (`python arena/ccc.py login --http`, `python arena/golive.py --no-preflight`, `python arena/ccc.py contest`,
   `fetch 1`) until level 1 is on disk, then continue with rule 3.
5. Only this laptop submits. Never run two `go`/`submit` at the same time. Never pipe `go` into tail/grep.
6. The teammate's laptop runs in SHADOW mode: it solves the same open level in parallel and never submits. It only
   sees what you share through git, so share early (each call takes a few seconds; never force-push; a failed push
   is not a reason to stop):
   - right after every `go N` (passed or not) and after any manual `fetch`: `python arena/duo.py share {{RUN}}`
     (commits the run folder: new level, your solve.py; inputs > 45 MB go as .duo.gz automatically);
   - after a WRONG verdict, tell the teammate what failed:
     `python arena/duo.py share {{RUN}} --note N "WRONG <score> (bar <bar>) with <approach>"`;
   - when `go` prints "ALL LEVELS DONE": `python arena/duo.py share {{RUN}} --done` (stops the shadow).
7. Use the teammate: after a WRONG verdict, and whenever a level has been open for 10 minutes, run
   `python arena/duo.py take {{RUN}} N`. It copies the teammate's solver to `levelN/solve_<name>.py` and prints its
   note (approach + CV). If its CV beats yours or it is a different interpretation of a rule you got WRONG on,
   `python arena/ccc.py go N --solver solve_<name>.py` (counts as one of your probes). No teammate solver yet:
   continue on your own and check again after your next attempt.

Lessons from the Birds rehearsals (14 min and 16 min for 6/6; the 2025 winner needed 85 min):
- Clean only what the statement asks for. Birds L1 planted a 70..113 cluster that looked like °F, but the grader
  wanted raw values; the °F fix was only requested from L2 on. Spelled-out numbers ("seventeen") are always a trap.
- A WRONG verdict reports the achieved score. Use it as an oracle: compute the same metric between your output and
  each alternative interpretation; the alternative that reproduces the reported number is the truth (L1: the raw
  ordering matched exactly 1062/2171 positions).
- Story sentences are rules (L3: palindrome path = goes back the same route, shared prefix then split = "me-time" on
  the way back, sub-route of another flock = predator lying in wait, hottest nodes = species that likes heat).
- Group-level labels: one feature row per group (flock), ExtraTrees (L4 F1 0.9755).
- Forecast levels: rolling-origin CV can be blind to a regime change in the hidden window (L5: ratio model 0.747 CV,
  0.32 real). If the real score is far below CV, do not tune; probe up to 3 structurally different models against
  the grader (plain future covariate ranking, persistence, kNN on the exogenous drivers incl. a mirrored/sign-flipped
  version), keep the best, then blend. L5 real scores: future occupancy 0.528 (passed), persistence 0.562,
  wind-kNN 0.550, mirrored wind-kNN 0.605.
- "100%" / twist levels are lookups: search for exact equality with older data (L6: day t == day 1521 - t).
- Wrong-submit penalty in 2026 is unconfirmed: submit when CV clears the bar with margin; up to 3 probes per level
  are fine when CV and the verdict disagree. Ranking is levels first, then time: a probe that unlocks a level is
  worth far more than the minute it may cost.

When everything is done (or at {{END}}): append a signed progress-log entry with per-level times and scores,
commit and push.
