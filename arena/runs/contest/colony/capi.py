"""Client for the Colony: One game server (/colony-api). Server plays MAGENTA."""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import ccc, requests

NAME, RUN, _ = ccc.active_run()
EXTRA = {"Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty", "Accept": "application/json"}
BASE = "https://colony.codingcontest.org/colony-api"


def _post(path, body):
    for attempt in range(2):
        r = requests.post(BASE + path, headers={**ccc.game_headers(RUN), **EXTRA}, json=body, timeout=30)
        if r.status_code in (401, 403) and attempt == 0 and "platform" not in r.text:
            ccc.refresh_token(NAME, RUN)
            continue
        break
    if not r.ok:
        raise RuntimeError(f"{path}: HTTP {r.status_code} {r.text[:300]}")
    return r.json()


def new_game(scene):
    return _post("/games", {"scene": scene})


def move(gid, index):
    return _post(f"/games/{gid}/moves", {"index": index})
