"""Colony: One rules engine. Board: dict (r,c)->(team, piece) with r=0 top row (rank 8), c=0 file A.
team 'C'/'M', piece 'K'/'P'. Action = (kind, (r,c), (r2,c2))."""
K8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
ORTH = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
N = 8


def sq(rc):
    return "ABCDEFGH"[rc[1]] + str(8 - rc[0])


def parse_render(render):
    b = {}
    for line in render.splitlines():
        p = line.split()
        if len(p) == 9 and p[0].isdigit():
            r = 8 - int(p[0])
            for c, t in enumerate(p[1:]):
                if t != "..":
                    b[(r, c)] = (t[0].upper(), t[1])
    return b


def inb(r, c):
    return 0 <= r < N and 0 <= c < N


def actions(b, team, locked=frozenset()):
    out = []
    for (r, c), (t, p) in b.items():
        if t != team:
            continue
        if p == "K":
            for dr, dc in K8:
                q = (r + dr, c + dc)
                if inb(*q) and q not in locked and (q not in b or b[q][0] != team):
                    out.append(("move", (r, c), q))
        elif p == "P":
            for dr, dc in ORTH:
                for k in (1, 2):
                    q = (r + dr * k, c + dc * k)
                    if not inb(*q) or q in b or q in locked:
                        break
                    out.append(("move", (r, c), q))
            for dr, dc in DIAG:
                for k in (1, 2):
                    q = (r + dr * k, c + dc * k)
                    if not inb(*q):
                        break
                    if q in b:
                        if b[q][0] != team:
                            out.append(("cap", (r, c), q))
                        break
    return out


def apply(b, a):
    nb = dict(b)
    _, f, t = a
    nb[t] = nb.pop(f)
    return nb


def kernel(b, team):
    for q, (t, p) in b.items():
        if t == team and p == "K":
            return q
    return None
