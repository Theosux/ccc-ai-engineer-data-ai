"""Kernel-blunder test on real tournament positions.
Replays our match protocols; for our last K turns of each game, lets MODEL play its 2 actions under the referee
MCTS (100 sims) and counts how often the enemy can then capture our Kernel within its 2 actions.
usage (cwd env4, .venv python): ../iustin3/blunder.py K model.onnx [model2.onnx ...]"""
import sys, re, json, copy, glob
from multiprocessing import Pool
sys.path.insert(0, "."); sys.path.insert(0, "play")
import numpy as np
from pathlib import Path
from colony_one import ColonyOneEnv, mcts
from colony_one.pieces import PieceType

TL = "../iustin2/tlogs/"


def sq(s):
    return (8 - int(s[1]), ord(s[0]) - 65)


def games():
    ms = {}
    for l in open(TL + "matches.jsonl"):
        d = json.loads(l); ms[d["match_id"]] = d
    for f in glob.glob(TL + "*.json"):
        j = json.load(open(f))
        for d in (j if isinstance(j, list) else j.get("matches", [])):
            if isinstance(d, dict) and "match_id" in d:
                ms.setdefault(d["match_id"], d)
    out = []
    for d in ms.values():
        pr = d.get("protocol")
        if not pr:
            continue
        mv = [(sq(m.group(1)), sq(m.group(2))) for m in re.finditer(r"\s\d+\.\s+\w+\s+\w\w\s+([A-H]\d) -> ([A-H]\d)", pr)]
        out.append((d["match_id"], d["you"], mv))
    return out


def find(env, fr, to):
    for a in env.legal_actions():
        if a.from_pos == fr and a.to_pos == to:
            return a
    raise KeyError((fr, to))


def kernel_falls(env, team):
    """Can the side to move (not `team`) take `team`'s Kernel within its remaining actions?"""
    if env.terminated:
        return env.winner != team if hasattr(env, "winner") else False
    for a in env.legal_actions():
        e = copy.deepcopy(env); e.step(a)
        if e.terminated:
            if getattr(e, "winner", None) not in (None, team):
                return True
            continue
        if e.current_team != team:
            for b in e.legal_actions():
                f = copy.deepcopy(e); f.step(b)
                if f.terminated and getattr(f, "winner", None) not in (None, team):
                    return True
    return False


def positions(K):
    pos = []
    for mid, you, mv in games():
        env = ColonyOneEnv(seed=0); env.reset()
        starts = []
        try:
            for i, (fr, to) in enumerate(mv):
                if env.current_team == you and env.actions_left == 2:
                    starts.append(i)
                env.step(find(env, fr, to))
        except Exception:
            continue
        for s in starts[-K:]:
            pos.append((mid, you, mv[:s]))
    return pos


def one(args):
    model, (mid, you, prefix), seed = args
    from model_vs_model import SearchAgent
    env = ColonyOneEnv(seed=0); env.reset()
    for fr, to in prefix:
        env.step(find(env, fr, to))
    ag = SearchAgent(Path(model), 100, seed=seed)
    for _ in range(2):
        if env.terminated or env.current_team != you:
            break
        env.step(ag.select(env.board, env.current_team, env.actions_left, env.round_number))
    if env.terminated:
        return 0
    return int(kernel_falls(env, you))


if __name__ == "__main__":
    K = int(sys.argv[1]); P = positions(K)
    print("positions", len(P), flush=True)
    for m in sys.argv[2:]:
        with Pool(6) as p:
            r = p.map(one, [(m, x, 11) for x in P])
        print(f"{m}: kernel hangs after our turn in {sum(r)}/{len(r)}", flush=True)
