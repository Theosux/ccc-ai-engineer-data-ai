"""One competition-research tick (read-only). Prints a compact report and ACTION lines worth messaging.
usage: python3 research.py   (state in tlogs/research_state.json)"""
import glob, json, sys, time
from datetime import datetime
from pathlib import Path

T = Path(__file__).resolve().parent / "tlogs"
sys.path.insert(0, "/Users/iustinepanu/ccc/ccc-ai-engineer-data-ai/arena/runs/contest/colony")
DRIVER = Path.home() / ".claude/projects/-Users-iustinepanu-ccc-ccc-ai-engineer-data-ai/b14c4474-1bc1-48f4-a6e4-ffd3bb6867da.jsonl"
now = datetime.now()
hm = now.strftime("%H:%M")
st_p = T / "research_state.json"
st = json.loads(st_p.read_text()) if st_p.exists() else {}

# dashboard (one read-only GET)
import requests, capi, ccc
d = requests.get(capi.BASE + "/tournament-dashboard", headers={**ccc.game_headers(capi.RUN), **capi.EXTRA}, timeout=40).json()
(T / f"dash_{now.strftime('%H%M%S')}.json").write_text(json.dumps(d))
lb = d["leaderboard"]
me = next((r for r in lb if r["is_you"]), None)

# leaderboard log (30 s cadence)
L = [json.loads(l) for l in open(T / "lb.jsonl") if l.strip()]
L = [x for x in L if "rows" in x]
age = (now - datetime.strptime(now.strftime("%Y-%m-%d ") + L[-1]["t"], "%Y-%m-%d %H:%M:%S")).total_seconds() if L else 1e9
ten = [x for x in L if (now - datetime.strptime(now.strftime("%Y-%m-%d ") + x["t"], "%Y-%m-%d %H:%M:%S")).total_seconds() <= 600]
base = {r["name"]: r["elo"] for r in (ten[0]["rows"] if ten else [])}
uploads = [(x["t"], e) for x in L for e in x["events"] if x["t"] > st.get("last_tick", "00:00:00")]

print(f"== {now.strftime('%H:%M:%S')} logger last line {age:.0f}s ago, {len(L)} snapshots")
third = next((r for r in lb if r["rank"] == 3), None); first = lb[0]
if me:
    print(f"US: rank {me['rank']} elo {me['elo']} cur-model games {me['games']} (cyan {me['cyan_wins']}/{me['cyan_games_played']}, "
          f"magenta {me['magenta_wins']}/{me['magenta_games_played']}); gap to 1st {first['elo'] - me['elo']}, to 3rd {third['elo'] - me['elo'] if third else '?'}")
else:
    print("US: not in the top-10 list")
for r in lb[:10]:
    ch = r["elo"] - base[r["name"]] if r["name"] in base else None
    print(f"  {r['rank']:2d} {r['name'][:20]:20s} {r['elo']}  cur {r['games']:3d}  10min {('%+d' % ch) if ch is not None else 'new':>5} {'YOU' if r['is_you'] else ''}")
for s in d["ascension"]["series"]:
    p = s["points"][-6:]
    sw = [abs(p[i]["value"] - p[i - 1]["value"]) for i in range(1, len(p))]
    if sw:
        print(f"  swing {s['name'][:18]:18s} last {len(sw)} games avg {sum(sw) / len(sw):.0f}")
for t, e in uploads:
    print("  ", t, e)

# driver's latest model events (read-only transcript)
drv = []
try:
    import re
    txt = DRIVER.read_text()[-400000:]
    drv = re.findall(r"(n\d+\w*\.onnx vs [\w.]+: \d+/\d+)", txt)[-2:] + re.findall(r"upload4\.py \.\./level4/env4/[\w]+\.onnx", txt)[-1:]
except Exception:
    pass
print("DRIVER:", drv)

# actions
act = []
if me:
    if st.get("rank_msg") and abs(me["rank"] - st["rank_msg"]) >= 3:
        st["rank_msg"] = me["rank"]
        act.append(f"our rank moved to {me['rank']} (elo {me['elo']})")
    if st.get("elo_msg") is not None and abs(me["elo"] - st["elo_msg"]) >= 80:
        act.append(f"our elo moved {me['elo'] - st['elo_msg']:+d} since the last message ({me['elo']})")
    g3 = third["elo"] - me["elo"] if third else 0
    if me["rank"] > 3 and st.get("gap3") is not None and (st["gap3"] > 60) != (g3 > 60):
        act.append(f"gap to 3rd crossed 60: now {g3}")
    st["rank"], st["gap3"] = me["rank"], g3
    st.setdefault("rank_msg", me["rank"])
for t, e in uploads:
    name = e.split()[1]
    if any(r["name"].startswith(name) and r["rank"] <= 5 for r in lb):
        act.append(f"top-5 upload: {e} at {t}")
if "19:28" <= hm <= "19:36" and not st.get("decision_sent"):
    act.append("19:35 DECISION WINDOW: " + ("we are on the podium: no more uploads" if me and me["rank"] <= 3 else
               f"off podium, gap to 3rd {third['elo'] - me['elo'] if me and third else '?'}: variance gamble only if <= 60"))
    st["decision_sent"] = True
w = st.get("watch")
if w and me:
    dlt = me["elo"] - w["elo0"]
    print(f"WATCH {w['model']} since {w['t']}: {me['games']} games, elo {me['elo']} ({dlt:+d} from {w['elo0']})")
    wr = (me["cyan_wins"] + me["magenta_wins"]) / max(1, me["games"])
    print(f"WATCH win rate {wr:.2f} over {me['games']} games (revert only if <= 0.35 after 10+)")
    if me["games"] >= 10 and wr >= 0.70 and not w.get("hot"):
        act.append(f"{w['model']} is HOT: {wr:.0%} after {me['games']} games: KEEP it, upload only a clearly stronger model (>= 58%)")
        w["hot"] = True
    if me["games"] >= 10 and wr <= 0.35 and not w.get("flagged"):
        act.append(f"{w['model']} wins only {wr:.0%} after {me['games']} games: consider re-uploading the previous seat")
        w["flagged"] = True
    if me["games"] >= 10 and not w.get("verdict_sent") and not w.get("flagged"):
        act.append(f"{w['model']} verdict after {me['games']} games: {dlt:+d} (win-rate rule decides)")
        w["verdict_sent"] = True
summary_due = time.time() - st.get("last_summary", 0) >= 600
print("ACTIONS:", act if act else "none", "| summary due" if summary_due else "")
st["last_tick"] = now.strftime("%H:%M:%S")
st_p.write_text(json.dumps(st))
