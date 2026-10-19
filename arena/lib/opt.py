"""Local search for optimization levels (score thresholds). Minimizes cost.

    best, cost = anneal(init, neighbor, cost, seconds=20)
neighbor(sol, rng) -> new candidate (return a copy; don't mutate sol). For speed with big states,
write a delta-cost version by hand using this as the template.
"""
import math
import random
import time


def hill_climb(sol, neighbor, cost, seconds=5.0, seed=0):
    rng = random.Random(seed)
    c = cost(sol)
    end = time.time() + seconds
    while time.time() < end:
        n = neighbor(sol, rng)
        nc = cost(n)
        if nc <= c:
            sol, c = n, nc
    return sol, c


def anneal(sol, neighbor, cost, seconds=10.0, t0=None, t1=1e-3, seed=0, log=False):
    """Simulated annealing with exponential cooling t0 -> t1 over `seconds`. Returns best (sol, cost)."""
    rng = random.Random(seed)
    c = cost(sol)
    best, bc = sol, c
    if t0 is None:  # estimate: average |delta| of a few random moves
        ds = [abs(cost(neighbor(sol, rng)) - c) for _ in range(20)]
        t0 = max(sum(ds) / len(ds), 1e-9)
    start = time.time()
    it = 0
    while True:
        frac = (time.time() - start) / seconds
        if frac >= 1:
            break
        t = t0 * (t1 / t0) ** frac
        n = neighbor(sol, rng)
        nc = cost(n)
        if nc <= c or rng.random() < math.exp((c - nc) / t):
            sol, c = n, nc
            if c < bc:
                best, bc = sol, c
        it += 1
        if log and it % 10000 == 0:
            print(f"it={it} t={t:.4g} cur={c} best={bc}")
    return best, bc
