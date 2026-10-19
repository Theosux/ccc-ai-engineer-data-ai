"""Cover-path helpers: validate a path, serpentine construction, Hamiltonian-path search.

Grid = list of row strings; FREE chars are walkable. Moves are WASD strings unless noted.
"""
import time

from .grid import WASD, VEC2WASD, SYMS, sym_grid, sym_moves_back, cells_to_moves


def path_cells(start, moves, dirs=WASD):
    x, y = start
    out = [(x, y)]
    for c in moves:
        dx, dy = dirs[c]
        x += dx
        y += dy
        out.append((x, y))
    return out


def covers_once(grid, start, moves, free=".", dirs=WASD):
    """True iff walking from start visits every free cell exactly once, stays in bounds, avoids non-free."""
    h, w = len(grid), len(grid[0])
    nfree = sum(sum(c in free for c in row) for row in grid)
    if len(moves) + 1 != nfree:
        return False
    x, y = start
    if not (0 <= x < w and 0 <= y < h) or grid[y][x] not in free:
        return False
    seen = {(x, y)}
    for c in moves:
        dx, dy = dirs[c]
        x += dx
        y += dy
        if not (0 <= x < w and 0 <= y < h) or grid[y][x] not in free or (x, y) in seen:
            return False
        seen.add((x, y))
    return True


def find_cover_start(grid, moves, free=".", dirs=WASD):
    """Start cell for which `moves` is a valid cover path (start not given), else None.
    Fast: start offset is fixed by the path's bounding box (min x/y must land in-grid)."""
    h, w = len(grid), len(grid[0])
    pts = path_cells((0, 0), moves, dirs)
    minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
    miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
    for sy in range(-miny, h - maxy):
        for sx in range(-minx, w - maxx):
            if covers_once(grid, (sx, sy), moves, free, dirs):
                return sx, sy
    return None


def valid_cover(grid, moves, cycle=False, free="."):
    """Level-3-style validator, start unknown. cycle=True also requires end 4-adjacent to start."""
    if any(c not in WASD for c in moves):
        return False
    st = find_cover_start(grid, moves, free)
    if st is None:
        return False
    if cycle:
        ex, ey = path_cells(st, moves)[-1]
        return abs(ex - st[0]) + abs(ey - st[1]) == 1
    return True


def snake_rows(x0, y0, x1, y1, start_left=True):
    """Boustrophedon cell list over rectangle [x0..x1] x [y0..y1], row by row, top to bottom."""
    out = []
    left = start_left
    for y in range(y0, y1 + 1):
        xs = range(x0, x1 + 1) if left else range(x1, x0 - 1, -1)
        out.extend((x, y) for x in xs)
        left = not left
    return out


def snake_cols(x0, y0, x1, y1, start_top=True):
    """Boustrophedon column by column, left to right."""
    out = []
    top = start_top
    for x in range(x0, x1 + 1):
        ys = range(y0, y1 + 1) if top else range(y1, y0 - 1, -1)
        out.extend((x, y) for y in ys)
        top = not top
    return out


