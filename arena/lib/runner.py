"""Case-level harness: parallel across cases, progress + ETA on stderr, probe mode.

In solve.py:

    def cases(data):            # split the input into independent cases (any picklable objects)
        r = Reader(data); return [r.grid(r.ints(2)[1]) for _ in range(r.int())]
    def solve_case(c):          # one case -> output text (no trailing newline needed)
        return ...
    if __name__ == "__main__":
        run_cases(cases, solve_case)        # reads stdin, writes stdout

Behaviour:
- Solves case 0 first and times it. If the projected sequential total is under ~1.5 s, it stays sequential
  (no spawn cost); otherwise it starts a multiprocessing Pool (CCC_WORKERS, default all cores) for the rest.
- Progress to stderr every ~10 s: `[runner] 37/500 cases  0.82 s/case  ETA 25 s`.
- CCC_PROBE=k: solve only the k largest cases (by repr length) in parallel, print per-case times and the
  extrapolated total, write NOTHING to stdout. `python arena/ccc.py probe N` uses this.
- CCC_SEQ=1: never use a pool (debugging, pdb, prints).  CCC_ONLY=3,7: solve only those case indices.
- init(*initargs) runs once per process before solving (shared precomputed tables), like Pool's initializer.
"""
import multiprocessing as mp
import os
import sys
import time
import traceback

_SOLVE = None


