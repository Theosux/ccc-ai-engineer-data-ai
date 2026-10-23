"""Cloud self-play with 8-core containers (8 selfplay.py workers each): more cores per container slot.
usage (from level4/): SIMS=200 cloud/.venv/bin/modal run cloud/modal_selfplay8.py::fanout8 \
    --prefix gc2 --models env4/n8b.onnx,env4/n7.onnx --calls 60 --games 4
-> env4/data/gc2.partN.npz (8 files per call), same format as selfplay.py."""
import os, pathlib
import modal

ENV4 = pathlib.Path(__file__).resolve().parent.parent / "env4"
NPROC = 8
img = (modal.Image.debian_slim(python_version="3.13")
       .pip_install("numpy==2.2.6", "onnxruntime==1.22.0", "onnx==1.18.0")
       .add_local_dir(ENV4 / "colony_one", "/root/env4/colony_one")
       .add_local_file(ENV4 / "selfplay.py", "/root/env4/selfplay.py"))
app = modal.App("ccc-colony-selfplay8")


@app.function(image=img, cpu=float(NPROC), memory=8192, timeout=3600, retries=1)
def play8(models: list[bytes], seed: int, ngames: int, sims: int) -> list[bytes]:
    import sys
    from multiprocessing import Pool
    os.chdir("/root/env4"); sys.path.insert(0, "/root/env4"); os.environ["OMP_NUM_THREADS"] = "1"
    from selfplay import worker
    paths = []
    for i, b in enumerate(models):
        p = f"/tmp/m{i}.onnx"; pathlib.Path(p).write_bytes(b); paths.append(p)
    jobs = [(f"/tmp/sp{seed}_{k}.npz", seed * 100 + k, ngames, paths, sims) for k in range(NPROC)]
    with Pool(NPROC) as pool:
        pool.map(worker, jobs)
    return [pathlib.Path(j[0]).read_bytes() for j in jobs]


@app.local_entrypoint()
def fanout8(prefix: str, models: str, calls: int = 60, games: int = 4, start: int = 0):
    sims = int(os.environ.get("SIMS", "100"))
    blobs = [pathlib.Path(m).read_bytes() for m in models.split(",")]
    outdir = ENV4 / "data"
    print(f"{calls} calls x {NPROC} procs x {games} games at {sims} sims, models {models}", flush=True)
    args = [(blobs, 104729 * (start + i) + 17, games, sims) for i in range(calls)]
    done = 0
    for i, res in enumerate(play8.starmap(args, order_outputs=False, return_exceptions=True)):
        if isinstance(res, Exception):
            print("call failed:", res, flush=True); continue
        for k, b in enumerate(res):
            tmp = outdir / f".{prefix}.tmp"
            tmp.write_bytes(b); os.replace(tmp, outdir / f"{prefix}.part{(start + i) * NPROC + k}.npz")
        done += 1
        print(f"{done}/{calls} calls saved", flush=True)
    print(f"done: {done} calls", flush=True)
