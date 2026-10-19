# Verification report: Data/AI research (agents A and B)

Verified 2026-10-19 using public sources only: the codingcontest.org public API, the platform's JS chunks (all 136 downloaded and searched), Birds `game-info` and its client bundle, cloudflight.io and Codeforces pages, the GitHub tree API and raw files, PyPI JSON, and download.pytorch.org. I checked 34 claims. Section 1.1 of report B and section 5b of report A were not read.

## Summary
- **✅ Confirmed: 22**
- **⚠️ Partly true, overstated, or unverifiable: 7**
- **❌ Wrong: 5**

The core facts hold up exactly: the edition list, no Data/AI track in 2024, ranking by levels then time, every benchmark number, Birds `game-info`, the absence of any AI/LLM rule, the 413/429 upload handling, and every Python 3.14 wheel claim. The errors are in report B's view of the past games (images *have* appeared, the 2021 statements *are* public, and the spy game's edition is wrong) and in one threshold and one time in report A.

## Claims

| # | Claim | Report | Verdict | Evidence (URL) | Correction / note |
|---|---|---|---|---|---|
| 1 | AI contests: 18 `production-line` (2021-11-05), 21 `dancingbees` (2022-11-11), 24 `spy-mission` (2023-03-31), 27 `smart-farming-final` (2023-10-20), 38 `ccc-2025.11-ai-birds` (2025-11-14), 41 `unknown-game` (2026-10-23 13:00Z, 30 venues) | A | ✅ | https://codingcontest.org/api/contests?page=0&size=100 | 34 contests, of which 6 are of type AI. Field sizes 148/145/214/214/303 match. |
| 2 | "Six Data/AI editions so far" | A | ⚠️ | same | **Five editions have been held.** 2026 is the sixth. |
| 3 | No Data/AI track in 2024 (39th and 40th were Classic and School only) | A, B | ✅ | https://codingcontest.org/api/hall-of-fame/editions/12/summary, `/13/summary`; the 39th CCC blog post | The `/api/games` list has only one AI game (Birds). |
| 4 | Ranking: levels, then time. Every AI leaderboard has `score:null` and displays "N levels" | A | ✅ | `/api/hall-of-fame/contests/{18,21,24,27,38}/leaderboard?page=N&size=100` | All 5 leaderboards are sorted by (level desc, timeMs asc). |
| 5 | Teams at the max level / winner's time: 2025 12/303, 85 min; autumn 2023 3/214, 176; spring 2023 23/214, 51; 2022 19/145, 32; 2021 9/148, 92 | A | ✅ | same | Exact. |
| 6 | 2025: winner "Mara&Cata" (2-person team, CREIC Cluj-Napoca, 85.0 min); 2nd DOOReLU (Timișoara, 100); 3rd Acica_Computers (Iasi, 118) | A, B | ✅ | API leaderboard 38; https://www.cloudflight.io/en/blog/41st-cloudflight-coding-contest-brings-together-developers-worldwide/ | The blog confirms "two-person team from Romania … on-site in Cluj". |
| 7 | 2025 finishing times 85…242; the first team stuck at L5 had 138 min; 6 of the top 10 were at Romanian venues | A | ✅ | API leaderboard 38 | Cluj 4, Timișoara 1, Iasi 1. |
| 8 | Spring 2023: the last team at the max level finished at "247 min" | A | ❌ | API leaderboard 24 | The last times are 247, 247, **263, 311** min. |
| 9 | `timeMs` is measured from each team's own start (inferred from times over 240 min) | A | ⚠️ | API leaderboards 24, 38 | Unproven. Spring 2023 times reach 311 min, which fits accumulated wrong-answer penalty minutes at least as well. |
| 10 | The Hall of Fame tag for AI says "Optimization scoring"; the client supports optimization levels ranked "level, then score, then time" | A | ✅ | codingcontest.org `chunk-BYS8D1Vy.js`; Birds `assets/index-C-Oaae9A.js` | The tag is marketing only. No past AI leaderboard has ever had a score. |
| 11 | Birds `game-info`: 6 levels, all `optimization:false`, no `passScore`, files L1 6, L2–L3 4, L4 example + `1-main`, L5–L6 `1-main` only; base 0.36.0. It needs the Referer and Sec-Fetch-Site headers | A, B | ✅ | https://birds.codingcontest.org/game/game-info | Without the headers it returns "This game can only be accessed through the CCC platform". |
| 12 | Upload cap: HTTP 413 "File too large (max ${r} MB)". Cooldown: HTTP 429 "retry after ${t}s", per file; the values are unknown | A | ✅ | Birds client bundle | The cooldown is keyed by (level, fileId). The server also returns `cooldownSec` after *every* submit, not only on a 429. |
| 13 | There is no AI/LLM, GPU or external-data rule anywhere public | A | ✅ | All 136 codingcontest.org chunks plus the Birds bundle: no hits for LLM, ChatGPT, Copilot, pretrained, artificial, GPU, external data, cheat or plagiar | The 42nd event page has none either. |
| 14 | Rules: "not allowed to perform excessive downloads or stream content" (on-site); "Teams may use multiple laptops…"; "You may only set up one account"; the venue's specific terms prevail; age 16+ (14+ in Austria) | A | ✅ | how-it-works `chunk-YQUgUH9b.js`; Terms `chunk-BldHdrxM.js` | The precedence clause covers the "Specific Terms of Participation and Official Rules and Regulations of the venue". |
| 15 | Team size: "#classic and #data/ai: 2–3 participants", `maxTeamSize` 3, solo allowed | A, B | ✅ | how-it-works chunk; contests API | The Data & AI box says "Up to 3". Solos appear on every leaderboard. |
| 16 | Codeforces: "into training your own AI — pick the #data/ai track!"; "Each location has prizes…" | A | ✅ | https://codeforces.com/blog/entry/147433 | WebFetch gets a 403; curl with a user-agent header works. |
| 17 | 42nd page: "Let your model find the perfect algorithms", "15:00 #data/ai (CET)", topic secret, possible hints | A, B | ✅ | https://www.cloudflight.io/en/event/42-cloudflight-coding-contest/ | 23 Oct 2026 is still CEST (summer time ends 25 Oct), so 15:00 local is 13:00Z, which matches the API. |
| 18 | Discord for hints: https://discord.gg/wySfbT7t9e | A | ⚠️ | Discord invite API | The invite is valid (created by "CLF \| Mike"). The how-it-works page now links `discord.gg/eJKvPJW7au` instead. |
| 19 | "2026 is ~3.7× bigger": `registrationCount` 1133 and `memberCount` 1320 vs 303 | A | ⚠️ | contests API; https://codingcontest.org/api/editions/active | The arithmetic is right (3.74×). Classic grew only 1.8× (1360 → 2441). Pre-contest registrations include no-shows, so treat this as an upper bound. |
| 20 | "Expect sub-60-min winners" | A | ⚠️ | n/a | This is speculation. Use 32–92 min as the historical range. |
| 21 | The spy/USB game (sheilateozy) is "probably the 38th (20 Oct 2023), whose AI winner was Random Forest Rangers" | B | ❌ | contests API (contest 24 = `spy-mission`, 11 levels max; contest 27 has 8); https://www.cloudflight.io/en/blog/cloudflight-coding-contest-2023-new-partners-and-locations-continue-event-success/ | It is the **37th, 31 Mar 2023**. Random Forest Rangers won the 37th. The 38th was Smart Farming (drone images). |
| 22 | Spy Mission's last level is "RMSE … 0.5 or less" | A | ❌ | sheilateozy `competition-tasks/level_11.pdf` | **L11 is ≤ 0.45.** A's source repo (GabrielNedianu) has only 7 of the 11 PDFs. B's thresholds (L5 2.0, L6 1.5, L8 1.0, L11 0.45) are correct where spot-checked. |
| 23 | Dancing Bees: "edition number unverified"; macro-F1 65/90/98 on L6–8 | B | ⚠️ | contests API (contest 21 `dancingbees`); dslavulj README ("36th … 2022 AI") | The edition is **36th AI CCC, 11 Nov 2022**. The thresholds were not re-read: the PDFs are image-only. A and B agree on 65% and 98%. |
| 24 | "None uses images"; images were "never seen"; "past games never needed" pretrained weights; "every past solution ran on CPU" | B | ❌ | dslavulj/CCC-2021-AI `Level 1.pdf` ("28x84 pixels", "minimum overall accuracy of 93%"); eduardhogea/CCC_AI_2023 `level_01.pdf` ("200 x 200 pixels RGB images") | **2021 and autumn 2023 were image tasks.** Autumn 2023 had only 3 finishers. Images are a real possibility, not a low one. |
| 25 | "2021 … Data/AI statements: not found" | B | ❌ | github.com/dslavulj/CCC-2021-AI (Level 1–3 PDFs, CSV inputs and outputs) | Public. B's open question 4 (a hidden 2024 AI slug) is moot: no 2024 track existed. |
| 26 | All 19 cited repos exist, with their editions as listed | A, B | ✅ | GitHub tree API | **PDFs:** dslavulj-2021 (3), dslavulj-2022 (8), MattiaSangermano (8, plus data), GabrielNedianu (7 of 11), sheilateozy (all 11, no data), Antony-gitau (L1–5), eduardhogea (L1–6, inputs as .7z), goncalogalante-2025 (6 PDFs, plus inputs). **Data, no PDFs:** DeepSmeag ×2, diogoparaujo99 ×2, murillo-teixeira, MadaPetru, catalin21java, ebartha10, moejoe95. **Code only:** flaviusfetean. `goncalogalante/ML-CCC` is a generic template with an empty README; its "2022" label is unverifiable. diogoparaujo99's "26th/27th" names are the author's own labels; the content is 2022 Bees and 2023 Spy. |
| 27 | README claims: 22nd worldwide (2021), 18th (2022), 1st in Cluj (DeepSmeag), 17th global (eduardhogea), 66/214 (Antony-gitau, contest 4880 = 37th), top 10% (sheilateozy) | A, B | ✅ | raw README.md files | |
| 28 | Birds file names `level_N_a.in` … `level_N_sample.in/.out`; L5 file ≈ 58 MB, re-shipped in L6 | A, B | ✅ | goncalogalante and catalin21java trees | 59.6 MB in decimal units, re-shipped as `all_data_from_level_5.in`. |
| 29 | Py3.14 Windows wheels: sklearn 1.9.1, catboost 1.2.10, torch 2.14.1, torchvision 0.29.1, pyarrow 26.0.0, statsmodels 0.15.0, statsforecast 2.1.1, numba, hdbscan, pandas, numpy and scipy are cp314; lightgbm 4.7.0, xgboost 3.4.1 and prophet are `py3-none-win_amd64`; opencv and safetensors are abi3; the rest are pure Python | B | ✅ | https://pypi.org/pypi/<pkg>/json | Every version matches. torchvision `requires_python` is `!=3.14.1`. The local Python is 3.14.5, so that is fine. |
| 30 | CUDA cp314 wheels exist at download.pytorch.org cu126 and cu130; local torch is `2.12.0+cpu`; RTX 4060 Laptop 8 GB; 16 cores | B | ✅ | https://download.pytorch.org/whl/cu126/torch/, `/cu130/torch/`; local checks | torch 2.14.1+cu126/+cu130 and torchvision 0.29.1+cu126/+cu130 exist. `cuda.is_available()` is False locally. |
| 31 | "Wrong uploads may cost penalty minutes" (legacy +1 min) | B | ⚠️ | No "penalt" string in any platform chunk or the Birds client; main-repo `docs/contest/scoring-and-ranking.md` cites Wayback | The legacy rule was not re-fetched (the Wayback CDX timed out). The 2026 rule is unknown, so being cautious is right, but don't state it as fact. |
| 32 | Hint policy: "keep an eye on your inbox—we occasionally share hints" | A | ✅ | how-it-works chunk | |
| 33 | 2021: "for the first time there will be an AI challenge" | A, B | ✅ | https://www.cloudflight.io/en/blog/europes-biggest-coding-contest-will-take-place-on-november-5th-as-hybrid-event/ | |
| 34 | Track renamed from "AI CCC" to "Data/AI CCC" in 2025 | A | ✅ | contests API names ("38th AI CCC" → "41st Data/AI CCC 2025") | |

