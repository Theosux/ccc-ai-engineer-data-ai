import sys, re, time, json, capi
import rules as R
from engine import sq, parse_render
INF = 10 ** 6


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def can_win(b, team, rnd):
    return any(w == team for _, _, w in R.turns(b, team, rnd))


def h(b, rnd):
    ck, mk = R.kernel(b, "C"), R.kernel(b, "M")
    s = -3 * R.ring(mk) - abs(cheb(ck, mk) - 3)
    for q, (t, p) in b.items():
        if t == "C" and p != "K":
            s -= 0.5 * cheb(q, mk)
        if t == "M" and p != "K":
            s -= 5
        if t == "C" and p != "K":
            s += 5
    return s


def choose(b, rnd):
    best, bv = None, -INF - 1
    for acts, b1, w in R.turns(b, "C", rnd):
        if w == "C":
            return acts, INF
        if w == "M":
            v = -INF
        else:
            v = INF
            for _, b2, w2 in R.turns(b1, "M", rnd):
                if w2 == "M":
                    v = -INF
                elif w2 == "C":
                    continue
                elif can_win(b2, "C", rnd + 1):
                    v = min(v, INF // 2)
                else:
                    v = min(v, h(b2, rnd + 1))
                if v <= bv:
                    break
        if v > bv:
            best, bv = acts, v
    return best, bv


def parse_sq(s):
    return (8 - int(s[1]), ord(s[0]) - 65)


def to_index(st, a):
    f, t = sq(a[0]), sq(a[1])
    for x in st["legal_actions"]:
        m = re.findall(r"[A-H][1-8]", x["notation"])
        if m[:1] == [f] and m[-1:] == [t]:
            return x["index"]
    raise RuntimeError(f"no legal action {f}->{t} in {[x['notation'] for x in st['legal_actions']]}")


def play(scene, log=print):
    st = capi.new_game(scene)["state"]
    gid = st["game_id"]
    while not st["terminated"]:
        b = parse_render(st["render"])
        rnd = st["round_number"]
        mine = sorted((sq(f), sq(t)) for f, t in R.actions(b, "C", R.fw_level(rnd)))
        srv = sorted(tuple(re.findall(r"[A-H][1-8]", x["notation"])[i] for i in (0, -1)) for x in st["legal_actions"])
        if mine != srv:
            log(f"!! legal mismatch mine-srv {set(mine)-set(srv)} srv-mine {set(srv)-set(mine)}")
        t0 = time.time()
        acts, v = choose(b, rnd) if st["actions_left"] == 2 else (None, None)
        if acts is None:
            raise RuntimeError("mid-turn state")
        log(f"round {rnd}: play {[sq(a[0])+'-'+sq(a[1]) for a in acts]} v={v} ({time.time()-t0:.1f}s)")
        for a in acts:
            r = capi.move(gid, to_index(st, a))
            st = r.get("state", r)
            if st["terminated"]:
                break
        log(st["render"].splitlines()[-1] + f"  magenta={st.get('magenta_actions')}")
        log("\n".join(st["render"].splitlines()[:9]))
    log(json.dumps({k: v for k, v in st.items() if k in ("winner", "victory", "password", "round_number")}))
    return st


if __name__ == "__main__":
    play(sys.argv[1])
