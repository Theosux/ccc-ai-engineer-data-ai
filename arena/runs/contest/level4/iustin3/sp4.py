"""Run env4/selfplay.py's worker (Q target included) on NPROC processes with chosen part numbers.
usage (cwd env4, .venv python): [SIMS=100] [NPROC=4] ../iustin3/sp4.py data/g3h FIRST_PART games model.onnx [more.onnx ...]"""
import os, sys
os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, ".")
from multiprocessing import Pool
import selfplay

if __name__ == "__main__":
    out, first, games, models = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
    sims = int(os.environ.get("SIMS", "100")); nproc = int(os.environ.get("NPROC", "4"))
    per = (games + nproc - 1) // nproc
    with Pool(nproc) as p:
        res = p.map(selfplay.worker, [(f"{out}.part{first + i}.npz", 4242 + first + i, per, models, sims) for i in range(nproc)])
    print("cyan wins", sum(r[0] for r in res), "/", sum(r[1] for r in res), "positions", sum(r[2] for r in res))
