"""Log the leaderboard every 30 s (read-only GET) to tlogs/lb.jsonl; detect uploads (current-model games reset)."""
import sys, json, time
sys.path.insert(0, "/Users/iustinepanu/ccc/ccc-ai-engineer-data-ai/arena/runs/contest/colony")
import requests, capi, ccc
from datetime import datetime
H = {**ccc.game_headers(capi.RUN), **capi.EXTRA}
out = "/Users/iustinepanu/ccc/ccc-ai-engineer-data-ai/arena/runs/contest/level4/iustin2/tlogs/lb.jsonl"
last = {}
while datetime.now().strftime("%H:%M") < "20:02":
    try:
        d = requests.get(capi.BASE + "/tournament-dashboard", headers=H, timeout=25).json()
        rows = [{k: r[k] for k in ("rank", "name", "elo", "games", "is_you")} for r in d["leaderboard"]]
        ev = []
        for r in rows:
            if r["name"] in last and r["games"] < last[r["name"]]:
                ev.append(f'UPLOAD {r["name"]} (games {last[r["name"]]} -> {r["games"]}, elo {r["elo"]})')
            last[r["name"]] = r["games"]
        with open(out, "a") as f:
            f.write(json.dumps({"t": datetime.now().strftime("%H:%M:%S"), "rows": rows, "events": ev}) + "\n")
    except Exception as e:
        with open(out, "a") as f:
            f.write(json.dumps({"t": datetime.now().strftime("%H:%M:%S"), "error": str(e)[:200]}) + "\n")
    time.sleep(30)
