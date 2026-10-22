"""Two-laptop contest mode: the driver submits, the second opinion solves the same open level in parallel and hands
alternative solvers back through git (main branch, each person in their own run folder, so rebases never conflict).

  driver  (iustin):  python arena/duo.py share RUN                 # push the run folder (new levels, solvers)
                     python arena/duo.py share RUN --note 5 "WRONG 0.32 with ratio model"   # tell the teammate
                     python arena/duo.py take RUN 5                # pull teammate solvers -> level5/solve_<sig>.py
                     python arena/duo.py share RUN --done          # all levels passed: the shadow stops
  shadow  (gurita):  python arena/duo.py shadow [--run RUN]        # wait for level 1, then start the agent
                       [--agent auto|claude|cursor|paste] [--model SLUG]   # Cursor CLI: `agent --force`
                     python arena/duo.py status RUN                # pull, mirror new levels, show the open level
                     python arena/duo.py publish RUN 5 "CV 0.61, mirrored wind kNN"
The shadow never talks to the platform: it reads the driver's levels from git and solves with `ccc.py run`
(active run <RUN>-<sig>). Inputs over 45 MB travel as `<file>.duo.gz` (GitHub rejects files > 50 MB).
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ARENA = Path(__file__).resolve().parent
REPO = ARENA.parent
RUNS = ARENA / "runs"
BIG = 45 * 1024 * 1024
SKIP = {"out", "models", "pages", "__pycache__"}
NOTES = ("DRIVER_NOTES.md", "NOTE.md")


def sig():
    p = REPO / ".claude" / "signature.local"
    s = p.read_text(encoding="utf-8").strip() if p.exists() else ""
    if not s:
        sys.exit(f"ERROR: no signature: write your name into {p} (iustin or gurita)")
    return s


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()[:400]}")
    return r


def lock():
    """One git writer at a time (the driver's background shares can overlap)."""
    p = REPO / ".git" / "duo.lock"
    for _ in range(120):
        try:
            os.close(os.open(p, os.O_CREAT | os.O_EXCL))
            return p
        except FileExistsError:
            if time.time() - p.stat().st_mtime > 120:
                p.unlink(missing_ok=True)
            time.sleep(0.5)
    sys.exit("ERROR: .git/duo.lock held for 60 s")


def pull():
    r = git("pull", "--rebase", "--autostash", "-q", check=False)
    if r.returncode:
        git("rebase", "--abort", check=False)
        print(f"WARN: git pull failed: {(r.stderr or r.stdout).strip()[:300]}")
        return False
    return True


def commit_push(paths, msg):
    """Commit only `paths`, then pull --rebase and push (retried: the teammate may push in between)."""
    s = sig()
    l = lock()
    try:
        git("add", "--", *paths)
        if not git("diff", "--cached", "--quiet", "--", *paths, check=False).returncode:
            print("nothing new to commit")
        else:
            git("commit", "-q", "-m", f"[{s}] {msg}", "-m", f"Signed-off-by: {s}", "--", *paths)
        for i in range(4):
            pull()
            r = git("push", "-q", check=False)
            if not r.returncode:
                print(f"pushed: {msg}")
                return True
            time.sleep(2 + 3 * i)
        print(f"WARN: push failed ({r.stderr.strip()[:300]}); committed locally, the next share retries")
        return False
    finally:
        l.unlink(missing_ok=True)


def exclude(path):
    p = REPO / ".git" / "info" / "exclude"
    line = "/" + path.relative_to(REPO).as_posix()
    have = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    if line not in have:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def levels(d):
    return sorted(int(p.name[5:]) for p in d.glob("level*") if p.name[5:].isdigit() and (p / "map.json").exists())


def rel(p):
    return p.relative_to(REPO).as_posix()


# ---------------------------------------------------------------- driver
def cmd_share(a):
    d = RUNS / a.run
    if not d.is_dir():
        sys.exit(f"ERROR: no run folder {rel(d)}")
    for f in d.rglob("*"):
        if f.is_file() and f.stat().st_size > BIG and not f.name.endswith(".duo.gz"):
            gz = f.with_name(f.name + ".duo.gz")
            if not gz.exists() or gz.stat().st_mtime < f.stat().st_mtime:
                with f.open("rb") as src, gzip.open(gz, "wb", compresslevel=6) as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
            exclude(f)
            if gz.stat().st_size > BIG:
                exclude(gz)
                print(f"WARN: {rel(f)} is {gz.stat().st_size >> 20} MB even gzipped: the teammate cannot get it via git")
    if a.note:
        n, text = a.note
        with (d / f"level{n}" / "DRIVER_NOTES.md").open("a", encoding="utf-8") as f:
            f.write(f"- {time.strftime('%H:%M:%S')} {text}\n")
    if a.done:
        (d / "ALL_DONE").write_text(time.strftime("%H:%M:%S") + "\n", encoding="utf-8")
    lv = levels(d)
    what = "all levels done" if a.done else f"note on level {a.note[0]}" if a.note else f"levels {lv[0]}..{lv[-1]}" if lv else "run"
    commit_push([rel(d)], f"{a.run}: share {what}")


def cmd_take(a):
    pull()
    me = sig()
    d = RUNS / a.run / f"level{a.level}"
    found = []
    for t in sorted(RUNS.glob(f"{a.run}-*/level{a.level}/solve.py")):
        who = t.parent.parent.name[len(a.run) + 1:]
        if who == me:
            continue
        dst = d / f"solve_{who}.py"
        shutil.copyfile(t, dst)
        found.append(dst.name)
        note = t.parent / "NOTE.md"
        print(f"== {who}: {rel(dst)}")
        print(note.read_text(encoding="utf-8").strip() if note.exists() else "(no NOTE.md)")
    if not found:
        print(f"no teammate solver for level {a.level} yet")
        return
    for f in found:
        print(f"try:  python arena/ccc.py run {a.level} --solver {f}   then   python arena/ccc.py go {a.level} --solver {f}")


# ---------------------------------------------------------------- shadow
def mirror(run, me):
    """Copy the driver's new level files (not its code or outputs) into <run>-<me>/; returns missing inputs."""
    src, dst = RUNS / run, RUNS / f"{run}-{me}"
    missing = []
    for n in levels(src):
        s, t = src / f"level{n}", dst / f"level{n}"
        for f in s.rglob("*"):
            r = f.relative_to(s)
            if f.is_dir() or SKIP & set(r.parts) or f.suffix == ".py" or f.name in NOTES:
                continue
            out = t / (r.as_posix()[:-len(".duo.gz")] if f.name.endswith(".duo.gz") else r)
            exclude(out)  # mirrored inputs stay local; only the shadow's own *.py and NOTE.md are committed
            if out.exists() and (f.name.endswith(".duo.gz") or out.stat().st_size == f.stat().st_size):
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            if f.name.endswith(".duo.gz"):
                with gzip.open(f, "rb") as i, out.open("wb") as o:
                    shutil.copyfileobj(i, o, 1 << 20)
            else:
                shutil.copyfile(f, out)
        if t.is_dir():
            m = json.loads((t / "map.json").read_text(encoding="utf-8"))
            missing += [rel(t / p) for p in m.get("inputs", {}) if not (t / p).exists()]
    return missing


def status(run, me, quiet=False):
    pull()
    missing = mirror(run, me)
    src, mine = RUNS / run, RUNS / f"{run}-{me}"
    lv = levels(src)
    done = (src / "ALL_DONE").exists()
    if quiet:
        return lv, done
    if not lv:
        print(f"driver has not shared level 1 of {run!r} yet")
        return lv, done
    n = lv[-1]
    print(f"driver run {run}: " + ("ALL LEVELS DONE: stop." if done else
          f"OPEN LEVEL {n}" + (f" (levels 1..{n - 1} passed)" if n > 1 else "")))
    if not done:
        print(f"  statement      {rel(mine / f'level{n}' / 'statement.txt')}")
        print(f"  your folder    {rel(mine / f'level{n}')}   (python arena/ccc.py run {n})")
        drv = src / f"level{n}" / "solve.py"
        print(f"  driver solver  {rel(drv) if drv.exists() else '(none shared yet)'}")
        notes = src / f"level{n}" / "DRIVER_NOTES.md"
        if notes.exists():
            print("  driver notes:\n    " + notes.read_text(encoding="utf-8").strip().replace("\n", "\n    "))
    if missing:
        print(f"  MISSING inputs (too big for git): {missing}")
    return lv, done


def cmd_status(a):
    status(a.run, sig())


def cmd_activate(a):
    """Shadow laptop only: mirror the driver's levels and make <run>-<sig> the active run for `ccc.py run`."""
    me = sig()
    status(a.run, me)
    set_active(f"{a.run}-{me}")
    print(f"active run: {a.run}-{me}")


def cmd_publish(a):
    me = sig()
    t = RUNS / f"{a.run}-{me}" / f"level{a.level}"
    if not (t / "solve.py").exists():
        sys.exit(f"ERROR: {rel(t / 'solve.py')} does not exist")
    with (t / "NOTE.md").open("a", encoding="utf-8") as f:
        f.write(f"- {time.strftime('%H:%M:%S')} {a.note}\n")
    commit_push([rel(p) for p in [*t.glob("*.py"), t / "NOTE.md"]], f"{a.run} level {a.level} alternative: {a.note}")


def keep_awake():
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])
    elif os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)


