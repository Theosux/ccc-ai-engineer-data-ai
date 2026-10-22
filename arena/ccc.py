#!/usr/bin/env python3
"""CCC arena CLI: fetch levels, run solvers, submit outputs on codingcontest.org.

  python arena/ccc.py fetch N [--png]   # download level N, print cleaned statement + example; solve.py = copy of N-1
  python arena/ccc.py go N [--force]    # run all inputs (parallel), check example (or solve.check), submit
                                        # (sequential, verified), and if the level passed: fetch N+1 + print it
  python arena/ccc.py run N [--only ID] [--solver CMD]     # outputs only
  python arena/ccc.py submit N [--only ID ...] [--include-example]
  python arena/ccc.py info [--raw]
  python arena/ccc.py wait [contestName] [--name contest]  # contest day: block until the game is live, then fetch 1
  python arena/ccc.py contest [contestName] [--name contest]
  python arena/ccc.py train <gameSlug> [--mode exploration|challenge] [--name NAME]
  python arena/ccc.py login [--http]    # browser login (Edge) or HTTP login from .auth/credentials.env
  python arena/ccc.py games | use NAME | api GET|POST <path> [--game]
Env: CCC_RUN=<name> selects the run for one command (and keeps `train`/`contest` from changing the active run).
"""
import argparse
import concurrent.futures as cf
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path

import requests

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

BASE = "https://codingcontest.org"
CONTEST = "42nd-data-ai-ccc-5873"
ARENA = Path(__file__).resolve().parent
AUTH = ARENA / ".auth"
RUNS = ARENA / "runs"
COOKIES = AUTH / "cookies.json"
STATE = AUTH / "state.json"
CREDS = AUTH / "credentials.env"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36 Edg/141.0"
T0 = time.time()
LOCK = threading.Lock()


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- state
def load_json(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except json.JSONDecodeError:
        return default


def save_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def state():
    return load_json(STATE, {"active": None, "runs": {}})


def active_run():
    st = state()
    name = os.environ.get("CCC_RUN") or st.get("active")
    if name and name not in st["runs"]:
        if (RUNS / name).is_dir():  # e.g. a teammate's clone: run/probe work from the local level folders
            return name, {"gameBaseUrl": ""}, st
        die(f"Unknown run {name!r}. Known: {', '.join(st['runs'])}")
    if not name:
        die("No active run. Use `train <gameSlug>`, `contest` or `wait` first.")
    return name, st["runs"][name], st


def update_run(name, **fields):
    """Re-read state.json and patch one run (other sessions may write the file concurrently)."""
    with LOCK:
        st = state()
        st["runs"].setdefault(name, {}).update(fields)
        save_json(STATE, st)


# ---------------------------------------------------------------- http
_TLS = threading.local()


def _sess():
    s = getattr(_TLS, "s", None)
    if s is None:  # one keep-alive session per thread (requests.Session is not guaranteed thread-safe)
        s = _TLS.s = requests.Session()
        s.headers["User-Agent"] = UA
    return s


def req(method, url, session=None, tries=3, **kw):
    """HTTP with retry on network errors and 502/503/504. Exits cleanly instead of a traceback."""
    kw.setdefault("timeout", 60)
    s = session or _sess()
    for i in range(tries):
        try:
            r = s.request(method, url, **kw)
            if r.status_code in (502, 503, 504) and i < tries - 1:
                time.sleep(1 + i)
                continue
            return r
        except (requests.ConnectionError, requests.Timeout) as e:
            if i == tries - 1:
                die(f"network error on {method} {url.split('?')[0]}: {e.__class__.__name__}. Check the connection and retry.")
            time.sleep(1 + 2 * i)


def platform_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": BASE + "/", "Origin": BASE})
    for c in load_json(COOKIES, []):
        s.cookies.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path", "/"))
    xsrf = s.cookies.get("XSRF-TOKEN")
    if xsrf:
        s.headers["X-XSRF-TOKEN"] = xsrf
    return s


def plat(method, path, s=None, **kw):
    """Platform request; on 401 with credentials available, re-login over HTTP once and retry."""
    r = req(method, BASE + path, session=s or platform_session(), **kw)
    if r.status_code == 401 and all(read_creds()):
        print("(session expired -> automatic HTTP re-login)", file=sys.stderr)
        http_login()
        fresh = platform_session()
        if s is not None:
            s.cookies, s.headers = fresh.cookies, fresh.headers
        r = req(method, BASE + path, session=s or fresh, **kw)
    return r


def check(r, what):
    if r.status_code == 401 or (r.status_code == 403 and "login" in r.text.lower()):
        die(f"{what}: SESSION EXPIRED / not logged in (HTTP {r.status_code}). Run `python arena/ccc.py login` "
            f"(or `login --http` if .auth/credentials.env exists), then repeat the command.")
    if not r.ok:
        die(f"{what}: HTTP {r.status_code} {r.text[:300]}")
    return r


def game_headers(run):
    origin = run["gameBaseUrl"].rstrip("/")
    return {"Authorization": run["token"], "X-CCC-SLUG": run["contestSlug"], "Referer": origin + "/",
            "Origin": origin, "Sec-Fetch-Site": "same-origin", "User-Agent": UA}


def refresh_token(name, run, seen=None):
    with LOCK:
        if seen is not None and run.get("token") != seen:  # another thread already refreshed
            return run
        r = check(plat("POST", "/api/game-token", json={"contestSlug": run["contestSlug"]}), "game-token")
        run["token"] = r.json()["token"]
        run["tokenAt"] = time.time()
    update_run(name, token=run["token"], tokenAt=run["tokenAt"])
    return run


def game_req(method, path, ctx, **kw):
    """Request against the game origin; refreshes the game token once on 401/403."""
    name, run, _ = ctx
    if not run.get("token"):
        refresh_token(name, run)
    url = run["gameBaseUrl"].rstrip("/") + path
    for attempt in range(2):
        tok = run["token"]
        r = req(method, url, headers=game_headers(run), **kw)
        if r.status_code in (401, 403) and attempt == 0:
            refresh_token(name, run, seen=tok)
            continue
        return r
    return r


def run_dir(name):
    d = RUNS / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def level_dir(name, n):
    return run_dir(name) / f"level{n}"


def game_info(ctx):
    """Public /game/game-info: level count + per level inputFiles/unscoredFiles/sandbox/optimization. Cached."""
    name, run, _ = ctx
    p = run_dir(name) / "game-info.json"
    gi = load_json(p, None)
    if gi is None and run.get("gameBaseUrl"):
        origin = run["gameBaseUrl"].rstrip("/")
        r = req("GET", origin + "/game/game-info", headers={"Referer": origin + "/", "Sec-Fetch-Site": "same-origin"})
        try:
            gi = r.json() if r.ok else {}
        except ValueError:
            gi = {}
        if gi:
            save_json(p, gi)
    return gi or {}


def level_meta(gi, n):
    lv = (gi.get("levelsInfo") or {}).get("levels") or []
    return lv[n - 1] if 0 < n <= len(lv) else {}


def total_levels(gi):
    return (gi.get("levelsInfo") or {}).get("count")


def contestant_info(ctx):
    if ctx[1].get("offlineGame"):
        return {"score": off_score(ctx[0])}
    r = game_req("GET", "/api/contestant/contestant-info", ctx)
    if not r.ok:
        die(f"contestant-info: HTTP {r.status_code} {r.text[:300]}")
    info = r.json()
    save_json(run_dir(ctx[0]) / "contestant-info.json", info)
    return info


def passed_files(score, n):
    lv = ((score or {}).get("state") or {}).get(f"level{n}") or {}
    return {f for f, v in (lv.get("passedFiles") or {}).items() if v}, lv.get("passedAt")


# ---------------------------------------------------------------- auth
def launch_browser(p, profile):
    """Persistent headed context on the first installed channel: Edge, else Chrome (macOS has no Edge by default),
    else playwright's own Chromium. Override with CCC_BROWSER=chrome (comma list)."""
    err = None
    for ch in (os.environ.get("CCC_BROWSER") or "msedge,chrome,chromium").split(","):
        try:
            kw = {} if ch == "chromium" else {"channel": ch}
            return p.chromium.launch_persistent_context(str(AUTH / profile), headless=False, viewport=None, **kw)
        except Exception as e:
            err = e
    raise err


def cmd_login(a):
    if a.http:
        return http_login()
    from playwright.sync_api import sync_playwright

    AUTH.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = launch_browser(p, "edge-profile")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BASE + "/login")
        print("Log in in the browser window (waiting up to 5 min)...")
        deadline, user = time.time() + 300, None
        while time.time() < deadline:
            r = ctx.request.get(BASE + "/api/auth/current-user")
            if r.ok:
                try:
                    user = r.json()
                except Exception:
                    user = None
                if user and (user.get("username") or user.get("id")):
                    break
            time.sleep(2)
        if not user:
            ctx.close()
            die("Login not detected.")
        save_json(COOKIES, [c for c in ctx.cookies() if "codingcontest.org" in c["domain"]])
        ctx.close()
    print(f"Logged in as {user.get('username')} (roles: {user.get('roles')}). Cookies saved.")


