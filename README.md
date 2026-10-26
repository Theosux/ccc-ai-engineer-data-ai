# Cloudflight Coding Contest Data/AI 2026

| Ranking | Place |
|---|---|
| Local (CREIC Cluj) | **2nd** |
| Country (Romania) | **5th** |
| World | **11th** |

This repo is our setup for the 42nd Cloudflight Coding Contest (CCC) Data/AI, held on 23 October 2026. We competed as team **The Posers**.

The idea was the same as in our Classic repo: let Claude Code handle the routine work so we could spend our time on ideas. Here we went one step further. On contest day an AI session ran the contest almost on its own, while we decided on strategy and gave it more computing power.

## The contest

The game was **Colony: One**, a two-player board game (CYAN against MAGENTA). There were no input files. Everything happened through the game server.

- **Level 1:** find a password and a safe square for your Kernel piece.
- **Level 2:** write a player that beats the server's bot.
- **Level 3:** upload a model (an ONNX file) that wins a match.
- **Level 4:** a live tournament against every other team's model, running until the end of the contest. Your score was your rating (Glicko-2).

Levels 1 to 3 were done in 13.5 minutes, all on the first submit. Then the real work was level 4.

## Level 4 strategy

**Understanding the rules first.** We rebuilt the game engine locally from the statement and the game's own JavaScript, so we could play thousands of games offline. We also noticed things the rules did not say out loud. For example, CYAN won only 43.6% of all tournament games, so the side you play matters.

**One model, trained over and over.** We used a small version of the AlphaZero approach:
1. The current best model plays against itself, with tree search (MCTS) choosing the moves.
2. A neural network (a small convolutional net in PyTorch) learns from those games.
3. The new model plays a test match against the current one, and it takes the seat only if it clearly wins.

We started from a simple hand-made linear model and went through more than ten versions (v1, n1, n2, ..., n11c). Each one beat the previous one, usually by 66% to 95%.

**Many models at the same time.** Once the loop worked, we ran it on more machines: a second laptop, cloud GPUs and a few extra Claude sessions. Some produced self-play games, some trained, and some only ran test matches. We tried a lot of variations: bigger networks, networks trained from scratch, ensembles of several models, and "hybrid" models with hand-written tactical rules added on top. The biggest single jump came from a bigger network (96 channels). Ensembles with older models never beat the newest single model, so we stopped using them.

**Learning from our losses.** We replayed the real tournament games we lost and looked for patterns. One script counted how often our model left its Kernel open to capture in the last turns of a game. Another checked whether a safe move had existed in those positions. A third tracked the leaderboard and the rating of each model we uploaded.

**Playing the rules of the tournament.** Each team had one seat, and every upload reset the 8-game count and made the rating swing more. So we only uploaded a model after it clearly won a test match (60% or more over 100 games) against the one already in the seat. We also stopped uploading about 20 minutes before the end, because a late model would not play enough games to settle. One more lesson: the upload checker tests models with extreme input values, so we clamped inputs and outputs after one model was rejected.

## What the AI workflow achieved

- **Autopilot.** A script waited for the contest to start, logged in and then handed the whole contest to an autonomous Claude Opus session. In a dress rehearsal on a past game (Migratory Birds, 6 levels) it went from start to "all levels done" in about 6.5 minutes with no human input.
- **Duo mode.** A second laptop ran a "shadow" AI on the same open level, on purpose with a different approach (it used Cursor with Grok). It never submitted. If the main solver got a wrong answer, the driver could try the shadow's solver right away.
- **Speed checks.** We measured settings instead of guessing. For example, LightGBM was much faster on one thread than on all cores for small data, which cut model selection from about 17 seconds to 1.8 seconds.

## How we worked as a team

- **Teo** built the repo first: the platform tools (taken from our Classic setup), the ML helpers, the research and a full solve of Migratory Birds in 16 minutes. On contest day Teo was in the Classic contest, and still sent strategy notes during the level 4 endgame.
- **Iustin** was the driver: the only laptop that submitted or uploaded, running the autopilot and the training loop.
- **Gurita** was the second opinion, running the shadow solver.

Each of us had our own Claude, and they talked through git. Every session had a signature (`[iustin] ...`), and messages for the other Claude went into `docs/team/handoff.md`. Each session started by pulling and reading the messages addressed to it. Ownership of files was written down in `docs/team/roles.md`, so we rarely had merge conflicts.

## How we worked in iterations

1. **Bootstrap (3 iterations):** port the tools, run research agents with a separate fact-checking agent, solve one past game by hand, and write the playbook and skills.
2. **Cold rehearsal:** Iustin solved Migratory Birds from zero in 14 minutes. The 2025 winner took 85.
3. **Autopilot and duo mode**, each tested end to end before the contest.
4. **Lessons into docs:** after each run, what went wrong went into `docs/knowledge/ml-playbook.md`, so the next session started smarter.

## The technical side

- **`arena/`**: the contest client (`ccc.py`), go-live watcher (`golive.py`), `autopilot.sh`, `duo.py` for the two-laptop setup, and `lib/ml.py` (data cleaning, quick model comparison with cross-validation, LightGBM settings).
- **`arena/runs/contest/colony/`**: the game API client, a local copy of the rules, a search player and the upload scripts.
- **`arena/runs/contest/level4/`**: self-play, network training, test matches, ONNX export, cloud jobs, ensembles, hybrid models and the loss analysis scripts.
- **Stack:** Python, PyTorch, ONNX, MCTS, scikit-learn, LightGBM, cloud GPUs, Claude Code skills in `.claude/skills/`.

## Repo layout

```
docs/            contest facts, strategy, team protocol, knowledge, progress log
arena/           ccc.py, golive.py, autopilot.sh, duo.py, lib/
arena/runs/      training runs and the contest run
.claude/         custom skills
```
