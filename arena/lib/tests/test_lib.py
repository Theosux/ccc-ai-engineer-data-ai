"""Self-test for arena/lib. Run: python arena/lib/tests/test_lib.py   (plain asserts, no pytest needed)."""
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from lib import *  # noqa
from lib import geom


def t_parse():
    r = Reader("2\n3 2\n..X\n...\nWDS\n1 1\n.\nX\n")
    assert r.int() == 2
    assert r.ints(2) == [3, 2] and r.grid(2) == ["..X", "..."] and r.word() == "WDS"
    L = Lines("a b\n\nc d e\n")
    assert L.line() == "a b" and L.line().split() == ["c", "d", "e"]
    assert paragraphs("a\nb\n\nc\n") == [["a", "b"], ["c"]]
    assert out_lines([1, (2, 3), "x"]) == "1\n2 3\nx\n"


def t_grid():
    g = ["..X", "..."]
    assert dims(g) == (3, 2) and find(g, "X") == (2, 0)
    assert walk("DS") == [(0, 0), (1, 0), (1, 1)]
    assert cells_to_moves([(0, 0), (1, 0), (1, 1), (0, 1)]) == "DSA"
    assert sorted(nb4(0, 0, 3, 2)) == [(0, 1), (1, 0)]
    assert len(list(nb8(1, 1, 3, 3))) == 8
    assert rot_cw(["ab", "cd"]) == ["ca", "db"] and transpose(["ab", "cd"]) == ["ac", "bd"]
    # symmetry round trip: a valid path on transformed grid maps back to a valid path on original
    rng = random.Random(3)
    for _ in range(50):
        w, h = rng.randint(2, 6), rng.randint(2, 6)
        grid = ["." * w for _ in range(h)]
        for s in SYMS:
            gg = sym_grid(grid, s)
            m = cells_to_moves(snake_rows(0, 0, len(gg[0]) - 1, len(gg) - 1))
            assert find_cover_start(grid, sym_moves_back(m, s)) is not None


def t_paths():
    lvl3 = ["..X..", ".....", "....."]  # lawnmower level-3 example: INVALID x3, then VALID
    assert [valid_cover(lvl3, p) for p in ("SSDWDSDWWDSS", "DSSAWDDSDWWDSS", "SSDWWDSSDWWDSS", "ASSDWDSDWWDSS")] \
        == [False, False, False, True]
    assert valid_cover(["....", "....", "....", "...."], cells_to_moves(snake_rows(0, 0, 3, 3)))
    assert not valid_cover(["...."], "DDDD") and not valid_cover(["...."], "DQ")
    # ham_path / exact on random small grids with one obstacle
    rng = random.Random(7)
    for _ in range(30):
        w, h = rng.randint(3, 7), rng.randint(3, 7)
        rows = [["."] * w for _ in range(h)]
        rows[rng.randrange(h)][rng.randrange(w)] = "X"
        g = ["".join(r) for r in rows]
        p = ham_path(g, time_limit=2)
        q = ham_path_exact(g, time_limit=5)
        assert (p is None) == (q is None) or p is None, g  # exact must find anything DFS finds
        if q:
            assert valid_cover(g, cells_to_moves(q))
    # cycles
    for g in (["...."] * 4, [".....", ".....", "X....", ".....", ".....", ".....", "....."],
              ["....", ".X..", "....", "...."]):
        c = ham_cycle(g, time_limit=5)
        if sum(r.count(".") for r in g) % 2 == 0 and g[1] != ".X..":
            assert c and valid_cover(g, cells_to_moves(c), cycle=True), g
    assert ham_cycle(["...", "...", "..."]) is None  # odd count
    hp = ham_path(["....", "....", "...."], cycle=True)
    assert hp and valid_cover(["....", "....", "...."], cells_to_moves(hp), cycle=True)
    # fixed endpoints
    g = ["....", "....", "...."]
    p = ham_path_exact(g, start=(0, 0), end=(3, 2))
    assert p[0] == (0, 0) and p[-1] == (3, 2) and valid_cover(g, cells_to_moves(p))


