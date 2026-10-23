"""Cloud self-play + GPU training on Modal. Runs env4/selfplay.py's worker on hundreds of rented CPU cores.

setup (once, ~2 min):   uv venv cloud/.venv && uv pip install -p cloud/.venv modal && cloud/.venv/bin/modal setup
self-play (from level4/):
  SIMS=200 cloud/.venv/bin/modal run cloud/modal_selfplay.py::selfplay_fanout \
      --prefix gc1 --models env4/n7.onnx,env4/n6.onnx --calls 400 --games-per-call 8
  -> env4/data/gc1.partN.npz as each call finishes (same format as selfplay.py, so net.py 'data/gc1.part*.npz' works)
GPU train (uploads the npz globs, trains on an H100, writes OUT.onnx + OUT.pt locally):
  cloud/.venv/bin/modal run cloud/modal_selfplay.py::train_gpu --out env4/n9g.onnx \
      --data 'env4/data/gc1.part*.npz,env4/data/g7.part*.npz' --args '--epochs 6 --ch 96 --blocks 6 --lr 2e-3'
Always gate the result with env4/match.py / play/model_vs_model.py before upload."""
import glob, os, pathlib
import modal

ENV4 = pathlib.Path(__file__).resolve().parent.parent / "env4"

cpu_image = (modal.Image.debian_slim(python_version="3.13")
             .pip_install("numpy==2.2.6", "onnxruntime==1.22.0", "onnx==1.18.0")  # OnnxEvaluator validates via onnx
             .add_local_dir(ENV4 / "colony_one", "/root/env4/colony_one")
             .add_local_file(ENV4 / "selfplay.py", "/root/env4/selfplay.py"))
gpu_image = (modal.Image.debian_slim(python_version="3.13")
             .pip_install("numpy==2.2.6", "torch==2.7.1", "onnx==1.18.0", "onnxscript==0.3.1")
             .add_local_file(ENV4 / "net.py", "/root/env4/net.py"))
app = modal.App("ccc-colony-selfplay")


@app.function(image=cpu_image, cpu=1.0, memory=1024, timeout=3600, retries=1)
def play(models: list[bytes], seed: int, ngames: int, sims: int) -> bytes:
    import sys
    os.chdir("/root/env4"); sys.path.insert(0, "/root/env4")
    from selfplay import worker
    paths = []
    for i, b in enumerate(models):
        p = f"/tmp/m{i}.onnx"; pathlib.Path(p).write_bytes(b); paths.append(p)
    out = f"/tmp/sp{seed}.npz"
    worker((out, seed, ngames, paths, sims))
    return pathlib.Path(out).read_bytes()


@app.local_entrypoint()
def selfplay_fanout(prefix: str, models: str, calls: int = 400, games_per_call: int = 8, start: int = 0):
    sims = int(os.environ.get("SIMS", "100"))
    blobs = [pathlib.Path(m).read_bytes() for m in models.split(",")]
    outdir = ENV4 / "data"
    print(f"{calls} calls x {games_per_call} games at {sims} sims, models {models}")
    args = [(blobs, 7919 * (start + i) + 13, games_per_call, sims) for i in range(calls)]
    done = 0
    for i, res in enumerate(play.starmap(args, order_outputs=False, return_exceptions=True)):
        if isinstance(res, Exception):
            print("call failed:", res); continue
        tmp = outdir / f".{prefix}.tmp"
        tmp.write_bytes(res); os.replace(tmp, outdir / f"{prefix}.part{start + i}.npz")
        done += 1
        if done % 20 == 0:
            print(f"{done}/{calls} calls saved", flush=True)
    print(f"done: {done} files in {outdir}/{prefix}.part*.npz")


@app.function(image=gpu_image, gpu="H100", timeout=3600)
def train(files: dict[str, bytes], out: str, extra: list[str]) -> dict[str, bytes]:
    import subprocess
    os.chdir("/root/env4"); os.makedirs("data", exist_ok=True)
    for name, b in files.items():
        pathlib.Path("data", name).write_bytes(b)
    src = pathlib.Path("net.py").read_text()
    src = src.replace('"mps" if torch.backends.mps.is_available() else "cpu"', '"cuda"')
    pathlib.Path("net_gpu.py").write_text(src)
    subprocess.run(["python", "net_gpu.py", out, "data/*.npz", *extra], check=True)
    pt = out.replace(".onnx", ".pt")
    return {out: pathlib.Path(out).read_bytes(), pt: pathlib.Path(pt).read_bytes()}


@app.local_entrypoint()
def train_gpu(out: str, data: str, args: str = "--epochs 6 --ch 96 --blocks 6 --lr 2e-3"):
    files = {}
    for g in data.split(","):
        for f in sorted(glob.glob(g)):
            if ".tmp" not in f:
                files[f.replace("/", "_")] = pathlib.Path(f).read_bytes()
    print(f"uploading {len(files)} files, {sum(map(len, files.values())) / 1e6:.0f} MB")
    res = train.remote(files, pathlib.Path(out).name, args.split())
    for name, b in res.items():
        dst = pathlib.Path(out).parent / name
        dst.write_bytes(b); print("wrote", dst)
