import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from collections import defaultdict
import numpy as np
from lib.ml import read_csv, clean_numeric

# Riddle level: map 6 flocks to 6 species from the story's behaviour descriptions (no ML needed).
#  Medieval Bluetit   : palindrome route (flies back the same way), the LARGER palindrome
#  Sticky Wolfthroat  : palindrome whose BOPs are a subset of the Bluetit route (waits along its segments)
#  Flanking Blackfinch: all rows identical, a loop (orbit together)
#  Rusty Goldhammer   : long shared prefix, then rows split up on the way back
#  Hurracurra Bird    : of the two remaining, the one visiting HOTTER BOPs (level-1 temps, °F fixed)
#  Red Firefinch      : the other (hub + individual excursions)
HERE = pathlib.Path(__file__).resolve().parent / "files"
HEAD = "Flock ID,Species"


def temps():
    d = clean_numeric(read_csv((HERE / "all_data_from_level_1.in").read_text(encoding="utf-8")), report=False)
    tc = np.where(d.temperature > 50, (d.temperature - 32) * 5 / 9, d.temperature)
    return dict(zip(d.bop, tc))


def classify(flocks, T):
    res, left = {}, set(flocks)
    pal = [f for f in flocks if all(r == r[::-1] for r in flocks[f])]
    if len(pal) >= 2:
        pal.sort(key=lambda f: -len({b for r in flocks[f] for b in r}))
        res[pal[0]] = "Medieval Bluetit"
        big = {b for r in flocks[pal[0]] for b in r}
        for f in pal[1:]:
            res[f] = "Sticky Wolfthroat" if {b for r in flocks[f] for b in r} <= big else "Medieval Bluetit"
    elif pal:
        res[pal[0]] = "Medieval Bluetit"
    left -= set(res)
    for f in list(left):
        rows = flocks[f]
        if len(rows) > 1 and all(r == rows[0] for r in rows):
            res[f] = "Flanking Blackfinch"
        elif len(rows) > 1:
            pre = 0
            while all(len(r) > pre and r[pre] == rows[0][pre] for r in rows):
                pre += 1
            if pre >= 3:
                res[f] = "Rusty Goldhammer"
    left -= set(res)
    heat = sorted(left, key=lambda f: -np.mean([T.get(b, 0) for r in flocks[f] for b in r[1:-1]]))
    for i, f in enumerate(heat):
        res[f] = "Hurracurra Bird" if i == 0 else "Red Firefinch"
    return res


def main():
    flocks = defaultdict(list)
    for line in sys.stdin.read().strip().splitlines()[1:]:
        fid, path = line.split(",")
        flocks[int(fid)].append(path.split())
    T = {str(k): v for k, v in temps().items()}
    for f in flocks:
        print(f"  flock {f}: {len(flocks[f])} rows, mean temp {np.mean([T.get(b, 0) for r in flocks[f] for b in r]):.1f}",
              file=sys.stderr)
    res = classify(flocks, T)
    print(HEAD)
    for f in sorted(flocks):
        print(f"{f},{res[f]}")


def check(data, out):
    lines = out.strip().splitlines()
    species = lines[1:]
    n = len({l.split(",")[0] for l in data.strip().splitlines()[1:]})
    names = [l.split(",")[1] for l in species]
    return lines[0] == HEAD and len(species) == n and len(set(names)) == n, ", ".join(names)


if __name__ == "__main__":
    main()
