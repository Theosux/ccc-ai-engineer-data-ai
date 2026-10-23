"""Cloud gate: A vs B under the referee MCTS (100 sims), sides alternated, same logic and output as env4/match.py,
spread over 8-core containers (8 games each). usage (from level4/):
  MODAL_PROFILE=iustin-epanu cloud/.venv/bin/modal run cloud/modal_gate.py::gate --a env4/n10g.onnx --b env4/n9b.onnx --n 150"""
import os, pathlib, sys
import modal

ENV4 = pathlib.Path(__file__).resolve().parent.parent / "env4"
img = (modal.Image.debian_slim(python_version="3.13")
       .pip_install("numpy==2.2.6", "onnxruntime==1.22.0", "onnx==1.18.0")
       .add_local_dir(ENV4 / "colony_one", "/root/env4/colony_one")
       .add_local_file(ENV4 / "play" / "model_vs_model.py", "/root/env4/play/model_vs_model.py"))
app = modal.App("ccc-colony-gate")


def _one(args):
    g, sims = args
    from model_vs_model import SearchAgent, play_game
    A = SearchAgent(pathlib.Path("/tmp/a.onnx"), sims, seed=7919 * g + 1)
    B = SearchAgent(pathlib.Path("/tmp/b.onnx"), sims, seed=7919 * g + 2)
    if g % 2 == 0:
        w, n = play_game(A, B)
        return w == "CYAN", "C", n
    w, n = play_game(B, A)
    return w == "MAGENTA", "M", n


@app.function(image=img, cpu=8.0, memory=8192, timeout=1200)
def games(a: bytes, b: bytes, gs: list[int], sims: int) -> list:
    from multiprocessing import Pool
    os.chdir("/root/env4"); sys.path[:0] = ["/root/env4", "/root/env4/play"]; os.environ["OMP_NUM_THREADS"] = "1"
    pathlib.Path("/tmp/a.onnx").write_bytes(a); pathlib.Path("/tmp/b.onnx").write_bytes(b)
    with Pool(8) as p:
        return p.map(_one, [(g, sims) for g in gs])


@app.local_entrypoint()
def gate(a: str, b: str, n: int = 150, sims: int = 100):
    A, B = pathlib.Path(a).read_bytes(), pathlib.Path(b).read_bytes()
    chunks = [list(range(i, min(i + 8, n))) for i in range(0, n, 8)]
    res = [r for out in games.starmap([(A, B, c, sims) for c in chunks]) for r in out]
    wc = sum(r[0] for r in res if r[1] == "C"); nc = sum(r[1] == "C" for r in res)
    wm = sum(r[0] for r in res if r[1] == "M"); nm = len(res) - nc
    avg = sum(r[2] for r in res) / max(1, len(res))
    print(f"{a} vs {b}: {wc + wm}/{len(res)}  (as CYAN {wc}/{nc}, as MAGENTA {wm}/{nm}), avg len {avg:.0f}", flush=True)
