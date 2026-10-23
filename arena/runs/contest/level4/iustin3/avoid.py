"""For positions where MODEL hangs its Kernel: does any safe 2-action turn exist?"""
import sys, copy
sys.path.insert(0, "."); sys.path.insert(0, "../iustin3")
from multiprocessing import Pool
import blunder as B
from colony_one import ColonyOneEnv


def check(args):
    m, x = args
    if not B.one((m, x, 11)):
        return None
    mid, you, prefix = x
    env = ColonyOneEnv(seed=0); env.reset()
    for fr, to in prefix:
        env.step(B.find(env, fr, to))
    safe = 0; total = 0
    for a in env.legal_actions():
        e = copy.deepcopy(env); e.step(a)
        for b in (e.legal_actions() if not e.terminated and e.current_team == you else [None]):
            f = copy.deepcopy(e)
            if b is not None: f.step(b)
            total += 1
            if not B.kernel_falls(f, you): safe += 1
    return (mid, you, len(prefix), safe, total)


if __name__ == "__main__":
    P = B.positions(3)
    with Pool(8) as p:
        for r in p.map(check, [(sys.argv[1], x) for x in P]):
            if r: print("hang", r)
