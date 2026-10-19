# Agent A: Data/AI CCC contest facts

Researched 2026-10-19 for the **42nd DATA/AI CCC** (Fri 23 Oct 2026, 13:00 UTC, 240 min).

**Tags**
- **[OFFICIAL]**: codingcontest.org public API, the platform/game JS bundles, or cloudflight.io pages.
- **[COMMUNITY]**: participant repos and posts.
- **[INFERRED]**: my own reading of the data.

> **SPOILER WARNING:** Section 5b has meta details about the *Migratory Birds* practice game (metrics, thresholds, data sizes). Skip it if you want to play Birds blind first. Everything else is spoiler-free.

## TL;DR
1. **Six Data/AI editions so far.** They ran in 2021, 2022, spring 2023, autumn 2023 and 2025. **None ran in 2024**: the 39th and 40th editions had only Classic and School. [OFFICIAL API]
2. **Topics change every year:**
   - 2021: image classification and regression
   - 2022: sequence classification
   - spring 2023: tabular data cleaning, PCA and regression, with "find the password" puzzles
   - autumn 2023: computer vision on drone images
   - 2025: tabular, time-series and structural-pattern data ("Migratory Birds")
3. **Format: levels, each with a hidden pass threshold.** Each level states a metric and a threshold, for example "accuracy ≥ 80%", "RMSE ≤ 0.75", "macro-F1 ≥ 65%/98%", "RMSE < 0.075". The grader returns pass or fail per file. There is no continuous score. [OFFICIAL bundle + COMMUNITY level PDFs]
4. **Ranking: levels completed, then time.** Every past AI leaderboard has `score: null`, and its display reads "N levels". The 2026 client can also run optimization levels, ranked "level, then score, then time". [OFFICIAL API/bundle]
5. **Birds `game-info`:** 6 levels, all `optimization:false`, no `passScore`. Levels 1–3 have 4–6 input files. Levels 4–6 have one "1-main" file each, and levels 5–6 have no example. [OFFICIAL]
6. **Winning benchmarks:**

   | Year | Finished all levels | Out of | Winner's time |
   |---|---|---|---|
   | 2025 | 12 teams | 303 | 85 min |
   | autumn 2023 | 3 | 214 | 176 min |
   | spring 2023 | 23 | 214 | 51 min |
   | 2022 | 19 | 145 | 32 min |
   | 2021 | 9 | 148 | 92 min |

   **To win you must clear every level.** Then speed decides. [OFFICIAL API]
7. **2026 is about 3.7× bigger.** The 2026 contest shows `registrationCount` 1133 and 1320 members, against 303 entries in 2025. Expect many more teams that clear everything. [OFFICIAL API, INFERRED]
8. **No AI/LLM rule exists for the Data/AI track** (or any track). The only rule texts are:
   - "not allowed to perform excessive downloads or stream content" (on-site)
   - multiple laptops are allowed
   - one account per person
   - venue rules take precedence

   Cloudflight markets the track as "training your own AI". [OFFICIAL]
9. **Uploads have a server-side size cap** (HTTP 413, `max ${maxSizeMb} MB`) and a per-file cooldown (HTTP 429). The cap value is unknown. [OFFICIAL bundle]
10. **No 2026 topic hint found.** The official line is "we occasionally share hints before the contest", via newsletter, social media and Discord. Check the inbox and Discord on 21–23 Oct.

## 1. History of the Data/AI track
Every edition's game slug comes from [OFFICIAL] `GET https://codingcontest.org/api/contests?page=0&size=100` (34 contests: 6 of type `AI`). Edition lists come from `GET /api/hall-of-fame/editions/{id}/summary`.

