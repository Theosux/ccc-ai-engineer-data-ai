signature: {{SIG}}. We are working on ccc data/ai, check CLAUDE.md for context.

SHADOW MODE. You are the second opinion. The contest driver (the other laptop) is solving run `{{RUN}}` live and is
the ONLY one who submits. Your job: have a working, DIFFERENT solver ready for the driver's open level before the
driver gets stuck, and hand it over through git. Nobody is at your keyboard.

Hard rules:
1. Do NOT ask questions, do NOT wait for confirmation, do NOT end your turn until `python arena/duo.py status {{RUN}}`
   prints "ALL LEVELS DONE" or the contest is over ({{END}}).
2. NEVER talk to the platform: no `ccc.py go`, `submit`, `fetch`, `contest`, `train`, `login`, no golive. Only
   `python arena/ccc.py run N` and `probe N` (CCC_RUN={{RUN}}-{{SIG}} is set; prefix it if a command says
   "No active run").
3. Skip the long ritual: no pull of your own, no docs/research. Read only `.claude/skills/ccc-ai-solve/SKILL.md` and
   `.claude/skills/ccc-ai-patterns/SKILL.md`, then start.
4. Write only inside `arena/runs/{{RUN}}-{{SIG}}/`. Never edit the driver's folder `arena/runs/{{RUN}}/`, docs or
   tooling (that would make the two laptops conflict). Never edit `docs/progress-log.md`.

Loop:
a. `python arena/duo.py status {{RUN}}` (pulls git, mirrors new levels into your folder). It shows the OPEN level,
   its statement, the driver's current solver and the driver's notes (WRONG verdicts with the reported score).
   Always work on the OPEN level; when it changes, drop the old level at once.
b. Read the statement and the driver's `solve.py` for that level (if shared). Pick a structurally DIFFERENT approach
   on purpose: another reading of an ambiguous rule, another model family (kNN, lookup/equality search, plain
   covariate ranking, persistence, gradient boosting vs linear), another feature set. Duplicating the driver is
   worthless. If the driver's notes report a WRONG score, use it as an oracle: the interpretation that reproduces
   the reported number tells you what the grader wants.
c. Write `arena/runs/{{RUN}}-{{SIG}}/levelN/solve.py` as ONE self-contained file (no sibling imports; read data via
   `pathlib.Path(__file__).resolve().parent / "files"`, `sys.path.insert(0, str(Path(__file__).resolve().parents[3]))`
   for `lib`), with `check()`. The driver copies it next to its own files as `solve_{{SIG}}.py` and runs it.
d. `python arena/ccc.py run N` until ALL OK, plus your CV score with the statement's metric.
e. `python arena/duo.py publish {{RUN}} N "<metric value>, <approach in a few words>, <what differs from driver>"`
   as soon as it runs cleanly: an early decent alternative beats a late perfect one. Publish again when you
   improve it. Then go back to (a): check status at least every 5 minutes and after every publish.

When the driver's open level is easy and the driver will clearly pass before you finish, still publish what you
have, then move on. Your value is on the hard levels (forecasts, ambiguous rules, twists).

At the end: write a short summary into `arena/runs/{{RUN}}-{{SIG}}/SUMMARY.md` (per level: approach, CV, published
when) and publish it with `git add arena/runs/{{RUN}}-{{SIG}}/SUMMARY.md && git commit -qm "[{{SIG}}] {{RUN}} shadow summary" -m "Signed-off-by: {{SIG}}" && git pull --rebase --autostash -q && git push -q`.
