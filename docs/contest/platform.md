# Platform (codingcontest.org, the rebuilt platform)

Copied from Teo's CLASSIC repo (verified hands-on 2026-10-09 to 2026-10-19 on Classic and School games). The
platform, API and game client are shared by all tracks, so this applies to DATA/AI too. Data/AI-specific findings
go in the section at the end.

## Key facts
- **Catcoder is retired.** `catcoder.codingcontest.org` and `register.codingcontest.org` now redirect with a 302 to codingcontest.org. Community tools built for Catcoder (Lingepumpe/ccc_solver_template, lcian/catcoder-cli, catcoder-vscode) are **probably broken**.
- **New platform:** an Angular app. The contest game page is `/contests/:contestName/game`. **Each game is its own app inside an iframe** (e.g. `spaceship.codingcontest.org`).
- **Auth:** the platform calls `POST /api/game-token`, then posts `{type:'ccc:auth-token', token, contestSlug, contestStartMs, contestDurationMinutes}` to the iframe. The game sends `Authorization: <token>` and `X-CCC-SLUG: <slug>`. Opened directly, a game URL returns 403: "This game can only be accessed through the CCC platform".
- **The 2026 contest is the first live contest on this platform.** It went live around 2026-09-15.

## Game API endpoints (from the game client, 2026)
| Purpose | Endpoint |
|---|---|
| Contestant state | `GET /api/contestant/contestant-info` |
| Level zip (statement + inputs) | `GET /api/contestant/level/{N}/files` → `level-N.zip` |
| Single input | `GET /api/contestant/level/{N}/input/{fileId}` |
| Visualizer/sandbox | `GET /api/contestant/level/{N}/sandbox` |
| Submit one output | `POST /api/contestant/submit-{level}-{fileId}` (multipart field `solution`) |
| Live scores (SSE) | `/api/contests/scores/stream?contestSlug=…` |

## Public API (no login needed)
| Purpose | Endpoint |
|---|---|
| Current edition | https://codingcontest.org/api/editions/active |
| Our contest | https://codingcontest.org/api/contests/42nd-classic-ccc-5872 (the game shows as `unknown-game` until the start) |
| Practice games list | https://codingcontest.org/api/games |
| One practice game | https://codingcontest.org/api/training/{slug} (e.g. `ccc-2025.11-classic-spaceship`) |
| Hall of Fame (2025 Classic) | https://codingcontest.org/api/hall-of-fame/contests/37/leaderboard |

## Practice: https://codingcontest.org/challenges (login + Participant role)
- **Challenge mode:** timed at 240 minutes; levels unlock one after another, exactly like the real contest.
- **Exploration mode:** no timer and every level is open. Use it to download statements and try the visualizer.
- **Classic games available (4):**

  | Game | Levels |
  |---|---|
  | Spaceship (2025.11) | 8 |
  | Room Planner (2024.10) | 7 |
  | Lawn Mower (2024.04) | 7 |
  | Rock Paper Scissors (2023.03) | 7 |

  (Islands is not available.)
- **Offline archives:**
  - https://github.com/gergely-elias/ccc (PDFs and inputs for Room Planner, Lawn Mower and RPS)
  - https://github.com/aarroyoc/catcoder
  - https://github.com/angua/CCC41 (a Spaceship solution in C#)

## Confirmed by hands-on test (2026-10-09, Lawn Mower in Exploration mode)
- **Auth:** cookies `SESSION` + `XSRF-TOKEN` (POSTs need the `X-XSRF-TOKEN` header).
  - `POST /api/game-token {contestSlug}` → `{token}`.
  - The game API lives on the **game's origin** (e.g. `https://lawn-mower.codingcontest.org/api/contestant/...`) with headers `Authorization: <token>` and `X-CCC-SLUG: <contestSlug>`.
  - **Scripted access works.** Our CLI is `arena/ccc.py`.
- **Training start:** `POST /api/training/{gameSlug}/start?mode=exploration|challenge` → contest `training-<slug>-<id>`. Then `GET /api/contests/{name}` gives the `gameBaseUrl`.
- **Zip contents:**
  - Inputs: `in_level-N_<fileId>.txt` with fileIds `0-example`, `1-small`, `2-small`, `3-medium`, `4-medium`, `5-large`.
  - Expected example output: `out_level-N_0-example.txt`.
  - Statement: `level-N.pdf`, about 1 MB, styled slides.
- **`contestant-info`** → `score.state.levelN.passedFiles` (scored ids) and `passedAt`; `score.gameScore {level, timeMs}`.
- **Submit response:** `{"evaluation":{"isCorrect":bool,"cases":[{isCorrect, caseState: CORRECT|WRONG_SOLUTION|NOT_GIVEN, startLineNumber, endLineNumberExcl, caseMessage}]}}`, i.e. **per-case feedback with line ranges**.
- **Cooldown:** about 5 s per file after a submit (HTTP 429 `{"cooldownSec":N}` plus a `Retry-After` header).
- **Speed:** one level took about 30 s from fetch to all files correct for the simple Lawn Mower L1–L3.