| # | Contest (id, slug) | Date (start UTC) | Game | Topic (source) | Field |
|---|---|---|---|---|---|
| 35th | "35th AI CCC 2021" (18, `35th-ai-ccc-2021-4096`) | 2021-11-05 14:00 | `production-line` | Factory "production line". Level 1 filters 28×84 label images by brightness. Level 2 is a binary classifier on label images, needing "minimum overall accuracy of 93%". Level 3 regresses an oven parameter from 28×196 formula images: "RMSE … must be lower than 0.075". [COMMUNITY: level PDFs in github.com/dslavulj/CCC-2021-AI] | 148 |
| 36th | "36th AI CCC 2022" (21) | 2022-11-11 14:00 | `dancingbees` | "Dancing Bees": 30-letter dance-move strings (a–i) map to 5 messages. Level 1 is a class histogram, then classifiers on simple, full and imbalanced test sets. Levels 6–8: "average F-Score across all classes of 65% … on the imbalanced test data", and 98% on level 8. [COMMUNITY: PDFs in github.com/dslavulj/CCC-2022-AI] | 145 |
| 37th | "37th AI CCC" (24) | 2023-03-31 13:00 | `spy-mission` | "Spy Mission", 11 levels. Run PCA on a CSV, read a password from a scatter plot, unlock a zip, clean NaNs and outliers, convert Kelvin units. Then "RMSE of 2.0 or less", decode a password hidden in the predictions (2500 = 50×50 image), and a last level of "RMSE … 0.5 or less". Answers were short strings or numbers, or prediction files. [COMMUNITY: PDFs in github.com/GabrielNedianu/AI-CONTEST-SPRING-2023] | 214 |
| 38th | "38th AI CCC" (27) | 2023-10-20 13:00 | `smart-farming-final` | "Smart Farming", computer vision on 200×200 RGB drone images. Level 1 detects animals ("accuracy of 80%", 100 training images and 1000 test images). Level 2 counts animals ("RMSE <= 0.75"). Level 3 counts under clouds using image pairs. Level 4 locates one animal ("Mean Squared Euclidean Distance <= 150"). Level 5 locates 5 animals ("Mean Chamfer Distance <= 20", hint: "Not all problems need to be solved with machine learning"). Level 6 counts animals outside the fence (accuracy ≥ 80%). There are 8 levels in total; levels 7–8 were not found. [COMMUNITY: PDFs in github.com/eduardhogea/CCC_AI_2023] | 214 |
| 41st | "41st Data/AI CCC 2025" (38, `41st-data-ai-ccc-2025-5774`) | 2025-11-14 14:00 | `ccc-2025.11-ai-birds` "Migratory Birds", 6 levels | "participants became ornithologists in the game 'Migratory Birds,' training their own AI models … to predict bird migration patterns. Each of the six levels presented increasing difficulty." [OFFICIAL: cloudflight.io blog] | 303 |
| 42nd | "42nd DATA/AI CCC" (41, `42nd-data-ai-ccc-5873`) | 2026-10-23 13:00 | `unknown-game` (placeholder) | Secret until start. 30 venues. | 1133 registrations / 1320 members |

**Notes**
- The track was renamed from "AI CCC" to "Data/AI CCC" in 2025. [OFFICIAL API]
- The 2021 launch press release says: "for the first time there will be an AI challenge, in which the contestants will have to solve a complex machine learning task." [OFFICIAL: cloudflight.io 2021 press release]
- **[INFERRED] The tasks are mostly *data science*, not deep learning.** Typical level types:
  - data cleaning traps (units, NaNs, outliers, numbers spelled out in words)
  - exploratory or "puzzle" levels with an exact answer
  - supervised learning with a threshold
  - a twist level where a non-ML insight beats modelling

  Only autumn 2023 needed vision (CNN-level) work, and that was also the edition where the fewest teams finished.

## 2. Format and scoring

