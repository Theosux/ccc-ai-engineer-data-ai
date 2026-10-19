# Roles

| Role | Who | Notes |
|---|---|---|
| **Contest driver** | **TBD** | Runs `golive`, `go`, `submit` on contest day. Only this laptop submits. Claude: while this says TBD, ask the user at session start and fill it in. |
| Second opinion | TBD (the other person) | Builds alternative solvers for the hardest open level with `run`/`probe` only, hands over via branch |
| Third member | TBD | The Data/AI registration allows 3. Teo competes in CLASSIC, so he is not available during the contest |

## Ownership (to avoid merge conflicts)
| Area | Owner | |
|---|---|---|
| `arena/ccc.py`, `arena/golive.py` | contest driver | the other person proposes changes via handoff or small commits |
| `arena/lib/` | both | add new functions; don't rename existing ones without a handoff message |
| `docs/knowledge/` | both | append sections, sign them (`*(dobrin)*`) |
| `docs/strategy/contest-day-runbook.md` | contest driver | |
| `arena/runs/<run>-<signature>/` | that person | never write into the other person's run folder |

## Registration (fill in)
- Data/AI team name on codingcontest.org: *(Teo's notes mention "The Posers"; confirm who is on it and the venue)*
- Venue: *(TBD)*
