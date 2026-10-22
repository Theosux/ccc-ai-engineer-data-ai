import sys

WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}


def num(s):
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        t = s.lower().replace("-", " ").split()
        neg = 1
        if t and t[0] in ("minus", "negative"):
            neg, t = -1, t[1:]
        v = 0
        for w in t:
            v += WORDS[w] if w in WORDS else TENS[w]
        print(f"word {s!r} -> {neg * v}", file=sys.stderr)
        return neg * v


def main():
    lines = sys.stdin.read().strip().splitlines()[1:]
    rows = []
    for l in lines:
        b, t, h = l.split(",")
        rows.append((int(b), num(t), num(h)))
    rows.sort(key=lambda r: (-r[1], r[2], r[0]))
    print(" ".join(str(r[0]) for r in rows))


def check(data, out):
    ids = sorted(int(l.split(",")[0]) for l in data.strip().splitlines()[1:])
    got = sorted(int(x) for x in out.split())
    return ids == got, "ids mismatch" if ids != got else "ok"


if __name__ == "__main__":
    main()
