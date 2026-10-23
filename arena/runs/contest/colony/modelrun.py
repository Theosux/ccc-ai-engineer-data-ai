"""Upload an ONNX model to /colony-api/model-run; on a win submit the key. usage: modelrun.py LEVEL FID LVLKEY model.onnx [tries]"""
import sys, time, json, pathlib, requests, capi, ccc
lvl, fid, lk, path = int(sys.argv[1]), sys.argv[2], sys.argv[3], pathlib.Path(sys.argv[4])
tries = int(sys.argv[5]) if len(sys.argv) > 5 else 1
for i in range(tries):
    r = requests.post(capi.BASE + "/model-run", headers={**ccc.game_headers(capi.RUN), **capi.EXTRA},
                      data={"level": lk}, files={"file": (path.name, path.read_bytes(), "model/onnx")}, timeout=120)
    try:
        d = r.json()
    except ValueError:
        d = {"text": r.text[:300]}
    short = {k: v for k, v in d.items() if k not in ("starting_observation", "actions", "steps")} if isinstance(d, dict) else d
    print(i, r.status_code, json.dumps(short)[:600], flush=True)
    if r.ok and d.get("won"):
        print(ccc.submit_one(capi.ccc.active_run(), lvl, fid, (lambda p: (p.write_text(d["submission_key"]), p)[1])(
            pathlib.Path(__file__).resolve().parent.parent / f"level{lvl}" / "key.txt")))
        break
    wait = 31
    if r.status_code == 429:
        try: wait = float(d.get("cooldownSec") or d.get("retry_after") or 31) + 1
        except Exception: pass
    if i + 1 < tries:
        time.sleep(wait)
