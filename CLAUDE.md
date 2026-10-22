# CCC DATA/AI AI-Engineer: project instructions

## Ritual (MANDATORY)
If the user's message contains **`signature: <name>`** or begins with **"We are working on ccc data/ai"**,
invoke the `ccc-ai-context` skill (`.claude/skills/ccc-ai-context/SKILL.md`) BEFORE doing anything else and
follow it exactly. It pulls the latest work from teammates, reloads all project knowledge after a `/clear`,
and tells you which messages the other teammate's Claude left for you.

## Who works here
- **Team:** Iustin (signature `iustin`, contest driver) and Gurita (signature `gurita`, second opinion), who replaced
  Dobrin on 2026-10-22. Each person has their own Claude Code subscription.
  Teo (signature `teo-bootstrap`) bootstrapped the repo once and competes in CLASSIC, not here.
- **Goal:** win **42nd DATA/AI CCC**, Fri **23 Oct 2026, 13:00 UTC = 16:00 Romania**, 240 min, teams of up to 3.
- **Contest driver** (the one laptop that runs the tooling and submits): see `docs/team/roles.md`.
  While it says TBD, ask the user once per session and record the answer there.
- **Signature:** every session has exactly one signature. If you don't know it, read `.claude/signature.local`
  (gitignored, per laptop); if that is missing too, ask "iustin or gurita?" and write the answer there.

## Where things live
- `docs/00-INDEX.md`: map of every doc. Start here.
- `docs/team/`: **how the two Claudes communicate** (`protocol.md`), roles (`roles.md`), message board (`handoff.md`).
- `docs/contest/`: verified facts about the Data/AI contest (rules, format, scoring, platform).
- `docs/knowledge/`: ML patterns, playbook, past games (Migratory Birds), resources, datasets.
- `docs/strategy/`: workflow, contest-day runbook, training plan.
- `docs/research/`: raw research reports + verification report (sources).
- `docs/progress-log.md`: dated, signed session log. Append an entry at the end of every session.
- `arena/`: `ccc.py` CLI (login/train/fetch/run/probe/go/submit), `golive.py`, `lib/` (incl. `lib/ml.py`),
  `runs/<run>/levelN/`. See `arena/README.md`.
- `.claude/skills/`: project skills.

## Rules
1. **Pull first, push often.** `git pull --rebase` at session start and before every push. One commit per logical
   change, then `git push` immediately. Never force-push `main`.
2. **Commit format:** `[<signature>] <what changed>` as the subject, and the trailer `Signed-off-by: <signature>`.
   No `Co-Authored-By: Claude` or other Claude attribution.
3. **Talk to the other Claude through `docs/team/handoff.md`** (format in `docs/team/protocol.md`), never only in chat.
   Anything the other person must know (a finding, a broken tool, a question) goes there and is pushed.
4. New knowledge goes into the right `docs/` file and gets a line in `docs/00-INDEX.md`.
   New skills go in `.claude/skills/<name>/SKILL.md` and get listed in the index.
5. Facts in `docs/contest/` need a source URL; unverified items go under "Open questions".
6. Keep `README.md` and the GitHub repo description **empty** until the contest is over. The repo stays private.
7. Never commit secrets: `arena/.auth/` (cookies, tokens, `credentials.env`) is gitignored. Each person logs in
   with their own codingcontest.org account.
8. `arena/runs/SPOILER-birds/` holds finished Migratory Birds solvers. Don't open it before a cold timed run if you
   want Birds as an honest rehearsal.
