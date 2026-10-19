# Training datasets

## On the platform (real judge, instant verdicts)
| Game | Slug | Levels | Use |
|---|---|---|---|
| **Migratory Birds** (Data/AI 2025) | `ccc-2025.11-ai-birds` | 6 | **The** rehearsal. `python arena/ccc.py train ccc-2025.11-ai-birds --mode challenge --name birds-<signature>` for a timed cold run (240 min clock, levels unlock like the contest). Solved reference: `arena/runs/SPOILER-birds/` |
| School / Classic games | `ccc.py games` | 5–8 | Drills for the CLI loop and fast pandas only; they are algorithmic, not ML |

Each person must use their **own account**, and the training start reuses an existing RUNNING contest for the same
game, so a second run of the same game has no fresh clock and counts files as already passed (use
`submit N --only <ids>` to get real verdicts again).

## Offline (statements + data from participant repos; no hidden test labels, so judge yourself with CV)
| Game | Repo(s) | What you can practise |
|---|---|---|
| Spy Mission (spring 2023, 11 levels) | github.com/GabrielNedianu/AI-CONTEST-SPRING-2023, github.com/sheilateozy/cloudflight-ai-coding-contest, github.com/murillo-teixeira/spy | PCA, hidden-password plots, cleaning (NaN, outliers, Kelvin), RMSE ladder |
| Dancing Bees (2022, 8 levels) | github.com/MattiaSangermano/Cloudflight-Coding-Contest-AI-2022, github.com/dslavulj/CCC-2022-AI | sequence classification, imbalanced macro-F1 |
| Smart Farming (autumn 2023, 8 levels) | github.com/eduardhogea/CCC_AI_2023, github.com/flaviusfetean/CCC_AI | image classification / counting / localisation |
| Production Line (2021, 3 levels) | github.com/dslavulj/CCC-2021-AI | small images, classifier + regression |
| Migratory Birds | github.com/goncalogalante/CCContest-2025-AI-solution | spoiler: full solution |

How to drill offline: clone into `arena/.data/<game>/` (gitignored), read the PDF, solve with a held-out split of
the labelled training data as your judge, time yourself. Exact-answer levels can be checked against the repo's code.