## Implications for automation
- **Downloading and submitting are scripted and tested** via `arena/ccc.py`. Teo cleared the rules with the organizers (2026-10-09).
- **The safest fallback** is a local pipeline that unzips the level, solves it, writes the outputs with the right file names, and leaves the drag-and-drop upload to a person.

## Open questions
- Whether the zip naming and statement format will be the same for the new 2026 game. If not, the tool falls back to the platform's "last number picks the case" rule.

## Confirmed by hands-on test (2026-10-09, Room Planner `speedtest` run; see docs/strategy/workflow-speed.md)
Sources are the game client bundle `https://desks.codingcontest.org/assets/index-*.js`, the platform bundle `https://codingcontest.org/main-*.js` + chunks, and live API responses.
- **Concurrent submits lose updates.** 5 parallel `submit-2-*` requests all returned CORRECT, but only 2 were recorded in `passedFiles`. Sequential submits accumulate correctly. Submit one file at a time, and teammates must not submit at the same moment.
- **The submit response includes the full `score`** (`gameScore.level`, `state.levelN.passedFiles/passedAt`) plus `cooldownSec`. No `contestant-info` call is needed after a submit.
- **Grading time scales with size:** ≤150 KB takes ~1–1.6 s; a 1.2 MB output took ~20 s (server side).
- **Public game metadata:** `GET <gameBaseUrl>/game/game-info` (no auth) → `levelsInfo.count` and per level `{optimization, sandbox, scoreDirection, passScore?, inputFiles, unscoredFiles}`.
- **Level files:** `GET /api/contestant/level/N/files` → `{"url": "https://files.codingcontest.org/game-files/<game>/level-N.zip?<SAS>"}` (a short-lived pre-signed blob). The client falls back to `...?raw=true` if the blob fetch fails. `/input/{fileId}` also returns `{url}`.
- **Unlocking in the client:** `maxAccessibleLevel = score.gameScore.level`; a level is accessible if untimed (`durationMinutes == 0`) or `N <= maxAccessibleLevel`.
- **`contestant-info`** also returns `cooldowns: [{level, fileId, remainingMs}]` and `state.levelN.submissions[{fileId, submittedAt, result, submittedBy}]`.
- **Case feedback fields:** `caseState`, `caseMessage`, `startLineNumber`, `endLineNumberExcl`, `errorLineNumber`, `optimizationScore`.
- **Other game endpoints:** `/api/game-engine/participant/state`, `/api/game-engine/leaderboard?scope=WORLD`, and the dev-only `/api/dev/*` (not used).
- **Platform endpoints:** `GET /api/contests/my-registrations`; SSE `/api/contests/status/stream` (event `contest-status` `{contestId, contestSlug, status}`); SSE `/api/contests/scores/stream?contestSlug=` (event `score-update`).
- **Contest page logic:** the game iframe loads only if the status is `RUNNING` or `STATS_FROZEN`, the user is registered (or it is a training run), and `gameBaseUrl` is https. The `serverNowMs` in `/api/contests/{name}` is used for clock offset.
- **Login:** `POST /api/auth/login {username, password}` with the `X-XSRF-TOKEN` header from the `XSRF-TOKEN` cookie (Angular default). There is no captcha on login (only on register and password reset). Bad credentials → 401 `{"error":"Invalid credentials"}`. `GET /api/auth/current-user` → 401 when logged out.
- **Session:** `SESSION` and `XSRF-TOKEN` are session cookies (no expiry). The game token is an opaque 36-char UUID with an unknown TTL.
- **Teo's registration (Classic, for reference):** 42nd CLASSIC CCC, team "Krateo", venue CREIC Cluj-Napoca. The Data/AI registration is in `docs/team/roles.md`.

## Data/AI specifics (public API, 2026-10-19)
- **Contest:** `42nd DATA/AI CCC`, slug `42nd-data-ai-ccc-5873`, contest id 41, `contestType: "AI"`, start `2026-10-23T13:00:00Z`, 240 min, `maxTeamSize: 3`, ~1320 members registered on 2026-10-19. Source: https://codingcontest.org/api/editions/active
- **Practice game:** `ccc-2025.11-ai-birds` "Migratory Birds", 6 levels, tags `CCC41, ai, data, levels`, `scoreType: LEVEL`, base URL `https://birds.codingcontest.org/`. Source: https://codingcontest.org/api/games
- It is the only Data/AI game in the practice list, so it is the main rehearsal material.
