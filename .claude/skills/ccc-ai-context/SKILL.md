---
name: ccc-ai-context
description: Session-start ritual for the CCC DATA/AI repo - sets the signature (iustin/gurita), pulls teammates' pushes, reloads contest facts, strategy, progress and the handoff messages addressed to you. Use when the message contains "signature: <name>" or starts with "We are working on ccc data/ai", or whenever project context is missing (e.g. after /clear).
---

# CCC DATA/AI context ritual

Run these steps in order before answering anything else. Read in parallel where possible.

0. **Signature.** Take it from `signature: <name>` in the user's message. Otherwise read `.claude/signature.local`.
   Otherwise ask "iustin or gurita?". Write the name (one line) to `.claude/signature.local` (gitignored).
1. `git pull --rebase` (if it fails because of local changes: `git stash`, pull, `git stash pop`, report it).
2. Read `docs/00-INDEX.md` and `docs/team/protocol.md`.
3. Read every file in `docs/contest/` and `docs/strategy/`.
4. Read the last 3 entries of `docs/progress-log.md`.
5. Read `docs/team/handoff.md`: collect every **OPEN** message addressed to me or to `both`.
6. Read `docs/team/roles.md`. If the contest driver is TBD, ask the user who drives and record it.
7. List `.claude/skills/*/SKILL.md` (name + description) so you know the project skills.
8. `git log --oneline -10` and `git status --short`.

Do NOT read `docs/research/` unless a question needs the raw sources. Do NOT open `arena/runs/SPOILER-birds/`
unless the user asks for it.

## Then reply with a short "Context loaded" summary (max ~6 lines)
- Signature, and days left until the contest (Fri 23 Oct 2026, 13:00 UTC) from today's date.
- What changed since this person's last session: commits by the other teammate (`git log`), new docs.
- OPEN handoff messages for me, one line each.
- The planned next step (from the progress log / training plan), and any uncommitted changes.

Then continue with the user's request.

## Standing rules (also in CLAUDE.md)
- Commit subject `[<signature>] ...`, trailer `Signed-off-by: <signature>`; pull --rebase, then push after every commit.
- Anything the other Claude must know goes into `docs/team/handoff.md` and is pushed.
- End of session: signed progress-log entry, handoff message if needed, clean `git status`.