def cmd_shadow(a):
    me = sig()
    keep_awake()
    print(f"== shadow {me} following run {a.run!r} ({time.strftime('%H:%M:%S')}); waiting for the driver's level 1")
    t0 = 0
    while not status(a.run, me, quiet=True)[0]:
        if time.time() - t0 > 60:
            print(f"   {time.strftime('%H:%M:%S')} not shared yet", flush=True)
            t0 = time.time()
        time.sleep(10)
    lv, _ = status(a.run, me)
    mine = RUNS / f"{a.run}-{me}"
    set_active(mine.name)  # plain `python arena/ccc.py run N` works in any terminal/IDE, no CCC_RUN needed
    tpl = (REPO / "docs" / "strategy" / "shadow-prompt.md").read_text(encoding="utf-8")
    pf = mine / "PROMPT.txt"
    pf.write_text(tpl.replace("{{RUN}}", a.run).replace("{{SIG}}", me).replace("{{END}}", a.end), encoding="utf-8")
    exclude(pf)
    # the full prompt goes through a file: Windows .cmd wrappers (claude.cmd, agent.cmd) mangle multi-line arguments
    prompt = (f"signature: {me}. SHADOW MODE. Read {rel(pf)} now and follow it exactly; it is your complete "
              f"instruction for this session and replaces the usual session ritual. Start immediately.")
    agent = pick_agent(a.agent)
    print(f"\a== level 1 is shared ({time.strftime('%H:%M:%S')}); agent: {agent}", flush=True)
    if agent == "paste":
        print(f"\nPaste this into the Cursor chat (Agent mode); this window then announces each new level:\n\n{prompt}\n", flush=True)
        watch(a.run, me, lv)
        return
    env = {**os.environ, "CCC_RUN": mine.name}
    argv = agent_argv(agent, a.model, prompt, a.headless)
    if a.headless:
        log = mine / "shadow.log"
        with log.open("w", encoding="utf-8") as f:
            rc = subprocess.call(argv, cwd=REPO, env=env, stdout=f, stderr=subprocess.STDOUT)
        print(f"== {agent} finished; log {rel(log)}")
    else:
        rc = subprocess.call(argv, cwd=REPO, env=env)
    sys.exit(rc)