def _err(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _worker_init(solve_case, init, initargs):
    global _SOLVE
    _SOLVE = solve_case
    if init:
        init(*initargs)


def _timed(arg):
    i, c = arg
    t0 = time.perf_counter()
    try:
        out = _SOLVE(c)
    except Exception:
        return i, None, time.perf_counter() - t0, traceback.format_exc()
    return i, out, time.perf_counter() - t0, None


def _fmt(s):
    return f"{s:.0f} s" if s >= 10 else f"{s:.1f} s"


def _join(outs, sep="\n", header=None):
    text = sep.join(str(o).rstrip("\n") for o in outs)
    if header is not None:
        text = f"{header}{sep}{text}" if text else str(header)
    return text + "\n" if text else ""


def _workers(n_cases):
    w = int(os.environ.get("CCC_WORKERS") or 0) or (os.cpu_count() or 4)
    return max(1, min(w, n_cases))


def _probe(items, solve_case, init, initargs, k):
    """Solve a sample (half the largest cases, half random) in parallel under a time budget, then extrapolate.
    Heavy-tailed searches show up as cases still unfinished at the budget; they count as >= budget."""
    import random
    n = len(items)
    budget = float(os.environ.get("CCC_PROBE_BUDGET") or 20)
    size = {i: len(repr(c)) for i, c in items}
    big = sorted(items, key=lambda ic: -size[ic[0]])[:(k + 1) // 2]
    taken = {i for i, _ in big}
    rest = [ic for ic in items if ic[0] not in taken]
    pick = big + random.Random(1).sample(rest, min(len(rest), k - len(big)))
    w = _workers(len(pick))
    t0 = time.perf_counter()
    times, crashed = {}, None
    if w == 1 or os.environ.get("CCC_SEQ"):
        _worker_init(solve_case, init, initargs)
        for ic in pick:
            if time.perf_counter() - t0 > budget:
                break
            i, out, dt, err = _timed(ic)
            if err:
                crashed = (i, dt, err)
                break
            times[i] = dt
    else:
        pool = mp.Pool(w, initializer=_worker_init, initargs=(solve_case, init, initargs))
        pending = [pool.apply_async(_timed, (ic,)) for ic in pick]
        for r in pending:
            left = budget - (time.perf_counter() - t0)
            try:
                i, out, dt, err = r.get(timeout=max(0.01, left))
            except mp.TimeoutError:
                continue
            if err:
                crashed = (i, dt, err)
                break
            times[i] = dt
        pool.terminate()
    wall = time.perf_counter() - t0
    if crashed:
        i, dt, err = crashed
        _err(f"[probe] case {i} CRASHED after {dt:.2f} s:\n{err}")
        sys.exit(1)
    for i, _ in pick:
        tag = "largest" if i in taken else "random "
        t = f"{times[i] * 1000:9.1f} ms" if i in times else f" > {budget:.0f} s (unfinished)"
        _err(f"[probe] case {i:>4} {tag} (size {size[i]:>8})  {t}")
    unfinished = len(pick) - len(times)
    est = list(times.values()) + [max(budget, wall)] * unfinished
    mx, mean = max(est), sum(est) / len(est)
    cores = _workers(n)
    eta = max(n * mean / cores, mx)
    lb = " (LOWER BOUND: some cases unfinished)" if unfinished else ""
    _err(f"[probe] {len(times)}/{len(pick)} sampled cases done of {n}: mean {mean:.3f} s, max {mx:.3f} s, "
         f"wall {wall:.1f} s")
    _err(f"[probe] ETA full file: {_fmt(eta)} on {cores} cores, {_fmt(n * mean)} sequential{lb}")
    if unfinished:
        _err("[probe] heavy tail: some cases take > budget. Use a restart portfolio / better heuristic, not a longer timeout.")
    _err(f"[probe] ETA_SECONDS={eta:.2f}" + (" HEAVY_TAIL" if unfinished else ""))


def run_cases(cases, solve_case, data=None, init=None, initargs=(), write=True, sep="\n", header=False):
    """Split `data` (default: stdin) with cases(), solve each with solve_case(), return/print the joined output.
    sep: between case outputs ("\\n\\n" = blank line between blocks). header=True: first line is the case count
    (followed by sep), as in "N, then N blocks" output formats."""
    if data is None:
        data = sys.stdin.read()
    cs = cases(data) if callable(cases) else list(cases)
    items = list(enumerate(cs))
    only = os.environ.get("CCC_ONLY")
    if only:
        keep = {int(x) for x in only.replace(" ", ",").split(",") if x}
        items = [ic for ic in items if ic[0] in keep]
    n = len(items)
    probe = int(os.environ.get("CCC_PROBE") or 0)
    if probe:
        if n:
            _probe(items, solve_case, init, initargs, probe)
        return ""
    if not n:
        return ""
    outs = [None] * n
    T0 = time.perf_counter()
    _worker_init(solve_case, init, initargs)
    i0, out, dt, err = _timed(items[0])
    if err:
        _err(f"[runner] case {i0} crashed:\n{err}")
        sys.exit(1)
    outs[0] = out
    rest = items[1:]
    seq = os.environ.get("CCC_SEQ") or not rest or dt * len(rest) < 1.5
    pos = {ic[0]: k for k, ic in enumerate(items)}
    done, last = 1, time.perf_counter()

    def tick(pending=()):
        nonlocal last
        now = time.perf_counter()
        if now - last >= 10:
            last = now
            el = now - T0
            tail = f"  still running: cases {sorted(pending)}" if 0 < len(pending) <= 8 else ""
            _err(f"[runner] {done}/{n} cases  {el / done:.2f} s/case wall  ETA {_fmt(el / done * (n - done))}{tail}")

    if seq:
        for ic in rest:
            i, out, dt, err = _timed(ic)
            if err:
                _err(f"[runner] case {i} crashed:\n{err}")
                sys.exit(1)
            outs[pos[i]] = out
            done += 1
            tick()
    else:
        w = _workers(len(rest))
        _err(f"[runner] {n} cases, first took {dt:.2f} s -> pool of {w} workers")
        with mp.Pool(w, initializer=_worker_init, initargs=(solve_case, init, initargs)) as pool:
            pending = {ic[0]: pool.apply_async(_timed, (ic,)) for ic in rest}
            while pending:  # poll (not imap) so stragglers are named while they run
                for k in [k for k, r in pending.items() if r.ready()]:
                    i, out, dt, err = pending.pop(k).get()
                    if err:
                        _err(f"[runner] case {i} crashed:\n{err}")
                        pool.terminate()
                        sys.exit(1)
                    outs[pos[i]] = out
                    done += 1
                tick(pending)
                time.sleep(0.02)
    el = time.perf_counter() - T0
    if el > 3:
        _err(f"[runner] done {n} cases in {_fmt(el)}")
    text = _join(outs, sep, len(cs) if header else None)
    if write:
        sys.stdout.write(text)
        sys.stdout.flush()
    return text