def read_creds():
    env = {}
    if CREDS.exists():
        for line in CREDS.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    user = os.environ.get("CCC_USER") or env.get("CCC_USER")
    pw = os.environ.get("CCC_PASS") or env.get("CCC_PASS")
    return user, pw


def http_login():
    """POST /api/auth/login {username,password} with the XSRF double-submit cookie. Saves cookies only on success."""
    user, pw = read_creds()
    if not user or not pw:
        die(f"No credentials. Put CCC_USER=... and CCC_PASS=... in {CREDS} (gitignored), or use `login` (browser).")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": BASE + "/login", "Origin": BASE})
    req("GET", BASE + "/api/auth/current-user", session=s)
    if not s.cookies.get("XSRF-TOKEN"):
        req("GET", BASE + "/login", session=s)
    xsrf = s.cookies.get("XSRF-TOKEN")
    if xsrf:
        s.headers["X-XSRF-TOKEN"] = xsrf
    r = req("POST", BASE + "/api/auth/login", session=s, json={"username": user, "password": pw}, tries=2)
    if not r.ok:
        die(f"HTTP login failed: HTTP {r.status_code} {r.text[:200]} (xsrf cookie {'present' if xsrf else 'MISSING'}). "
            "Fall back to `python arena/ccc.py login` (browser).")
    me = req("GET", BASE + "/api/auth/current-user", session=s)
    try:
        who = me.json()
    except ValueError:
        who = {}
    if not me.ok or not who.get("username"):
        die(f"HTTP login: current-user check failed (HTTP {me.status_code}). Use browser `login`.")
    save_json(COOKIES, [{"name": c.name, "value": c.value, "domain": c.domain.lstrip("."), "path": c.path or "/"}
                        for c in s.cookies if "codingcontest.org" in (c.domain or "")])
    print(f"Logged in (HTTP) as {who.get('username')} (roles: {who.get('roles')}). Cookies saved.")


# ---------------------------------------------------------------- runs
def cmd_games(a):
    for g in check(req("GET", f"{BASE}/api/games"), "games").json():
        print(f"{g.get('slug'):45} {g.get('totalLevels')!s:>3} lv  {g.get('title') or g.get('name')}")


def register_run(name, contest_name, extra, c=None):
    c = c or check(plat("GET", f"/api/contests/{contest_name}"), "contest").json()
    gbu, slug = c.get("gameBaseUrl"), c.get("slug") or contest_name
    save_json(run_dir(name) / "contest.json", c)
    if not gbu:
        die(f"Contest {slug} has no game yet (status {c.get('status')}, start {c.get('startTime')}). "
            f"Use `python arena/ccc.py wait` to block until it is live.")
    with LOCK:
        st = state()
        st["runs"][name] = {"contestName": contest_name, "contestSlug": slug, "gameBaseUrl": gbu, "token": None, **extra}
        if not os.environ.get("CCC_RUN"):
            st["active"] = name
        save_json(STATE, st)
    run = st["runs"][name]
    (run_dir(name) / "game-info.json").unlink(missing_ok=True)
    refresh_token(name, run)
    gi = game_info((name, run, st))
    act = "active" if not os.environ.get("CCC_RUN") else "not activated (CCC_RUN set)"
    print(f"Run {name} [{act}]: contest {slug}, game {gi.get('name') or gbu}, {total_levels(gi)} levels. Token OK.")
    return name, run, st


def cmd_train(a):
    s = platform_session()
    r = plat("POST", f"/api/training/{a.slug}/start", s, params={"mode": a.mode})
    if not r.ok:
        if r.status_code == 401:
            check(r, "training start")
        act = plat("GET", "/api/training/active", s)
        print(f"start -> HTTP {r.status_code} {r.text[:200]}; active training: {act.status_code} {act.text[:300]}")
        if not act.ok or not act.text.strip():
            sys.exit(1)
        data = act.json()
    else:
        data = r.json()
    contest_name = data.get("contestName") or data.get("name") or data.get("slug")
    register_run(a.name or a.slug.split("-")[-1], contest_name, {"gameSlug": a.slug, "mode": a.mode})


def cmd_contest(a):
    register_run(a.name, a.contest_name, {})