def set_active(name):
    p = ARENA / ".auth" / "state.json"
    try:
        st = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except json.JSONDecodeError:
        st = {}
    st.setdefault("runs", {})
    st["active"] = name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, indent=2), encoding="utf-8")


def cursor_exe():
    return shutil.which("agent") or shutil.which("cursor-agent")


def pick_agent(want):
    if want != "auto":
        return want
    return "claude" if shutil.which("claude") else "cursor" if cursor_exe() else "paste"


def agent_argv(agent, model, prompt, headless):
    if agent == "claude":
        exe = shutil.which("claude") or sys.exit("ERROR: `claude` not on PATH")
        return [exe, *(["-p"] if headless else []), "--dangerously-skip-permissions", "--model", model or "opus", prompt]
    exe = cursor_exe() or sys.exit("ERROR: Cursor CLI `agent` not on PATH (install: https://cursor.com/cli)")
    # --force: run commands without asking; no --model = the model chosen in Cursor (`agent models` lists slugs)
    return [exe, *(["-p", "--output-format", "text"] if headless else []), "--force",
            *(["--model", model] if model else []), prompt]


def watch(run, me, lv):
    """Paste mode: keep pulling and announce each newly opened level until the driver is done."""
    last = lv[-1] if lv else 0
    while True:
        time.sleep(30)
        lv, done = status(run, me, quiet=True)
        if done:
            print(f"\a== {time.strftime('%H:%M:%S')} driver: ALL LEVELS DONE. Stop.")
            return
        if lv and lv[-1] != last:
            last = lv[-1]
            print(f"\a== {time.strftime('%H:%M:%S')} LEVEL {last} OPEN: tell the agent "
                  f"\"level {last} is open, run python arena/duo.py status {run}\"", flush=True)


def main():
    ap = argparse.ArgumentParser(description="two-laptop contest mode (driver + second opinion)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("share"); p.add_argument("run"); p.add_argument("--note", nargs=2, metavar=("LEVEL", "TEXT"))
    p.add_argument("--done", action="store_true"); p.set_defaults(f=cmd_share)
    p = sp.add_parser("take"); p.add_argument("run"); p.add_argument("level", type=int); p.set_defaults(f=cmd_take)
    p = sp.add_parser("status"); p.add_argument("run"); p.set_defaults(f=cmd_status)
    p = sp.add_parser("activate"); p.add_argument("run"); p.set_defaults(f=cmd_activate)
    p = sp.add_parser("publish"); p.add_argument("run"); p.add_argument("level", type=int); p.add_argument("note")
    p.set_defaults(f=cmd_publish)
    p = sp.add_parser("shadow"); p.add_argument("--run", default="contest"); p.add_argument("--headless", action="store_true")
    p.add_argument("--agent", default="auto", choices=["auto", "claude", "cursor", "paste"],
                   help="auto: claude if installed, else Cursor's `agent` CLI, else print the prompt to paste")
    p.add_argument("--model", default="", help="claude default opus; cursor default = the model set in Cursor")
    p.add_argument("--end", default="20:00 Romania time (17:00 UTC)"); p.set_defaults(f=cmd_shadow)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