**Birds `game-info`** [OFFICIAL]. Fetched from `https://birds.codingcontest.org/game/game-info`. It needs the headers `Referer: https://birds.codingcontest.org/` and `Sec-Fetch-Site: same-origin`; without them it returns "This game can only be accessed through the CCC platform". The response, condensed:
```json
{"id":"ccc-2025.11-ai-birds","edition":"41","name":"Migratory Birds","tags":["CCC41","ai","data","levels"],
 "levelsInfo":{"count":6,"levels":[
  {"optimization":false,"sandbox":false,"scoreDirection":"LOWER_IS_BETTER","inputFiles":["0-example","1-a","2-b","3-c","4-d","5-e"],"unscoredFiles":["0-example"]},
  {"optimization":false,"sandbox":false,"scoreDirection":"LOWER_IS_BETTER","inputFiles":["0-example","1-a","2-b","3-c"],"unscoredFiles":["0-example"]},
  {"optimization":false,"sandbox":false,"scoreDirection":"LOWER_IS_BETTER","inputFiles":["0-example","1-a","2-b","3-c"],"unscoredFiles":["0-example"]},
  {"optimization":false,"sandbox":false,"scoreDirection":"LOWER_IS_BETTER","inputFiles":["0-example","1-main"],"unscoredFiles":["0-example"]},
  {"optimization":false,"sandbox":false,"scoreDirection":"LOWER_IS_BETTER","inputFiles":["1-main"]},
  {"optimization":false,"sandbox":false,"scoreDirection":"LOWER_IS_BETTER","inputFiles":["1-main"]}]},
 "dev":false,"versions":{"base":{"version":"0.36.0","commit":"48090eb3"},"game":{"version":"1.0.0-rc18","commit":"34d86055"}}}
```
- **No level has `passScore`.** Every level is a binary per-file verdict. "Correct" means you met the metric threshold stated in the PDF, which the server checks. `scoreDirection` is a default with no effect when `optimization:false`. [INFERRED]
- Birds runs on the **same game-client base** (v0.36.0) as the Classic games. The upload flow, per-file verdicts and level unlocking all match the Classic docs (`docs/contest/platform.md` in the main repo). [OFFICIAL bundle]

**What the client's text says** [OFFICIAL, Birds client bundle `/assets/index-C-Oaae9A.js`]:
- "Any language, any tool. The problem statement defines the exact format."
- "Read the description carefully. Each level has its own download."
- For optimization levels: "The next level opens with ${…}. Ranking goes by level, then score, then time: the next level outranks any extra points here."
- The per-case display is "Case N: … — Score X". There is a "Total score" for optimization levels, and "Unscored / Optional" for example files.
- Errors: 413 gives "File too large (max ${r} MB) — not submitted."; 429 gives "rate limited: retry after ${t}s".

**Ranking** [OFFICIAL]. Every AI leaderboard (`/api/hall-of-fame/contests/{18,21,24,27,38}/leaderboard`) has `score: null` and `displayScore` "N levels". It is sorted by level descending, then `timeMs` ascending. That is identical to Classic.
- The Hall of Fame marketing tag for AI says "Machine learning and data science challenges · Optimization scoring" (platform chunk `chunk-BYS8D1Vy.js`).
- **So 2026 *may* include optimization levels.** If it does, the score breaks ties within a level. [INFERRED]
- 2025 leaderboard times of up to 242 min appear (rank 12), so `timeMs` is probably measured from an individual start, not a global clock. [INFERRED]

**Old versus new platform** [COMMUNITY + OFFICIAL]
- 2021–2023 ran on Catcoder. Some levels asked for single answers, such as "0.12, 3.10" or a password.
- 2025 ran on the new platform with output files per input file. Birds file names were `level_N_a.in`, … `level_N_sample.in` with a `level_N_sample.out` example, per the community repos.

## 3. Rules
- **AI/LLM policy: none, for any track.** A search of the full codingcontest.org bundle (38 chunks), the Terms of Participation chunk and the Birds client found no rule on AI, LLMs, ChatGPT, Copilot, pretrained models, external data or GPUs. [OFFICIAL, searched 2026-10-19]
- **The track's marketing says the opposite of a ban:**
  - "if you are into training your own AI — pick the #data/ai track!" (Codeforces blog by the organizers, title "41st Cloudflight Coding Contest — for all programming languages and AI") https://codeforces.com/blog/entry/147433 [OFFICIAL]
  - "Inspired by the Classic track, the Data & AI track focuses on analyzing datasets, solving data-driven challenges, and building intelligent solutions. Whether you're exploring machine learning models or experimenting with neural networks…" (how-it-works) [OFFICIAL]
  - "Data/AI: Let your model find the perfect algorithms." (cloudflight.io 42nd event page) [OFFICIAL]
