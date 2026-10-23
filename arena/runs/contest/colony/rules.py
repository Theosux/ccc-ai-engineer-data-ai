"""Full Colony: One rules (levels 2+): bodyguard, firewall, kernel endgame.
State: (board, team_to_move, actions_left, round). board: dict (r,c)->(team,piece)."""
from engine import K8, ORTH, DIAG, sq, parse_render
FW_ROUNDS = {8: 1, 16: 2, 24: 3, 26: 4}
OPP = {"C": "M", "M": "C"}


def fw_level(rnd):
    """rings removed before round rnd is played"""
    return sum(1 for k in FW_ROUNDS if k < rnd)


def ring(q):
    r, c = q
    return min(r, c, 7 - r, 7 - c)


def alive_sq(q, f):
    return 0 <= q[0] < 8 and 0 <= q[1] < 8 and ring(q) >= f


def kernel(b, team):
    for q, (t, p) in b.items():
        if t == team and p == "K":
            return q
    return None


def actions(b, team, f):
    out = []
    for (r, c), (t, p) in b.items():
        if t != team:
            continue
        if p == "K":
            for dr, dc in K8:
                q = (r + dr, c + dc)
                if alive_sq(q, f) and (q not in b or b[q][0] != team):
                    out.append(((r, c), q))
        elif p == "P":
            for dr, dc in ORTH:
                for k in (1, 2):
                    q = (r + dr * k, c + dc * k)
                    if not alive_sq(q, f) or q in b:
                        break
                    out.append(((r, c), q))
            for dr, dc in DIAG:
                for k in (1, 2):
                    q = (r + dr * k, c + dc * k)
                    if not alive_sq(q, f):
                        break
                    if q in b:
                        if b[q][0] != team:
                            out.append(((r, c), q))
                        break
    return out


def guards(b, q):
    t = b[q][0]
    return [(q[0] + dr, q[1] + dc) for dr, dc in K8 if b.get((q[0] + dr, q[1] + dc), ("", ""))[0] == t]


def apply(b, a):
    """returns new board (attack resolution incl. bodyguard)"""
    f, t = a
    nb = dict(b)
    if t in nb and nb[t][1] == "K":
        g = guards(nb, t)
        if g:
            del nb[sorted(g)[0]]   # which guard dies if several: unknown, pick first
            return nb
    nb[t] = nb.pop(f)
    return nb


def end_turn(b, team, rnd):
    """after `team` finished its turn. returns (board, winner or None)"""
    ck, mk = kernel(b, "C"), kernel(b, "M")
    if ck is None:
        return b, "M"
    if mk is None:
        return b, "C"
    if team == "M" and rnd in FW_ROUNDS:
        f = FW_ROUNDS[rnd]
        b = {q: v for q, v in b.items() if ring(q) >= f}
        ck, mk = kernel(b, "C"), kernel(b, "M")
        if ck is None:
            return b, "M"
        if mk is None:
            return b, "C"
    if len(b) == 2:
        d = max(abs(ck[0] - mk[0]), abs(ck[1] - mk[1]))
        if d <= 2:
            return b, OPP[team]
        rc, rm = ring(ck), ring(mk)
        return b, ("C" if rc > rm else "M")
    if team == "M" and rnd >= 26:
        return b, "M"
    return b, None


def turns(b, team, rnd):
    """all distinct results of a full 2-action turn: list of (actions, board, winner)"""
    f = fw_level(rnd)
    seen = {}
    for a1 in actions(b, team, f):
        b1 = apply(b, a1)
        if kernel(b1, OPP[team]) is None:
            key = frozenset(b1.items())
            seen.setdefault(key, ([a1], b1, team))
            continue
        for a2 in actions(b1, team, f):
            b2 = apply(b1, a2)
            key = frozenset(b2.items())
            if key in seen:
                continue
            b3, w = end_turn(b2, team, rnd)
            seen[key] = ([a1, a2], b3, w)
    return list(seen.values())
