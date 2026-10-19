"""OR-Tools CP-SAT helpers: model a construction/feasibility/optimization level declaratively, let 16 cores search.

Use when a level says "find any arrangement/assignment/path such that ..." and a hand-written search is fiddly or
heavy-tailed. CP-SAT is usually the FASTEST TO WRITE exact method for: Hamiltonian paths/cycles (AddCircuit),
exact cover / tiling, assignment with side constraints, scheduling (intervals + NoOverlap), small ILPs.

    from lib.cp import cp_model, cp_solve, cp_circuit_on_grid, exact_cover
    m = cp_model.CpModel(); x = m.NewIntVar(0, 10, "x"); m.Add(x * 2 >= 7); m.Minimize(x)
    s = cp_solve(m, seconds=10)          # -> solver with values, or None if infeasible/timeout
    s.Value(x)

Limits: integer only (scale floats); big models (>~1e6 literals) get slow to build in Python.
"""
import os

from ortools.sat.python import cp_model  # noqa: F401  (re-exported)


def cp_solve(m, seconds=10.0, workers=None, log=False, hint_first=False):
    """Solve model m. Returns the CpSolver (use .Value/.BooleanValue/.ObjectiveValue) or None if no solution.
    In a lib.runner pool, pass workers=1..2 (the pool already uses all cores)."""
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = float(seconds)
    s.parameters.num_workers = workers or int(os.environ.get("CCC_CP_WORKERS") or 0) or (os.cpu_count() or 8)
    s.parameters.log_search_progress = log
    st = s.Solve(m)
    return s if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None


def grid_cells(grid, free="."):
    cells = [(x, y) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch in free]
    return cells, {c: i for i, c in enumerate(cells)}


def cp_circuit(n, arcs, start=None, end=None, cycle=True, seconds=20.0, workers=None):
    """Hamiltonian cycle (cycle=True) or path over nodes 0..n-1 using directed arcs [(u, v)] (give both directions
    for undirected). Path: optional fixed start/end. Returns node order (list) or None."""
    m = cp_model.CpModel()
    lits = {}
    for u, v in arcs:
        if u != v and (u, v) not in lits:
            lits[(u, v)] = m.NewBoolVar("")
    allarcs = [(u, v, l) for (u, v), l in lits.items()]
    if not cycle:  # dummy node n closes the path: n -> start, end -> n
        D = n
        for v in range(n):
            if start is None or v == start:
                l = m.NewBoolVar(""); allarcs.append((D, v, l)); lits[(D, v)] = l
            if end is None or v == end:
                l = m.NewBoolVar(""); allarcs.append((v, D, l)); lits[(v, D)] = l
    m.AddCircuit(allarcs)
    s = cp_solve(m, seconds, workers)
    if s is None:
        return None
    nxt = {u: v for (u, v), l in lits.items() if s.BooleanValue(l)}
    first = nxt[n] if not cycle else 0
    order, u = [first], first
    while True:
        u = nxt[u]
        if u == first or u == n:
            break
        order.append(u)
    return order


def cp_circuit_on_grid(grid, free=".", cycle=True, start=None, end=None, seconds=20.0, diag=False, workers=None):
    """Hamiltonian cycle/path through all free cells of a grid (4-neighbour moves, or 8 with diag=True).
    start/end are (x, y) cells. Returns list of (x, y) or None. Grid graphs are bipartite: a cycle needs an even
    number of cells (checked by the solver anyway)."""
    cells, idx = grid_cells(grid, free)
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)] + ([(1, 1), (1, -1), (-1, 1), (-1, -1)] if diag else [])
    arcs = [(i, idx[(x + dx, y + dy)]) for i, (x, y) in enumerate(cells) for dx, dy in dirs if (x + dx, y + dy) in idx]
    o = cp_circuit(len(cells), arcs, idx.get(start) if start else None, idx.get(end) if end else None, cycle, seconds,
                   workers)
    return [cells[i] for i in o] if o is not None else None


def exact_cover(rows, n_items, seconds=20.0, optional_items=(), minimize_rows=False, workers=None):
    """Choose rows (each an iterable of item ids in 0..n_items-1) covering every item exactly once
    (optional_items: at most once). Returns list of chosen row indices or None. Tilings: one row per placement."""
    m = cp_model.CpModel()
    x = [m.NewBoolVar("") for _ in rows]
    by_item = [[] for _ in range(n_items)]
    for r, items in enumerate(rows):
        for it in items:
            by_item[it].append(x[r])
    opt = set(optional_items)
    for it, lst in enumerate(by_item):
        if it in opt:
            m.Add(sum(lst) <= 1)
        else:
            m.AddExactlyOne(lst)
    if minimize_rows:
        m.Minimize(sum(x))
    s = cp_solve(m, seconds, workers)
    return [r for r in range(len(rows)) if s.BooleanValue(x[r])] if s else None
