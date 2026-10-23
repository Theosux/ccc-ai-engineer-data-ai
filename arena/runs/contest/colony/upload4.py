"""Upload a model to the L4 tournament seat; print dashboard. usage: upload4.py model.onnx | upload4.py --dash"""
import sys, json, pathlib, requests, capi, ccc
H = lambda: {**ccc.game_headers(capi.RUN), **capi.EXTRA}
if sys.argv[1] != "--dash":
    p = pathlib.Path(sys.argv[1])
    import time
    for _ in range(4):
        r = requests.post(capi.BASE + "/model-upload", headers=H(), files={"file": (p.name, p.read_bytes(), "model/onnx")}, timeout=120)
        if r.status_code != 429:
            break
        time.sleep(12)
    print("upload", r.status_code, r.text[:600])
for ep in ("tournament-dashboard",):
    r = requests.get(capi.BASE + "/" + ep, headers=H(), timeout=60)
    print(ep, r.status_code, r.text[:2500])