- **Rules text (all tracks), from how-it-works** [OFFICIAL]:
  - "On-site participants are not allowed to perform excessive downloads or stream content during the contest."
  - "Teams may use multiple laptops, and every team member can submit solutions on behalf of the team."
  - **[INFERRED] Download large models or wheels *before* the contest if you plan to use them on-site.**
- **Team size:** "#classic and #data/ai: 2–3 participants per team". Solo is allowed. API `maxTeamSize` is 3. [OFFICIAL]
- **Terms** [OFFICIAL]: "You may only set up one account". Age 16+ (14+ in Austria). "special terms and conditions of participation for that Contest … shall prevail" over the general Terms (venue rules). Submissions grant Cloudflight usage rights.
- **Languages:** "All programming languages are allowed – it's up to the coders to choose." (cloudflight.io contest page) [OFFICIAL]
- **Compute/GPU, file size limit and internet:** no rule found. The upload size limit exists server-side, but its value is unknown. Internet is not restricted beyond the on-site downloads/streaming line.
- **Prizes are per venue:** "Each location has prizes and you are competing with the local community for it" (Codeforces blog). [OFFICIAL]

## 4. Winning benchmarks
All figures are from [OFFICIAL] `/api/hall-of-fame/contests/{id}/leaderboard`. The full leaderboards were paged with `?page=N&size=100`.

| Edition | Max level | Teams at max | Winner (team or solo, venue, time) | Time of the last team at max | Bottleneck |
|---|---|---|---|---|---|
| 2021 (18) | 3 | 9 / 148 | gahaalt (solo, ALAN Systems Rybnik), **92 min** | 232 min | 68 teams finished with 0 levels |
| 2022 (21) | 8 | 19 / 145 | "Welp, we tried" (team, AI Cuza Iasi), **32 min**. 2nd: dominikschmidt (solo) at 57 min | 240 min | 57 teams finished with 0 levels |
| spring 2023 (24) | 11 | 23 / 214 | "Random Forest Rangers" (team, JKU Linz), **51 min**. 2nd: 83 min | 247 min | 108 teams finished with 0 levels |
| autumn 2023 (27) | 8 | **3** / 214 | jdeller (solo, online), **176 min**. Then UW at 181 min and Macronic at 188 min | 188 min | Vision levels; 6 teams reached 7 |
| 2025 (38) | 6 | 12 / 303 | **"Mara&Cata"** (2-person team, CREIC Cluj-Napoca), **85 min**. 2nd: DOOReLU (Timișoara), 100 min. 3rd: Acica_Computers (Iasi), 118 min | 242 min | 37 teams stuck at L5; 126 finished with 0 levels |

