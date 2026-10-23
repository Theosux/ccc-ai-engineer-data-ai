"""Level 4 auto-improvement loop: one process owns the tournament seat until the upload deadline.

Each round:
  1. gate every new model the driver saved in env4/ (*.onnx with a .pt next to it), newest first;
  2. self-play with the champion at 300 sims (deeper than the tournament's 100) -> data/a<k>.part*.npz;
  3. train the next net from the champion's weights on the newest datasets (GPU);
  4. gate: validator ACCEPTED, >= 55% over 200 games vs the champion, >= 90% vs GreedyAgent;
     a winner becomes champion and is uploaded (colony/upload4.py), never after UPLOAD_DEADLINE.
State and log: iustin2/auto/. The current champion is mirrored to env4/BEST.onnx + env4/BEST.json.
usage (cwd env4): nohup .venv/bin/python ../iustin2/autoloop.py CHAMPION.onnx > ../iustin2/auto/stdout.log 2>&1 &
"""
import glob, json, os, shutil, subprocess, sys, time
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path

ENV = Path.cwd()
AUTO = ENV.parent / "iustin2" / "auto"
COLONY = ENV.parents[1] / "colony"
PY = str(ENV / ".venv" / "bin" / "python")
UPLOAD_DEADLINE = os.environ.get("UPLOAD_DEADLINE", "19:20")      # local time, HH:MM
STOP_AT = os.environ.get("STOP_AT", "19:25")
GAMES = int(os.environ.get("GAMES", "1500"))
SIMS = os.environ.get("SIMS", "300")
GATE_GAMES = int(os.environ.get("GATE_GAMES", "200"))
GATE_WIN = float(os.environ.get("GATE_WIN", "0.55"))
sys.path.insert(0, str(ENV)); sys.path.insert(0, str(ENV / "play")); sys.path.insert(0, str(ENV.parent / "iustin2"))


def now():
    return datetime.now().strftime("%H:%M:%S")


def log(msg):
    line = f"{now()} {msg}"
    print(line, flush=True)
    with (AUTO / "log.txt").open("a") as f:
        f.write(line + "\n")


def past(hhmm):
    return datetime.now().strftime("%H:%M") >= hhmm


def load_state(champ):
    p = AUTO / "state.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"champion": champ, "history": [{"t": now(), "model": champ, "why": "start (seated)"}], "seen": {},
            "round": 0, "last_upload": 0}


def save_state(st):
    (AUTO / "state.json").write_text(json.dumps(st, indent=1))
    c = Path(st["champion"])
    shutil.copyfile(c, ENV / "BEST.onnx")
    (ENV / "BEST.json").write_text(json.dumps({"champion": st["champion"], "since": st["history"][-1]["t"],
                                                "history": st["history"][-8:]}, indent=1))


def arch(pt):
    import torch
    sd = torch.load(pt, map_location="cpu")
    return int(sd["stem.0.weight"].shape[0]), len({k.split(".")[1] for k in sd if k.startswith("body.")})


def validate(onnx_path):
    r = subprocess.run([PY, "tools/validate_submission.py", str(onnx_path)], capture_output=True, text=True, timeout=300)
    return "ACCEPTED" in r.stdout + r.stderr


def match(a, b, n):
    import match as M
    with Pool(10) as p:
        res = p.map(M.one, [(str(a), str(b), g, 100) for g in range(n)])
    return sum(r[0] for r in res) / n


def greedy(model, n=20):
    import probe
    with Pool(10) as p:
        res = p.map(probe.one, [(str(model), g, c) for g in range(n) for c in (True, False)])
    return sum(w for _, w in res) / len(res)


def upload(model, st):
    if past(UPLOAD_DEADLINE):
        log(f"NOT uploading {model}: past the upload deadline {UPLOAD_DEADLINE}")
        return
    wait = st["last_upload"] + 35 - time.time()
    if wait > 0:
        time.sleep(wait)
    r = subprocess.run(["python3", "upload4.py", str(model)], cwd=COLONY, capture_output=True, text=True, timeout=180)
    first = (r.stdout or r.stderr).strip().splitlines()[:1]
    log(f"UPLOAD {model}: {first[0][:200] if first else r.returncode}")
    if "upload 200" in r.stdout:
        st["last_upload"] = time.time()
        st["history"][-1]["uploaded"] = now()


