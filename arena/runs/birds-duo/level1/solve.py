import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import io
import pandas as pd

WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}


def num(s):
    s = str(s).strip().lower()
    try:
        return float(s)
    except ValueError:
        pass
    neg = s.startswith("minus ") or s.startswith("negative ")
    if neg:
        s = s.split(" ", 1)[1]
    v = 0
    for p in s.replace("-", " ").split():
        v += WORDS.get(p, TENS.get(p, 0))
    return -v if neg else v


def load(data):
    d = pd.read_csv(io.StringIO(data), dtype=str)
    d.columns = ["id", "t", "h"]
    d["id"] = d.id.astype(int)
    d["t"] = d.t.map(num)
    d["h"] = d.h.map(num)
    return d


def main():
    d = load(sys.stdin.read())
    d = d.sort_values(["t", "h", "id"], ascending=[False, True, True])
    print(" ".join(map(str, d.id)))


def check(data, out):
    d = load(data)
    got = out.split()
    if sorted(map(int, got)) != sorted(d.id):
        return False, "not a permutation of ids"
    return True, f"{len(got)} ids"


if __name__ == "__main__":
    main()
