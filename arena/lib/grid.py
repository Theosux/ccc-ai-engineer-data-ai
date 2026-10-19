"""Grid helpers. Convention: cell = (x, y), x = column, y = row, y grows DOWN; grid[y][x].

North = up = y-1. WASD: W=N, A=W(est), S=S, D=E. Width = len(grid[0]), height = len(grid).
"""

# direction vectors (dx, dy), y down
N, E, S, W = (0, -1), (1, 0), (0, 1), (-1, 0)
DIRS4 = [N, E, S, W]                      # clockwise from north
DIRS8 = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
WASD = {"W": N, "D": E, "S": S, "A": W}
NESW = {"N": N, "E": E, "S": S, "W": W}
UDLR = {"U": N, "R": E, "D": S, "L": W}
VEC2WASD = {v: k for k, v in WASD.items()}
VEC2NESW = {v: k for k, v in NESW.items()}
OPP = {"W": "S", "S": "W", "A": "D", "D": "A", "N": "S", "E": "W", "U": "D", "L": "R", "R": "L"}
TURN_R = {N: E, E: S, S: W, W: N}           # clockwise 90
TURN_L = {v: k for k, v in TURN_R.items()}


def dims(grid):
    """(width, height)."""
    return len(grid[0]), len(grid)


def inb(x, y, w, h):
    return 0 <= x < w and 0 <= y < h


def nb4(x, y, w, h):
    for dx, dy in DIRS4:
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny


def nb8(x, y, w, h):
    for dx, dy in DIRS8:
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny


def cells(grid, ch=None):
    """All (x, y); or only those whose char is ch (str of allowed chars)."""
    return [(x, y) for y, row in enumerate(grid) for x, c in enumerate(row) if ch is None or c in ch]


def find(grid, ch):
    """First (x, y) with grid[y][x] == ch, else None."""
    for y, row in enumerate(grid):
        x = row.find(ch) if isinstance(row, str) else (row.index(ch) if ch in row else -1)
        if x >= 0:
            return x, y
    return None


def walk(moves, start=(0, 0), dirs=WASD):
    """List of visited cells incl. start for a move string."""
    x, y = start
    out = [(x, y)]
    for c in moves:
        dx, dy = dirs[c]
        x += dx
        y += dy
        out.append((x, y))
    return out


def bbox(points):
    """(minx, miny, maxx, maxy)."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def cells_to_moves(cells_, dirs=VEC2WASD):
    """Adjacent cell sequence -> move string. Raises KeyError if two cells are not 4-adjacent."""
    return "".join(dirs[(b[0] - a[0], b[1] - a[1])] for a, b in zip(cells_, cells_[1:]))


def idx_to_rc(p, cols, base=1):
    """Linear position -> (row, col), e.g. 1-based 'position 7 in a 5-col board' -> (2, 2)."""
    return (p - base) // cols + base, (p - base) % cols + base


def rc_to_idx(r, c, cols, base=1):
    return (r - base) * cols + (c - base) + base


def to_str(grid):
    return "\n".join("".join(map(str, r)) for r in grid)


def show(grid, marks=None, file=None):
    """Debug print to stderr; marks = {(x,y): ch} overlay."""
    import sys
    g = [list(map(str, r)) for r in grid]
    for (x, y), c in (marks or {}).items():
        g[y][x] = c
    print(to_str(g), file=file or sys.stderr)


def mutable(grid):
    return [list(r) for r in grid]


def transpose(grid):
    return ["".join(c) for c in zip(*grid)] if isinstance(grid[0], str) else [list(c) for c in zip(*grid)]


def rot_cw(grid):
    """Rotate 90 deg clockwise."""
    return transpose(grid[::-1])


def flip_h(grid):
    return [r[::-1] for r in grid]


def flip_v(grid):
    return grid[::-1]


# --- 8 symmetries with move-string mapping: solve on a transformed grid, map the answer back ---
SYMS = [(t, fx, fy) for t in (0, 1) for fx in (0, 1) for fy in (0, 1)]  # (transpose, flip x, flip y)


def sym_grid(grid, s):
    t, fx, fy = s
    g = transpose(grid) if t else list(grid)
    if fx:
        g = flip_h(g)
    if fy:
        g = flip_v(g)
    return g


def sym_moves_back(moves, s):
    """Map a WASD move string on sym_grid(grid, s) back to the original grid."""
    t, fx, fy = s
    m = {}
    for c, (dx, dy) in WASD.items():
        if fy:
            dy = -dy
        if fx:
            dx = -dx
        if t:
            dx, dy = dy, dx
        m[c] = VEC2WASD[(dx, dy)]
    return "".join(m[c] for c in moves)


def sym_cell_back(x, y, w, h, s):
    """Cell (x,y) on transformed grid of size (w,h) -> cell on original grid."""
    t, fx, fy = s
    if fy:
        y = h - 1 - y
    if fx:
        x = w - 1 - x
    if t:
        x, y = y, x
    return x, y
