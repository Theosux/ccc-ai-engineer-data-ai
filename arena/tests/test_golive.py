"""Offline fixture tests for arena/golive.py: replay go-live sequences through a fake transport.

  python arena/tests/test_golive.py
"""
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ccc  # noqa: E402
import golive  # noqa: E402

SLUG = "42nd-data-ai-ccc-5873"
FAST = lambda left: 0.03  # noqa: E731


def contest(status="OPEN_REGISTRATION", start_in=3600, gbu="", game="unknown-game"):
    now = time.time()
    return {"id": 41, "slug": SLUG, "name": "42nd DATA/AI CCC", "status": status, "gameSlug": game, "gameBaseUrl": gbu,
            "gameName": "Game" if gbu else "Unknown Game", "serverNowMs": now * 1000,
            "startTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + start_in)), "durationMinutes": 240}


class Fake:
    """Scripted transport. Each script is a list of callables/values consumed per call; the last one repeats."""

    def __init__(self, contests, regs=None, tokens=None, level1=None, sse=None):
        self.scripts = {"contest": list(contests), "regs": list(regs or [(200, [])]),
                        "token": list(tokens or [(200, {"token": "t"})]), "level1": list(level1 or [(403, "not started")])}
        self.sse_script = sse
        self.calls = {k: 0 for k in self.scripts}
        self.lock = threading.Lock()

    def _next(self, k):
        with self.lock:
            self.calls[k] += 1
            sc = self.scripts[k]
            item = sc.pop(0) if len(sc) > 1 else sc[0]
        item = item() if callable(item) else item
        if isinstance(item, BaseException):
            raise item
        return item

    def contest(self, slug):
        return self._next("contest")

    def registrations(self):
        return self._next("regs")

    def token(self, slug):
        return self._next("token")

    def level1(self, gbu, token, slug):
        return self._next("level1")

    def user(self):
        return 200, {"username": "teosux"}

    def sse(self, stop):
        if self.sse_script is None:
            stop.wait(5)
            return
        for item in self.sse_script():
            if isinstance(item, BaseException):
                raise item
            yield item


def watch(fake, tmp, timeout=5, **kw):
    w = golive.Watcher(SLUG, fake, Path(tmp) / "log.jsonl", interval_fn=FAST, quiet=True, **kw)
    first = w.run_until_live(timeout)
    w.stop.set()
    w.poke.set()
    for th in w.threads:
        th.join(timeout=2)
    return w, first


def t_running_without_then_with_game(tmp):
    f = Fake([(200, contest()), (200, contest(start_in=-1, status="OPEN_REGISTRATION")),
              (200, contest("RUNNING", -2)), (200, contest("RUNNING", -3, "https://g.codingcontest.org/", "g"))])
    w, first = watch(f, tmp, regs=False, sse=False)
    assert first and first["det"] == "D1" and "RUNNING" in first["why"], first
    assert [e["key"][0] for e in w.timeline][:2] == ["OPEN_REGISTRATION", "RUNNING"], w.timeline


def t_survives_401_and_network_errors(tmp):
    f = Fake([(401, {"error": "unauthorized"}), SystemExit(2), ConnectionError("boom"), (200, contest()),
              (200, contest("RUNNING", -1, "https://g.codingcontest.org/", "g"))])
    w, first = watch(f, tmp, regs=False, sse=False)
    assert first and first["det"] == "D1", first
    assert w.errors == {} or "D1" not in w.errors, w.errors  # errors reset after success


def t_sse_disconnect_then_event(tmp):
    state = {"n": 0}

    def sse():
        state["n"] += 1
        if state["n"] == 1:
            yield RuntimeError("SSE dropped")
        yield ("status", '{"contestSlug":"%s","status":"RUNNING"}' % SLUG)

    f = Fake([(200, contest())], sse=sse)
    w, first = watch(f, tmp, regs=False)
    assert first and first["det"] == "D2", first
    assert state["n"] >= 2


def t_level1_probe_fires(tmp):
    # status not live yet, start 60 s away, game slug known (URL derived) -> D4 probes level 1: 403 then 200
    f = Fake([(200, contest(start_in=60, game="spaceship"))], level1=[(403, "not started"), (403, "not started"), (200, "")])
    w, first = watch(f, tmp, regs=False, sse=False, token_window=180, probe_every=0.05)
    assert first and first["det"] == "D4", first
    assert first["info"]["gameBaseUrl"] == "https://spaceship.codingcontest.org/"


def t_token_is_not_a_signal(tmp):
    # token issued days before: D4 must NOT fire without a game URL
    f = Fake([(200, contest(start_in=60))], tokens=[(200, {"token": "t"})], level1=[(200, "")])
    w, first = watch(f, tmp, timeout=0.6, regs=False, sse=False, token_window=180, probe_every=0.05)
    assert first is None, first


def t_registration_status_fires(tmp):
    f = Fake([(200, contest(start_in=30))], regs=[(200, [{"contestSlug": SLUG, "status": "OPEN_REGISTRATION"}]),
                                                (200, [{"contestSlug": SLUG, "status": "RUNNING"}])])
    orig = golive.Watcher.d3

    def fast_d3(self):  # same logic, faster cadence for the test
        last = None
        while not self.stop.is_set():
            code, regs = self.t.registrations()
            mine = next((r for r in regs if r.get("contestSlug") == self.slug), None)
            if mine and mine.get("status") in golive.LIVE_STATUSES:
                self.signal("D3", "registration status RUNNING")
            self.stop.wait(0.05)
    golive.Watcher.d3 = fast_d3
    try:
        w, first = watch(f, tmp, sse=False)
    finally:
        golive.Watcher.d3 = orig
    assert first and first["det"] == "D3", first


def t_observe_skips_token_and_regs(tmp):
    f = Fake([(200, contest()), (200, contest("RUNNING", -1, "https://g.codingcontest.org/", "g"))])
    w, first = watch(f, tmp, observe=True, regs=True, sse=False)
    assert first and first["det"] == "D1"
    names = {th.name for th in w.threads}
    assert "d4" not in names and "d3" not in names, names
    assert f.calls["token"] == 0 and f.calls["regs"] == 0


def t_signal_once(tmp):
    w = golive.Watcher(SLUG, Fake([(200, contest())]), Path(tmp) / "l.jsonl", quiet=True)
    w.signal("D2", "a")
    w.signal("D1", "b")
    assert w.first["det"] == "D2" and w.fired.is_set()


def t_trigger_retries_and_derives_url(tmp):
    calls = {"reg": 0, "fetch": 0, "gbu": None}
    ccc.RUNS = Path(tmp) / "runs"

    def fake_register(name, slug, extra, c=None):
        calls["reg"] += 1
        calls["gbu"] = c.get("gameBaseUrl")
        if calls["reg"] < 3:
            raise SystemExit(2)
        return name, {"gameBaseUrl": c["gameBaseUrl"]}, {}

    o_reg, o_fetch, o_alert, o_sleep = ccc.register_run, ccc.fetch_level, golive.alert, golive.time.sleep
    ccc.register_run = fake_register
    ccc.fetch_level = lambda ctx, n, **kw: calls.__setitem__("fetch", calls["fetch"] + 1)
    golive.alert = lambda *a: None
    golive.time.sleep = lambda s: None
    try:
        f = Fake([(200, contest("RUNNING", -1, "", "spaceship"))])
        w = golive.Watcher(SLUG, f, Path(tmp) / "t.jsonl", quiet=True)
        w.first = {"det": "D1", "why": "status RUNNING", "info": {}}
        ok = golive.trigger(w, SLUG, "contest")
    finally:
        ccc.register_run, ccc.fetch_level, golive.alert, golive.time.sleep = o_reg, o_fetch, o_alert, o_sleep
    assert ok and calls["reg"] == 3 and calls["fetch"] == 1, calls
    assert calls["gbu"] == "https://spaceship.codingcontest.org/", calls
    assert (ccc.RUNS / "contest" / "LIVE.txt").exists()


def t_interval_schedule(tmp):
    iv = golive.Watcher.default_interval
    assert iv(4 * 86400) == 240 and iv(1000) == 100 and iv(600) == 15 and iv(60) == 1 and iv(-60) == 1 and iv(None) == 5


def t_log_redacts_tokens(tmp):
    w = golive.Watcher(SLUG, Fake([(200, contest())]), Path(tmp) / "r.jsonl", quiet=True)
    w.log("X", "e", {"token": "SECRET", "nested": {"Authorization": "SECRET2"}})
    txt = (Path(tmp) / "r.jsonl").read_text()
    assert "SECRET" not in txt, txt


if __name__ == "__main__":
    t0, failed = time.time(), 0
    for name, fn in list(globals().items()):
        if name.startswith("t_") and callable(fn):
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                try:
                    fn(tmp)
                    print(f"ok   {name}")
                except Exception as e:
                    failed += 1
                    print(f"FAIL {name}: {e!r}")
    print(f"{'ALL OK' if not failed else f'{failed} FAILED'} ({time.time() - t0:.1f}s)")
    sys.exit(1 if failed else 0)