def hms(sec):
    sec = int(sec)
    d, h, m, s = sec // 86400, sec % 86400 // 3600, sec % 3600 // 60, sec % 60
    return (f"{d}d " if d else "") + f"{h:02d}:{m:02d}:{s:02d}"


def cmd_wait(a):
    """Block until the contest is live (status RUNNING + gameBaseUrl), keeping the session warm; then register + fetch 1."""
    s = platform_session()
    last_auth = 0
    while True:
        if time.time() - last_auth > 240:  # also keeps the server-side session from idling out
            check(plat("GET", "/api/auth/current-user", s), "session check")
            last_auth = time.time()
        r = plat("GET", f"/api/contests/{a.contest_name}", s)
        if r.status_code == 401:
            check(r, "contest")
        c = r.json() if r.ok else {}
        status, gbu = c.get("status"), c.get("gameBaseUrl")
        if status in ("RUNNING", "STATS_FROZEN") and gbu:
            break
        left = None
        if c.get("startTime") and c.get("serverNowMs"):
            from datetime import datetime
            start = datetime.fromisoformat(c["startTime"].replace("Z", "+00:00")).timestamp() * 1000
            left = (start - c["serverNowMs"]) / 1000
        nap = 2 if left is None or left < 90 else min(left - 60, 240)
        print(f"[{time.strftime('%H:%M:%S')}] status={status} game={'yes' if gbu else 'no'} "
              f"starts in {'?' if left is None else hms(left)}; next check in {nap:.0f}s", flush=True)
        time.sleep(nap)
    print(f"[{time.strftime('%H:%M:%S')}] LIVE: {c.get('gameName')} at {gbu}", flush=True)
    for i in range(30):  # game token / game API can lag the status flip by a few seconds
        try:
            ctx = register_run(a.name, a.contest_name, {}, c=c)
            break
        except SystemExit:
            if i == 29:
                raise
            time.sleep(2)
            c = plat("GET", f"/api/contests/{a.contest_name}", s).json()
    os.environ["CCC_RUN"] = a.name
    fetch_level(ctx, 1, retry_s=60)


def cmd_use(a):
    with LOCK:
        st = state()
        if a.name not in st["runs"]:
            die(f"Unknown run. Known: {', '.join(st['runs'])}")
        st["active"] = a.name
        save_json(STATE, st)
    print(f"Active run: {a.name}")


def cmd_info(a):
    ctx = active_run()
    info = contestant_info(ctx)
    if a.raw:
        print(json.dumps(info, indent=2)[:6000])
        return
    gi = game_info(ctx)
    score = info.get("score") or {}
    gs = score.get("gameScore") or {}
    print(f"Run {ctx[0]} ({ctx[1]['contestSlug']}): unlocked level {gs.get('level')}/{total_levels(gi)}")
    st = score.get("state") or {}
    for k in sorted(st, key=lambda x: int(re.sub(r"\D", "", x) or 0)):
        n = int(re.sub(r"\D", "", k) or 0)
        ok, at = passed_files(score, n)
        allf = list((st[k].get("passedFiles") or {}).keys())
        todo = [f for f in allf if f not in ok]
        print(f"  {k}: {'PASSED' if at else f'{len(ok)}/{len(allf)} passed, todo {todo}'}")
    cds = [f"L{c['level']}/{c['fileId']} {c['remainingMs'] / 1000:.0f}s" for c in info.get("cooldowns") or [] if c.get("remainingMs", 0) > 0]
    if cds:
        print(f"  cooldowns: {', '.join(cds)}")


# ---------------------------------------------------------------- fetch
IN_RE = re.compile(r"^in_level-?(\d+)_(.+)\.[a-z]+$", re.I)
BOILER = re.compile(r"#WeLoveSoftware|cloudflight\.io/career|^PROCESSING|^For each input file, calculate the output"
                    r"|^Upload your output file|^LEVEL (ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)\b", re.I)

SOLVE_TEMPLATE = '''import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from lib import *  # Reader, grid/paths/search helpers: see .claude/skills/ccc-patterns
# First line '# ccc: pypy' (or CCC_PY=pypy) runs this solver on PyPy.


def cases(data: str) -> list:
    """Split the input into independent cases (picklable). One case for a whole-file problem: [data]."""
    r = Reader(data)
    return [r.word() for _ in range(r.int())]


def solve_case(c) -> str:
    raise NotImplementedError


# Optional: def check(data: str, out: str) -> bool | (bool, str)
# If defined, `go` accepts outputs that check() validates even when the example output differs.

if __name__ == "__main__":
    run_cases(cases, solve_case)  # parallel across cases when slow, progress + ETA; `ccc.py probe N` times it
'''


def file_id_for(stem, ids):
    """Platform rule: exact id at the end of the name, else the last number in the filename picks the case."""
    for fid in sorted(ids, key=len, reverse=True):
        if re.search(rf"(^|[^0-9a-z]){re.escape(fid.lower())}$", stem.lower()):
            return fid
    if "example" in stem.lower():
        ex = [i for i in ids if "example" in i]
        if ex:
            return ex[0]
    nums = re.findall(r"\d+", stem)
    if nums:
        last = str(int(nums[-1]))
        for fid in ids:
            if re.match(rf"^0*{last}(-|$)", fid):
                return fid
        return last
    return None


def pdf_pages(pdf_bytes):
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf_bytes)
        pages = [doc[i].get_textpage().get_text_bounded() for i in range(len(doc))]
        doc.close()
        return pages
    except Exception:
        from pypdf import PdfReader
        return [pg.extract_text() or "" for pg in PdfReader(io.BytesIO(pdf_bytes)).pages]


def clean_statement(pages, game_name=None):
    """Drop slide boilerplate (#WeLoveSoftware, career link, PROCESSING, duplicate LEVEL headers, game name)."""
    out, seen = [], set()
    for i, txt in enumerate(pages, 1):
        lines = []
        for line in txt.replace("\r", "").splitlines():
            s = line.strip()
            if not s or BOILER.search(s) or (game_name and s == game_name):
                continue
            if re.fullmatch(r"LEVEL \d+", s, re.I):
                if s.upper() in seen:
                    continue
                seen.add(s.upper())
            lines.append(line.rstrip())
        if lines:
            out += [f"[p{i}]"] + lines + [""]
    return "\n".join(out).strip() + "\n", [int(l[2:-1]) for l in out if re.fullmatch(r"\[p\d+\]", l)]


def render_png(pdf_bytes, pages, outdir, scale):
    import pypdfium2 as pdfium
    outdir.mkdir(exist_ok=True)
    doc = pdfium.PdfDocument(pdf_bytes)
    paths = []
    for p in pages:
        path = outdir / f"p{p}.png"
        doc[p - 1].render(scale=scale).to_pil().save(path)
        paths.append(path)
    doc.close()
    return paths