- **2025 times of the teams that finished all 6 levels (min):** 85, 100, 118, 154, 173, 178, 181, 204, 209, 223, 239, 242. The median is about 180. The first team stuck at L5 had 138 min. [OFFICIAL]
- **Repeat names** [OFFICIAL]: VladCec (2021 #7, 2022 #3, spring 2023 #3), jdeller (spring 2023 #4, autumn 2023 #1) and VFF (autumn 2023 #7, 2025 #9).
- **Solo versus team:** solos are competitive, with 2–5 of each year's top 10 solo. [OFFICIAL]
- **Venue effects** [INFERRED from the API]:
  - Romanian on-site venues (Cluj CREIC, Timișoara, Iasi, Craiova) took 6 of the top 10 in 2025.
  - JKU Linz and Vienna City Hall dominate the top 30 overall.
  - "Online" teams win often (2021–2023).
  - There is no visible advantage either way. Prizes are per venue, so local rank matters for prizes.
- **The real target for 2026** [INFERRED]: clear every level, with the winning time historically 32–92 min on easier games. 2025's 85 min took first. With about 3.7× more registrations, we should expect sub-60-min winners if the game difficulty is similar to 2025.

## 5. Write-ups, repos and lessons
[COMMUNITY] GitHub repos with original task PDFs and data:

| Year | Repo | Notes |
|---|---|---|
| 2021 | `dslavulj/CCC-2021-AI` | Team ";DROP TABLE WINNERS", 22nd worldwide. Keras CNN `.h5` models. |
| 2021 | `moejoe95/ccc-21` | Prep: Kaggle titanic/house-prices pipelines, then CNNs per level |
| 2022 | `dslavulj/CCC-2022-AI` | Team "Apes Together Strong", 18th |
| 2022 | `DeepSmeag/CCC2022AI` | 1st in Cluj. Notes: KNN/MLP first, then a Keras **LSTM** reaching about 96% F-score. |
| 2022 | `diogoparaujo99/AI-26th-CCC` | |
| 2022 | `goncalogalante/ML-CCC` | A pre-built sklearn/XGBoost model-zoo template |
| spring 2023 | `murillo-teixeira/spy` | XGBoost + DNN + blending for the final RMSE level |
| spring 2023 | `GabrielNedianu/AI-CONTEST-SPRING-2023` | |
| spring 2023 | `Antony-gitau/Cloudflight_Coding_Contest` | 66th of 214 |
| spring 2023 | `DeepSmeag/CCC2023AI`, `diogoparaujo99/AI-27th-CCC`, `MadaPetru/CCC-AI-spy-mission` | |
| autumn 2023 | `eduardhogea/CCC_AI_2023` | 17th globally. Notebooks + PDFs. |
| autumn 2023 | `flaviusfetean/CCC_AI` | Image classifier + animal "pinpoint" scripts |
| 2025 | `goncalogalante/CCContest-2025-AI-solution` | All 6 levels, with PDFs and data |
| 2025 | `catalin21java/ccc_ai_2025` | Pure-stdlib Python |
| 2025 | `ebartha10/CCC-2025-Datascience-AI` | Reached L5 |

**Recurring lessons** [COMMUNITY, INFERRED]:
- **The first levels are "get to know the data" with an exact answer.** Examples: histogram counts, a PCA standard deviation, row counts after cleaning, a sort order. Speed on these is pure pandas fluency.
- **Data traps are deliberate.** Seen so far:
  - mixed units (Kelvin/Celsius/"?", Fahrenheit mixed into Celsius)
  - numbers written as words
  - NaNs and outliers
  - imbalanced test sets
  - the same table shipped again in later levels
- **Simple models usually pass.** Linear regression, random forest and XGBoost are typical. Deep nets were needed only for images (2021, autumn 2023) and helped on 2022 sequences.
- **Every edition has a "think, don't train" level:**
  - a password hidden in a scatter plot or in the predictions
  - "Not all problems need to be solved with machine learning" (2023)
  - Birds L6, solved without a model
- **The validation scheme matters on forecasting levels.** Random CV overestimated the score in Birds L5.
- **Data size:** Birds L5 was a 58 MB CSV with 1.9M rows. Use pandas or parquet, not pure Python loops.

### 5b. SPOILER: Migratory Birds meta details (skip if playing blind)
[COMMUNITY: goncalogalante README]

| Level | Metric | Pass threshold |
|---|---|---|
| L1 | exact | exact |
| L2 | RMSE | < 3 |
| L3 | exact | exact |
| L4 | macro-F1 | > 0.90 |
| L5 | daily top-50 accuracy over 30 days | > 0.50 |
| L6 | exact | 100% |

L5 was the leaderboard bottleneck (37 teams stopped there). [OFFICIAL count + COMMUNITY]

## 6. Hints about 2026
- **Topic: none found.** The API game is `unknown-game` ("Placeholder for contests with no recorded game"). [OFFICIAL]
- "The actual topic of each game remains secret until the event." / "we might share a few hints and teasers in our newsletter and via our social media channels." (cloudflight.io 42nd event page) [OFFICIAL]
- How-it-works: "keep an eye on your inbox—we occasionally share hints before the contest." Join Discord (https://discord.gg/wySfbT7t9e) for "hints and updates". [OFFICIAL]
- The cloudflight.io event page lists the start as "15:00 #data/ai (CET)". On 23 Oct, Vienna is on summer time (CEST), so 15:00 there is 13:00 UTC, which matches the API. [OFFICIAL]
- **[INFERRED] Prepare for any of these modalities:**
  - tabular regression/classification
  - time-series forecasting
  - sequences
  - small images (CNN)
  - exact-answer EDA levels

## What I could NOT find
- An official per-track AI/LLM rule. None exists anywhere public.
- The upload size cap value and the cooldown length.
- GPU or compute rules.
- Topics of levels 7–8 for 2021 and autumn 2023 (2021 had only 3 levels reached by anyone).
- Any 2026 teaser. LinkedIn and Discord are not readable without a login.
- Reddit, Medium or dev.to write-ups specific to the AI track. Searches returned none.

## Open questions
1. Will 2026 use optimization levels (`passScore` + score tiebreak)? Check `game-info` the moment the game opens.
2. What is the upload `maxSizeMb`? It matters if a level needs a large prediction file.
3. Will the venue email add rules on AI tools or internet?
4. Is `timeMs` per-team (counted from the team's own start)? The 2025 entries above 240 min suggest so.

## Sources
- https://codingcontest.org/api/editions/active
- https://codingcontest.org/api/contests?page=0&size=100
- https://codingcontest.org/api/contests/41st-data-ai-ccc-2025-5774 and `/api/contests/{35th-ai-ccc-2021-4096, 36th-ai-ccc-2022-4637, 37th-ai-ccc-4880, 38th-ai-ccc-5272, 42nd-data-ai-ccc-5873}`
- https://codingcontest.org/api/hall-of-fame/contests/{18,21,24,27,38,37}/leaderboard?page=N&size=100
- https://codingcontest.org/api/hall-of-fame/editions/{9..13,latest}/summary
- https://codingcontest.org/api/games
- https://birds.codingcontest.org/game/game-info (needs the Referer header) and the client bundle https://birds.codingcontest.org/assets/index-C-Oaae9A.js
- https://codingcontest.org/info/how-it-works (chunk-YQUgUH9b.js), the Terms (chunk-BldHdrxM.js) and the Hall of Fame (chunk-BYS8D1Vy.js)
- https://www.cloudflight.io/en/blog/41st-cloudflight-coding-contest-brings-together-developers-worldwide/
- https://engineering.cloudflight.io/en/event/42-cloudflight-coding-contest/
- https://www.cloudflight.io/en/the-cloudflight-coding-contest/
- https://www.cloudflight.io/en/blog/europes-biggest-coding-contest-will-take-place-on-november-5th-as-hybrid-event/
- https://www.cloudflight.io/en/blog/ccc-2022-keeps-growing/
- https://www.cloudflight.io/en/blog/cloudflight-coding-contest-2023-new-partners-and-locations-continue-event-success/
- https://www.cloudflight.io/en/blog/39th-cloudflight-coding-contest-the-latest-technology-meets-young-coders (no AI track in 2024)
- https://codeforces.com/blog/entry/147433
- GitHub repos:
  - github.com/dslavulj/CCC-2021-AI
  - github.com/dslavulj/CCC-2022-AI
  - github.com/moejoe95/ccc-21
  - github.com/DeepSmeag/CCC2022AI
  - github.com/DeepSmeag/CCC2023AI
  - github.com/diogoparaujo99/AI-26th-CCC
  - github.com/diogoparaujo99/AI-27th-CCC
  - github.com/goncalogalante/ML-CCC
  - github.com/GabrielNedianu/AI-CONTEST-SPRING-2023
  - github.com/murillo-teixeira/spy
  - github.com/Antony-gitau/Cloudflight_Coding_Contest
  - github.com/MadaPetru/CCC-AI-spy-mission
  - github.com/eduardhogea/CCC_AI_2023
  - github.com/flaviusfetean/CCC_AI
  - github.com/goncalogalante/CCContest-2025-AI-solution
  - github.com/catalin21java/ccc_ai_2025
  - github.com/ebartha10/CCC-2025-Datascience-AI