def t_search():
    g = ["..#", "...", "#.."]
    dist, par = grid_bfs(g, [(0, 0)])
    assert dist[(2, 2)] == 4 and path_to(par, (2, 2))[0] == (0, 0)
    d2, _ = grid_bfs(g, [(0, 0), (2, 2)])
    assert d2[(1, 1)] == 2
    adj = {0: [(1, 4), (2, 1)], 1: [(3, 1)], 2: [(1, 2), (3, 5)], 3: []}
    dist, par, _ = dijkstra(0, lambda u: adj[u])
    assert dist[3] == 4 and path_to(par, 3) == [0, 2, 1, 3]
    c, p = astar((0, 0), lambda u: [((u[0] + 1, u[1]), 1), ((u[0], u[1] + 1), 1)],
                 lambda u: abs(3 - u[0]) + abs(3 - u[1]), lambda u: u == (3, 3))
    assert c == 6 and p[-1] == (3, 3)
    d, par, found = bfs(0, lambda u: [u + 1, u * 2], goal=lambda u: u == 10)
    assert found == 10 and d[10] == 5  # 0-1-2-4-5-10
    assert len(grid_components([".#.", "##.", "..."])) == 2
    assert toposort([1, 2, 3], [(1, 2), (2, 3)]) == [1, 2, 3] and toposort([1, 2], [(1, 2), (2, 1)]) is None
    u = DSU()
    u.union(1, 2); u.union(3, 4)
    assert u.same(1, 2) and not u.same(1, 3)


def t_sim_opt_geom():
    assert state_at(0, lambda s: (s + 3) % 7, 10**18) == (3 * 10**18) % 7
    assert state_at(5, lambda s: max(s - 1, 0), 3) == 2
    best, c = anneal([5, -3, 8], lambda s, r: [x + r.choice((-1, 1)) for x in s], lambda s: sum(x * x for x in s), seconds=0.3)
    assert c <= 3
    assert geom.segments_intersect((0, 0), (2, 2), (0, 2), (2, 0))
    assert not geom.segments_intersect((0, 0), (1, 0), (0, 1), (1, 1))
    assert geom.rects_overlap((0, 0, 1, 1), (1, 1, 2, 2)) and not geom.rects_overlap((0, 0, 1, 1), (2, 0, 3, 1))
    assert geom.rects_overlap((0, 0, 1, 1), (2, 0, 3, 1), touch=True)
    assert geom.convex_hull([(0, 0), (1, 1), (2, 0), (2, 2), (0, 2)]) == [(0, 0), (2, 0), (2, 2), (0, 2)]
    assert crosscheck(lambda s: str(sum(map(int, s.split()))), lambda s: str(sum(int(x) for x in s.split())),
                      lambda r: " ".join(str(r.randint(0, 9)) for _ in range(5)), trials=20) is None


def t_pack():
    from lib.pack import pack_rects, render_rects, check_rects_grid
    # Room Planner L4 (3x1, no touch) / L5 (1x2, pinwheel 6x6 -> 8) / L6 (len 4) / L7 (mixed, cover)
    for (x, y, k, d) in ((7, 5, 6, (3, 1)), (9, 7, 10, (3, 1)), (6, 6, 8, (2, 1)), (9, 7, 13, (2, 1)), (9, 5, 6, (4, 1)),
                         (17, 32, 59, (4, 1))):
        R = pack_rects(x, y, [d], gap=1, target=k)
        g = render_rects(x, y, R[:k])
        assert check_rects_grid(g, x, y, [d], 1, k) == (True, ""), (x, y, k, d, len(R))
    P = [(L, 1) for L in range(1, 8)]
    for (x, y, k) in ((10, 9, 47), (9, 7, 35), (6, 8, 24)):
        R = pack_rects(x, y, P, gap=1, target=k, value=lambda w, h: w * h)
        g = render_rects(x, y, R)
        assert check_rects_grid(g, x, y, P, 1)[0] and sum(r.count("X") for r in g) == k
    assert not check_rects_grid(["XX.", "..X"], sizes=[(2, 1)], gap=1)[0]  # diagonal touch
    assert not check_rects_grid(["XX", "XX"], sizes=[(2, 1)], gap=1)[0]   # merged desks


