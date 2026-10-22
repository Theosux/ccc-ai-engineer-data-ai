# Roles

| Role | Who | Notes |
|---|---|---|
| **Contest driver** | **iustin** | Runs `golive`, `go`, `submit` on contest day. Only this laptop submits. Decided by Iustin 2026-10-21. |
| Second opinion | **gurita** (replaced Dobrin on 2026-10-22) | Shadow mode (`autopilot.sh --shadow` / `duo.py shadow`): solves the driver's open level with a different approach, `run`/`probe` only, hands over via `duo.py publish` (own run folder on main) |
| Third member | TBD | The Data/AI registration allows 3. Teo competes in CLASSIC, so he is not available during the contest |

## Ownership (to avoid merge conflicts)
| Area | Owner | |
|---|---|---|
| `arena/ccc.py`, `arena/golive.py` | contest driver | the other person proposes changes via handoff or small commits |
| `arena/lib/` | both | add new functions; don't rename existing ones without a handoff message |
| `docs/knowledge/` | both | append sections, sign them (`*(dobrin)*`) |
| `docs/strategy/contest-day-runbook.md` | contest driver | |
| `arena/runs/<run>-<signature>/` | that person | never write into the other person's run folder |

## Registration
Verified by `golive.py --preflight` on Teo's account (2026-10-19):
- Data/AI team **"The Posers"**, **3/3 members**, venue **CREIC Cluj-Napoca** (on-site, same venue as Teo's Classic team).
- Teo is one of the 3 members but competes in CLASSIC at the same time, so in practice the team is Iustin + Gurita.
- **2026-10-22: Dobrin was removed from the platform team and replaced by Gurita** (signature `gurita`).
  *(Confirm the member list on codingcontest.org → My registrations; each person's own `--preflight` shows it.)*
