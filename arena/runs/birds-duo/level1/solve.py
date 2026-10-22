import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from lib import *  # Reader, grid/paths/search helpers: see .claude/skills/ccc-patterns
# First line '# ccc: pypy' (or CCC_PY=pypy) runs this solver on PyPy.


def cases(data: str) -> list:
    """Split the input into independent cases (picklable). One case for a whole-file problem: [data]."""
    r = Reader(data)
    return [r.word() for _ in range(r.int())]


def solve_case(c) -> str:
    raise NotImplementedError


# Optional: def check(data: str, out: str) -> bool | (bool, str)
# If defined, `go` accepts outputs that check() validates even when the example output differs.

if __name__ == "__main__":
    run_cases(cases, solve_case)  # parallel across cases when slow, progress + ETA; `ccc.py probe N` times it