## Key corrections
- **Images have appeared twice.** 2021 used 28×84 label images (classification at 93% accuracy, then regression from formula images). Autumn 2023 used 200×200 RGB drone images (detection, counting and localisation). Do not write "never images" or "CPU-only every time". Keep the CUDA torch install and the pretrained-CNN fallback as a *real* contingency, and test `torch.cuda.is_available()` before Friday. That was also the hardest edition: only 3 teams finished.
- **The spy/USB game is the 37th CCC (31 Mar 2023)**, not the 38th. Random Forest Rangers won the 37th. The 38th was Smart Farming.
- **Spy Mission's final threshold is RMSE ≤ 0.45 (L11)**, not 0.5.
- **The 2021 statements are public** (dslavulj/CCC-2021-AI). **Dancing Bees is the 36th (2022)**; its edition is verified, not unknown.
- **Five Data/AI editions have been held**, not six. 2026 is the sixth.
- **Spring 2023 times run to 311 min**, not 247. So it is not established that `timeMs` counts from each team's own start: penalty minutes would explain it too.
- **The "3.7× bigger" figure compares pre-contest registrations with a final field.** State it as an upper bound. "Sub-60-min winners" is a guess, not a benchmark.
- **The wrong-submission penalty is not in any current public text.** Keep "treat as costly" as advice, not a fact.
- **The "Optimization scoring" tag is marketing.** No AI leaderboard has ever used a score.
- **Upload cooldowns** are set after every submit, per (level, file), not only after a 429.

## Still open
- The `maxSizeMb` value and the `cooldownSec` length. Both are only visible from a real submit.
- Whether wrong submissions cost time in 2026.
- Whether `timeMs` is per-team or includes penalties.
- Whether 2026 will use optimization or `passScore` levels. Check `game-info` at 13:00Z.
- The Dancing Bees L6–8 thresholds: the PDFs are image-only, so they were not re-read here.
- How many levels the 2021 game had: only 3 PDFs are public and the top level reached on the leaderboard is 3, so there may have been more levels.
- Smart Farming L7–8: their content is not public.
- Which Discord invite is current. Both work; the platform links eJKvPJW7au.
