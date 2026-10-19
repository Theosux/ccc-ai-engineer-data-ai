#!/usr/bin/env python3
"""Contest go-live automation: log in, detect "live" with several independent detectors, land on level 1.

  python arena/golive.py                    # preflight, then watch 42nd DATA/AI until live, register + fetch level 1
  python arena/golive.py --preflight        # checks only (all must be OK before the contest)
  python arena/golive.py --browser          # + D6: an Edge window on the contest page that logs what the real UI does
  python arena/golive.py --contest <slug>   # any contest, e.g. a Challenge-mode training (rehearsal)
  python arena/golive.py --observe school   # read-only: record the #school go-live (08:00 UTC) without triggering

Detectors (threads; first one wins, then the contest API is re-checked once):
  D1 contest API poll   adaptive: 240s far away, 15s from T-15min, 1s from T-90s
  D2 SSE status stream  /api/contests/status/stream -> any event pokes D1 immediately
  D3 my-registrations   DATA/AI entry status
  D4 level-1 probe      once a game URL is known: GET <game>/api/contestant/level/1/files every 3s from T-3min
                        (200 = live). NOTE: /api/game-token is issued even days BEFORE the start, so a token is no signal.
  D5 server clock       at T0 force 1s polling + token probe (built into D1/D4 scheduling)
  D6 browser witness    optional, captures the game iframe URL + every /api call of the real UI
Everything raw goes to arena/runs/<name>/golive-log.jsonl (tokens are never logged).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ccc  # noqa: E402

LIVE_STATUSES = {"RUNNING", "STATS_FROZEN"}
DONE_STATUSES = {"FINISHED"}


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() if s else None


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%H:%M:%S")


def game_assigned(c):
    return bool(c.get("gameBaseUrl")) and c.get("gameSlug") not in (None, "", "unknown-game")


def is_live(c):
    return c.get("status") in LIVE_STATUSES


def sanitize(o):
    if isinstance(o, dict):
        return {k: ("<redacted>" if "token" in k.lower() or k.lower() in ("password", "authorization") else sanitize(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [sanitize(v) for v in o[:50]]
    return o


# ---------------------------------------------------------------- transport (real); tests swap in a fake
class RealTransport:
    def __init__(self):
        self.relogin_lock = threading.Lock()

    def _call(self, method, path, **kw):
        s = ccc.platform_session()
        r = ccc.req(method, ccc.BASE + path, session=s, tries=2, timeout=kw.pop("timeout", 20), **kw)
        if r.status_code == 401:
            with self.relogin_lock:  # one re-login for all threads; later threads find fresh cookies
                r2 = ccc.req(method, ccc.BASE + path, session=ccc.platform_session(), tries=1, timeout=20, **kw)
                if r2.status_code != 401:
                    return r2
                if all(ccc.read_creds()):
                    ccc.http_login()
            r = ccc.req(method, ccc.BASE + path, session=ccc.platform_session(), tries=2, timeout=20, **kw)
        return r

    @staticmethod
    def _json(r):
        try:
            return r.json()
        except ValueError:
            return {"_text": r.text[:300]}

    def contest(self, slug):
        r = self._call("GET", f"/api/contests/{slug}")
        return r.status_code, self._json(r)

    def registrations(self):
        r = self._call("GET", "/api/contests/my-registrations")
        return r.status_code, self._json(r)

    def token(self, slug):
        r = self._call("POST", "/api/game-token", json={"contestSlug": slug})
        return r.status_code, self._json(r)

    def level1(self, gbu, token, slug):
        """Probe the game API: can level 1 be downloaded? Body is not read beyond a peek."""
        origin = gbu.rstrip("/")
        h = {"Authorization": token, "X-CCC-SLUG": slug, "Referer": origin + "/", "Origin": origin,
             "Sec-Fetch-Site": "same-origin", "User-Agent": ccc.UA}
        r = ccc.req("GET", origin + "/api/contestant/level/1/files", tries=1, timeout=20, headers=h, stream=True)
        try:
            peek = "" if r.status_code == 200 else r.raw.read(300, decode_content=True).decode("utf-8", "replace")
        finally:
            r.close()
        return r.status_code, peek

    def user(self):
        r = self._call("GET", "/api/auth/current-user")
        return r.status_code, self._json(r)

    def sse(self, stop):
        s = ccc.platform_session()
        s.headers["Accept"] = "text/event-stream"
        with s.get(ccc.BASE + "/api/contests/status/stream", stream=True, timeout=(10, 120)) as r:
            if r.status_code != 200:
                raise RuntimeError(f"SSE HTTP {r.status_code}")
            ev, data = None, []
            for line in r.iter_lines(decode_unicode=True):
                if stop.is_set():
                    return
                if line is None:
                    continue
                if line == "":
                    if ev or data:
                        yield ev or "message", "\n".join(data)
                    ev, data = None, []
                elif line.startswith("event:"):
                    ev = line[6:].strip()
                elif line.startswith("data:"):
                    data.append(line[5:].strip())


# ---------------------------------------------------------------- watcher
class Watcher:
    def __init__(self, slug, transport, log_path, observe=False, interval_fn=None, token_window=180,
                 regs=True, sse=True, browser=False, sleep=time.sleep, quiet=False, probe_every=3):
        self.slug, self.t, self.observe = slug, transport, observe
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.interval_fn = interval_fn or self.default_interval
        self.token_window, self.use_regs, self.use_sse, self.use_browser = token_window, regs, sse, browser
        self.sleep, self.quiet, self.probe_every = sleep, quiet, probe_every
        self.lock = threading.Lock()
        self.fired = threading.Event()
        self.stop = threading.Event()
        self.poke = threading.Event()
        self.first = None
        self.start_ts = None          # contest start (epoch s)
        self.offset = 0.0             # server - local seconds
        self.last = {}                # last contest JSON
        self.contest_id = None
        self.timeline = []            # distinct (status, game) changes
        self.hints = {}               # e.g. gameBaseUrl seen by the browser
        self.errors = {}

    # -- helpers
    def now(self):
        return time.time() + self.offset

    def left(self):
        return None if self.start_ts is None else self.start_ts - self.now()

    @staticmethod
    def default_interval(left):
        if left is None:
            return 5
        if left > 900:
            return min(240, left - 900)
        if left > 90:
            return min(15, left - 90) or 1
        if left > -900:
            return 1
        return 3

    def log(self, det, event, data=None):
        rec = {"t": round(time.time(), 3), "server": round(self.now(), 3), "det": det, "event": event}
        if data is not None:
            rec["data"] = sanitize(data)
        with self.lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def say(self, msg):
        if not self.quiet:
            print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    def signal(self, det, why, info=None):
        with self.lock:
            if self.fired.is_set():
                return
            self.first = {"det": det, "why": why, "info": info or {}, "at": time.time()}
            self.fired.set()
        self.log(det, "SIGNAL", {"why": why})
        self.say(f">>> {det} says LIVE: {why}")
        self.poke.set()

    def err(self, det, e):
        n = self.errors[det] = self.errors.get(det, 0) + 1
        self.log(det, "error", {"err": repr(e)[:300], "n": n})
        if n in (1, 5, 20) or n % 100 == 0:
            self.say(f"{det}: error #{n}: {repr(e)[:160]}")
        lf = self.left()
        cap = 1 if lf is None or abs(lf) < 900 else 30  # never back off for long around the start
        return min(cap, 2 ** min(n - 1, 5))

    def wait(self, sec):
        """Sleep that wakes early on poke/stop."""
        self.poke.wait(timeout=max(0.05, sec))
        self.poke.clear()

    # -- D1 contest poll (+ D5 clock scheduling)
    def update_contest(self, c, rtt):
        if c.get("serverNowMs"):
            self.offset = c["serverNowMs"] / 1000 - (time.time() - rtt / 2)
        if c.get("startTime"):
            self.start_ts = parse_ts(c["startTime"])
        self.contest_id = c.get("id") or c.get("contestId") or self.contest_id
        key = (c.get("status"), c.get("gameSlug"), bool(c.get("gameBaseUrl")))
        if not self.timeline or self.timeline[-1]["key"] != list(key):
            self.timeline.append({"key": list(key), "server": utc(self.now()), "left": self.left()})
            self.log("D1", "CHANGE", {k: c.get(k) for k in ("status", "gameSlug", "gameBaseUrl", "gameName",
                                                            "startTime", "durationMinutes")})
            lf = self.left()
            self.say(f"D1: status={key[0]} game={key[1]} url={'yes' if key[2] else 'no'}"
                     + (f"  (T{'-' if lf > 0 else '+'}{ccc.hms(abs(lf))})" if lf is not None else ""))
            if game_assigned(c) and not is_live(c):
                self.say(f"D1: game assigned before start: {c.get('gameName')} ({c.get('gameBaseUrl')})")
        self.last = c

    def d1(self):
        while not self.stop.is_set():
            try:
                t0 = time.time()
                code, c = self.t.contest(self.slug)
                rtt = time.time() - t0
                if code == 200 and isinstance(c, dict):
                    self.update_contest(c, rtt)
                    if is_live(c):
                        self.signal("D1", f"status {c.get('status')}")
                    elif game_assigned(c) and self.left() is not None and self.left() <= 0:
                        self.signal("D1", "start time passed and game assigned")
                    if c.get("status") in DONE_STATUSES:
                        self.say("D1: contest FINISHED")
                else:
                    self.log("D1", "http", {"code": code, "body": c})
                    self.wait(self.err("D1", f"HTTP {code}"))
                    continue
                self.errors.pop("D1", None)
            except BaseException as e:  # SystemExit from ccc.die on network errors must not kill the watcher
                if isinstance(e, KeyboardInterrupt):
                    raise
                self.wait(self.err("D1", e))
                continue
            iv = 1 if (self.fired.is_set() and self.observe) else self.interval_fn(self.left())
            self.wait(iv)

    # -- D2 SSE
    def d2(self):
        while not self.stop.is_set():
            try:
                self.log("D2", "connect")
                for ev, data in self.t.sse(self.stop):
                    self.log("D2", "event", {"event": ev, "data": data[:500]})
                    if self.slug in data or (self.contest_id is not None and str(self.contest_id) in data):
                        if any(s in data for s in LIVE_STATUSES):
                            self.signal("D2", f"status stream: {data[:120]}")
                    self.poke.set()  # any status event -> D1 re-checks immediately
                    if self.stop.is_set():
                        return
                self.log("D2", "closed")
                self.wait(2)
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                self.stop.wait(self.err("D2", e))

    # -- D3 registrations
    def d3(self):
        last = None
        while not self.stop.is_set():
            try:
                code, regs = self.t.registrations()
                if code == 200 and isinstance(regs, list):
                    mine = next((r for r in regs if r.get("contestSlug") == self.slug), None)
                    st = mine and mine.get("status")
                    if st != last:
                        self.log("D3", "CHANGE", mine)
                        last = st
                    if st in LIVE_STATUSES:
                        self.signal("D3", f"registration status {st}")
                else:
                    self.log("D3", "http", {"code": code})
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                self.err("D3", e)
            lf = self.left()
            self.stop.wait(5 if lf is not None and lf < 120 else 30)

    # -- D4 level-1 probe (needs a game URL; the game token itself is available before the start)
    def game_url(self):
        c = self.last or {}
        if c.get("gameBaseUrl"):
            return c["gameBaseUrl"]
        if self.hints.get("gameBaseUrl"):
            return self.hints["gameBaseUrl"]
        if c.get("gameSlug") not in (None, "", "unknown-game"):
            return f"https://{c['gameSlug']}.codingcontest.org/"
        return None

    def d4(self):
        last, token = None, None
        while not self.stop.is_set():
            lf = self.left()
            gbu = self.game_url()
            if lf is None or lf > self.token_window or not gbu:
                self.stop.wait(1 if lf is None or lf <= self.token_window else min(30, lf - self.token_window))
                continue
            try:
                if token is None:
                    code, body = self.t.token(self.slug)
                    if code != 200 or not isinstance(body, dict) or not body.get("token"):
                        self.log("D4", "token", {"code": code, "body": body})
                        self.stop.wait(self.err("D4", f"token HTTP {code}"))
                        continue
                    token = body["token"]
                code, peek = self.t.level1(gbu, token, self.slug)
                if code in (401, 403) and "only be accessed" not in str(peek):
                    token = None  # refresh the token next round
                if (code, str(peek)[:120]) != last:
                    self.log("D4", "CHANGE", {"code": code, "peek": peek, "gbu": gbu})
                    self.say(f"D4: level-1 probe HTTP {code} {str(peek)[:100]}")
                    last = (code, str(peek)[:120])
                if code == 200:
                    self.signal("D4", "level 1 is downloadable", {"gameBaseUrl": gbu})
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                self.err("D4", e)
            self.stop.wait(self.probe_every)

    # -- keep-alive
    def keepalive(self):
        while not self.stop.is_set():
            try:
                code, _ = self.t.user()
                self.log("KA", "user", {"code": code})
                if code != 200:
                    self.say(f"KA: session check HTTP {code} (re-login attempted). If this repeats: python arena/ccc.py login")
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                self.err("KA", e)
            self.stop.wait(240)

    # -- D6 browser witness
    def d6(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            self.err("D6", e)
            return
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(str(ccc.AUTH / "edge-profile-golive"), channel="msedge",
                                                           headless=False, viewport=None)
                ctx.add_cookies([{"name": c["name"], "value": c["value"], "domain": c.get("domain") or "codingcontest.org",
                                  "path": c.get("path", "/")} for c in ccc.load_json(ccc.COOKIES, [])])
                page = ctx.pages[0] if ctx.pages else ctx.new_page()

                def on_resp(r):
                    if "/api/" in r.url and "codingcontest.org" in r.url:
                        self.log("D6", "api", {"url": r.url.split("?")[0], "status": r.status, "method": r.request.method})
                        host = r.url.split("/")[2]
                        # the real UI talking to a game host (e.g. spaceship.codingcontest.org/api/contestant/...)
                        if host != "codingcontest.org" and "/api/contestant/" in r.url and r.status == 200:
                            base = "https://" + host + "/"
                            if self.hints.get("gameBaseUrl") != base:
                                self.hints["gameBaseUrl"] = base
                                self.signal("D6", f"real UI is using game API {base}", {"gameBaseUrl": base})
                page.on("response", on_resp)
                url = f"{ccc.BASE}/contests/{self.slug}/game"
                page.goto(url)
                self.log("D6", "open", {"url": url})
                while not self.stop.is_set():
                    for fr in page.frames:
                        u = fr.url or ""
                        host = u.split("/")[2] if u.startswith("http") else ""
                        if host.endswith(".codingcontest.org") and host != "codingcontest.org":
                            base = "https://" + host + "/"
                            if self.hints.get("gameBaseUrl") != base:
                                self.hints["gameBaseUrl"] = base
                                self.log("D6", "iframe", {"gameBaseUrl": base})
                                self.signal("D6", f"real UI loaded the game iframe {base}", {"gameBaseUrl": base})
                    lf = self.left()
                    nap = 60 if lf is None or lf > 300 else 10
                    if not self.hints.get("gameBaseUrl") and (lf is None or lf < 600):
                        page.wait_for_timeout(nap * 1000)
                        if not self.stop.is_set() and not self.hints.get("gameBaseUrl"):
                            page.reload()
                    else:
                        page.wait_for_timeout(nap * 1000)
                    if self.fired.is_set() and not self.observe:
                        page.wait_for_timeout(5000)  # leave the window open a bit for Teo, then stop logging
                        break
                # keep the browser open for Teo's eyes; context closes when the process exits
                while not self.stop.is_set():
                    page.wait_for_timeout(1000)
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            self.err("D6", e)

    # -- run
    def start(self):
        dets = [self.d1, self.d4, self.keepalive]
        if self.use_sse:
            dets.append(self.d2)
        if self.use_regs:
            dets.append(self.d3)
        if self.use_browser:
            dets.append(self.d6)
        if self.observe:  # no token probe / registration for a contest we are not in
            dets = [d for d in dets if d not in (self.d4, self.d3)]
        self.threads = [threading.Thread(target=d, name=d.__name__, daemon=True) for d in dets]
        for th in self.threads:
            th.start()
        self.log("W", "start", {"slug": self.slug, "detectors": [d.__name__ for d in dets], "observe": self.observe})

    def run_until_live(self, timeout=None):
        self.start()
        ok = self.fired.wait(timeout)
        return self.first if ok else None


# ---------------------------------------------------------------- preflight
def preflight(slug):
    res, ok_all = [], True

    def item(ok, name, detail=""):
        nonlocal ok_all
        ok_all &= bool(ok) or ok is None
        mark = "OK  " if ok else ("WARN" if ok is None else "FAIL")
        print(f"  [{mark}] {name}: {detail}", flush=True)
        res.append({"check": name, "ok": ok, "detail": detail})

    print("== Preflight ==", flush=True)
    t = RealTransport()
    try:
        code, u = t.user()
        item(code == 200 and u.get("username"), "login", f"{u.get('username')} roles={u.get('roles')}" if code == 200
             else f"HTTP {code}: run `python arena/ccc.py login`")
    except BaseException as e:
        item(False, "login", repr(e)[:200])
    try:
        code, regs = t.registrations()
        mine = next((r for r in regs if r.get("contestSlug") == slug), None) if code == 200 else None
        others = [r.get("contestSlug") for r in regs if r.get("contestSlug") != slug] if code == 200 else []
        item(bool(mine), "registration", f"{mine.get('contestType')} team={mine.get('teamName')} "
             f"({mine.get('teamMemberCount')}/{mine.get('maxTeamSize')}) venue={mine.get('venueName', '')[:40]} "
             f"{mine.get('venueCity')} online={mine.get('isOnline')}" if mine else f"not registered for {slug}")
        if others:
            item(None, "other registrations (ignored)", ", ".join(others))
    except BaseException as e:
        item(False, "registration", repr(e)[:200])
    try:
        t0 = time.time()
        code, c = t.contest(slug)
        rtt = time.time() - t0
        start = parse_ts(c.get("startTime"))
        off = c["serverNowMs"] / 1000 - (time.time() - rtt / 2) if c.get("serverNowMs") else None
        item(code == 200, "contest", f"{c.get('name')} status={c.get('status')} start={c.get('startTime')} "
             f"({c.get('durationMinutes')} min) game={c.get('gameSlug')}")
        if start and off is not None:
            left = start - (time.time() + off)
            item(True, "countdown", f"T-{ccc.hms(left)} (server clock)" if left > 0 else f"started {ccc.hms(-left)} ago")
        item(abs(off) < 30 if off is not None else None, "clock offset", f"local vs server {off:+.2f}s" if off is not None else "?")
        item(rtt < 2, "API latency", f"{rtt * 1000:.0f} ms")
    except BaseException as e:
        item(False, "contest", repr(e)[:200])
    try:
        code, body = t.token(slug)
        item(code == 200, "game token", "issued (works before the start; D4 probes level 1 once a game URL exists)"
             if code == 200 else f"HTTP {code} {str(body)[:100]}")
    except BaseException as e:
        item(None, "token probe", repr(e)[:200])
    item(ccc.PYPY.exists() or None, "PyPy", str(ccc.PYPY) if ccc.PYPY.exists() else "missing (optional, not needed for ML)")
    try:
        p = subprocess.run([sys.executable, str(ccc.ARENA / "lib" / "tests" / "test_lib.py")], capture_output=True,
                           text=True, timeout=180)
        item(p.returncode == 0, "lib tests", (p.stdout.strip().splitlines() or ["?"])[-1])
    except Exception as e:
        item(False, "lib tests", repr(e)[:200])
    try:
        p = subprocess.run(["git", "push", "--dry-run"], capture_output=True, text=True, timeout=60, cwd=ccc.ARENA.parent)
        item(p.returncode == 0, "git push", "ok" if p.returncode == 0 else p.stderr.strip()[:160])
    except Exception as e:
        item(None, "git push", repr(e)[:200])
    free = shutil.disk_usage(ccc.ARENA).free / 2 ** 30
    item(free > 2, "disk", f"{free:.1f} GB free")
    try:
        import playwright  # noqa: F401
        item(True, "browser fallback", "playwright available (golive --browser / ccc.py login)")
    except ImportError:
        item(None, "browser fallback", "playwright missing")
    out = ccc.run_dir("contest") / "preflight.json"
    ccc.save_json(out, {"t": time.time(), "slug": slug, "ok": ok_all, "checks": res})
    print(f"== Preflight {'ALL OK' if ok_all else 'HAS FAILURES'} (saved {out}) ==", flush=True)
    return ok_all


# ---------------------------------------------------------------- trigger
FALLBACKS = """
FALLBACK LADDER (docs/strategy/contest-day-runbook.md):
  * 401 / not logged in      -> python arena/ccc.py login --http ; else python arena/ccc.py login (Edge)
  * live but no game URL     -> rerun with --browser (D6 reads the real game iframe), or open the contest in Opera GX
  * game token refused (403) -> open the contest page in Opera GX (check-in / accept terms?), then rerun golive
  * zip download fails       -> download level zip in Opera GX, then: python arena/ccc.py fetch N --zip <path>
  * submit fails             -> drag & drop arena/runs/contest/levelN/out/* into the platform's Solutions panel
  * venue Wi-Fi down         -> phone hotspot; nothing to reconfigure
"""


def alert(title, msg):
    print("\n" + "#" * 70 + f"\n#  {title}\n#  {msg}\n" + "#" * 70 + "\n", flush=True)
    try:
        import winsound
        for f in (880, 1175, 1568):
            winsound.Beep(f, 180)
    except Exception:
        pass
    ps = ("[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
          "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
          f"$t=$x.GetElementsByTagName('text');$t.Item(0).AppendChild($x.CreateTextNode('{title}'))|Out-Null;"
          f"$t.Item(1).AppendChild($x.CreateTextNode('{msg}'))|Out-Null;"
          "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('PowerShell').Show([Windows.UI.Notifications.ToastNotification]::new($x))")
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def trigger(w, slug, name, fetch=True):
    first = w.first or {}
    deadline = time.time() + 120
    ctx, c = None, w.last or {}
    while time.time() < deadline:
        code, c2 = w.t.contest(slug)
        if code == 200 and isinstance(c2, dict):
            c = c2
        gbu = c.get("gameBaseUrl") or w.hints.get("gameBaseUrl") or first.get("info", {}).get("gameBaseUrl")
        if not gbu and c.get("gameSlug") not in (None, "", "unknown-game"):
            gbu = f"https://{c['gameSlug']}.codingcontest.org/"
            print(f"(no gameBaseUrl in API; trying derived {gbu})", flush=True)
        if gbu:
            c = {**c, "gameBaseUrl": gbu}
            try:
                ctx = ccc.register_run(name, slug, {}, c=c)
                break
            except SystemExit:
                pass
        w.log("T", "register-retry", {"status": c.get("status"), "gbu": bool(gbu)})
        print(f"[{time.strftime('%H:%M:%S')}] not ready yet (status={c.get('status')} game url={'yes' if gbu else 'no'}); retry in 2s",
              flush=True)
        time.sleep(2)
    if ctx is None:
        print("COULD NOT REGISTER THE RUN WITHIN 120s." + FALLBACKS, flush=True)
        return False
    live_txt = ccc.run_dir(name) / "LIVE.txt"
    live_txt.write_text(f"live detected {datetime.now().isoformat()} by {first.get('det')}: {first.get('why')}\n"
                        f"game {c.get('gameName')} {c.get('gameBaseUrl')}\n", encoding="utf-8")
    w.log("T", "registered", {"game": c.get("gameName"), "gbu": c.get("gameBaseUrl"), "first": first.get("det")})
    alert("CCC IS LIVE", f"{c.get('gameName') or 'game'}: level 1 incoming (detected by {first.get('det')})")
    if fetch:
        os.environ["CCC_RUN"] = name
        try:
            ccc.fetch_level(ctx, 1, retry_s=120)
        except SystemExit:
            print("LEVEL 1 FETCH FAILED." + FALLBACKS, flush=True)
            return False
    return True


# ---------------------------------------------------------------- main
def resolve_school():
    r = RealTransport()._call("GET", "/api/editions/active")
    ed = r.json() if r.ok else {}
    found = []

    def walk(o):
        if isinstance(o, dict):
            slug = o.get("slug") or o.get("contestSlug") or ""
            if isinstance(slug, str) and "school" in slug.lower():
                found.append(slug)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(ed)
    if found:
        return found[0]
    ccc.die(f"could not find the #school contest in /api/editions/active (HTTP {r.status_code})")


def sleep_until(hhmmz):
    hh, mm = map(int, hhmmz.rstrip("Zz").split(":"))
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    sec = (target - now).total_seconds()
    if sec > 0:
        print(f"sleeping {ccc.hms(sec)} until {hhmmz} UTC", flush=True)
        time.sleep(sec)


def main():
    ap = argparse.ArgumentParser(description="CCC go-live automation")
    ap.add_argument("--contest", default=ccc.CONTEST)
    ap.add_argument("--name", default="contest", help="run name for arena/runs/<name>")
    ap.add_argument("--preflight", action="store_true", help="checks only")
    ap.add_argument("--no-preflight", action="store_true")
    ap.add_argument("--browser", action="store_true", help="also open the contest page in Edge (D6 witness)")
    ap.add_argument("--observe", metavar="SLUG|school", help="read-only recording of another contest's go-live")
    ap.add_argument("--minutes", type=float, default=10, help="observe: keep recording this long after live")
    ap.add_argument("--from", dest="from_", metavar="HH:MMZ", help="sleep until this UTC time first")
    ap.add_argument("--no-fetch", action="store_true", help="register the run but do not fetch level 1")
    a = ap.parse_args()

    if a.from_:
        sleep_until(a.from_)
    if a.observe:
        slug = resolve_school() if a.observe == "school" else a.observe
        w = Watcher(slug, RealTransport(), ccc.run_dir("observe") / f"{slug}.jsonl", observe=True, regs=False,
                    browser=a.browser)
        print(f"OBSERVING {slug} (read-only). Log: {w.log_path}", flush=True)
        w.run_until_live()
        print(f"live seen by {w.first['det']}; recording {a.minutes} more minutes...", flush=True)
        time.sleep(a.minutes * 60)
        w.stop.set()
        print("TIMELINE (server UTC):")
        for e in w.timeline:
            print(f"  {e['server']}  status={e['key'][0]}  game={e['key'][1]}  url={e['key'][2]}  left={e['left']}")
        return

    if not a.no_preflight:
        ok = preflight(a.contest)
        if a.preflight:
            sys.exit(0 if ok else 1)
        if not ok:
            print("Preflight has failures; continuing to watch anyway (fix them now)." + FALLBACKS, flush=True)
    w = Watcher(a.contest, RealTransport(), ccc.run_dir(a.name) / "golive-log.jsonl", browser=a.browser)
    print(f"WATCHING {a.contest} -> run '{a.name}'. Ctrl+C to abort. Log: {w.log_path}", flush=True)
    first = w.run_until_live()
    ok = trigger(w, a.contest, a.name, fetch=not a.no_fetch)
    w.stop.set()
    if a.browser:
        print("(browser window stays open until you close this process)", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
