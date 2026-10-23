import requests, capi, ccc
H = {**ccc.game_headers(capi.RUN), **capi.EXTRA}
d = requests.get(capi.BASE + "/tournament-dashboard", headers=H, timeout=60).json()
print(d["generated_at"], d["stats"])
for r in d["leaderboard"]:
    if r["rank"] <= 10 or r["is_you"]:
        print(r["rank"], r["name"][:22].ljust(22), r["elo"], r["games"], round(r["win_rate"] or 0, 3), "YOU" if r["is_you"] else "")
