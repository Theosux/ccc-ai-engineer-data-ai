# Index

## Team (`docs/team/`): read first
| File | Purpose |
|---|---|
| [protocol.md](team/protocol.md) | How the two Claudes communicate through git: signature, session start/end, commit format, handoff format |
| [roles.md](team/roles.md) | Contest driver, second opinion, file ownership, registration |
| [handoff.md](team/handoff.md) | Message board between the Claudes (OPEN / DONE) |
| [session-prompt.txt](team/session-prompt.txt) | The full starting prompt (fill `signature: ` on line 1, paste as the first message) |

## Contest facts (`docs/contest/`)
| File | Purpose |
|---|---|
| [overview.md](contest/overview.md) | 42nd DATA/AI CCC: date, team, size, track history 2021 to 2025 with winner times |
| [format-and-scoring.md](contest/format-and-scoring.md) | Levels, files, metrics/thresholds, score shown in the verdict, ranking, penalties |
| [rules-and-ai-policy.md](contest/rules-and-ai-policy.md) | Official rules; no AI/LLM restriction |
| [platform.md](contest/platform.md) | codingcontest.org mechanics + game API (shared with Classic), Data/AI specifics |

## Research (`docs/research/`)
| File | Purpose |
|---|---|
| [agent-A-contest-facts.md](research/agent-A-contest-facts.md) | Raw report: Data/AI editions 2021 to 2025, format, ranking, rules, leaderboards, participant repos (§5b Birds spoiler) |
| [agent-B-problems-strategy.md](research/agent-B-problems-strategy.md) | Raw report: past problems, typical progression, fast-baseline playbook, team workflow, environment (§1.1 Birds spoiler) |
| [verification-report.md](research/verification-report.md) | Cross-check of 34 key claims (22 ✅ / 7 ⚠️ / 5 ❌) + corrections |

## Strategy (`docs/strategy/`)
| File | Purpose |
|---|---|
| [workflow.md](strategy/workflow.md) | The loop per level, contest roles, second-opinion handover |
| [contest-day-runbook.md](strategy/contest-day-runbook.md) | **Contest day**: timeline (Romania time), golive, fallback ladder, rules of the road |
| [training-plan.md](strategy/training-plan.md) | What to do Mon 19 → Fri 23 Oct |
| [autopilot-prompt.md](strategy/autopilot-prompt.md) | Prompt that `arena/autopilot.sh` hands to the autonomous contest Claude (lessons from the rehearsals) |
| [../.cursor/rules/ccc.mdc](../.cursor/rules/ccc.mdc) | Cursor project rule (always on): CLAUDE.md and `.claude/skills/` apply to Cursor agents too |
| [shadow-prompt.md](strategy/shadow-prompt.md) | Prompt for the second laptop (`arena/duo.py shadow`): same open level, different approach, never submits; handover via `duo.py` (runbook, Duo section) |

## Problem-solving knowledge (`docs/knowledge/`)
| File | Purpose |
|---|---|
| [data-ai-patterns.md](knowledge/data-ai-patterns.md) | "Level says X → do Y → use Z", trap checklist, output rules, `lib/ml.py` API |
| [ml-playbook.md](knowledge/ml-playbook.md) | Step-by-step procedure per level under time pressure; ladder when not passing; score-in-verdict |
| [past-games.md](knowledge/past-games.md) | Level-by-level: Migratory Birds (our 6/6 run, SPOILER), Spy Mission, Dancing Bees, Smart Farming, Production Line |
| [datasets.md](knowledge/datasets.md) | Training material: Birds on the platform + offline repos of past games |
| [resources.md](knowledge/resources.md) | Installed / optional packages, pre-downloads, references |

## Custom skills (`.claude/skills/`)
| Skill | Purpose |
|---|---|
| `ccc-ai-context` | The ritual: signature, pull, reload context, read handoff messages |
| `ccc-ai-solve` | Fast loop per level: fetch → traps + CV → solve.py with `check()` → `go` → read score |
| `ccc-ai-patterns` | Technique cheat sheet + `lib/ml.py` skeleton and decision rules (with ccc-ai-solve) |

## Other
- [progress-log.md](progress-log.md): dated, signed session log
- `arena/`: CLI `ccc.py`, `golive.py`, `lib/` (incl. `ml.py`), runs. See [arena/README.md](../arena/README.md). Tests: `python arena/lib/tests/test_lib.py`, `python arena/lib/tests/test_ml.py`, `python arena/tests/test_golive.py`
- `arena/runs/SPOILER-birds/`: our Migratory Birds solvers (6/6), do not open before a cold rehearsal
