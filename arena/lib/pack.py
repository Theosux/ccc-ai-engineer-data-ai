"""Rectangle packing for "place max number of desks/boxes in a room" levels.

    rects = pack_rects(W, H, [(3, 1)], gap=1)       # max 3x1 pieces (rotations allowed), pieces must not touch (incl. diagonal)
    g = render_rects(W, H, rects)                    # ['X.X', ...] rows (y down), or ids=True for 1..n numbering
    ok, msg = check_rects_grid(g, sizes=[(3, 1)], gap=1, count=k)   # validator for check()

No-touch trick: with gap g, inflate every piece and the room by g -> plain non-overlapping packing.
pack_rects = guillotine DP (exact over guillotine layouts, cut positions restricted to sums of piece sides)
+ optional non-guillotine improvement by DFS (`pack_exact`) for small rooms when the DP misses a target.
"""
import sys
from functools import lru_cache


def _normal_positions(L, sides):
    """All sums of piece sides <= L (cut positions worth trying)."""
    ok = [False] * (L + 1)
    ok[0] = True
    for i in range(1, L + 1):
        ok[i] = any(i >= s and ok[i - s] for s in sides)
    return [i for i in range(1, L + 1) if ok[i]]


_BLOCKS = {}  # pieces-tuple -> {(w,h): rects} exact non-guillotine blocks


@lru_cache(maxsize=None)
def _guillotine_solver(pieces, blocks_key=(), values=()):
    """pieces: tuple of (w,h) INCLUDING rotations; values: tuple of ((w,h), v) (default v=1).
    Returns memoized f(w,h)->(total value, choice)."""
    vals = dict(values)
    blocks = {k: len(v) for k, v in _BLOCKS.get(pieces, {}).items()} if blocks_key and not vals else {}
    sides = sorted({s for p in pieces for s in p} | {s for b in blocks for s in b})
    memo = {}
    normal_cache = {}

    def norm(L):
        if L not in normal_cache:
            normal_cache[L] = _normal_positions(L, sides)
        return normal_cache[L]

    def f(w, h):
        key = (w, h)
        r = memo.get(key)
        if r is not None:
            return r
        best = (0, None)
        for p in pieces:
            if p[0] <= w and p[1] <= h:
                v = vals.get(p, 1)
                if v > best[0]:
                    best = (v, ('P', p))
        if key in blocks and blocks[key] > best[0]:
            best = (blocks[key], ('B', key))
        if best[0]:
            for a in norm(w):
                if a > w // 2:
                    break
                c = f(a, h)[0] + f(w - a, h)[0]
                if c > best[0]:
                    best = (c, ('V', a))
            for b in norm(h):
                if b > h // 2:
                    break
                c = f(w, b)[0] + f(w, h - b)[0]
                if c > best[0]:
                    best = (c, ('H', b))
        memo[key] = best
        return best

    return f


def _norm_pieces(pieces, rotate):
    ps = set()
    for (a, b) in pieces:
        ps.add((a, b))
        if rotate:
            ps.add((b, a))
    return tuple(sorted(ps))


def exact_blocks(pieces, max_side=10, rotate=True, node_limit=200_000):
    """Find small boxes (<= max_side) where a non-guillotine layout (pinwheel) beats the guillotine DP; register
    them as DP primitives for pack_guillotine(..., blocks=True). Cached per piece set. Returns {(w,h): rects}."""
    key = _norm_pieces(pieces, rotate)
    if key in _BLOCKS:
        return _BLOCKS[key]
    f = _guillotine_solver(key)
    area = min(a * b for a, b in key)
    found = {}
    for w in range(1, max_side + 1):
        for h in range(1, max_side + 1):
            g = f(w, h)[0]
            if (w * h) // area > g:
                E = pack_exact(w, h, list(key), g + 1, rotate=False, node_limit=node_limit)
                if E:
                    found[(w, h)] = E
    _BLOCKS[key] = found
    return found


def _values(key, value):
    return tuple((p, value(*p)) for p in key) if value else ()


def pack_guillotine(W, H, pieces, rotate=True, blocks=False, value=None):
    """Max count of pieces (list of (w,h)) in a W x H box using guillotine layouts. Returns [(x,y,w,h)].
    blocks=True: also use exact non-guillotine small blocks from exact_blocks() (pinwheels; unit value only).
    value(w,h) -> weight of a piece: maximizes total weight instead of count (e.g. covered area)."""
    key = _norm_pieces(pieces, rotate)
    if blocks and not value:
        exact_blocks(pieces, rotate=rotate)
    f = _guillotine_solver(key, bool(blocks), _values(key, value))
    return _unpack(f, key, [(0, 0, W, H)])


