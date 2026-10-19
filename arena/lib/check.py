"""Local validation for constructive levels (multiple valid answers) + fast-vs-brute cross-check.

Pattern: solve.py defines solve(data)->str and check(data, out)->(ok, msg) or bool. Then:
    python arena/lib/check.py arena/runs/<run>/levelN [1-small ...] [--profile]   # solve+check every input
If all OK -> python arena/ccc.py go N --force   (example output differs because many answers are valid)
"""
import importlib.util
import pathlib
import random
import sys
import time


def _load(path):
    spec = importlib.util.spec_from_file_location("solve_mod", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_level(level_dir, only=None, profile=False):
    """Run solve() and check() from level_dir/solve.py on every files/in_*.txt. Returns True if all pass.
    profile=True: cProfile each solve() call, print top 15 by cumulative time to stderr."""
    d = pathlib.Path(level_dir)
    mod = _load(d / "solve.py")
    if not hasattr(mod, "check"):
        print("solve.py has no check(data, out) -> nothing to validate", file=sys.stderr)
    ok_all = True
    for inp in sorted((d / "files").glob("in_*.txt")):
        if only and not any(o in inp.name for o in only):
            continue
        data = inp.read_text(encoding="utf-8")
        t0 = time.time()
        if profile:
            import cProfile, pstats
            pr = cProfile.Profile()
            out = pr.runcall(mod.solve, data)
            pstats.Stats(pr, stream=sys.stderr).sort_stats("cumtime").print_stats(15)
        else:
            out = mod.solve(data)
        dt = time.time() - t0
        if hasattr(mod, "check"):
            r = mod.check(data, out)
            ok, msg = (r if isinstance(r, tuple) else (r, ""))
        else:
            ok, msg = True, "(unchecked)"
        ok_all &= bool(ok)
        print(f"  {inp.name}: {'OK ' if ok else 'BAD'} {dt:.2f}s {msg}")
    return ok_all


def crosscheck(fast, brute, gen, trials=300, seed=1, eq=None):
    """Compare fast(inp) vs brute(inp) on random inputs from gen(rng)->str. Returns failing input or None."""
    rng = random.Random(seed)
    eq = eq or (lambda a, b: a.split() == b.split())
    for t in range(trials):
        inp = gen(rng)
        a, b = fast(inp), brute(inp)
        if not eq(a, b):
            print(f"MISMATCH on trial {t}:\n{inp}\n--- fast ---\n{a}\n--- brute ---\n{b}", file=sys.stderr)
            return inp
    print(f"crosscheck: {trials} trials OK", file=sys.stderr)
    return None


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    if len(sys.argv) < 2:
        sys.exit("usage: python arena/lib/check.py <levelDir> [fileSubstr ...] [--profile]")
    args = [a for a in sys.argv[2:] if a != "--profile"]
    sys.exit(0 if check_level(sys.argv[1], args, profile="--profile" in sys.argv) else 1)
