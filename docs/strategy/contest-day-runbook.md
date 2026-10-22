# Contest-day runbook: 42nd DATA/AI CCC, Fri 23 Oct 2026

**Start 13:00 UTC = 16:00 Romania (EEST). 240 min → ends 20:00 Romania.**
Driver and venue: `docs/team/roles.md`. Teo is at the CLASSIC contest at the same time and cannot help.
This runbook is adapted from Teo's Classic runbook, whose tooling (`golive.py`, `ccc.py`) was rehearsed live.

## Autopilot (default since 2026-10-22, driver iustin, macOS)
One command does the whole start: `bash arena/autopilot.sh` (from the repo root, any time before 15:45).
It keeps the Mac awake (`caffeinate`), pulls, logs in over HTTP, runs `golive.py --browser` until the contest is live
and level 1 is fetched, then launches `claude --model opus --dangerously-skip-permissions` with
`docs/strategy/autopilot-prompt.md`: an autonomous driver that solves every level with the `ccc-ai-solve` loop,
never asks, commits after each level, and follows the fallback ladder on its own if go-live fails.
- Zero-touch start: `bash arena/autopilot.sh --schedule 15:30` (one-shot launchd job; Terminal opens by itself at
  15:30 and starts the line above). Undo: `--unschedule`. Lid open, charger in, Wi-Fi joined.
- The Claude window stays interactive: watch it; type only if it is clearly stuck or the platform needs a click.
- Rehearsal: `bash arena/autopilot.sh --train [--headless]` = fresh Birds Challenge run through the same hand-off.

## Timeline (Romania time)
| When | Who | Action |
|---|---|---|
| Thu evening | both | `git pull`. `pip install -r requirements.txt`. Driver: `python arena/ccc.py login` (or create `arena/.auth/credentials.env` with `CCC_USER=` / `CCC_PASS=` for `login --http`), then `python arena/golive.py --preflight`: login, **DATA/AI registration**, contest, clock, token must be OK. Pre-download optional weights (`docs/knowledge/resources.md`). Phone hotspot ready. |
| Fri 11:00 | driver (optional) | `python arena/golive.py --observe school --minutes 15` in the background records the real #school go-live (08:00 UTC) as a dress rehearsal of the detectors. |
| 15:00 (T-60) | both | At the venue: Wi-Fi, `git pull`, `python arena/golive.py --preflight`. |
| 15:30 (T-30) | driver | **Autopilot:** started by `--schedule 15:30` or by hand (`bash arena/autopilot.sh`); the rows below are the manual fallback. Open Claude Code in the repo. Model **Opus** (`/model opus`; optional `/fast` **now**, before the first message, if usage credits are on). First message: `signature: <driver>` + *"We are working on ccc data/ai check claude.md for context"*, then *"contest is about to start"*. |
| 15:30 | helper | Same on the second laptop with their own signature; skills loaded; ready to read PDFs. |
| **15:45 (T-15)** | driver's Claude | Start `python arena/golive.py --browser` with `run_in_background`. It watches the contest (API poll, SSE, registration, level-1 probe, Edge window), registers run `contest` and prints the level 1 statement when live. |
| 16:00 (T0) | auto | golive fires (beep, toast, `LIVE.txt`, level 1 printed). Claude solves immediately. Check `arena/runs/contest/game-info.json` for `optimization` / `passScore`. |
| During | driver | `ccc-ai-solve` loop. Commit after each level in the background. |
| Stuck > 15 min | both | `docs/knowledge/ml-playbook.md` §5, then the second-opinion handover (`workflow.md`). |
| 19:30 (T-30) | both | Endgame: submit anything that passes `check()` and clears the local CV threshold. Ranking is level, then time. |
| 20:00 | | End. `git add -A && git commit && git push`, signed progress-log entry. |

## Fallback ladder
| Problem | Do this |
|---|---|
| golive login failures | `python arena/ccc.py login --http` (credentials.env), else `python arena/ccc.py login` (Edge window). Rerun golive. |
| LIVE but "not ready yet" > 2 min | Rerun with `--browser`. Open the contest page in a normal browser: check-in / terms / start button? Click it, rerun golive. |
| Game token refused (403) | Same as above; make sure `--preflight` shows the DATA/AI registration. |
| Level zip download fails | Download the zip in the browser, then `python arena/ccc.py fetch N --zip "<path>.zip"`. |
| Submit API fails | `python arena/ccc.py run N`, drag and drop `arena/runs/contest/levelN/out/*` onto the platform's Solutions panel. |
| Wi-Fi dies | Phone hotspot. |
| Driver laptop dies | Helper laptop: `git pull`, `python arena/ccc.py login`, `python arena/ccc.py contest`, `fetch N`. Solvers are in git if committed after each level. |

## Rules of the road
- **One submitter.** The server loses concurrent submits (5 parallel CORRECT → 2 recorded, Classic test).
- **Traps before models**, every level. **Read story pages fully**: the rules are in the prose.
- **The verdict shows the score**: use it, don't guess. But don't spam: a penalty for wrong submits is unconfirmed.
- **Write/Edit only** for solvers; never pipe `go` into `tail`/`grep` and then chain a submit.
- **No side work** while a level is unsolved.
- Heavy training: `go N --timeout 900`; `probe N` before slow full runs.