def head(path, n=25, width=160):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    shown = [l if len(l) <= width else l[:width] + " ..." for l in lines[:n]]
    more = f"\n... ({len(lines)} lines total)" if len(lines) > n else ""
    return "\n".join(shown) + more


# ---------------------------------------------------------------- offline games (arena/offline.py)
OFFLINE_GAMES = ARENA / ".data" / "games"


def log_timing(name, event, n, **kw):
    """Append to runs/<run>/timing.jsonl: fetch/pass/wrong events per level (training retros, A/B)."""
    with (run_dir(name) / "timing.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": round(time.time(), 1), "event": event, "level": n, **kw}) + "\n")


def off_score(name):
    return load_json(run_dir(name) / "offline-score.json", {"gameScore": {"level": 1}, "state": {}, "wrongSubmits": 0})


def offline_judge(ctx, n, fid, path):
    """Local stand-in for POST submit-N-fid: reference output, else judges/levelN.py, else accept (UNVERIFIED)."""
    name, run, _ = ctx
    g = OFFLINE_GAMES / run["offlineGame"]
    d = level_dir(name, n)
    inp = next((i for i, f in inputs_of(d) if f == fid), None)
    out = path.read_text(encoding="utf-8")
    exp_p = g / "expected" / f"level{n}" / f"{fid}.txt"
    judge_p = g / "judges" / f"level{n}.py"
    ok, msg, line = False, "", None
    if exp_p.exists() and norm(exp_p.read_text(encoding="utf-8")) == norm(out):
        ok, msg = True, "matches reference"
    elif judge_p.exists():
        spec = importlib.util.spec_from_file_location(f"judge_{n}", str(judge_p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        try:
            res = mod.judge(inp.read_text(encoding="utf-8"), out)
            ok, msg = res if isinstance(res, tuple) else (bool(res), "")
        except Exception as e:
            ok, msg = False, f"judge raised {e!r}"
    elif exp_p.exists():
        msg = "differs from reference: " + first_diff(norm(exp_p.read_text(encoding="utf-8")), norm(out))
        m = re.match(r"line (\d+)", msg.split(": ", 1)[1])
        line = int(m.group(1)) if m else None
    else:
        ok, msg = True, "UNVERIFIED: no reference output and no judge for this file"
    sc = off_score(name)
    lv = sc["state"].setdefault(f"level{n}", {"passedFiles": {}, "passedAt": None})
    if ok:
        lv["passedFiles"][fid] = True
    else:
        sc["wrongSubmits"] = sc.get("wrongSubmits", 0) + 1
        log_timing(name, "wrong", n, file=fid, msg=str(msg)[:200])
    scored = load_json(d / "map.json", {"scoredFiles": []})["scoredFiles"]
    if not lv["passedAt"] and all(lv["passedFiles"].get(f) for f in scored):
        lv["passedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        sc["gameScore"]["level"] = max(sc["gameScore"]["level"], n + 1)
        log_timing(name, "pass", n, wrong=sc.get("wrongSubmits", 0))
    save_json(run_dir(name) / "offline-score.json", sc)
    case = {"isCorrect": ok, "caseState": "CORRECT" if ok else "WRONG", "caseMessage": msg,
            "startLineNumber": 1, "endLineNumberExcl": None, "errorLineNumber": line}
    return fid, 200, {"evaluation": {"isCorrect": ok, "cases": [case]}, "score": sc}


def download_zip(ctx, n, retry_s=0):
    name, run, _ = ctx
    if run.get("offlineGame"):
        lvl = off_score(name)["gameScore"]["level"]
        if n > lvl:
            die(f"level {n} is locked (offline game: pass level {lvl} first)")
        return (OFFLINE_GAMES / run["offlineGame"] / f"level-{n}.zip").read_bytes()
    deadline = time.time() + retry_s
    while True:
        r = game_req("GET", f"/api/contestant/level/{n}/files", ctx)
        if r.ok:
            break
        if time.time() >= deadline:
            die(f"level {n} files: HTTP {r.status_code} {r.text[:200]} (level not unlocked yet? check `info`)")
        time.sleep(2)
    if "application/json" in r.headers.get("content-type", ""):
        z = req("GET", r.json()["url"], timeout=(10, 30))  # pre-signed blob URL, no auth; retried on stalls
        if not z.ok:  # same fallback as the game client
            z = game_req("GET", f"/api/contestant/level/{n}/files?raw=true", ctx)
        if not z.ok:
            die(f"level {n} zip download: HTTP {z.status_code}")
        return z.content
    return r.content


def fetch_level(ctx, n, png=False, scale=0.75, quiet=False, retry_s=0, zip_path=None):
    """Download level N (or ingest a manually downloaded zip with zip_path) and print statement + example."""
    name, run, _ = ctx
    t0 = time.time()
    d = level_dir(name, n)
    d.mkdir(parents=True, exist_ok=True)
    zpath = d / f"level-{n}.zip"
    with cf.ThreadPoolExecutor(3) as ex:
        f_gi = ex.submit(game_info, ctx)
        reuse = png and zpath.exists() and not zip_path
        f_zip = None if reuse or zip_path else ex.submit(download_zip, ctx, n, retry_s)
        gi = f_gi.result()
        meta = level_meta(gi, n)
        online = bool(run.get("gameBaseUrl")) and not zip_path
        f_sb = ex.submit(game_req, "GET", f"/api/contestant/level/{n}/sandbox", ctx) if online and meta.get("sandbox", True) else None
        data = Path(zip_path).read_bytes() if zip_path else zpath.read_bytes() if reuse else f_zip.result()
        sandbox = f_sb.result() if f_sb else None
    if not reuse:
        if not zpath.exists():
            log_timing(name, "fetch", n)
        zpath.write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(d / "files")
    if sandbox is not None and sandbox.ok and sandbox.text.strip():
        (d / "sandbox.html").write_text(sandbox.text, encoding="utf-8")
    files = sorted(p for p in (d / "files").rglob("*") if p.is_file())
    # input -> fileId mapping: game-info lists the ids; files are in_level-N_<fileId>.txt (2026 naming)
    ids = meta.get("inputFiles") or []
    unscored = meta.get("unscoredFiles") or [i for i in ids if "example" in i]
    mapping = {}
    for p in files:
        m = IN_RE.match(p.name)
        if m:
            mapping[str(p.relative_to(d)).replace("\\", "/")] = m.group(2)
    if not mapping:
        for p in files:
            if p.suffix.lower() in (".in", ".txt") and not p.stem.lower().startswith("out"):
                mapping[str(p.relative_to(d)).replace("\\", "/")] = file_id_for(p.stem, ids or ["0-example"])
    if not ids:
        ids = sorted(set(mapping.values()))
        unscored = [i for i in ids if i and "example" in i]
    scored = [i for i in ids if i not in unscored]
    save_json(d / "map.json", {"scoredFiles": scored, "unscoredFiles": unscored, "inputs": mapping})
    # statement
    stmt, content_pages, pdf_bytes = None, [], None
    pdfs = [p for p in files if p.suffix.lower() == ".pdf"]
    if pdfs:
        pdf_bytes = pdfs[0].read_bytes()
        stmt, content_pages = clean_statement(pdf_pages(pdf_bytes), gi.get("name"))
        stmt = repair_garbled(stmt)
        (d / "statement.txt").write_text(stmt, encoding="utf-8")
    image_only = stmt is not None and looks_image_only(stmt)
    if content_pages:  # pages with NO text at all between content pages are pure images (Pacman L7 rules on p3)
        gaps = [k for k in range(min(content_pages) + 1, max(content_pages)) if k not in content_pages]
        image_only = sorted(set(image_only or []) | set(gaps)) or image_only
    all_pages = list(range(1, len(pdf_pages(pdf_bytes)) + 1)) if pdf_bytes else []
    pngs = render_png(pdf_bytes, all_pages, d / "pages", scale) if (png or image_only) and pdf_bytes else []
    # solver: start from the previous level's solver (most levels extend it)
    solve, prev = d / "solve.py", level_dir(name, n - 1) / "solve.py"
    if solve.exists():
        solve_note = "kept existing"
    elif n > 1 and prev.exists():
        shutil.copy(prev, solve)
        solve_note = f"copied from level{n - 1}/solve.py"
    else:
        solve.write_text(SOLVE_TEMPLATE, encoding="utf-8")
        solve_note = "stub"
    if quiet:
        return d
    flags = [k for k in ("optimization", "sandbox") if meta.get(k)]
    print(f"===== Level {n}/{total_levels(gi) or '?'}  {d}  ({time.time() - t0:.1f}s)  {' '.join(flags)}")
    print(f"inputs: {', '.join(f'{fid}' + ('*' if fid in unscored else '') for fid in mapping.values())}  (* = unscored)")
    sizes = []
    for rel, fid in mapping.items():  # size first: pick the algorithm for the LARGE file, not the example
        p = d / rel
        txt = p.read_text(encoding="utf-8", errors="replace")
        first = txt.split(None, 1)[0] if txt.strip() else "?"
        longest = max((len(l) for l in txt.splitlines()), default=0)
        sizes.append(f"{fid}: {p.stat().st_size / 1024:.0f} KB, {txt.count(chr(10))} lines, first token {first}, longest line {longest}")
    print("sizes: " + " | ".join(sizes))
    other = [str(p.relative_to(d)) for p in files if str(p.relative_to(d)).replace('\\', '/') not in mapping
             and not p.name.startswith("out_") and p.suffix.lower() != ".pdf"]
    if other:
        print(f"other files: {other}")
    if (d / "sandbox.html").exists():
        print(f"sandbox (visualizer): {d / 'sandbox.html'}")
    print(f"solve.py: {solve_note}")
    if pngs:
        print("page PNGs (Read these for diagrams): " + ", ".join(str(p) for p in pngs))
    if stmt is not None:
        print(f"----- statement (statement.txt, pages {content_pages}; `fetch {n} --png` renders them)\n{stmt}")
        if image_only:
            print(f"!!!!! RULES ARE IN IMAGES on page(s) {image_only} (text is only bullets). "
                  f"Read {', '.join(str(d / 'pages' / f'p{k}.png') for k in image_only)} before solving.")
        bad = garbled_lines(stmt)
        if bad:
            print(f"!!!!! {len(bad)} statement line(s) were garbled (auto-repaired lines start with '[repaired]'),"
                  f" e.g. {bad[0][:80]!r}. If still unclear: `fetch {n} --png` and Read the pages")
    else:
        print(f"(no PDF statement; files: {[p.name for p in files]})")
    for inp_rel, fid in mapping.items():
        if fid in unscored:
            inp = d / inp_rel
            print(f"----- example input {inp.name}\n{head(inp)}")
            exp = expected_path(inp)
            if exp:
                print(f"----- expected output {exp.name}\n{head(exp)}")
                blanks = sum(not l.strip() for l in exp.read_text(encoding="utf-8").strip().splitlines())
                if blanks:
                    print(f"!!!!! expected output has {blanks} BLANK separator line(s): keep them "
                          f"(run_cases(..., sep='\\n\\n', header=...))")
    return d


def looks_image_only(stmt):
    """Pages whose extracted text has no letters/digits at all (e.g. just '▪▪▪▪') hold their rules as images
    (RPS L3/L5). Returns the list of such page numbers."""
    pages, cur = {}, None
    for l in stmt.splitlines():
        m = re.fullmatch(r"\[p(\d+)\]", l.strip())
        if m:
            cur = int(m.group(1))
            pages[cur] = []
        elif cur is not None and l.strip():
            pages[cur].append(l)
    return [p for p, ls in pages.items() if ls and not any(c.isalnum() for l in ls for c in l)]


def repair_garbled(stmt):
    """Some PDF fonts extract as UTF-16-ish bytes with glyph codes shifted by -29 ('D' -> 'a', '\\x03' -> ' ').
    Decode those lines in place and tag them '[repaired]'."""
    out = []
    for line in stmt.splitlines():
        # variant 2 (Spaceship L3): same shift without NUL bytes, e.g. '7KH\x03WLPH' = 'The time'
        if "\x00" in line or ("\x03" in line and sum(c.isupper() or c.isdigit() for c in line) > len(line) // 3):
            s = line.replace("\x00", "")
            line = "[repaired] " + "".join(chr(ord(c) + 29) if 3 <= ord(c) <= 93 else "?" if ord(c) > 126 else c for c in s)
        out.append(line)
    return "\n".join(out)


def garbled_lines(stmt):
    """PDF fonts sometimes extract as shifted/odd glyphs: flag lines dominated by 1-char tokens, control chars
    or odd symbols."""
    bad = []
    for line in stmt.splitlines():
        if line.startswith("[repaired] ") or any(ord(c) < 32 and c != "\t" for c in line):
            bad.append(line)
            continue
        toks = line.split()
        if len(toks) >= 8 and sum(len(t) == 1 and t.isalpha() for t in toks) / len(toks) > 0.6:
            bad.append(line)
        elif len(line) >= 20 and sum(not (c.isascii() or c in "–—‘’“”•▪…→×≤≥") for c in line) / len(line) > 0.3:
            bad.append(line)
    return bad


def cmd_fetch(a):
    if a.zip:
        if not Path(a.zip).is_file():
            die(f"zip not found: {a.zip}")
        st = state()
        name = os.environ.get("CCC_RUN") or st.get("active") or "contest"
        if name not in st["runs"]:  # emergency: platform API unusable, work fully offline from the zip
            update_run(name, contestName=CONTEST, contestSlug=CONTEST, gameBaseUrl="", token=None, offline=True)
            print(f"(created offline run {name!r}; submit by drag&drop of levelN/out/* in the browser)")
        ctx = (name, state()["runs"][name], state())
    else:
        ctx = active_run()
    fetch_level(ctx, a.level, png=a.png, scale=a.scale, zip_path=a.zip)


# ---------------------------------------------------------------- run / submit
def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def inputs_of(d):
    m = load_json(d / "map.json", {"inputs": {}})["inputs"]
    return [(d / rel, fid) for rel, fid in m.items()]


def out_path(d, inp):
    stem = inp.stem[3:] if inp.stem.lower().startswith("in_") else inp.stem
    return d / "out" / f"out_{stem}.txt"


def expected_path(inp):
    if inp.stem.lower().startswith("in_"):
        q = inp.with_name("out_" + inp.name[3:])
        if q.exists():
            return q
    q = inp.with_suffix(".out")
    return q if q.exists() else None


def first_diff(want, got):
    w, g = want.splitlines(), got.splitlines()
    for i in range(max(len(w), len(g))):
        a_ = w[i] if i < len(w) else "<missing>"
        b_ = g[i] if i < len(g) else "<missing>"
        if a_ != b_:
            return f"line {i + 1}: want {a_[:120]!r} got {b_[:120]!r} (want {len(w)} lines, got {len(g)})"
    return "identical"


PYPY = ARENA / ".tools" / "pypy" / "pypy3.exe"


def python_for(py_file):
    """CPython by default; PyPy if CCC_PY=pypy or solve.py's first line contains '# ccc: pypy'."""
    want = os.environ.get("CCC_PY", "")
    try:
        first = py_file.open(encoding="utf-8", errors="replace").readline()
    except OSError:
        first = ""
    if want == "pypy" or "ccc: pypy" in first:
        if PYPY.exists():
            return str(PYPY)
        print(f"  (PyPy requested but {PYPY} missing; using CPython)")
    elif want and want != "cpython":
        return want
    return sys.executable


def solver_cmd(d, solver):
    if not solver:
        return [python_for(d / "solve.py"), str(d / "solve.py")], False
    if solver.endswith(".py"):
        p = Path(solver)
        p = p if p.is_absolute() or p.exists() else d / p
        return [python_for(p), str(p)], False
    return solver, True  # arbitrary shell command, e.g. "pypy3 solve.py" or "node solve.js"


def load_checker(d):
    p = d / "solve.py"
    if not p.exists() or "def check(" not in p.read_text(encoding="utf-8", errors="replace"):
        return None
    sys.path.insert(0, str(ARENA))
    spec = importlib.util.spec_from_file_location("ccc_solve_mod", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "check", None)


def solver_env(extra=None):
    return {**os.environ, "PYTHONPATH": str(ARENA) + os.pathsep + os.environ.get("PYTHONPATH", ""),
            "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHON_COLORS": "0", "NO_COLOR": "1", **(extra or {})}


def run_solver(cmd, shell, inp, d, env, timeout, tag):
    """Run one solver process on one input file. Streams lib.runner's `[runner]`/`[probe]` stderr lines live
    (prefixed with tag) so long runs are never silent. Returns (stdout or None, error text, seconds)."""
    t0 = time.time()
    with inp.open("rb") as fin:
        p = subprocess.Popen(cmd, stdin=fin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell, cwd=d, env=env)
    err_tail, out_buf = [], []

    def pump_err():
        for raw in p.stderr:
            line = raw.decode("utf-8", errors="replace").rstrip()
            if line.startswith(("[runner]", "[probe]")):
                m = re.search(r"ETA_SECONDS=([\d.]+)", line)
                if m:
                    run_solver.last_eta = float(m.group(1))
                    run_solver.heavy_tail = "HEAVY_TAIL" in line
                    continue
                print(f"  {tag}: {line}", flush=True)
            else:
                err_tail.append(line)
                del err_tail[:-60]

    def pump_out():
        out_buf.append(p.stdout.read())

    th = [threading.Thread(target=pump_err, daemon=True), threading.Thread(target=pump_out, daemon=True)]
    for t in th:
        t.start()
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True) if os.name == "nt" else p.kill()
        p.kill()
        return None, f"TIMEOUT after {timeout}s (raise with --timeout; check `probe` ETA first)", time.time() - t0
    for t in th:
        t.join(5)
    if p.returncode != 0:
        return None, "\n".join(err_tail)[-1500:] or f"exit code {p.returncode}", time.time() - t0
    return (out_buf[0] if out_buf else b"").decode("utf-8", errors="replace").replace("\r\n", "\n"), None, time.time() - t0


def run_level(name, n, only=None, solver=None, timeout=180):
    """Run the solver on every input in parallel. Returns (ok_all, list of fileIds produced)."""
    d = level_dir(name, n)
    if not (d / "map.json").exists():
        die(f"level {n} not fetched: run `fetch {n}`")
    (d / "out").mkdir(exist_ok=True)
    cmd, shell = solver_cmd(d, solver)
    env = solver_env()
    jobs = [(inp, fid) for inp, fid in inputs_of(d) if not only or fid in only or inp.stem in only]

    def one(job):
        inp, fid = job
        out, err, dt = run_solver(cmd, shell, inp, d, env, timeout, fid)
        return inp, fid, out, err, dt

    with cf.ThreadPoolExecutor(max(1, min(len(jobs), os.cpu_count() or 4))) as ex:
        results = list(ex.map(one, jobs))
    checker, ok_all, produced, shown = None, True, [], set()
    try:
        checker = load_checker(d)
    except Exception as e:
        print(f"  (check() in solve.py failed to load: {e})")
    for inp, fid, out, err, dt in results:
        if out is None:
            ok_all = False
            print(f"  {fid}: CRASH ({dt:.1f}s)" + ("  (same error as above)" if err in shown else f"\n{err}"))
            shown.add(err)
            continue
        op = out_path(d, inp)
        op.write_text(out, encoding="utf-8", newline="\n")
        produced.append(fid)
        status = ""
        exp = expected_path(inp)
        if exp:
            want = norm(exp.read_text(encoding="utf-8"))
            match = want == norm(out)
            status = "EXAMPLE OK" if match else "EXAMPLE MISMATCH " + first_diff(want, norm(out))
            if not match and checker is None:
                ok_all = False
        if checker is not None:
            try:
                res = checker(inp.read_text(encoding="utf-8"), out)
                cok, msg = (res if isinstance(res, tuple) else (bool(res), ""))
            except Exception as e:
                cok, msg = False, f"check() raised {e!r}"
            if cok and status.startswith("EXAMPLE MISMATCH"):
                status = "check OK (example output differs; answer not unique)"
                want_raw = exp.read_text(encoding="utf-8").strip().splitlines()
                got_raw = out.strip().splitlines()
                wb, gb = sum(not l.strip() for l in want_raw), sum(not l.strip() for l in got_raw)
                if wb != gb:  # honeycomb L5: blank-line block separators missing -> server saw no cases
                    ok_all = False
                    status += (f"  BUT SHAPE DIFFERS: example output has {wb} blank separator lines, yours {gb}"
                               f" -> fix the format (or --force)")
                elif len(want_raw) != len(got_raw):
                    status += f"  (note: {len(got_raw)} lines vs example {len(want_raw)})"
            else:
                status += f"  check:{'OK' if cok else 'FAIL ' + str(msg)[:200]}"
            ok_all &= bool(cok)
        print(f"  {fid}: {dt:.1f}s  {status}".rstrip())
    return ok_all, produced


def cmd_run(a):
    name, _, _ = active_run()
    ok, _ = run_level(name, a.level, a.only, a.solver, a.timeout)
    print("ALL OK" if ok else "NOT OK")


def cmd_probe(a):
    """Time the k largest cases of the largest input (lib.runner CCC_PROBE) and extrapolate. Never writes outputs."""
    name, _, _ = active_run()
    d = level_dir(name, a.level)
    if not (d / "map.json").exists():
        die(f"level {a.level} not fetched: run `fetch {a.level}`")
    inp, fid = max(inputs_of(d), key=lambda j: j[0].stat().st_size)
    cmd, shell = solver_cmd(d, a.solver)
    sp = next((Path(c) for c in (cmd if isinstance(cmd, list) else cmd.split()) if str(c).endswith(".py")), d / "solve.py")
    src = sp.read_text(encoding="utf-8", errors="replace") if sp.exists() else ""
    uses_runner = "run_cases" in src
    print(f"probe {fid} ({inp.stat().st_size / 1e6:.2f} MB), {a.k} sampled cases (largest + random), 20 s budget"
          + ("" if uses_runner else "  [solve.py does not use lib.runner.run_cases: timing the WHOLE file]"))
    run_solver.last_eta, run_solver.heavy_tail = None, False
    out, err, dt = run_solver(cmd, shell, inp, d, solver_env({"CCC_PROBE": str(a.k)}), a.timeout, fid)
    if out is None:
        print(f"  {fid}: {err}")
        print("VERDICT: TOO SLOW or CRASH -> change the algorithm (or fix the crash) before a full run")
        return
    eta = run_solver.last_eta if uses_runner else dt
    print(f"  probe wall {dt:.1f}s")
    if eta is None:
        return
    pypy = "ccc: pypy" in src.split("\n", 1)[0] or os.environ.get("CCC_PY") == "pypy"
    if uses_runner and getattr(run_solver, "heavy_tail", False):
        v = ("HEAVY TAIL: some sampled cases did not finish in 20 s -> change the formulation "
             "(exact model: flow/min-cut, CP-SAT, DP) or a restart portfolio; a longer timeout will not help")
    elif eta < 60:
        v = "OK: full run"
    elif eta < 300:
        v = f"SLOW but feasible: go {a.level} --timeout {int(eta * 1.5) + 30}" + ("" if pypy else "  (or add `# ccc: pypy`: 10-60x)")
    else:
        v = "TOO SLOW: change the algorithm/heuristic" + ("" if pypy else " or add `# ccc: pypy`")
    print(f"VERDICT: {v}  (ETA {eta:.0f}s for {fid})")


def verdict_line(status, body):
    ev = body.get("evaluation") if isinstance(body, dict) else None
    if not ev:
        return f"HTTP {status} {json.dumps(body)[:300]}"
    cases = ev.get("cases") or []
    bad = [c for c in cases if not c.get("isCorrect")]
    s = f"{'CORRECT' if ev.get('isCorrect') else 'WRONG'} {len(cases) - len(bad)}/{len(cases)}"
    extra = {k: v for k, v in ev.items() if k not in ("isCorrect", "cases")}
    scores = [c["optimizationScore"] for c in cases if c.get("optimizationScore") is not None]
    if scores:
        s += f" score={sum(scores)}"
    if extra:
        s += f" {json.dumps(extra)[:200]}"
    for c in bad[:3]:
        el = c.get("errorLineNumber")
        s += (f"\n      lines {c.get('startLineNumber')}-{c.get('endLineNumberExcl')}: {c.get('caseState')} "
              f"{c.get('caseMessage') or ''}{f' (error at line {el})' if el is not None else ''}")
    if len(bad) > 3:
        s += f"\n      ... {len(bad) - 3} more failing cases"
    return s


def submit_one(ctx, n, fid, path):
    if ctx[1].get("offlineGame"):
        return offline_judge(ctx, n, fid, path)
    for _ in range(6):
        r = game_req("POST", f"/api/contestant/submit-{n}-{fid}", ctx,
                     files={"solution": (path.name, path.read_bytes(), "text/plain")})
        if r.status_code == 429:
            try:
                wait = float(r.json().get("cooldownSec") or 0)
            except Exception:
                wait = float(r.headers.get("Retry-After") or 5)
            time.sleep(max(wait, 1) + 0.3)
            continue
        break
    try:
        body = r.json()
    except ValueError:
        body = r.text[:300]
    return fid, r.status_code, body


def submit_level(ctx, n, fids, optimization=False, stop_on_wrong=True):
    """Submit fileIds SEQUENTIALLY and return the server score state from the last response.

    Smallest file first; stops at the first non-CORRECT file (big files take ~16 s/MB to grade server-side).
    Never submit in parallel: the game engine loses updates on concurrent submits (tested 2026-10-09: 5 parallel
    CORRECT verdicts, only 2 recorded). Each response carries the cumulative score, so the last one is the truth;
    a CORRECT file missing from it (e.g. a teammate submitted at the same moment) is re-submitted once."""
    d = level_dir(ctx[0], n)
    paths = {fid: out_path(d, inp) for inp, fid in inputs_of(d)}
    todo = sorted((f for f in fids if paths.get(f) and paths[f].exists()), key=lambda f: paths[f].stat().st_size)
    for f in fids:
        if f not in todo:
            print(f"  {f}: no output file, skipped")
    score, log, correct = None, {}, set()
    for rnd in range(2):
        for i, f in enumerate(todo):
            fid, status, body = submit_one(ctx, n, f, paths[f])
            if rnd == 0:
                print(f"  {fid}: {verdict_line(status, body)}")
            ev = body.get("evaluation") if isinstance(body, dict) else None
            if ev:
                log[fid] = {"correct": ev.get("isCorrect"), "bad": [c for c in ev.get("cases") or [] if not c.get("isCorrect")][:20]}
                if ev.get("isCorrect"):
                    correct.add(fid)
            else:
                log[fid] = body
            if isinstance(body, dict) and body.get("score"):
                score = body["score"]
            if stop_on_wrong and not (ev and ev.get("isCorrect")) and todo[i + 1:]:
                print(f"  stopped at first failure; not submitted: {todo[i + 1:]} (submit --only ... to force)")
                break
        lost = sorted(correct - passed_files(score, n)[0]) if score and not optimization else []
        if not lost:
            break
        print(f"  CORRECT but not recorded by the server (concurrent submit?): {lost} -> re-submitting")
        todo = lost
    with (d / "submissions.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.time(), "results": log}) + "\n")
    return score


def cmd_submit(a):
    ctx = active_run()
    d = level_dir(ctx[0], a.level)
    m = load_json(d / "map.json", {"scoredFiles": [], "unscoredFiles": []})
    fids = a.only or [f for f in m["scoredFiles"]] + (m["unscoredFiles"] if a.include_example else [])
    sc = submit_level(ctx, a.level, fids, level_meta(game_info(ctx), a.level).get("optimization", False), stop_on_wrong=not a.only)
    ok, at = passed_files(sc, a.level)
    print(f"level {a.level}: {'PASSED' if at else f'{len(ok)} files passed'}")


def cmd_go(a):
    ctx = active_run()
    name, n = ctx[0], a.level
    with cf.ThreadPoolExecutor(1) as ex:
        f_info = ex.submit(contestant_info, ctx)  # overlaps with the solver run
        ok, produced = run_level(name, n, solver=a.solver, timeout=a.timeout)
        info = f_info.result()
    if not ok and not a.force:
        die("Example mismatch / check failed / crash: NOT submitted (fix solve.py, or --force).", 1)
    m = load_json(level_dir(name, n) / "map.json", {"scoredFiles": []})
    done, at = passed_files(info.get("score"), n)
    todo = [f for f in m["scoredFiles"] if f not in done and f in produced]
    if done:
        print(f"  already passed (skipped): {sorted(done)}")
    gi = game_info(ctx)
    total = total_levels(gi)
    sc = submit_level(ctx, n, todo, level_meta(gi, n).get("optimization", False)) if todo else info.get("score")
    sc = sc or info.get("score")
    ok_files, at = passed_files(sc, n)
    level_now = ((sc or {}).get("gameScore") or {}).get("level")
    if at or (level_now or 0) > n:
        print(f"LEVEL {n} PASSED  (unlocked level {level_now}/{total})  [{time.time() - T0:.1f}s]")
        if not ctx[1].get("offlineGame") and todo:
            log_timing(name, "pass", n)
        if total and n >= total:
            print("ALL LEVELS DONE.")
        elif (level_dir(name, n + 1) / "map.json").exists():
            print(f"level {n + 1} already fetched: {level_dir(name, n + 1) / 'statement.txt'}")
        elif not a.no_next:
            fetch_level(ctx, n + 1, retry_s=20)
    else:
        missing = [f for f in m["scoredFiles"] if f not in ok_files]
        print(f"LEVEL {n} NOT PASSED: failing {missing}. Fix solve.py, then `go {n}` again (passed files are skipped).")


def cmd_api(a):
    path = a.path.replace("\\", "/")
    i = max(path.find("/api/"), path.find("/game/"))
    path = path[i:] if i >= 0 else "/" + path.lstrip("/")  # undo Git Bash path mangling (C:/Program Files/Git/api/...)
    r = game_req(a.method, path, active_run()) if a.game else plat(a.method, path)
    print(r.status_code, r.headers.get("content-type"))
    print(r.text[:5000])


def main():
    ap = argparse.ArgumentParser(description="CCC arena CLI")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("login"); p.add_argument("--http", action="store_true"); p.set_defaults(f=cmd_login)
    sp.add_parser("games").set_defaults(f=cmd_games)
    p = sp.add_parser("train"); p.add_argument("slug"); p.add_argument("--mode", default="exploration", choices=["exploration", "challenge"]); p.add_argument("--name"); p.set_defaults(f=cmd_train)
    for nm, fn in (("contest", cmd_contest), ("wait", cmd_wait)):
        p = sp.add_parser(nm); p.add_argument("contest_name", nargs="?", default=CONTEST); p.add_argument("--name", default="contest"); p.set_defaults(f=fn)
    p = sp.add_parser("use"); p.add_argument("name"); p.set_defaults(f=cmd_use)
    p = sp.add_parser("info"); p.add_argument("--raw", action="store_true"); p.set_defaults(f=cmd_info)
    p = sp.add_parser("fetch"); p.add_argument("level", type=int); p.add_argument("--png", action="store_true"); p.add_argument("--scale", type=float, default=0.75); p.add_argument("--zip", help="ingest a manually downloaded level zip (emergency, no download API)"); p.set_defaults(f=cmd_fetch)
    for nm, fn in (("run", cmd_run), ("submit", cmd_submit), ("go", cmd_go)):
        p = sp.add_parser(nm); p.add_argument("level", type=int)
        if nm != "submit":
            p.add_argument("--timeout", type=int, default=180)
            p.add_argument("--solver", help="solver .py path or shell command (default levelN/solve.py)")
        if nm != "go":
            p.add_argument("--only", nargs="*")
        if nm == "submit":
            p.add_argument("--include-example", action="store_true")
        if nm == "go":
            p.add_argument("--force", action="store_true")
            p.add_argument("--no-next", action="store_true")
        p.set_defaults(f=fn)
    p = sp.add_parser("probe"); p.add_argument("level", type=int); p.add_argument("k", type=int, nargs="?", default=os.cpu_count() or 8); p.add_argument("--timeout", type=int, default=45); p.add_argument("--solver"); p.set_defaults(f=cmd_probe)
    p = sp.add_parser("api"); p.add_argument("method"); p.add_argument("path"); p.add_argument("--game", action="store_true"); p.set_defaults(f=cmd_api)
    a = ap.parse_args()
    try:
        a.f(a)
    except KeyboardInterrupt:
        die("interrupted", 130)
    except OSError as e:
        if getattr(e, "errno", None) in (22, 32):  # stdout closed (e.g. piped into head)
            os._exit(0)
        raise


if __name__ == "__main__":
    main()