def _unpack(f, key, stack):
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))
    out = []
    while stack:
        x, y, w, h = stack.pop()
        if w <= 0 or h <= 0:
            continue
        cnt, ch = f(w, h)
        if not cnt:
            continue
        if ch[0] == 'P':
            out.append((x, y, ch[1][0], ch[1][1]))
        elif ch[0] == 'B':
            out += [(x + bx, y + by, bw, bh) for bx, by, bw, bh in _BLOCKS[key][ch[1]]]
        elif ch[0] == 'V':
            a = ch[1]
            stack += [(x, y, a, h), (x + a, y, w - a, h)]
        else:
            b = ch[1]
            stack += [(x, y, w, b), (x, y + b, w, h - b)]
    return out


def pack_pinwheel(W, H, pieces, rotate=True, max_center=None, target=None, value=None):
    """Top-level non-guillotine split: 4 arms around a center rectangle, each region solved by the DP (with
    blocks). TL=[0,x2)x[0,y1) TR=[x2,W)x[0,y2) BR=[x1,W)x[y2,H) BL=[0,x1)x[y1,H) C=[x1,x2)x[y1,y2).
    max_center bounds center size (default: 2*longest piece side). Returns best rects found (or None)."""
    key = _norm_pieces(pieces, rotate)
    if not value:
        exact_blocks(pieces, rotate=rotate)
    f = _guillotine_solver(key, not value, _values(key, value))
    D = max_center or 2 * max(s for p in key for s in p)
    g = lambda w, h: f(w, h)[0] if w > 0 and h > 0 else 0
    best, arg = -1, None
    for x1 in range(1, W):
        for x2 in range(x1 + 1, min(W, x1 + D + 1)):
            for y1 in range(1, H):
                tl = g(x2, y1)
                bl_w = x1
                for y2 in range(y1 + 1, min(H, y1 + D + 1)):
                    c = tl + g(W - x2, y2) + g(W - x1, H - y2) + g(bl_w, H - y1) + g(x2 - x1, y2 - y1)
                    if c > best:
                        best, arg = c, (x1, x2, y1, y2)
        if target is not None and best >= target:
            break
    if arg is None:
        return None
    x1, x2, y1, y2 = arg
    return _unpack(f, key, [(0, 0, x2, y1), (x2, 0, W - x2, y2), (x1, y2, W - x1, H - y2), (0, y1, x1, H - y1),
                            (x1, y1, x2 - x1, y2 - y1)])