def ham_path(grid, start=None, end=None, free=".", time_limit=5.0, cycle=False, seed=0):
    """Hamiltonian path/cycle over free cells. Returns list of (x,y) or None (timeout / impossible).
    DFS with Warnsdorff ordering + exact local degree pruning + connectivity check + random restarts.
    cycle=True: picks a min-degree start S and tries each neighbour of S as the fixed end E
    (closing edge E-S), which makes pruning strong. Handles ~1000 free cells on 'solvable' CCC grids."""
    import random
    h, w = len(grid), len(grid[0])
    ids = [y * w + x for y in range(h) for x in range(w) if grid[y][x] in free]
    total = len(ids)
    if total == 0:
        return []
    isfree = [False] * (w * h)
    for i in ids:
        isfree[i] = True
    nbr = [[] for _ in range(w * h)]
    for i in ids:
        x, y = i % w, i // w
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and isfree[ny * w + nx]:
                nbr[i].append(ny * w + nx)
    ring = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]  # consecutive = 4-adjacent
    tostart = (lambda c: c[1] * w + c[0])
    deadline = time.time() + time_limit

    jobs = []  # (S, E or None)
    if cycle:
        S = tostart(start) if start else min(ids, key=lambda i: len(nbr[i]))
        jobs = [(S, E) for E in nbr[S]]
        if len(nbr[S]) == 2:
            jobs = jobs[:1]  # degree-2 start: both neighbours are on the cycle, orientation irrelevant
    else:
        E0 = tostart(end) if end else None
        ss = [tostart(start)] if start else sorted(ids, key=lambda i: len(nbr[i]))
        jobs = [(S, E0) for S in ss]

    vis = [False] * (w * h)
    rng = random.Random(seed)

    def avail(c, head):
        n = 0
        for d in nbr[c]:
            if not vis[d] or d == head:
                n += 1
        return n

    def may_split(c):
        x, y = c % w, c // w
        fr = [0 <= x + dx < w and 0 <= y + dy < h and isfree[(y + dy) * w + x + dx] and not vis[(y + dy) * w + x + dx]
              for dx, dy in ring]
        return sum(1 for i in range(8) if fr[i] and not fr[i - 1]) > 1

    def connected(c, rem):
        st = [d for d in nbr[c] if not vis[d]][:1]
        if not st:
            return rem == 0
        seen = {st[0]}
        while st:
            u = st.pop()
            for d in nbr[u]:
                if not vis[d] and d not in seen:
                    seen.add(d); st.append(d)
        return len(seen) == rem

    def attempt(S, E, until, randomize):
        for i in ids:
            vis[i] = False
        path = [S]
        vis[S] = True

        def cands(c):
            cs = [d for d in nbr[c] if not vis[d] and (d != E or len(path) + 1 == total)]
            cs.sort(key=lambda d: (avail(d, c), rng.random() if randomize else 0))
            return iter(cs)

        stack = [cands(S)]
        it = 0
        while stack:
            if len(path) == total:
                return path
            it += 1
            if it & 255 == 0 and time.time() > until:
                return None
            v = next(stack[-1], None)
            if v is None:
                stack.pop()
                vis[path.pop()] = False
                continue
            u = path[-1]
            vis[v] = True
            path.append(v)
            ok = True
            rem = total - len(path)
            for c in nbr[u]:  # u became interior: its unvisited neighbours lost one option
                if not vis[c]:
                    need = 1 if (c == E or (E is None and not cycle)) else 2
                    if avail(c, v) < need:
                        ok = False
                        break
            if ok and rem and may_split(v) and not connected(v, rem):
                ok = False
            if not ok:
                vis[path.pop()] = False
                continue
            stack.append(cands(v))
        return None

    k = 0
    while jobs and time.time() < deadline:
        for job in list(jobs):
            if time.time() >= deadline:
                break
            slice_ = min(deadline, time.time() + 0.2 * 1.1 ** min(60, k // max(1, len(jobs))))
            p = attempt(job[0], job[1], slice_, randomize=k > 0)
            k += 1
            if p:
                return [(i % w, i // w) for i in p]
            if p is None and time.time() < slice_:
                jobs.remove(job)  # search space exhausted: no solution from this (S, E)
    return None


def try_symmetries(grid, construct, check):
    """Run construct(g) -> moves|None on all 8 symmetric versions of grid; map back; return first
    moves for which check(grid, moves) is True. Lets you write ONE construction for one orientation."""
    for s in SYMS:
        g = sym_grid(grid, s)
        m = construct(g)
        if m is None:
            continue
        mo = sym_moves_back(m, s)
        if check(grid, mo):
            return mo
    return None


# ---------- exact Hamiltonian cycle via edge constraint propagation (strong; use when DFS times out) ----------
def ham_cycle_graph(n, edges, time_limit=30.0, must_on=(), rng=None, p_off_first=0.3):
    """Hamiltonian cycle on graph (nodes 0..n-1, edges list of (u,v)). Returns node order or None.
    Propagates: every node has exactly 2 'on' edges; no premature sub-cycle; on+unknown graph connected.
    Branches on an unknown edge at a chain end. must_on: edge indices forced on."""
    m = len(edges)
    inc = [[] for _ in range(n)]
    for e, (u, v) in enumerate(edges):
        inc[u].append(e)
        inc[v].append(e)
    deadline = time.time() + time_limit

    # state: es (-1/0/1), on, unk, endo (other end of chain), size (chain size at endpoints), closed
    es0 = [-1] * m
    on0 = [0] * n
    unk0 = [len(inc[v]) for v in range(n)]
    endo0 = list(range(n))
    size0 = [1] * n

    class Fail(Exception):
        pass

    def propagate(st, q_on, q_off):
        es, on, unk, endo, size = st
        stack_v = []

        def set_on(e):
            if es[e] == 1:
                return
            if es[e] == 0:
                raise Fail
            u, v = edges[e]
            es[e] = 1
            on[u] += 1; on[v] += 1; unk[u] -= 1; unk[v] -= 1
            if on[u] > 2 or on[v] > 2:
                raise Fail
            eu, ev = endo[u], endo[v]
            if eu == v:  # closes a cycle
                if size[u] != n:
                    raise Fail
                st.append(True)  # closed marker
            else:
                s = size[eu] + size[ev]
                endo[eu] = ev; endo[ev] = eu
                size[eu] = size[ev] = s
                if s < n:  # forbid closing edge between the new chain ends
                    for f in inc[eu]:
                        a, b = edges[f]
                        if es[f] == -1 and (a == ev or b == ev):
                            q_off.append(f)
            stack_v.append(u); stack_v.append(v)

        def set_off(e):
            if es[e] == 0:
                return
            if es[e] == 1:
                raise Fail
            u, v = edges[e]
            es[e] = 0
            unk[u] -= 1; unk[v] -= 1
            stack_v.append(u); stack_v.append(v)

        while q_on or q_off or stack_v:
            if q_on:
                set_on(q_on.pop()); continue
            if q_off:
                set_off(q_off.pop()); continue
            x = stack_v.pop()
            if on[x] == 2 and unk[x]:
                q_off.extend(f for f in inc[x] if es[f] == -1)
            elif on[x] + unk[x] < 2:
                raise Fail
            elif on[x] + unk[x] == 2 and unk[x]:
                q_on.extend(f for f in inc[x] if es[f] == -1)

    def connected(es):
        seen = [False] * n
        seen[0] = True
        st = [0]
        c = 1
        while st:
            u = st.pop()
            for f in inc[u]:
                if es[f] != 0:
                    a, b = edges[f]
                    v = b if a == u else a
                    if not seen[v]:
                        seen[v] = True; c += 1; st.append(v)
        return c == n

    st = [es0, on0, unk0, endo0, size0]
    try:
        propagate(st, list(must_on), [])
        propagate(st, [], [])
        for v in range(n):
            if unk0[v] + on0[v] < 2:
                raise Fail
    except Fail:
        return None
    # initial vertex checks
    try:
        q_on = []
        for v in range(n):
            if on0[v] + unk0[v] == 2:
                q_on.extend(f for f in inc[v] if es0[f] == -1)
        propagate(st, q_on, [])
    except Fail:
        return None

    stack = [st]
    it = 0
    while stack:
        it += 1
        if it & 63 == 0 and time.time() > deadline:
            return None
        st = stack.pop()
        es, on, unk, endo, size = st[:5]
        if len(st) > 5 or all(o == 2 for o in on):
            if all(o == 2 for o in on):
                return _order_from_edges(n, edges, es, inc)
        if not connected(es):
            continue
        # choose branching edge: chain end (on==1) with fewest unknowns, else any node with min unknowns
        best, bk = None, 99
        for v in range(n):
            if unk[v] and on[v] < 2:
                k = unk[v] - (2 if on[v] == 1 else 0) + (rng.random() * 0.5 if rng else 0)
                if k < bk:
                    bk, best = k, v
        if best is None:
            continue
        fs = [f for f in inc[best] if es[f] == -1]
        e = rng.choice(fs) if rng else fs[0]
        for val in ((1, 0) if rng and rng.random() < p_off_first else (0, 1)):  # LIFO: last pushed explored first; default explores ON first
            ns = [es[:], on[:], unk[:], endo[:], size[:]]
            try:
                propagate(ns, [e] if val else [], [] if val else [e])
            except Fail:
                continue
            stack.append(ns)
    return None


def _order_from_edges(n, edges, es, inc):
    order = [0]
    prev, cur = -1, 0
    for _ in range(n - 1):
        for f in inc[cur]:
            if es[f] == 1:
                a, b = edges[f]
                nxt = b if a == cur else a
                if nxt != prev:
                    break
        prev, cur = cur, nxt
        order.append(cur)
    return order


def grid_graph(grid, free="."):
    """(cells list, index dict, edge list) for 4-adjacent free cells."""
    h, w = len(grid), len(grid[0])
    cells_ = [(x, y) for y in range(h) for x in range(w) if grid[y][x] in free]
    idx = {c: i for i, c in enumerate(cells_)}
    edges = []
    for (x, y), i in idx.items():
        for c in ((x + 1, y), (x, y + 1)):
            j = idx.get(c)
            if j is not None:
                edges.append((i, j))
    return cells_, idx, edges


def ham_cycle(grid, free=".", time_limit=30.0):
    """Exact Hamiltonian cycle on grid free cells -> list of cells (last adjacent to first) or None."""
    cells_, idx, edges = grid_graph(grid, free)
    if len(cells_) < 4 or len(cells_) % 2:
        return None  # grid graphs are bipartite: cycle needs even count
    import random
    deadline = time.time() + time_limit
    o, k = None, 0
    while o is None and time.time() < deadline:  # random restarts with growing slices (heavy-tailed search)
        # portfolio: even k = deterministic run with doubling slice; odd k = random seed, short slice
        # (search is heavy-tailed: lucky random runs finish in <0.2 s)
        sl = 0.5 * 2 ** min(k // 2, 12) if k % 2 == 0 else 0.2 * 1.05 ** min(k // 2, 60)
        sl = min(deadline - time.time(), sl)
        o = ham_cycle_graph(len(cells_), edges, sl, rng=random.Random(k) if k % 2 else None)
        k += 1
    return [cells_[i] for i in o] if o else None


def ham_path_exact(grid, start=None, end=None, free=".", time_limit=30.0):
    """Exact Hamiltonian path via cycle + virtual node V adjacent to allowed endpoints."""
    cells_, idx, edges = grid_graph(grid, free)
    n = len(cells_)
    V = n
    ends = [idx[start]] if start else range(n)
    ends2 = [idx[end]] if end else range(n)
    ex = set()
    for i in ends:
        ex.add(i)
    for i in ends2:
        ex.add(i)
    edges = edges + [(i, V) for i in sorted(ex)]
    must = []
    if start:
        must.append(len(edges) - len(ex) + sorted(ex).index(idx[start]))
    if end:
        must.append(len(edges) - len(ex) + sorted(ex).index(idx[end]))
    o = ham_cycle_graph(n + 1, edges, time_limit, must_on=must)
    if not o:
        return None
    k = o.index(V)
    o = o[k + 1:] + o[:k]
    p = [cells_[i] for i in o]
    if start and p[0] != start:
        p.reverse()
    return p
