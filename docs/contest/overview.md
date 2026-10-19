# 42nd DATA/AI CCC: overview

Verified 2026-10-19 (see [verification-report](../research/verification-report.md)).

| Item | Fact | Source |
|---|---|---|
| Contest | **42nd DATA/AI CCC**, slug `42nd-data-ai-ccc-5873`, contest id 41, `contestType: AI` | https://codingcontest.org/api/editions/active |
| Date / start | **Fri 23 Oct 2026, 13:00 UTC = 16:00 Romania (EEST)**, same moment as CLASSIC | same |
| Duration | **240 min** | same |
| Team | up to **3** per team ("2–3 participants", solo allowed). Every member can submit; multiple laptops allowed | API `maxTeamSize: 3`; https://codingcontest.org/info/how-it-works |
| Size | ~1133 registrations / 1320 members on 2026-10-19 (2025 final leaderboard: 303 teams). Classic grew ~1.8× over the same period, so "3.7× bigger" is an upper bound | API; verification report |
| Game | secret until the start (`unknown-game` placeholder) | https://codingcontest.org/api/contests/42nd-data-ai-ccc-5873 |
| Hints | "we occasionally share hints before the contest": check email + Discord (https://discord.gg/eJKvPJW7au) on 21–23 Oct | how-it-works |
| Prizes | per venue (you compete with your local venue), plus the Hall of Fame | https://codeforces.com/blog/entry/147433 |

## Track history (5 editions held; 2026 is the 6th; no Data/AI track in 2024)
| Edition | Contest id | Game | Type | Teams finishing all / field | Winner time |
|---|---|---|---|---|---|
| 35th, Nov 2021 | 18 | Production Line | small images (classifier + regression) | 9 / 148 (3 levels max) | 92 min |
| 36th, Nov 2022 | 21 | Dancing Bees | sequence classification | 19 / 145 | 32 min |
| 37th, Mar 2023 | 24 | Spy Mission | tabular cleaning, PCA, regression, hidden passwords | 23 / 214 | 51 min |
| 38th, Oct 2023 | 27 | Smart Farming | computer vision (drone images) | **3** / 214 | 176 min |
| 41st, Nov 2025 | 38 | Migratory Birds (`ccc-2025.11-ai-birds`, on the practice list) | tabular, paths, panel forecast, puzzle | 12 / 303 | **85 min** (Mara&Cata, 2 people, CREIC Cluj) |
Source: `https://codingcontest.org/api/hall-of-fame/contests/{18,21,24,27,38}/leaderboard`. Level-by-level:
[past-games.md](../knowledge/past-games.md).

**What it takes to win:** clear every level, then be fast. In 2025 the 2nd and 3rd places took 100 and 118 min;
the median finisher ~180 min; 37 teams stalled on L5 (the forecasting level).

## Open questions
- Team composition and venue of our Data/AI registration: see `docs/team/roles.md`.
- Venue-specific rules arrive by email before the event and take precedence over the general Terms.