def pack_exact(W, H, pieces, target, rotate=True, node_limit=2_000_000):
    """Non-guillotine DFS: first empty cell (row-major) is either covered by a piece's top-left or left empty.
    Prunes with free-area bound. Returns [(x,y,w,h)] with len >= target, or None. Only for small rooms."""
    ps = set()
    for (a, b) in pieces:
        ps.add((a, b))
        if rotate:
            ps.add((b, a))
    ps = sorted(ps, key=lambda p: -p[0])
    area = min(a * b for a, b in ps)
    occ = [[False] * W for _ in range(H)]
    placed = []
    nodes = [0]
    best = [None]
    # empty-cell budget: cells we may leave empty while still reaching target
    budget0 = W * H - target * area if len({a * b for a, b in ps}) == 1 else W * H

    def fits(x, y, w, h):
        if x + w > W or y + h > H:
            return False
        for yy in range(y, y + h):
            row = occ[yy]
            for xx in range(x, x + w):
                if row[xx]:
                    return False
        return True

    def setr(x, y, w, h, v):
        for yy in range(y, y + h):
            row = occ[yy]
            for xx in range(x, x + w):
                row[xx] = v

    def dfs(pos, budget):
        nodes[0] += 1
        if nodes[0] > node_limit:
            return True
        if len(placed) >= target:
            best[0] = list(placed)
            return True
        while pos < W * H and occ[pos // W][pos % W]:
            pos += 1
        if pos >= W * H:
            return False
        y, x = divmod(pos, W)
        for (w, h) in ps:
            if fits(x, y, w, h):
                setr(x, y, w, h, True)
                placed.append((x, y, w, h))
                if dfs(pos + 1, budget):
                    return True
                placed.pop()
                setr(x, y, w, h, False)
        if budget > 0:
            occ[y][x] = True
            r = dfs(pos + 1, budget - 1)
            occ[y][x] = False
            if r:
                return True
        return False

    dfs(0, budget0)
    return best[0]


def pack_rects(W, H, pieces, gap=0, target=None, rotate=True, exact_limit=300_000, exact_max_cells=150, value=None):
    """Max pieces in W x H room; `gap` cells between pieces (gap=1: no touching incl. diagonal; walls OK).
    If `target` is given and missed: guillotine DP -> + exact small blocks -> top-level pinwheel ->
    pack_exact (only rooms <= exact_max_cells, unit value). Returns [(x,y,w,h)] in room coords.
    value(w,h) (piece dims WITHOUT gap): maximize total value, e.g. value=lambda w,h: w*h = covered cells;
    target is then a total value."""
    infl = [(a + gap, b + gap) for a, b in pieces]
    v = (lambda w, h: value(w - gap, h - gap)) if value else None
    score = (lambda R: sum(v(r[2], r[3]) for r in R)) if v else len
    R = pack_guillotine(W + gap, H + gap, infl, rotate, value=v)
    if target is not None and score(R) < target and not v:
        R = max(R, pack_guillotine(W + gap, H + gap, infl, rotate, blocks=True), key=len)
    if target is not None and score(R) < target:
        P = pack_pinwheel(W + gap, H + gap, infl, rotate, target=target, value=v)
        if P and score(P) > score(R):
            R = P
    if target is not None and score(R) < target and (W + gap) * (H + gap) <= exact_max_cells and not v:
        E = pack_exact(W + gap, H + gap, infl, target, rotate, exact_limit)
        if E:
            R = E
    return [(x, y, w - gap, h - gap) for x, y, w, h in R]


def render_rects(W, H, rects, fill='X', empty='.', ids=False, sep=''):
    """Rows of the room. ids=True writes 1..n per rect (use sep=' ' for numeric grids)."""
    g = [[empty] * W for _ in range(H)]
    for i, (x, y, w, h) in enumerate(rects, 1):
        v = str(i) if ids else fill
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                g[yy][xx] = v
    return [sep.join(r) for r in g]


def grid_rects(g, ch='X'):
    """Connected (4-neighbour) groups of `ch` -> list of (x,y,w,h) or None for a group that is not a full rectangle."""
    H, W = len(g), len(g[0]) if g else 0
    seen = [[False] * W for _ in range(H)]
    res = []
    for y in range(H):
        for x in range(W):
            if g[y][x] == ch and not seen[y][x]:
                st = [(x, y)]
                seen[y][x] = True
                cs = []
                while st:
                    cx, cy = st.pop()
                    cs.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx] and g[ny][nx] == ch:
                            seen[ny][nx] = True
                            st.append((nx, ny))
                xs = [c[0] for c in cs]
                ys = [c[1] for c in cs]
                w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
                res.append((min(xs), min(ys), w, h) if w * h == len(cs) else None)
    return res


def check_rects_grid(g, W=None, H=None, sizes=None, gap=1, count=None, ch='X', rotate=True):
    """Validate a room drawing: shape W x H, every desk a rectangle of an allowed size, pairwise gap
    (gap=1 -> no 8-neighbour touching between different desks), exact count. Returns (ok, msg)."""
    if H is not None and len(g) != H:
        return False, f"rows {len(g)} != {H}"
    if W is not None and any(len(r) != W for r in g):
        return False, f"row length != {W}"
    if any(c not in (ch, '.') for r in g for c in r):
        return False, "bad char"
    rs = grid_rects(g, ch)
    if any(r is None for r in rs):
        return False, "non-rectangular desk"
    if sizes is not None:
        ok = {tuple(s) for s in sizes} | ({(b, a) for a, b in sizes} if rotate else set())
        for r in rs:
            if (r[2], r[3]) not in ok:
                return False, f"desk size {r[2]}x{r[3]} at {r[:2]} not allowed"
    if gap >= 1:  # 8-neighbour touching between different components = diagonal contact (4-adjacent would merge)
        Hh, Ww = len(g), len(g[0]) if g else 0
        comp = {}
        for i, (x, y, w, h) in enumerate(rs):
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    comp[(xx, yy)] = i
        for (xx, yy), i in comp.items():
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    j = comp.get((xx + dx, yy + dy))
                    if j is not None and j != i:
                        return False, f"desks touch at {(xx, yy)}"
    if count is not None and len(rs) != count:
        return False, f"count {len(rs)} != {count}"
    return True, ""