def gate(cand, st, why):
    champ = st["champion"]
    if not validate(cand):
        log(f"gate {cand}: REJECTED by the validator"); return False
    w = match(cand, champ, GATE_GAMES)
    log(f"gate {cand} vs {champ}: {w:.3f} over {GATE_GAMES} ({why})")
    if w < GATE_WIN:
        return False
    g = greedy(cand)
    log(f"gate {cand} vs Greedy: {g:.3f}")
    if g < 0.9:
        return False
    st["champion"] = str(cand)
    st["history"].append({"t": now(), "model": str(cand), "why": f"{why}; {w:.3f} vs {champ}"})
    save_state(st)
    log(f"NEW CHAMPION {cand}")
    upload(cand, st)
    save_state(st)
    return True


def external(st):
    """Models the driver session saved since the last look (needs a .pt for the next training round)."""
    out = []
    for f in sorted(ENV.glob("*.onnx"), key=lambda p: p.stat().st_mtime, reverse=True):
        key, mt = f.name, f.stat().st_mtime
        if f.name == "BEST.onnx" or str(f) == st["champion"] or st["seen"].get(key) == mt:
            continue
        st["seen"][key] = mt
        if f.with_suffix(".pt").exists() and mt > st.get("t0", 0):
            out.append(f)
    return out


def datasets():
    """Newest self-play datasets (prefixes), newest first."""
    pre = {}
    for f in glob.glob(str(ENV / "data" / "*.part*.npz")):
        k = f.split(".part")[0]
        pre[k] = max(pre.get(k, 0), os.path.getmtime(f))
    return [k for k, _ in sorted(pre.items(), key=lambda t: -t[1])]


def driver_alive():
    r = subprocess.run(["pgrep", "-f", "claude --dangerously-skip-permissions --model opus"], capture_output=True, text=True)
    return bool(r.stdout.strip())


def main():
    if driver_alive() and os.environ.get("FORCE") != "1":
        sys.exit("the driver Claude session is still running and owns the seat; start this only if it died (FORCE=1 overrides)")
    AUTO.mkdir(parents=True, exist_ok=True)
    champ0 = str((ENV / sys.argv[1]).resolve()) if len(sys.argv) > 1 else str(ENV / "n2b.onnx")
    st = load_state(champ0)
    st.setdefault("t0", time.time())
    save_state(st)
    (AUTO / "pid").write_text(str(os.getpid()))
    log(f"start: champion {st['champion']}, upload deadline {UPLOAD_DEADLINE}, games {GAMES} at {SIMS} sims")
    for f in external(st):          # mark everything already on disk as seen; only newer driver models get gated
        pass
    save_state(st)
    while not past(STOP_AT):
        try:
            for f in external(st):
                gate(f, st, "driver model")
            st["round"] += 1
            k = st["round"]
            champ = Path(st["champion"]); prev = Path(st["history"][-2]["model"]) if len(st["history"]) > 1 else champ
            out = ENV / "data" / f"a{k}"
            newest = datasets()[:1]
            fresh = newest and os.path.getmtime(glob.glob(newest[0] + ".part*.npz")[0]) > champ.stat().st_mtime
            if fresh:
                log(f"round {k}: {Path(newest[0]).name} is newer than {champ.name}: train first")
            else:
                t = time.time()
                subprocess.run([PY, "selfplay.py", str(out), str(GAMES), str(champ), str(prev)], cwd=ENV, timeout=3600,
                               env={**os.environ, "SIMS": SIMS}, capture_output=True)
                log(f"round {k}: self-play {GAMES} games ({SIMS} sims) with {champ.name}+{prev.name} in {time.time() - t:.0f}s")
            if past(STOP_AT):
                break
            for f in external(st):
                gate(f, st, "driver model")
            champ = Path(st["champion"])
            ch, bl = arch(champ.with_suffix(".pt"))
            data = [d + ".part*.npz" for d in datasets()[:3]]
            cand = ENV / f"auto{k}.onnx"
            t = time.time()
            r = subprocess.run([PY, "net.py", str(cand), *data, "--init", str(champ.with_suffix(".pt")),
                                "--ch", str(ch), "--blocks", str(bl), "--epochs", "4", "--lr", "1e-3"],
                               cwd=ENV, timeout=3600, capture_output=True, text=True)
            tail = [l for l in r.stdout.splitlines() if l.startswith("ep ")][-1:]
            log(f"round {k}: trained {cand.name} ({ch}x{bl}) on {[Path(d).name for d in data]} in {time.time() - t:.0f}s {tail}")
            st["seen"][cand.name] = cand.stat().st_mtime if cand.exists() else 0
            if cand.exists():
                gate(cand, st, f"auto round {k}")
            save_state(st)
        except Exception as e:
            log(f"ERROR {type(e).__name__}: {e}")
            time.sleep(20)
    log(f"stop at {STOP_AT}: champion {st['champion']}")


if __name__ == "__main__":
    main()
