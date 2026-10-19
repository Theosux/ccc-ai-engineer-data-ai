"""Knockout tournaments (power-of-2 brackets): simulate + construct a rigged first-round order.

    beats = {"R": "S", "S": "P", "P": "R"}            # or {style: set_of_beaten_styles} (RPSLS)
    fight = make_fight(beats)                           # fight(a, b) -> winner (equal styles: that style)
    play_round(s, fight) / play_rounds(s, fight, k) / champion(s, fight)
    s = build_bracket({"R": 5, "P": 5, "S": 6}, "S", beats)   # order whose champion is S, or None

build_bracket: round-based. Survivor multisets s_k={W} <= s_{k-1} <= ... <= s_0=counts (|s_t| = n/2^t); round
t's losers s_{t-1}-s_t must be matchable to survivors (x beats-or-ties y; Hall check). DFS picks s_t close to
counts/2^t (proportional), then every survivor x expands to the pair (x, its loser). Exact-ish, fast, any beats table.
build_bracket_halves (fallback): recursive halves. Half A targets the winner W, half B targets some X with W beats X (or X == W);
B soaks up W's enemies that X beats (up to size-1), plus one X, then harmless fillers. Memoized, tries all X and
a few fill orders; the result is always verified by simulation, so None means "heuristic failed" (not proof).
"""


def _norm_beats(beats):
    return {k: set(v) for k, v in beats.items()}  # 'SL' or {'S','L'} both work


def make_fight(beats):
    B = _norm_beats(beats)

    def fight(a, b):
        if a == b or b in B.get(a, ()):
            return a
        if a in B.get(b, ()):
            return b
        raise ValueError(f"no rule for {a} vs {b}")
    return fight


def play_round(s, fight):
    return "".join(fight(s[i], s[i + 1]) for i in range(0, len(s), 2))


def play_rounds(s, fight, k):
    for _ in range(k):
        s = play_round(s, fight)
    return s


def champion(s, fight):
    while len(s) > 1:
        s = play_round(s, fight)
    return s


