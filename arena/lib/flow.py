"""Fast max-flow / min-cut on grids with OR-Tools (C++), for "separate A from B with the fewest cells" levels.

Pattern (Islands L7, Honeycomb L5): the shortest closed route around a region that keeps other things outside
is a MINIMUM VERTEX CUT: water cells cost 1, the region is the source, everything that must stay outside
(+ the window border) is the sink. A minimal 4-separating cell set is an 8-connected loop (and vice versa).
100x faster than BFS over (cell, parity-mask) states. Caveat: a min cut may split into several rings
(e.g. an extra ring around a nearby island); detect that and add uncuttable `hard` corridors.

    from lib.flow import grid_vertex_cut
    cut, value = grid_vertex_cut(W, H, cost=lambda x, y: 1 if g[y][x] == "W" else None,
                                 source=lambda x, y: (x, y) in T, sink=lambda x, y: g[y][x] == "L" and (x, y) not in T,
                                 border_is_sink=True)
"""
from ortools.graph.python import max_flow

INF = 10 ** 9


def grid_vertex_cut(W, H, cost, source, sink, border_is_sink=False, diag=False, x0=0, y0=0):
    """Min-cost set of cells separating source cells from sink cells in the W x H window at (x0, y0).
    cost(x, y) -> int capacity of cutting that cell, or None = uncuttable. Adjacency: 4 (or 8 with diag=True).
    Returns (set of cut cells (x, y), cut value)."""
    idx = lambda x, y: (y - y0) * W + (x - x0)
    S, T = 2 * W * H, 2 * W * H + 1
    f = max_flow.SimpleMaxFlow()
    nb = [(1, 0), (0, 1)] + ([(1, 1), (1, -1)] if diag else [])
    for y in range(y0, y0 + H):
        for x in range(x0, x0 + W):
            i = idx(x, y)
            c = cost(x, y)
            f.add_arc_with_capacity(2 * i, 2 * i + 1, INF if c is None else c)
            if source(x, y):
                f.add_arc_with_capacity(S, 2 * i, INF)
            elif sink(x, y) or (border_is_sink and (x in (x0, x0 + W - 1) or y in (y0, y0 + H - 1))):
                f.add_arc_with_capacity(2 * i + 1, T, INF)
            for dx, dy in nb:
                if x0 <= x + dx < x0 + W and y0 <= y + dy < y0 + H:
                    j = idx(x + dx, y + dy)
                    f.add_arc_with_capacity(2 * i + 1, 2 * j, INF)
                    f.add_arc_with_capacity(2 * j + 1, 2 * i, INF)
    f.solve(S, T)
    side = set(f.get_source_side_min_cut())
    cut = {(x, y) for y in range(y0, y0 + H) for x in range(x0, x0 + W)
           if 2 * idx(x, y) in side and 2 * idx(x, y) + 1 not in side}
    return cut, f.optimal_flow()


def max_flow_graph(n, arcs, s, t):
    """Plain max flow on nodes 0..n-1, arcs [(u, v, cap)]. Returns (value, [flow per arc], source-side set)."""
    f = max_flow.SimpleMaxFlow()
    for u, v, c in arcs:
        f.add_arc_with_capacity(u, v, c)
    f.solve(s, t)
    return f.optimal_flow(), [f.flow(i) for i in range(len(arcs))], set(f.get_source_side_min_cut())
