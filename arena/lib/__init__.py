"""CCC helper library. In solve.py (arena/runs/<run>/levelN/solve.py):

    import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    from lib import *

Modules: parse (Reader/Lines), grid (dirs, symmetries), paths (cover/hamiltonian),
search (BFS/Dijkstra/A*/DSU/toposort), sim (cycle skip), check (local validation), opt (annealing), geom,
pack (rectangle packing: guillotine DP + pinwheel + exact; no-touch gap; validator),
tourney (knockout brackets: simulate, construct by counts, fill wildcards, rig vs adversary),
runner (run_cases: pool across cases, progress/ETA, CCC_PROBE), cp (OR-Tools CP-SAT: circuit, exact cover),
flow (OR-Tools max flow: grid_vertex_cut, max_flow_graph), ml (pandas/sklearn/LightGBM: read_csv, best_model, cv_score, fmt_*);
import cp/flow/ml explicitly: `from lib.ml import ...`, they load heavy libraries.
"""
from .parse import Reader, Lines, paragraphs, out_lines, run, ints_of, pairs_of
from .grid import *  # noqa: F401,F403
from .paths import (path_cells, covers_once, find_cover_start, valid_cover, snake_rows, snake_cols, ham_path, try_symmetries,
    ham_cycle, ham_path_exact, ham_cycle_graph, grid_graph)
from .search import grid_bfs, bfs, path_to, dijkstra, astar, grid_components, toposort, DSU
from .sim import find_cycle, state_at
from .check import check_level, crosscheck
from .opt import anneal, hill_climb
from .pack import pack_rects, pack_guillotine, pack_pinwheel, pack_exact, render_rects, grid_rects, check_rects_grid
from .tourney import make_fight, play_round, play_rounds, champion, build_bracket, fill_bracket, rig_bracket
from .runner import run_cases
from . import geom
