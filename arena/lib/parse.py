"""Input parsing for CCC formats.

Typical use in solve.py:
    r = Reader(sys.stdin.read())
    for _ in range(r.int()):
        w, h = r.ints(2)
        grid = r.grid(h)          # list of h row strings (no spaces in rows)
        path = r.word()
"""
import re
import sys


class Reader:
    """Token reader over whitespace-split input. Use line mode (Lines) if rows contain spaces."""

    __slots__ = ("tok", "i")

    def __init__(self, data=None):
        if data is None:
            data = sys.stdin.read()
        self.tok = data.split()
        self.i = 0

    def word(self):
        t = self.tok[self.i]
        self.i += 1
        return t

    def words(self, n):
        t = self.tok[self.i:self.i + n]
        self.i += n
        return t

    def int(self):
        return int(self.word())

    def ints(self, n):
        return [int(x) for x in self.words(n)]

    def float(self):
        return float(self.word())

    def floats(self, n):
        return [float(x) for x in self.words(n)]

    def grid(self, h):
        """h tokens = h rows of a paragraph grid (rows without spaces)."""
        return self.words(h)

    def int_grid(self, h, w):
        return [self.ints(w) for _ in range(h)]

    def rest(self):
        t = self.tok[self.i:]
        self.i = len(self.tok)
        return t

    def done(self):
        return self.i >= len(self.tok)


class Lines:
    """Line reader (keeps spaces inside lines, skips nothing unless asked)."""

    __slots__ = ("lines", "i")

    def __init__(self, data=None, skip_blank=True):
        if data is None:
            data = sys.stdin.read()
        ls = data.splitlines()
        self.lines = [l for l in ls if l.strip()] if skip_blank else ls
        self.i = 0

    def line(self):
        l = self.lines[self.i]
        self.i += 1
        return l

    def nlines(self, n):
        t = self.lines[self.i:self.i + n]
        self.i += n
        return t

    def ints(self):
        return [int(x) for x in self.line().split()]

    def int(self):
        return int(self.line().strip())

    def done(self):
        return self.i >= len(self.lines)


def ints_of(s):
    """All integers in a string: ints_of("4,2 8,-5") -> [4, 2, 8, -5]. Great for 'x,y' coords and messy lines."""
    return [int(x) for x in re.findall(r"-?\d+", s)]


def pairs_of(s):
    """'4,2 8,5' -> [(4, 2), (8, 5)]."""
    v = ints_of(s)
    return list(zip(v[::2], v[1::2]))


def paragraphs(data):
    """Split on blank lines -> list of lists of lines (for blocks separated by empty lines)."""
    out, cur = [], []
    for l in data.splitlines():
        if l.strip():
            cur.append(l)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def out_lines(items):
    """Join answers one per line with trailing newline. Lists/tuples become space-joined."""
    res = []
    for x in items:
        if isinstance(x, (list, tuple)):
            res.append(" ".join(map(str, x)))
        else:
            res.append(str(x))
    return "\n".join(res) + "\n"


def run(solve_case=None, solve=None):
    """Boilerplate: run(solve=lambda data: str) or run(solve_case=fn(reader)->answer) for 'N cases'."""
    data = sys.stdin.read()
    if solve is not None:
        sys.stdout.write(solve(data))
        return
    r = Reader(data)
    n = r.int()
    sys.stdout.write(out_lines(solve_case(r) for _ in range(n)))