def t_tourney():
    from lib.tourney import make_fight, play_rounds, champion, build_bracket, fill_bracket, rig_bracket
    rps = {"R": "S", "S": "P", "P": "R"}
    f = make_fight(rps)
    assert f("P", "R") == "P" and f("R", "R") == "R" and play_rounds("PRRRSSSR", f, 2) == "PR"
    rpsls = {"R": "SL", "P": "RY", "S": "PL", "Y": "SR", "L": "YP"}
    g = make_fight(rpsls)
    for c in ({"R": 5, "P": 5, "S": 6}, {"R": 11, "P": 3, "S": 2}):
        s = build_bracket(c, "S", rps)
        assert s and champion(s, f) == "S" and all(s.count(k) == v for k, v in c.items())
    c = {"R": 15, "P": 0, "S": 1, "Y": 10, "L": 6}  # needs asymmetric splits (halving heuristic failed)
    s = build_bracket(c, "S", rpsls)
    assert s and champion(s, g) == "S" and all(s.count(k) == v for k, v in c.items())
    assert champion(fill_bracket("RYPYPSRYXYRPLXXP", "S", rpsls), g) == "S"
    o = rig_bracket("ZYPXPSXYZXRPLSZX", "S", rpsls)
    rng = random.Random(1)
    for _ in range(50):
        assert champion("".join(rng.choice("RPSYL") if ch == "Z" else ch for ch in o), g) == "S"


def _sq_case(c):  # module level so pool workers can pickle it
    time.sleep(0.05)
    return str(int(c) ** 2)


def t_runner():
    import os
    from lib.runner import run_cases
    data = "40\n" + "\n".join(map(str, range(40))) + "\n"
    split = lambda d: d.split()[1:]
    want = "\n".join(str(i * i) for i in range(40)) + "\n"
    assert run_cases(split, _sq_case, data=data, write=False) == want      # 2 s sequential -> pool path
    os.environ["CCC_SEQ"] = "1"
    try:
        assert run_cases(split, _sq_case, data=data, write=False) == want
    finally:
        del os.environ["CCC_SEQ"]
    assert run_cases(split, lambda c: c, data="0\n", write=False) == ""


def t_cp():
    from lib.cp import cp_circuit_on_grid, exact_cover, cp_model, cp_solve
    g = [".....", ".....", "X....", ".....", ".....", ".....", "....."]
    assert valid_cover(g, cells_to_moves(cp_circuit_on_grid(g, seconds=10)), cycle=True)
    p = cp_circuit_on_grid(["...", "...", "..."], cycle=False, start=(0, 0), end=(2, 2), seconds=10)
    assert p[0] == (0, 0) and p[-1] == (2, 2) and len(p) == 9
    assert cp_circuit_on_grid(["...", "...", "..."], seconds=5) is None  # odd count: no cycle
    assert sorted(exact_cover([{0, 1}, {1, 2}, {2, 3}, {1}], 4)) == [0, 2]
    m = cp_model.CpModel(); x = m.NewIntVar(0, 10, "x"); m.Add(x * 2 >= 7); m.Minimize(x)
    assert cp_solve(m, 5).Value(x) == 4


def t_flow():
    from lib.flow import grid_vertex_cut, max_flow_graph
    cut, v = grid_vertex_cut(5, 5, cost=lambda x, y: None if (x, y) == (2, 2) else 1,
                             source=lambda x, y: (x, y) == (2, 2), sink=lambda x, y: False, border_is_sink=True)
    assert v == 4 and cut == {(1, 2), (3, 2), (2, 1), (2, 3)}  # the diamond (Islands L5 example "5,4 6,5 5,6 4,5")
    assert max_flow_graph(4, [(0, 1, 3), (0, 2, 2), (1, 3, 2), (2, 3, 3)], 0, 3)[0] == 4


if __name__ == "__main__":
    t0 = time.time()
    for name, fn in list(globals().items()):
        if name.startswith("t_"):
            fn()
            print(f"ok {name}")
    print(f"ALL OK ({time.time() - t0:.1f}s)")
