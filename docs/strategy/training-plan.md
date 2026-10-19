# Training plan: Mon 19 → Fri 23 Oct 2026

Goal: by Friday both of you can run the full loop without thinking, and the driver's laptop passes `--preflight`.

| Day | Who | Do | Done when |
|---|---|---|---|
| Mon 19 / Tue 20 | both | Accept the GitHub invite, `git clone`, `pip install -r requirements.txt`, `python arena/lib/tests/test_ml.py`, `python arena/ccc.py login`. Start Claude with the desktop prompt. **Decide the driver** and write it in `docs/team/roles.md`. Confirm the Data/AI registration (team, members ≤ 3, venue) in `roles.md`. | tests ALL OK, login OK, roles filled |
| Tue 20 | **driver** | **Cold timed rehearsal on Migratory Birds**: `python arena/ccc.py train ccc-2025.11-ai-birds --mode challenge --name birds-<signature>`, `fetch 1`, solve with the `ccc-ai-solve` loop. Do NOT open `SPOILER-birds/`. Log per-level times; compare with our 16 min and the 2025 winner's 85 min. | 6/6, times in progress-log |
| Tue 20 | **helper** | Same rehearsal on your own account (`birds-<signature>`), *or* if the driver already spoiled it for you: offline drill on Spy Mission L1–L7 (`docs/knowledge/datasets.md`). | 6/6 or Spy L1–7 |
| Wed 21 | both | Compare runs through `handoff.md`: what slowed you down? Fix the docs/lib (append to `data-ai-patterns.md`, add helpers to `lib/ml.py` + a test). Drill one more offline game each: Dancing Bees (sequences) and Smart Farming L1–L2 (images, tests the torch setup). | lessons pushed |
| Wed 21 | helper | Practise the **second-opinion handover** once end-to-end (branch `alt-N`, `go --solver`), on a Birds level. | handover works |
| Thu 22 | driver | `python arena/golive.py --preflight` with the real DATA/AI registration. Optional short dress rehearsal on a School game (`ccc.py games`). Pre-download weights. Charge laptops. | preflight all OK |
| Thu 22 | both | Read `contest-day-runbook.md` together; check email/Discord for hints. | |
| Fri 23 | both | Runbook. | win |

Open the progress log and the handoff board at the start of every session (the ritual does it).
