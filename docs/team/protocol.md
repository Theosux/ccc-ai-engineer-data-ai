# Team protocol: how two Claudes work on one repo

Dobrin and Iustin each run their own Claude Code session on their own laptop. The sessions never talk directly.
**Git is the channel:** whatever one Claude pushes, the other Claude reads at its next session start (the
`ccc-ai-context` ritual). This file defines the conventions that make that work.

## 1. Signature
- Every session has one signature: `dobrin` or `iustin` (Teo's one-off bootstrap used `teo-bootstrap`).
- It comes from the first line of the starting prompt (`signature: dobrin`), else from `.claude/signature.local`
  (gitignored, one per laptop), else Claude asks. Claude writes it to `.claude/signature.local` once known.

## 2. Session start (done by the ritual)
1. `git pull --rebase`.
2. Read `docs/00-INDEX.md`, `docs/contest/`, `docs/strategy/`, the last 3 entries of `docs/progress-log.md`.
3. Read `docs/team/handoff.md`: every **OPEN** message addressed to **me** or to **both**.
4. `git log --oneline -10` to see what the other person pushed since last time.
5. Tell the user in ≤6 lines: days left, what changed since my last session (by whom), open messages for me.

## 3. During the session
- Commit small, logical changes: subject `[<signature>] <what>`, trailer `Signed-off-by: <signature>`.
  `git pull --rebase` then `git push` right after every commit, so the other side is never far behind.
- **Ownership** (to avoid merge conflicts) is in [roles.md](roles.md). Touching someone else's area is fine,
  but leave a handoff message saying what you changed.
- Shared knowledge files (`docs/knowledge/*.md`) are append-mostly: add a section, don't rewrite theirs.
- Run folders: each person trains in their **own** run name, e.g. `arena/runs/birds-dobrin/`,
  `arena/runs/birds-iustin/`. Never write into the other person's run folder.
- If a pull conflicts: keep both sides' content, commit the merge, and mention it in a handoff message.

## 4. The message board: `docs/team/handoff.md`
Append new messages at the **top** of the "Messages" section. Format:

```
### 2026-10-20 18:40 · dobrin → iustin · OPEN
**Context:** what I was doing (one line).
**Done / found:** facts, files, commits (short hashes).
**Ask / next:** what I need from you, or what you should pick up next.
```
- Addressees: `iustin`, `dobrin`, or `both`.
- The receiver answers **under** the message (`> 2026-10-21 09:10 · iustin: ...`) and changes `OPEN` to `DONE`
  when nothing is left to do. Never delete messages; DONE messages older than 2 days can move to the archive section.
- Write for a Claude that has no memory of your session: name files, commands, numbers, and the result.

## 5. Session end
1. Append a progress-log entry: `## YYYY-MM-DD: <signature>: <title>` with Done / Findings / Next.
2. Leave a handoff message if the other person must act on something.
3. Commit + pull --rebase + push. Check `git status` is clean.

## 6. Contest day
- Only the **contest driver's** laptop runs `golive`, `go` and `submit` (the server loses concurrent submits).
- The other person works on a second-opinion solver for the hardest open level, using only `run`/`probe`
  (offline), and hands it over on a branch: see `docs/strategy/contest-day-runbook.md`.
