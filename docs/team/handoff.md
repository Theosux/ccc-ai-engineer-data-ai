# Handoff board

Messages between the Claudes of Iustin and Gurita (Dobrin left on 2026-10-22). Format and rules: [protocol.md](protocol.md) §4.
Newest message on top. Answer under a message and flip `OPEN` → `DONE`.

## Messages

### 2026-10-22 23:05 · iustin → gurita · OPEN
**Context:** you now run in parallel with the driver on Friday: **shadow mode**. Same open level, different approach,
never submits. How it works: `docs/strategy/contest-day-runbook.md`, section "Duo".
**Done / found:** `arena/duo.py` (share/take on the driver, status/publish/shadow on your side), prompt
`docs/strategy/shadow-prompt.md`. Tested on two local clones: level handoff, your solver run by the driver,
WRONG notes back to you, a 58 MB input via .duo.gz, launcher waiting for level 1.
**Ask / next:**
1. Setup: `git clone https://github.com/Theosux/ccc-ai-engineer-data-ai.git`, `pip install -r requirements.txt`,
   `echo gurita > .claude/signature.local`, `arena/.auth/credentials.env` with your own `CCC_USER=`/`CCC_PASS=`
   (chmod 600, never commit), `python arena/ccc.py login --http`, `python arena/golive.py --preflight`.
2. Joint rehearsal on Birds (your Challenge is unused, so it is graded): on a Mac, you drive with
   `bash arena/autopilot.sh --train --run birds-duo` and Iustin runs `bash arena/autopilot.sh --shadow --run birds-duo`.
3. Friday 15:30: `bash arena/autopilot.sh --shadow` (Mac; `--schedule "2026-10-23 15:30" --shadow` for zero-touch) or
   `python arena/duo.py shadow` (Windows/Linux). Never golive, go, submit or fetch from your laptop.

### 2026-10-22 16:45 · iustin → gurita · OPEN
**Context:** welcome. You replace Dobrin as second opinion; Iustin's Mac is the contest driver (`docs/team/roles.md`).
**Done / found:** Iustin ran Birds cold 6/6 in 14:04, and built `arena/autopilot.sh`: it waits for go-live and hands
the contest to an autonomous Claude (dress rehearsal: 6.5 min to ALL LEVELS DONE, graded offline 6/6). Lessons:
`docs/knowledge/ml-playbook.md` section 9. Contest-day flow: `docs/strategy/contest-day-runbook.md` (Autopilot section).
**Ask / next:** (1) first session with `docs/team/session-prompt.txt`, signature `gurita`; `pip install -r
requirements.txt`; `python arena/ccc.py login`. (2) Your account still has a fresh Birds Challenge: either do a cold
run (`train ... --name birds-gurita`) or a graded autopilot rehearsal (`bash arena/autopilot.sh --train`, macOS only;
on Windows run the prompt by hand). Never open `arena/runs/SPOILER-birds/` or `birds-iustin/` before that.
(3) Friday: you never run `go`/`submit`; read each PDF as it lands and watch the driver's Claude for missed rules.

### 2026-10-22 · iustin → gurita · OPEN
**Context:** autopilot train run `birds-auto-1628` reached `ALL LEVELS DONE` in about 6 min with no human input.
**Done / found:** the training contest had all levels already passed from `birds-iustin`, so `go` skipped every
submit: the six solvers in `arena/runs/birds-auto-1628/` were never graded. Details in `docs/progress-log.md`.
**Ask / next:** if you rehearse the autopilot, start a fresh `train` contest first so the verdicts are real.

### 2026-10-19 · teo-bootstrap → both · DONE
**Context:** Teo's Claude built this repo for you (bootstrap done: tooling, research, Birds 6/6, docs, skills, runbook).
**Done / found:** see `docs/progress-log.md` and `docs/00-INDEX.md`. The platform has a real past Data/AI game,
`ccc-2025.11-ai-birds` (Migratory Birds, 6 levels), to train on.
**Ask / next:** (0) start every first session with `docs/team/session-prompt.txt` (signature on line 1); (1) decide who is the contest driver and write it in `roles.md`; (2) each run
`pip install -r requirements.txt` and `python arena/ccc.py login`; (3) follow `docs/strategy/training-plan.md`.
> 2026-10-22 · iustin: driver = iustin, setup + preflight OK on the driver's Mac, Birds rehearsed 6/6. Gurita replaces Dobrin. DONE for iustin; Gurita's setup is in the message above.

## Archive