def build_bracket_halves(counts, winner, beats, node_limit=200_000):
    """counts: {style: n} summing to a power of 2. Returns a first-round string whose champion is `winner`."""
    B = _norm_beats(beats)
    styles = sorted(set(B) | set(counts))
    fight = make_fight(beats)

    def beats_(a, b):
        return b in B.get(a, ())

    from itertools import permutations
    budget = [node_limit]
    memo = {}

    def orders(W, X, present):
        # fill priority for half B (target X): styles X beats that threaten W first, then other threats, then the rest
        def score(perm):
            sc = 0
            for i, y in enumerate(perm):
                w = 0 if (y != W and not beats_(W, y) and beats_(X, y)) else 1 if (y != W and not beats_(W, y))                     else 2 if y == X else 3
                sc += w * (10 ** (len(perm) - i))
            return sc
        return sorted(permutations(present), key=score)

    def go(cnt, W):
        key = (cnt, W)
        if key in memo:
            return memo[key]
        budget[0] -= 1
        if budget[0] < 0:
            return None
        c = dict(zip(styles, cnt))
        n = sum(cnt)
        res = None
        if c.get(W, 0) == 0:
            pass
        elif n == 1:
            res = W
        else:
            present = [x for x in styles if c[x]]
            if all(x == W or beats_(W, x) for x in present):
                res = "".join(x * c[x] for x in present)   # W wins regardless of order
            else:
                res = split(c, n, W, present)
        memo[key] = res
        return res

    def fill(c, h, W, X, base, perm):
        take = dict(base)
        room = h - sum(take.values())
        if room < 0 or take[X] < 1:
            return None
        for y in perm:
            k = min(c[y] - take[y] - (1 if y == W else 0), room)
            if k > 0:
                take[y] += k; room -= k
        return None if room else tuple(take[x] for x in styles)

    def candidates(c, h, W, X, present):
        # 1) proportional: every style split ~in half (keep >=1 W in A, >=1 X in B), repaired by perm fill
        half = {y: c[y] // 2 for y in styles}
        half[X] = max(half[X], 1)
        if W != X:
            half[W] = min(half[W], c[W] - 1)
        else:
            half[W] = min(max(half[W], 1), c[W] - 1)
        for sh in (0, 1):  # odd counts: round down / up
            base = {y: min(c[y] - (1 if y == W else 0), half[y] + (sh and c[y] % 2)) for y in styles}
            base[X] = max(base[X], 1)
            while sum(base.values()) > h:  # trim from the most plentiful non-required
                y = max((y for y in styles if base[y] > (1 if y == X else 0)), key=lambda y: base[y])
                base[y] -= 1
            for perm in orders(W, X, present)[:6]:
                tb = fill(c, h, W, X, base, perm)
                if tb:
                    yield tb
        # 2) greedy by priority permutation (take max of each style in order)
        zero = dict.fromkeys(styles, 0)
        zero[X] = 1
        for perm in orders(W, X, present):
            tb = fill(c, h, W, X, zero, perm)
            if tb:
                yield tb

    def split(c, n, W, present):
        h = n // 2
        tried = set()
        for X in [x for x in styles if beats_(W, x)] + [W]:
            if c.get(X, 0) == 0 or (X == W and c[W] < 2):
                continue
            for tb in candidates(c, h, W, X, present):
                if (tb, X) in tried:
                    continue
                tried.add((tb, X))
                right = go(tb, X)
                if right is None:
                    if budget[0] < 0:
                        return None
                    continue
                left = go(tuple(c[x] - tb[i] for i, x in enumerate(styles)), W)
                if left is not None:
                    return left + right
                if budget[0] < 0:
                    return None
        return None

    res = go(tuple(counts.get(x, 0) for x in styles), winner)
    if res is not None and champion(res, fight) != winner:
        return None
    return res


def _match(surv, lose, dom, styles):
    """Type-level perfect matching losers->survivors (each survivor takes exactly one loser).
    dom[x] = set of y that x beats or ties. Returns {(x,y): k} or None."""
    # max flow: source->x (surv[x]) -> y (if y in dom[x]) -> sink (lose[y]); tiny graph, augmenting paths
    S = [x for x in styles if surv.get(x, 0)]
    L = [y for y in styles if lose.get(y, 0)]
    flow = {}
    cap_s = {x: surv[x] for x in S}
    need = {y: lose[y] for y in L}
    # identity first (ties)
    for y in L:
        if y in cap_s:
            k = min(cap_s[y], need[y])
            if k:
                flow[(y, y)] = k; cap_s[y] -= k; need[y] -= k
    while True:
        y0 = next((y for y in L if need[y] > 0), None)
        if y0 is None:
            return flow
        # BFS over alternating paths: loser y needs a survivor x with spare cap, possibly re-routing
        prev = {}
        frontier = [('y', y0)]
        seen = {('y', y0)}
        end = None
        while frontier and end is None:
            nxt = []
            for kind, v in frontier:
                if kind == 'y':
                    for x in S:
                        if v in dom[x] and ('x', x) not in seen:
                            seen.add(('x', x)); prev[('x', x)] = ('y', v)
                            if cap_s[x] > 0:
                                end = ('x', x); break
                            nxt.append(('x', x))
                    if end:
                        break
                else:  # survivor x is full: free it by moving one of its losers y' to another survivor
                    for (a, b), k in flow.items():
                        if a == v and k > 0 and ('y', b) not in seen:
                            seen.add(('y', b)); prev[('y', b)] = ('x', v)
                            nxt.append(('y', b))
            frontier = nxt
        if end is None:
            return None
        # augment by 1 along the path
        node = end
        cap_s[end[1]] -= 1
        while node != ('y', y0):
            p = prev[node]
            if node[0] == 'x':           # edge y(p) -> x(node): add flow
                flow[(node[1], p[1])] = flow.get((node[1], p[1]), 0) + 1
            else:                         # edge x(p) -> y(node) existing flow: remove
                flow[(p[1], node[1])] -= 1
            node = p
        need[y0] -= 1


def build_bracket(counts, winner, beats, branch=40, node_limit=20000, fallback=True):
    """First-round order (string) of a power-of-2 knockout whose champion is `winner`, using exactly `counts`.
    Round-based DFS (see module doc). Falls back to build_bracket_halves. None if both fail."""
    B = _norm_beats(beats)
    styles = sorted(set(B) | set(counts))
    dom = {x: {x} | B.get(x, set()) for x in styles}
    c = {x: counts.get(x, 0) for x in styles}
    n = sum(c.values())
    k = n.bit_length() - 1
    assert 1 << k == n, "size must be a power of 2"
    fight = make_fight(beats)
    if c.get(winner, 0) == 0:
        return None
    budget = [node_limit]
    dead = set()

    def feasible(surv, lose):
        return _match(surv, lose, dom, styles) is not None

    def cands(t, st):
        size = n >> t
        need = size - sum(st.values())
        if t == 0:
            l = {x: c[x] - st[x] for x in styles}
            return [l] if all(v >= 0 for v in l.values()) else []
        ideal = {x: c[x] * size / n for x in styles}
        room = {x: c[x] - st[x] for x in styles}
        base = {x: min(room[x], max(0, int(ideal[x]) - st[x])) for x in styles}
        rest = need - sum(base.values())
        order = sorted(styles, key=lambda x: -(ideal[x] - st[x] - base[x]))
        while rest > 0:
            moved = False
            for x in order:
                if rest and base[x] < room[x]:
                    base[x] += 1; rest -= 1; moved = True
            if not moved:
                return []
        while rest < 0:
            x = max((x for x in styles if base[x] > 0), key=lambda x: base[x] + st[x] - ideal[x])
            base[x] -= 1; rest += 1
        out, seen = [], set()
        frontier = [base]
        while frontier and len(out) < branch:
            nf = []
            for l in frontier:
                key = tuple(l[x] for x in styles)
                if key in seen:
                    continue
                seen.add(key)
                out.append(l)
                for a in styles:          # move one unit a -> b
                    if l[a] == 0:
                        continue
                    for b in styles:
                        if b != a and l[b] < room[b]:
                            m = dict(l); m[a] -= 1; m[b] += 1
                            nf.append(m)
            frontier = nf
        return out

    def dfs(t, st, chain):
        budget[0] -= 1
        if budget[0] < 0:
            return None
        if t < 0:
            return chain
        key = (t, tuple(st[x] for x in styles))
        if key in dead:
            return None
        for l in cands(t, st):
            if feasible(st, l):
                nst = {x: st[x] + l[x] for x in styles}
                r = dfs(t - 1, nst, chain + [(st, l)])
                if r is not None:
                    return r
                if budget[0] < 0:
                    return None
        dead.add(key)
        return None

    st0 = dict.fromkeys(styles, 0); st0[winner] = 1
    chain = dfs(k - 1, st0, []) if k > 0 else []
    if chain is None:
        return build_bracket_halves(counts, winner, beats) if fallback else None
    order = [winner]
    for surv, lose in chain:
        flow = _match(surv, lose, dom, styles)
        pool = {}
        for (x, y), m in flow.items():
            pool.setdefault(x, []).extend([y] * m)
        nxt = []
        for x in order:
            nxt += [x, pool[x].pop()]
        order = nxt
    res = "".join(order)
    assert champion(res, fight) == winner and all(res.count(x) == c[x] for x in styles)
    return res


def fill_bracket(s, winner, beats, wild="X", styles=None, prefer=None):
    """Fixed first-round order with wildcard spots: choose styles for `wild` so that `winner` is champion.
    Exact tree DP over achievable-winner sets. prefer(style list) -> ordering for ties (default: winner first).
    Returns the filled string or None."""
    B = _norm_beats(beats)
    styles = list(styles or sorted(set(B)))
    fight = make_fight(beats)
    n = len(s)
    # level 0 sets
    levels = [[frozenset(styles) if ch == wild else frozenset(ch) for ch in s]]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        levels.append([frozenset(fight(a, b) for a in cur[i] for b in cur[i + 1]) for i in range(0, len(cur), 2)])
    if winner not in levels[-1][0]:
        return None
    want = [winner]  # wanted winner per node at current level (top-down)
    for lv in range(len(levels) - 1, 0, -1):
        child = levels[lv - 1]
        nw = []
        for i, w in enumerate(want):
            L, R = child[2 * i], child[2 * i + 1]
            pick = None
            cand = sorted(((a, b) for a in L for b in R if fight(a, b) == w),
                          key=lambda p: (p[0] != w and p[1] != w))  # prefer ties/keeping w
            if cand:
                pick = cand[0]
            nw += list(pick)
        want = nw
    out = "".join(want)
    assert all(ch == wild or ch == o for ch, o in zip(s, out)) and champion(out, fight) == winner
    return out


def rig_bracket(s, winner, beats, wild="X", adv="Z", styles=None):
    """Fixed order with `wild` spots we choose and `adv` spots an adversary fills (any style, after us).
    Choose wild styles so `winner` is champion for EVERY adversary filling. Exact DP over families of
    outcome sets (bitmasks). Returns the string with wild filled (adv spots kept) or None."""
    B = _norm_beats(beats)
    styles = list(styles or sorted(set(B)))
    fight = make_fight(beats)
    idx = {x: i for i, x in enumerate(styles)}
    full = (1 << len(styles)) - 1
    M = full + 1
    comb = [[0] * M for _ in range(M)]
    for a in range(1, M):
        for b in range(1, M):
            m = 0
            for x in styles:
                if a >> idx[x] & 1:
                    for y in styles:
                        if b >> idx[y] & 1:
                            m |= 1 << idx[fight(x, y)]
            comb[a][b] = m
    # level 0: dict mask -> leaf style choice
    lvl = []
    for ch in s:
        if ch == wild:
            lvl.append({1 << idx[x]: x for x in styles})
        elif ch == adv:
            lvl.append({full: adv})
        else:
            lvl.append({1 << idx[ch]: ch})
    levels = [lvl]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        nxt = []
        for i in range(0, len(cur), 2):
            L, R = cur[i], cur[i + 1]
            d = {}
            for a in L:
                ca = comb[a]
                for b in R:
                    m = ca[b]
                    if m not in d:
                        d[m] = (a, b)
            nxt.append(d)
        levels.append(nxt)
    target = 1 << idx[winner]
    if target not in levels[-1][0]:
        return None
    want = [target]
    for lv in range(len(levels) - 1, 0, -1):
        nw = []
        for i, m in enumerate(want):
            nw += list(levels[lv][i][m])
        want = nw
    return "".join(levels[0][i][m] for i, m in enumerate(want))
